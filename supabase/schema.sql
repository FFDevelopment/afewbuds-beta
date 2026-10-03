-- AFewBuds account + analytics backend for Supabase/Postgres.
-- Run in Supabase SQL editor after creating the project.
create extension if not exists pgcrypto;

create table if not exists public.afb_player_accounts (
  id uuid primary key default gen_random_uuid(),
  username text not null,
  password_hash text not null,
  email text null,
  updates_opt_in boolean not null default false,
  created_at timestamptz not null default now(),
  last_login_at timestamptz null,
  last_seen_at timestamptz null,
  total_play_seconds bigint not null default 0,
  launch_count bigint not null default 0,
  constraint afb_username_format check (username ~ '^[A-Za-z0-9_]{3,20}$'),
  constraint afb_email_optin_requires_email check (not updates_opt_in or nullif(trim(email),'') is not null)
);

-- IMPORTANT: usernames are unique case-insensitively.
create unique index if not exists afb_player_username_lower_unique
  on public.afb_player_accounts (lower(username));

create table if not exists public.afb_login_sessions (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references public.afb_player_accounts(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  last_used_at timestamptz not null default now()
);

create table if not exists public.afb_play_sessions (
  id uuid primary key default gen_random_uuid(),
  account_id uuid null references public.afb_player_accounts(id) on delete set null,
  guest_device_id text null,
  build_version text null,
  started_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  play_seconds bigint not null default 0,
  ended_at timestamptz null
);

create table if not exists public.afb_admin_users (
  user_id uuid primary key references auth.users(id) on delete cascade,
  created_at timestamptz not null default now()
);

alter table public.afb_player_accounts enable row level security;
alter table public.afb_login_sessions enable row level security;
alter table public.afb_play_sessions enable row level security;
alter table public.afb_admin_users enable row level security;

-- No direct anonymous table access. The public site only uses the SECURITY DEFINER RPCs below.
revoke all on public.afb_player_accounts from anon, authenticated;
revoke all on public.afb_login_sessions from anon, authenticated;
revoke all on public.afb_play_sessions from anon, authenticated;
revoke all on public.afb_admin_users from anon, authenticated;

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
  return jsonb_build_object('session_token', v_token, 'account_id', p_account_id, 'expires_at', v_exp, 'username', v_username);
end;
$$;

create or replace function public.afb_register(
  p_username text,
  p_password text,
  p_email text default null,
  p_updates_opt_in boolean default false,
  p_remember boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_username text := trim(coalesce(p_username,''));
  v_email text := nullif(trim(coalesce(p_email,'')), '');
  v_id uuid;
begin
  if v_username !~ '^[A-Za-z0-9_]{3,20}$' then
    raise exception 'username_invalid';
  end if;
  if length(coalesce(p_password,'')) < 8 then
    raise exception 'password_too_short';
  end if;
  if p_updates_opt_in and v_email is null then
    raise exception 'email_required_for_updates';
  end if;
  if exists(select 1 from public.afb_player_accounts where lower(username)=lower(v_username)) then
    raise exception 'username_taken';
  end if;
  insert into public.afb_player_accounts(username,password_hash,email,updates_opt_in,last_login_at,last_seen_at)
  values (v_username, crypt(p_password, gen_salt('bf', 10)), v_email, coalesce(p_updates_opt_in,false), now(), now())
  returning id into v_id;
  return public.afb_make_session(v_id, coalesce(p_remember,false));
exception when unique_violation then
  raise exception 'username_taken';
end;
$$;

create or replace function public.afb_login(
  p_username text,
  p_password text,
  p_remember boolean default false
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v public.afb_player_accounts%rowtype;
begin
  select * into v from public.afb_player_accounts where lower(username)=lower(trim(coalesce(p_username,''))) limit 1;
  if v.id is null or v.password_hash <> crypt(coalesce(p_password,''), v.password_hash) then
    raise exception 'invalid_username_or_password';
  end if;
  update public.afb_player_accounts set last_login_at=now(), last_seen_at=now() where id=v.id;
  return public.afb_make_session(v.id, coalesce(p_remember,false));
end;
$$;

create or replace function public.afb_account_from_token(p_token text)
returns uuid
language sql
security definer
set search_path = public, extensions
as $$
  select s.account_id
  from public.afb_login_sessions s
  where s.token_hash = encode(digest(coalesce(p_token,''), 'sha256'),'hex')
    and s.expires_at > now()
  order by s.created_at desc
  limit 1;
$$;

create or replace function public.afb_open_session(
  p_session_token text default null,
  p_device_id text default null,
  p_build_version text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_session uuid;
begin
  insert into public.afb_play_sessions(account_id,guest_device_id,build_version)
  values (v_account, case when v_account is null then left(coalesce(p_device_id,'unknown'),128) else null end, left(coalesce(p_build_version,''),64))
  returning id into v_session;
  if v_account is not null then
    update public.afb_player_accounts set launch_count=launch_count+1,last_seen_at=now() where id=v_account;
  end if;
  return jsonb_build_object('play_session_id',v_session,'registered',v_account is not null);
end;
$$;

create or replace function public.afb_heartbeat(
  p_play_session_id uuid,
  p_session_token text default null,
  p_device_id text default null,
  p_seconds integer default 60
)
returns boolean
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_delta integer := greatest(0, least(coalesce(p_seconds,0), 180));
  v_owner uuid;
  v_guest text;
begin
  select account_id,guest_device_id into v_owner,v_guest from public.afb_play_sessions where id=p_play_session_id;
  if not found then return false; end if;
  if v_owner is not null then
    if v_account is distinct from v_owner then return false; end if;
  else
    if coalesce(v_guest,'') <> left(coalesce(p_device_id,''),128) then return false; end if;
  end if;
  update public.afb_play_sessions set play_seconds=play_seconds+v_delta,last_seen_at=now() where id=p_play_session_id;
  if v_owner is not null then
    update public.afb_player_accounts set total_play_seconds=total_play_seconds+v_delta,last_seen_at=now() where id=v_owner;
  end if;
  return true;
end;
$$;

create or replace function public.afb_end_session(
  p_play_session_id uuid,
  p_session_token text default null,
  p_device_id text default null
)
returns boolean
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_owner uuid;
  v_guest text;
begin
  select account_id,guest_device_id into v_owner,v_guest from public.afb_play_sessions where id=p_play_session_id;
  if not found then return false; end if;
  if v_owner is not null and v_account is distinct from v_owner then return false; end if;
  if v_owner is null and coalesce(v_guest,'') <> left(coalesce(p_device_id,''),128) then return false; end if;
  update public.afb_play_sessions set ended_at=coalesce(ended_at,now()),last_seen_at=now() where id=p_play_session_id;
  return true;
end;
$$;

create or replace function public.afb_is_admin()
returns boolean
language sql
security definer
set search_path = public
as $$ select exists(select 1 from public.afb_admin_users where user_id=auth.uid()); $$;

create or replace function public.afb_admin_summary()
returns table(registered_players bigint,total_opens bigint,total_play_seconds bigint,active_24h bigint,update_opt_ins bigint,guest_devices bigint)
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.afb_is_admin() then raise exception 'admin_required'; end if;
  return query select
    (select count(*) from public.afb_player_accounts),
    (select count(*) from public.afb_play_sessions),
    (select coalesce(sum(play_seconds),0) from public.afb_play_sessions),
    (select count(*) from public.afb_player_accounts where last_seen_at >= now()-interval '24 hours'),
    (select count(*) from public.afb_player_accounts where updates_opt_in=true),
    (select count(distinct guest_device_id) from public.afb_play_sessions where account_id is null and guest_device_id is not null);
end;
$$;

create or replace function public.afb_admin_players()
returns table(username text,total_play_seconds bigint,launch_count bigint,last_seen_at timestamptz,email text,updates_opt_in boolean,created_at timestamptz)
language plpgsql
security definer
set search_path = public
as $$
begin
  if not public.afb_is_admin() then raise exception 'admin_required'; end if;
  return query select a.username,a.total_play_seconds,a.launch_count,a.last_seen_at,a.email,a.updates_opt_in,a.created_at from public.afb_player_accounts a order by a.last_seen_at desc nulls last,a.created_at desc;
end;
$$;

grant execute on function public.afb_register(text,text,text,boolean,boolean) to anon, authenticated;
grant execute on function public.afb_login(text,text,boolean) to anon, authenticated;
grant execute on function public.afb_open_session(text,text,text) to anon, authenticated;
grant execute on function public.afb_heartbeat(uuid,text,text,integer) to anon, authenticated;
grant execute on function public.afb_end_session(uuid,text,text) to anon, authenticated;
grant execute on function public.afb_admin_summary() to authenticated;
grant execute on function public.afb_admin_players() to authenticated;

-- After creating your own Supabase Auth user, make yourself an admin with:
-- insert into public.afb_admin_users(user_id) values ('YOUR_AUTH_USER_UUID');

-- ---------------------------------------------------------------------------
-- AFewBuds beta.17 cloud-save/session compatibility additions.
-- Safe to run after the base schema above; objects are idempotent/replaced.
-- ---------------------------------------------------------------------------

create table if not exists public.afb_player_saves (
  account_id uuid primary key references public.afb_player_accounts(id) on delete cascade,
  save_json jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

alter table public.afb_player_saves enable row level security;
revoke all on public.afb_player_saves from anon, authenticated;

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
  return jsonb_build_object(
    'session_token', v_token,
    'account_id', p_account_id,
    'expires_at', v_exp,
    'username', v_username
  );
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
  if v_account is null then
    raise exception 'session_invalid';
  end if;
  select a.username into v_username from public.afb_player_accounts a where a.id=v_account;
  select s.expires_at into v_exp
  from public.afb_login_sessions s
  where s.account_id=v_account
    and s.token_hash=encode(digest(coalesce(p_session_token,''),'sha256'),'hex')
    and s.expires_at>now()
  order by s.created_at desc limit 1;
  update public.afb_login_sessions
     set last_used_at=now()
   where account_id=v_account
     and token_hash=encode(digest(coalesce(p_session_token,''),'sha256'),'hex');
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
  select s.save_json,s.updated_at into v_save,v_updated
    from public.afb_player_saves s where s.account_id=v_account;
  if not found then
    return jsonb_build_object('exists',false,'save_json','{}'::jsonb,'updated_at',null);
  end if;
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
as $$
begin
  return public.afb_set_save(p_session_token,p_save_json);
end;
$$;

grant execute on function public.afb_validate_session(text) to anon, authenticated;
grant execute on function public.afb_get_save(text) to anon, authenticated;
grant execute on function public.afb_set_save(text,jsonb) to anon, authenticated;
grant execute on function public.afb_replace_save(text,jsonb) to anon, authenticated;
