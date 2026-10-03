-- AFewBuds account hotfix for an existing Supabase project.
-- Safe to run in Supabase SQL Editor. It does not delete player accounts.
create extension if not exists pgcrypto;

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

grant execute on function public.afb_make_session(uuid,boolean) to anon, authenticated;
