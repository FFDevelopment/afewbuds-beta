-- AFewBuds single-canonical-career guard.
-- Safe to run after PATCH_CLOUD_SAVE.sql.
-- Keeps exactly one afb_player_saves row per account and prevents an older
-- device save from overwriting a newer cloud career.

create or replace function public.afb_set_save(p_session_token text, p_save_json jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_now timestamptz := now();
  v_existing jsonb;
  v_existing_unix numeric := 0;
  v_incoming_unix numeric := 0;
  v_incoming_text text;
  v_existing_text text;
begin
  if v_account is null then raise exception 'session_invalid'; end if;
  if p_save_json is null or jsonb_typeof(p_save_json) <> 'object' then raise exception 'save_invalid'; end if;
  if pg_column_size(p_save_json) > 5242880 then raise exception 'save_too_large'; end if;

  v_incoming_text := coalesce(p_save_json->>'saved_unix','');
  if v_incoming_text ~ '^[0-9]+([.][0-9]+)?$' then
    v_incoming_unix := v_incoming_text::numeric;
  end if;

  select s.save_json
    into v_existing
    from public.afb_player_saves s
   where s.account_id = v_account
   for update;

  if found then
    v_existing_text := coalesce(v_existing->>'saved_unix','');
    if v_existing_text ~ '^[0-9]+([.][0-9]+)?$' then
      v_existing_unix := v_existing_text::numeric;
    end if;

    -- Existing cloud career is newer: never let this device roll the account back.
    if v_existing_unix > 0
       and (v_incoming_unix = 0 or v_existing_unix > v_incoming_unix) then
      return jsonb_build_object(
        'ok', false,
        'reason', 'cloud_newer',
        'cloud_saved_unix', v_existing_unix,
        'updated_at', (select updated_at from public.afb_player_saves where account_id=v_account)
      );
    end if;
  end if;

  insert into public.afb_player_saves(account_id,save_json,updated_at)
  values(v_account,p_save_json,v_now)
  on conflict(account_id) do update
    set save_json=excluded.save_json,
        updated_at=excluded.updated_at;

  update public.afb_player_accounts
     set last_seen_at=v_now
   where id=v_account;

  return jsonb_build_object(
    'ok', true,
    'saved_unix', v_incoming_unix,
    'updated_at', v_now
  );
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

grant execute on function public.afb_set_save(text,jsonb) to anon, authenticated;
grant execute on function public.afb_replace_save(text,jsonb) to anon, authenticated;
