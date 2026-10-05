-- AFewBuds cloudtest.35 account settings.
-- Additive/backward-compatible account operations. No save tables or account IDs are changed.

create or replace function public.afb_make_session(p_account_id uuid, p_remember boolean default false)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_token text := encode(gen_random_bytes(32), 'hex');
  v_exp timestamptz := now() + case when p_remember then interval '30 days' else interval '12 hours' end;
  v_username text;
  v_email text;
  v_updates_opt_in boolean;
begin
  delete from public.afb_login_sessions where expires_at < now();

  insert into public.afb_login_sessions(account_id, token_hash, expires_at)
  values (p_account_id, encode(digest(v_token, 'sha256'), 'hex'), v_exp);

  select username, email, updates_opt_in
    into v_username, v_email, v_updates_opt_in
  from public.afb_player_accounts
  where id = p_account_id;

  return jsonb_build_object(
    'session_token', v_token,
    'account_id', p_account_id,
    'expires_at', v_exp,
    'username', v_username,
    'email', v_email,
    'updates_opt_in', coalesce(v_updates_opt_in, false)
  );
end;
$$;

-- Internal helper only. Player-facing RPCs call this while running as the function owner.
revoke execute on function public.afb_make_session(uuid, boolean) from public, anon, authenticated;
grant execute on function public.afb_make_session(uuid, boolean) to service_role;

create or replace function public.afb_validate_session(p_session_token text)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_username text;
  v_email text;
  v_updates_opt_in boolean;
  v_exp timestamptz;
begin
  if v_account is null then
    raise exception 'session_invalid';
  end if;

  select a.username, a.email, a.updates_opt_in
    into v_username, v_email, v_updates_opt_in
  from public.afb_player_accounts a
  where a.id = v_account;

  select s.expires_at
    into v_exp
  from public.afb_login_sessions s
  where s.account_id = v_account
    and s.token_hash = encode(digest(coalesce(p_session_token, ''), 'sha256'), 'hex')
    and s.expires_at > now()
  order by s.created_at desc
  limit 1;

  if v_exp is null then
    raise exception 'session_invalid';
  end if;

  update public.afb_login_sessions
  set last_used_at = now()
  where account_id = v_account
    and token_hash = encode(digest(coalesce(p_session_token, ''), 'sha256'), 'hex');

  update public.afb_player_accounts
  set last_seen_at = now()
  where id = v_account;

  return jsonb_build_object(
    'account_id', v_account,
    'username', v_username,
    'email', v_email,
    'updates_opt_in', coalesce(v_updates_opt_in, false),
    'expires_at', v_exp
  );
end;
$$;

revoke execute on function public.afb_validate_session(text) from public;
grant execute on function public.afb_validate_session(text) to anon, authenticated;

create or replace function public.afb_account_get_profile(p_session_token text)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v public.afb_player_accounts%rowtype;
begin
  if v_account is null then
    raise exception 'session_invalid';
  end if;

  select * into v
  from public.afb_player_accounts
  where id = v_account;

  if v.id is null then
    raise exception 'session_invalid';
  end if;

  return jsonb_build_object(
    'account_id', v.id,
    'username', v.username,
    'email', v.email,
    'updates_opt_in', v.updates_opt_in
  );
end;
$$;

revoke execute on function public.afb_account_get_profile(text) from public;
grant execute on function public.afb_account_get_profile(text) to anon, authenticated;

create or replace function public.afb_username_available(
  p_session_token text,
  p_username text
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_username text := trim(coalesce(p_username, ''));
  v_taken boolean;
begin
  if v_account is null then
    raise exception 'session_invalid';
  end if;

  if v_username !~ '^[A-Za-z0-9_]{3,20}$' then
    raise exception 'username_invalid';
  end if;

  select exists(
    select 1
    from public.afb_player_accounts a
    where lower(a.username) = lower(v_username)
      and a.id <> v_account
  ) into v_taken;

  return jsonb_build_object('username', v_username, 'available', not v_taken);
end;
$$;

revoke execute on function public.afb_username_available(text, text) from public;
grant execute on function public.afb_username_available(text, text) to anon, authenticated;

create or replace function public.afb_account_update_profile(
  p_session_token text,
  p_current_password text,
  p_username text,
  p_email text default null,
  p_updates_opt_in boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v public.afb_player_accounts%rowtype;
  v_username text := trim(coalesce(p_username, ''));
  v_email text := nullif(trim(coalesce(p_email, '')), '');
begin
  if v_account is null then
    raise exception 'session_invalid';
  end if;

  select * into v
  from public.afb_player_accounts
  where id = v_account
  for update;

  if v.id is null then
    raise exception 'session_invalid';
  end if;

  if v.password_hash <> crypt(coalesce(p_current_password, ''), v.password_hash) then
    raise exception 'password_incorrect';
  end if;

  if v_username !~ '^[A-Za-z0-9_]{3,20}$' then
    raise exception 'username_invalid';
  end if;

  if v_email is not null
     and v_email !~* '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' then
    raise exception 'email_invalid';
  end if;

  if coalesce(p_updates_opt_in, false) and v_email is null then
    raise exception 'email_required_for_updates';
  end if;

  if exists(
    select 1
    from public.afb_player_accounts a
    where lower(a.username) = lower(v_username)
      and a.id <> v_account
  ) then
    raise exception 'username_taken';
  end if;

  update public.afb_player_accounts
  set username = v_username,
      email = v_email,
      updates_opt_in = coalesce(p_updates_opt_in, false),
      last_seen_at = now()
  where id = v_account;

  return jsonb_build_object(
    'account_id', v_account,
    'username', v_username,
    'email', v_email,
    'updates_opt_in', coalesce(p_updates_opt_in, false),
    'session_token', p_session_token
  );
exception
  when unique_violation then
    raise exception 'username_taken';
end;
$$;

revoke execute on function public.afb_account_update_profile(text, text, text, text, boolean) from public;
grant execute on function public.afb_account_update_profile(text, text, text, text, boolean) to anon, authenticated;

create or replace function public.afb_account_change_password(
  p_session_token text,
  p_current_password text,
  p_new_password text,
  p_remember boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v public.afb_player_accounts%rowtype;
begin
  if v_account is null then
    raise exception 'session_invalid';
  end if;

  select * into v
  from public.afb_player_accounts
  where id = v_account
  for update;

  if v.id is null then
    raise exception 'session_invalid';
  end if;

  if v.password_hash <> crypt(coalesce(p_current_password, ''), v.password_hash) then
    raise exception 'password_incorrect';
  end if;

  if length(coalesce(p_new_password, '')) < 8 then
    raise exception 'password_too_short';
  end if;

  update public.afb_player_accounts
  set password_hash = crypt(p_new_password, gen_salt('bf', 10)),
      last_seen_at = now()
  where id = v_account;

  -- Password changes revoke all previous tokens before issuing this device a fresh one.
  delete from public.afb_login_sessions
  where account_id = v_account;

  return public.afb_make_session(v_account, coalesce(p_remember, false));
end;
$$;

revoke execute on function public.afb_account_change_password(text, text, text, boolean) from public;
grant execute on function public.afb_account_change_password(text, text, text, boolean) to anon, authenticated;
