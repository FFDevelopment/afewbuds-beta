begin;
create index if not exists afb_play_sessions_last_seen_idx on public.afb_play_sessions(last_seen_at);
create or replace function public.afb_open_session(p_session_token text default null,p_device_id text default null,p_build_version text default null)
returns jsonb language plpgsql security definer set search_path=public,extensions as $$
declare v_account uuid:=public.afb_account_from_token(p_session_token); v_session uuid;
begin
 -- Recent sessions support heartbeat ownership; account totals survive cleanup.
 delete from public.afb_play_sessions where last_seen_at<now()-interval '30 days' and (ended_at is null or ended_at<now()-interval '30 days');
 insert into public.afb_play_sessions(account_id,guest_device_id,build_version)
 values(v_account,case when v_account is null then left(coalesce(p_device_id,'unknown'),128) else null end,left(coalesce(p_build_version,''),64)) returning id into v_session;
 if v_account is not null then update public.afb_player_accounts set last_seen_at=now() where id=v_account; end if;
 return jsonb_build_object('play_session_id',v_session,'registered',v_account is not null);
end $$;
create or replace function public.afb_admin_summary()
returns table(registered_players bigint,total_opens bigint,total_play_seconds bigint,active_24h bigint,update_opt_ins bigint,guest_devices bigint)
language plpgsql security definer set search_path=public as $$
begin
 if not public.afb_is_admin() then raise exception 'admin_required'; end if;
 return query select
 (select count(*) from public.afb_player_accounts),
 0::bigint,
 (select coalesce(sum(a.total_play_seconds),0)::bigint from public.afb_player_accounts a),
 (select count(*) from public.afb_player_accounts where last_seen_at>=now()-interval '24 hours'),
 (select count(*) from public.afb_player_accounts where updates_opt_in),
 (select count(distinct guest_device_id) from public.afb_play_sessions where account_id is null and last_seen_at>=now()-interval '30 days');
end $$;
-- Login sessions are deliberately untouched.
delete from public.afb_play_sessions where last_seen_at<now()-interval '30 days' and (ended_at is null or ended_at<now()-interval '30 days');
commit;
