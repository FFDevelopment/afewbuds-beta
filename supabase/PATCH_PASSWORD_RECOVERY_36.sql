-- AFewBuds cloudtest.36 forgotten-password recovery.
-- Additive only: does not alter account IDs or cloud-save rows.

create table if not exists public.afb_password_reset_tokens (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references public.afb_player_accounts(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  used_at timestamptz null,
  created_at timestamptz not null default now()
);

create index if not exists afb_password_reset_tokens_account_created_idx
  on public.afb_password_reset_tokens(account_id, created_at desc);

alter table public.afb_password_reset_tokens enable row level security;
revoke all on table public.afb_password_reset_tokens from public, anon, authenticated;

-- Service-only helper: generates a single-use token for an account username.
-- The caller always presents a generic response to avoid account enumeration.
create or replace function public.afb_password_reset_issue(p_username text)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_username text := trim(coalesce(p_username, ''));
  v_account uuid;
  v_account_username text;
  v_email text;
  v_recent integer := 0;
  v_token text;
  v_exp timestamptz;
begin
  delete from public.afb_password_reset_tokens
   where expires_at < now() - interval '7 days'
      or (used_at is not null and used_at < now() - interval '7 days');

  if v_username !~ '^[A-Za-z0-9_]{3,20}$' then
    return jsonb_build_object('deliver', false);
  end if;

  select a.id, a.username, nullif(trim(a.email), '')
    into v_account, v_account_username, v_email
  from public.afb_player_accounts a
  where lower(a.username) = lower(v_username)
  limit 1;

  if v_account is null or v_email is null then
    return jsonb_build_object('deliver', false);
  end if;

  select count(*)::integer
    into v_recent
  from public.afb_password_reset_tokens r
  where r.account_id = v_account
    and r.created_at > now() - interval '15 minutes';

  if v_recent >= 3 then
    return jsonb_build_object('deliver', false, 'rate_limited', true);
  end if;

  -- Only the newest link remains valid.
  update public.afb_password_reset_tokens
     set used_at = now()
   where account_id = v_account
     and used_at is null
     and expires_at > now();

  v_token := encode(gen_random_bytes(32), 'hex');
  v_exp := now() + interval '30 minutes';

  insert into public.afb_password_reset_tokens(account_id, token_hash, expires_at)
  values (
    v_account,
    encode(digest(v_token, 'sha256'), 'hex'),
    v_exp
  );

  return jsonb_build_object(
    'deliver', true,
    'username', v_account_username,
    'email', v_email,
    'reset_token', v_token,
    'expires_at', v_exp
  );
end;
$$;

revoke execute on function public.afb_password_reset_issue(text) from public, anon, authenticated;
grant execute on function public.afb_password_reset_issue(text) to service_role;

-- Service-only helper for the Edge Function. Brevo credentials are read from Supabase Vault.
create or replace function public.afb_password_reset_brevo_config()
returns jsonb
language plpgsql
security definer
set search_path = public, vault
as $$
declare
  v_api_key text;
  v_from text;
begin
  select decrypted_secret
    into v_api_key
  from vault.decrypted_secrets
  where name = 'afb_brevo_api_key'
  order by created_at desc
  limit 1;

  select decrypted_secret
    into v_from
  from vault.decrypted_secrets
  where name = 'afb_brevo_from'
  order by created_at desc
  limit 1;

  return jsonb_build_object(
    'configured', nullif(v_api_key, '') is not null and nullif(v_from, '') is not null,
    'api_key', v_api_key,
    'from_address', v_from
  );
end;
$$;

revoke execute on function public.afb_password_reset_brevo_config() from public, anon, authenticated;
grant execute on function public.afb_password_reset_brevo_config() to service_role;

-- Public completion endpoint. Possession of the high-entropy single-use token
-- authorizes the reset; successful resets revoke all previous login sessions.
create or replace function public.afb_password_reset_complete(
  p_reset_token text,
  p_new_password text,
  p_remember boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_hash text;
  v_reset_id uuid;
  v_account uuid;
begin
  if coalesce(p_reset_token, '') !~ '^[0-9a-fA-F]{64}$' then
    raise exception 'reset_token_invalid';
  end if;

  if length(coalesce(p_new_password, '')) < 8 then
    raise exception 'password_too_short';
  end if;

  if length(p_new_password) > 128 then
    raise exception 'password_too_long';
  end if;

  v_hash := encode(digest(p_reset_token, 'sha256'), 'hex');

  select r.id, r.account_id
    into v_reset_id, v_account
  from public.afb_password_reset_tokens r
  where r.token_hash = v_hash
    and r.used_at is null
    and r.expires_at > now()
  limit 1
  for update;

  if v_reset_id is null or v_account is null then
    raise exception 'reset_token_invalid';
  end if;

  update public.afb_player_accounts
     set password_hash = crypt(p_new_password, gen_salt('bf', 10)),
         last_seen_at = now()
   where id = v_account;

  update public.afb_password_reset_tokens
     set used_at = now()
   where account_id = v_account
     and used_at is null;

  delete from public.afb_login_sessions
   where account_id = v_account;

  return public.afb_make_session(v_account, coalesce(p_remember, false));
end;
$$;

revoke execute on function public.afb_password_reset_complete(text, text, boolean) from public;
grant execute on function public.afb_password_reset_complete(text, text, boolean) to anon, authenticated;
