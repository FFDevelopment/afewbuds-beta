-- AFewBuds cloud career transfer patch for an EXISTING Supabase project.
-- Safe/idempotent: does not delete player accounts or existing cloud saves.
create extension if not exists pgcrypto;

create table if not exists public.afb_player_saves (
  account_id uuid primary key references public.afb_player_accounts(id) on delete cascade,
  save_json jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.afb_player_saves enable row level security;
revoke all on public.afb_player_saves from anon, authenticated;

-- Ensure browser/player sessions always include the account UUID.
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
begin
  delete from public.afb_login_sessions where expires_at < now();
  insert into public.afb_login_sessions(account_id, token_hash, expires_at)
  values (p_account_id, encode(digest(v_token, 'sha256'), 'hex'), v_exp);
  select username into v_username from public.afb_player_accounts where id = p_account_id;
  return jsonb_build_object('session_token',v_token,'account_id',p_account_id,'expires_at',v_exp,'username',v_username);
end;
$$;

create or replace function public.afb_validate_session(p_session_token text)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_username text;
  v_exp timestamptz;
begin
  if v_account is null then raise exception 'session_invalid'; end if;
  select a.username into v_username from public.afb_player_accounts a where a.id=v_account;
  select s.expires_at into v_exp from public.afb_login_sessions s
   where s.account_id=v_account
     and s.token_hash=encode(digest(coalesce(p_session_token,''),'sha256'),'hex')
     and s.expires_at>now()
   order by s.created_at desc limit 1;
  update public.afb_login_sessions set last_used_at=now()
   where account_id=v_account and token_hash=encode(digest(coalesce(p_session_token,''),'sha256'),'hex');
  update public.afb_player_accounts set last_seen_at=now() where id=v_account;
  return jsonb_build_object('account_id',v_account,'username',v_username,'expires_at',v_exp);
end;
$$;

create or replace function public.afb_get_save(p_session_token text)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_save jsonb;
  v_updated timestamptz;
begin
  if v_account is null then raise exception 'session_invalid'; end if;
  select s.save_json,s.updated_at into v_save,v_updated from public.afb_player_saves s where s.account_id=v_account;
  if not found then return jsonb_build_object('exists',false,'save_json','{}'::jsonb,'updated_at',null); end if;
  return jsonb_build_object('exists',true,'save_json',v_save,'updated_at',v_updated);
end;
$$;

create or replace function public.afb_set_save(p_session_token text, p_save_json jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_now timestamptz := now();
begin
  if v_account is null then raise exception 'session_invalid'; end if;
  if p_save_json is null or jsonb_typeof(p_save_json) <> 'object' then raise exception 'save_invalid'; end if;
  if pg_column_size(p_save_json) > 5242880 then raise exception 'save_too_large'; end if;
  insert into public.afb_player_saves(account_id,save_json,updated_at)
  values(v_account,p_save_json,v_now)
  on conflict(account_id) do update set save_json=excluded.save_json,updated_at=excluded.updated_at;
  update public.afb_player_accounts set last_seen_at=v_now where id=v_account;
  return jsonb_build_object('ok',true,'updated_at',v_now);
end;
$$;

create or replace function public.afb_replace_save(p_session_token text, p_save_json jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$ begin return public.afb_set_save(p_session_token,p_save_json); end; $$;

grant execute on function public.afb_make_session(uuid,boolean) to anon, authenticated;
grant execute on function public.afb_validate_session(text) to anon, authenticated;
grant execute on function public.afb_get_save(text) to anon, authenticated;
grant execute on function public.afb_set_save(text,jsonb) to anon, authenticated;
grant execute on function public.afb_replace_save(text,jsonb) to anon, authenticated;
