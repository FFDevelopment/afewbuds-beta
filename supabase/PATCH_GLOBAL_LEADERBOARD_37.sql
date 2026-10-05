-- AFewBuds cloudtest.37 global leaderboard.
-- Public output is intentionally limited to gameplay statistics only.
-- Email, password hashes, session tokens, raw saves and account-private fields are never returned.

create table if not exists public.afb_leaderboard_state (
  account_id uuid primary key references public.afb_player_accounts(id) on delete cascade,
  lifetime_revenue bigint not null default 0,
  sales bigint not null default 0,
  dealer_sales bigint not null default 0,
  harvests bigint not null default 0,
  hybrids_created bigint not null default 0,
  raids_survived bigint not null default 0,
  days_played bigint not null default 1,
  grower_level integer not null default 1,
  grower_xp bigint not null default 0,
  reputation integer not null default 0,
  customers_known integer not null default 0,
  milestones_claimed integer not null default 0,
  updated_at timestamptz not null default now()
);

create table if not exists public.afb_leaderboard_weekly (
  account_id uuid not null references public.afb_player_accounts(id) on delete cascade,
  week_start date not null,
  revenue bigint not null default 0,
  sales bigint not null default 0,
  dealer_sales bigint not null default 0,
  harvests bigint not null default 0,
  hybrids_created bigint not null default 0,
  raids_survived bigint not null default 0,
  days_played bigint not null default 0,
  updated_at timestamptz not null default now(),
  primary key (account_id, week_start)
);

create index if not exists afb_leaderboard_weekly_week_idx
  on public.afb_leaderboard_weekly(week_start);

alter table public.afb_leaderboard_state enable row level security;
alter table public.afb_leaderboard_weekly enable row level security;

revoke all on table public.afb_leaderboard_state from public, anon, authenticated;
revoke all on table public.afb_leaderboard_weekly from public, anon, authenticated;

create or replace function public.afb_leaderboard_week_start()
returns date
language sql
stable
security invoker
set search_path = public
as $$
  select
    (now() at time zone 'America/New_York')::date
    - (extract(isodow from (now() at time zone 'America/New_York'))::integer - 1);
$$;

revoke execute on function public.afb_leaderboard_week_start() from public, anon, authenticated;
grant execute on function public.afb_leaderboard_week_start() to service_role;

create or replace function public.afb_leaderboard_int(
  p_json jsonb,
  p_key text,
  p_max bigint default 1000000000000
)
returns bigint
language sql
immutable
security invoker
set search_path = public
as $$
  select greatest(
    0::bigint,
    least(
      case
        when coalesce(p_json ->> p_key, '') ~ '^-?[0-9]+$'
          then (p_json ->> p_key)::bigint
        else 0::bigint
      end,
      greatest(0::bigint, p_max)
    )
  );
$$;

create or replace function public.afb_leaderboard_nested_int(
  p_json jsonb,
  p_parent text,
  p_key text,
  p_max bigint default 1000000000000
)
returns bigint
language sql
immutable
security invoker
set search_path = public
as $$
  select greatest(
    0::bigint,
    least(
      case
        when jsonb_typeof(p_json -> p_parent) = 'object'
         and coalesce((p_json -> p_parent) ->> p_key, '') ~ '^-?[0-9]+$'
          then ((p_json -> p_parent) ->> p_key)::bigint
        else 0::bigint
      end,
      greatest(0::bigint, p_max)
    )
  );
$$;

revoke execute on function public.afb_leaderboard_int(jsonb, text, bigint) from public, anon, authenticated;
revoke execute on function public.afb_leaderboard_nested_int(jsonb, text, text, bigint) from public, anon, authenticated;
grant execute on function public.afb_leaderboard_int(jsonb, text, bigint) to service_role;
grant execute on function public.afb_leaderboard_nested_int(jsonb, text, text, bigint) to service_role;

-- Seed existing careers into lifetime ranking without pretending their historical
-- lifetime totals were earned during the current week.
insert into public.afb_leaderboard_state (
  account_id,
  lifetime_revenue,
  sales,
  dealer_sales,
  harvests,
  hybrids_created,
  raids_survived,
  days_played,
  grower_level,
  grower_xp,
  reputation,
  customers_known,
  milestones_claimed,
  updated_at
)
select
  s.account_id,
  public.afb_leaderboard_int(s.save_json, 'lifetime_revenue', 1000000000000),
  public.afb_leaderboard_nested_int(s.save_json, 'advancement_stats', 'sales', 1000000000),
  public.afb_leaderboard_nested_int(s.save_json, 'advancement_stats', 'dealer_sales', 1000000000),
  public.afb_leaderboard_nested_int(s.save_json, 'advancement_stats', 'harvests', 1000000000),
  public.afb_leaderboard_nested_int(s.save_json, 'advancement_stats', 'hybrids_created', 1000000000),
  greatest(
    public.afb_leaderboard_int(s.save_json, 'raids_survived', 100000000),
    public.afb_leaderboard_nested_int(s.save_json, 'advancement_stats', 'raids_survived', 100000000)
  ),
  greatest(1, public.afb_leaderboard_int(s.save_json, 'game_day', 1000000)),
  greatest(1, public.afb_leaderboard_int(s.save_json, 'grower_level', 100000)::integer),
  public.afb_leaderboard_int(s.save_json, 'grower_xp', 1000000000),
  public.afb_leaderboard_int(s.save_json, 'reputation', 1000000000)::integer,
  public.afb_leaderboard_nested_int(s.save_json, 'advancement_stats', 'customers_known', 1000000)::integer,
  case
    when jsonb_typeof(s.save_json -> 'advancement_claimed') = 'object' then
      (
        select count(*)::integer
        from jsonb_each(s.save_json -> 'advancement_claimed') e
        where e.value = 'true'::jsonb
      )
    else 0
  end,
  s.updated_at
from public.afb_player_saves s
on conflict (account_id) do nothing;

-- Called after a signed-in cloud save. It reads the canonical cloud save itself,
-- then converts lifetime counter deltas into the active weekly bucket.
create or replace function public.afb_leaderboard_report(p_session_token text)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_account uuid := public.afb_account_from_token(p_session_token);
  v_save jsonb;
  v_week date := public.afb_leaderboard_week_start();
  v_old public.afb_leaderboard_state%rowtype;

  v_revenue bigint := 0;
  v_sales bigint := 0;
  v_dealer_sales bigint := 0;
  v_harvests bigint := 0;
  v_hybrids bigint := 0;
  v_raids bigint := 0;
  v_days bigint := 1;
  v_grower_level integer := 1;
  v_grower_xp bigint := 0;
  v_reputation integer := 0;
  v_customers_known integer := 0;
  v_milestones integer := 0;

  d_revenue bigint := 0;
  d_sales bigint := 0;
  d_dealer_sales bigint := 0;
  d_harvests bigint := 0;
  d_hybrids bigint := 0;
  d_raids bigint := 0;
  d_days bigint := 0;
begin
  if v_account is null then
    raise exception 'session_invalid';
  end if;

  select s.save_json
    into v_save
  from public.afb_player_saves s
  where s.account_id = v_account;

  if v_save is null or jsonb_typeof(v_save) <> 'object' then
    return jsonb_build_object('ok', false, 'reason', 'save_missing');
  end if;

  v_revenue := public.afb_leaderboard_int(v_save, 'lifetime_revenue', 1000000000000);
  v_sales := public.afb_leaderboard_nested_int(v_save, 'advancement_stats', 'sales', 1000000000);
  v_dealer_sales := public.afb_leaderboard_nested_int(v_save, 'advancement_stats', 'dealer_sales', 1000000000);
  v_harvests := public.afb_leaderboard_nested_int(v_save, 'advancement_stats', 'harvests', 1000000000);
  v_hybrids := public.afb_leaderboard_nested_int(v_save, 'advancement_stats', 'hybrids_created', 1000000000);
  v_raids := greatest(
    public.afb_leaderboard_int(v_save, 'raids_survived', 100000000),
    public.afb_leaderboard_nested_int(v_save, 'advancement_stats', 'raids_survived', 100000000)
  );
  v_days := greatest(1, public.afb_leaderboard_int(v_save, 'game_day', 1000000));
  v_grower_level := greatest(1, public.afb_leaderboard_int(v_save, 'grower_level', 100000)::integer);
  v_grower_xp := public.afb_leaderboard_int(v_save, 'grower_xp', 1000000000);
  v_reputation := public.afb_leaderboard_int(v_save, 'reputation', 1000000000)::integer;
  v_customers_known := public.afb_leaderboard_nested_int(v_save, 'advancement_stats', 'customers_known', 1000000)::integer;

  if jsonb_typeof(v_save -> 'advancement_claimed') = 'object' then
    select count(*)::integer
      into v_milestones
    from jsonb_each(v_save -> 'advancement_claimed') e
    where e.value = 'true'::jsonb;
  end if;

  select *
    into v_old
  from public.afb_leaderboard_state
  where account_id = v_account
  for update;

  if not found then
    insert into public.afb_leaderboard_state (
      account_id, lifetime_revenue, sales, dealer_sales, harvests,
      hybrids_created, raids_survived, days_played, grower_level,
      grower_xp, reputation, customers_known, milestones_claimed, updated_at
    ) values (
      v_account, v_revenue, v_sales, v_dealer_sales, v_harvests,
      v_hybrids, v_raids, v_days, v_grower_level,
      v_grower_xp, v_reputation, v_customers_known, v_milestones, now()
    );
    return jsonb_build_object('ok', true, 'week_start', v_week, 'initialized', true);
  end if;

  d_revenue := greatest(v_revenue - v_old.lifetime_revenue, 0);
  d_sales := greatest(v_sales - v_old.sales, 0);
  d_dealer_sales := greatest(v_dealer_sales - v_old.dealer_sales, 0);
  d_harvests := greatest(v_harvests - v_old.harvests, 0);
  d_hybrids := greatest(v_hybrids - v_old.hybrids_created, 0);
  d_raids := greatest(v_raids - v_old.raids_survived, 0);
  d_days := greatest(v_days - v_old.days_played, 0);

  insert into public.afb_leaderboard_weekly (
    account_id, week_start, revenue, sales, dealer_sales,
    harvests, hybrids_created, raids_survived, days_played, updated_at
  ) values (
    v_account, v_week, d_revenue, d_sales, d_dealer_sales,
    d_harvests, d_hybrids, d_raids, d_days, now()
  )
  on conflict (account_id, week_start) do update
    set revenue = public.afb_leaderboard_weekly.revenue + excluded.revenue,
        sales = public.afb_leaderboard_weekly.sales + excluded.sales,
        dealer_sales = public.afb_leaderboard_weekly.dealer_sales + excluded.dealer_sales,
        harvests = public.afb_leaderboard_weekly.harvests + excluded.harvests,
        hybrids_created = public.afb_leaderboard_weekly.hybrids_created + excluded.hybrids_created,
        raids_survived = public.afb_leaderboard_weekly.raids_survived + excluded.raids_survived,
        days_played = public.afb_leaderboard_weekly.days_played + excluded.days_played,
        updated_at = now();

  update public.afb_leaderboard_state
     set lifetime_revenue = v_revenue,
         sales = v_sales,
         dealer_sales = v_dealer_sales,
         harvests = v_harvests,
         hybrids_created = v_hybrids,
         raids_survived = v_raids,
         days_played = v_days,
         grower_level = v_grower_level,
         grower_xp = v_grower_xp,
         reputation = v_reputation,
         customers_known = v_customers_known,
         milestones_claimed = v_milestones,
         updated_at = now()
   where account_id = v_account;

  return jsonb_build_object(
    'ok', true,
    'week_start', v_week,
    'delta', jsonb_build_object(
      'revenue', d_revenue,
      'sales', d_sales,
      'dealer_sales', d_dealer_sales,
      'harvests', d_harvests,
      'hybrids', d_hybrids,
      'raids', d_raids,
      'days', d_days
    )
  );
end;
$$;

revoke execute on function public.afb_leaderboard_report(text) from public;
grant execute on function public.afb_leaderboard_report(text) to anon, authenticated;

-- Public read endpoint. It returns username + one selected gameplay metric only.
create or replace function public.afb_leaderboard_get(
  p_metric text default 'revenue',
  p_range text default 'lifetime',
  p_limit integer default 5,
  p_session_token text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  v_metric text := lower(trim(coalesce(p_metric, 'revenue')));
  v_range text := lower(trim(coalesce(p_range, 'lifetime')));
  v_limit integer := least(50, greatest(1, coalesce(p_limit, 5)));
  v_account uuid := null;
  v_week date := public.afb_leaderboard_week_start();
  v_top jsonb := '[]'::jsonb;
  v_me jsonb := null;
  v_count integer := 0;
begin
  if v_metric not in ('revenue','sales','dealer_sales','harvests','hybrids','raids','days','career_score') then
    raise exception 'leaderboard_metric_invalid';
  end if;
  if v_range not in ('lifetime','weekly') then
    raise exception 'leaderboard_range_invalid';
  end if;

  if nullif(coalesce(p_session_token,''),'') is not null then
    v_account := public.afb_account_from_token(p_session_token);
  end if;

  if v_range = 'weekly' then
    with valueset as (
      select
        st.account_id,
        a.username,
        case v_metric
          when 'revenue' then coalesce(w.revenue,0)
          when 'sales' then coalesce(w.sales,0)
          when 'dealer_sales' then coalesce(w.dealer_sales,0)
          when 'harvests' then coalesce(w.harvests,0)
          when 'hybrids' then coalesce(w.hybrids_created,0)
          when 'raids' then coalesce(w.raids_survived,0)
          when 'days' then coalesce(w.days_played,0)
          when 'career_score' then
            (coalesce(w.revenue,0) / 10)
            + coalesce(w.sales,0) * 20
            + coalesce(w.dealer_sales,0) * 15
            + coalesce(w.harvests,0) * 50
            + coalesce(w.hybrids_created,0) * 100
            + coalesce(w.raids_survived,0) * 250
            + coalesce(w.days_played,0) * 25
        end::bigint as value
      from public.afb_leaderboard_state st
      join public.afb_player_accounts a on a.id = st.account_id
      left join public.afb_leaderboard_weekly w
        on w.account_id = st.account_id
       and w.week_start = v_week
    ),
    ranked as (
      select
        account_id,
        username,
        value,
        row_number() over(order by value desc, lower(username), account_id) as rank
      from valueset
      where value > 0
    )
    select
      coalesce(
        jsonb_agg(
          jsonb_build_object(
            'account_id', account_id,
            'username', username,
            'value', value,
            'rank', rank
          )
          order by rank
        ),
        '[]'::jsonb
      )
      into v_top
    from (select * from ranked order by rank limit v_limit) q;

    with valueset as (
      select
        st.account_id,
        a.username,
        case v_metric
          when 'revenue' then coalesce(w.revenue,0)
          when 'sales' then coalesce(w.sales,0)
          when 'dealer_sales' then coalesce(w.dealer_sales,0)
          when 'harvests' then coalesce(w.harvests,0)
          when 'hybrids' then coalesce(w.hybrids_created,0)
          when 'raids' then coalesce(w.raids_survived,0)
          when 'days' then coalesce(w.days_played,0)
          when 'career_score' then
            (coalesce(w.revenue,0) / 10)
            + coalesce(w.sales,0) * 20
            + coalesce(w.dealer_sales,0) * 15
            + coalesce(w.harvests,0) * 50
            + coalesce(w.hybrids_created,0) * 100
            + coalesce(w.raids_survived,0) * 250
            + coalesce(w.days_played,0) * 25
        end::bigint as value
      from public.afb_leaderboard_state st
      join public.afb_player_accounts a on a.id = st.account_id
      left join public.afb_leaderboard_weekly w
        on w.account_id = st.account_id
       and w.week_start = v_week
    ),
    ranked as (
      select
        account_id,
        username,
        value,
        row_number() over(order by value desc, lower(username), account_id) as rank
      from valueset
      where value > 0
    )
    select jsonb_build_object(
      'account_id', account_id,
      'username', username,
      'value', value,
      'rank', rank
    )
      into v_me
    from ranked
    where account_id = v_account;

    select count(*)::integer into v_count
    from public.afb_leaderboard_state;
  else
    with valueset as (
      select
        st.account_id,
        a.username,
        case v_metric
          when 'revenue' then st.lifetime_revenue
          when 'sales' then st.sales
          when 'dealer_sales' then st.dealer_sales
          when 'harvests' then st.harvests
          when 'hybrids' then st.hybrids_created
          when 'raids' then st.raids_survived
          when 'days' then greatest(st.days_played - 1, 0)
          when 'career_score' then
            (st.lifetime_revenue / 10)
            + st.sales * 20
            + st.dealer_sales * 15
            + st.harvests * 50
            + st.hybrids_created * 100
            + st.raids_survived * 250
            + greatest(st.days_played - 1, 0) * 25
        end::bigint as value
      from public.afb_leaderboard_state st
      join public.afb_player_accounts a on a.id = st.account_id
    ),
    ranked as (
      select
        account_id,
        username,
        value,
        row_number() over(order by value desc, lower(username), account_id) as rank
      from valueset
    )
    select
      coalesce(
        jsonb_agg(
          jsonb_build_object(
            'account_id', account_id,
            'username', username,
            'value', value,
            'rank', rank
          )
          order by rank
        ),
        '[]'::jsonb
      )
      into v_top
    from (select * from ranked order by rank limit v_limit) q;

    with valueset as (
      select
        st.account_id,
        a.username,
        case v_metric
          when 'revenue' then st.lifetime_revenue
          when 'sales' then st.sales
          when 'dealer_sales' then st.dealer_sales
          when 'harvests' then st.harvests
          when 'hybrids' then st.hybrids_created
          when 'raids' then st.raids_survived
          when 'days' then greatest(st.days_played - 1, 0)
          when 'career_score' then
            (st.lifetime_revenue / 10)
            + st.sales * 20
            + st.dealer_sales * 15
            + st.harvests * 50
            + st.hybrids_created * 100
            + st.raids_survived * 250
            + greatest(st.days_played - 1, 0) * 25
        end::bigint as value
      from public.afb_leaderboard_state st
      join public.afb_player_accounts a on a.id = st.account_id
    ),
    ranked as (
      select
        account_id,
        username,
        value,
        row_number() over(order by value desc, lower(username), account_id) as rank
      from valueset
    )
    select jsonb_build_object(
      'account_id', account_id,
      'username', username,
      'value', value,
      'rank', rank
    )
      into v_me
    from ranked
    where account_id = v_account;

    select count(*)::integer into v_count
    from public.afb_leaderboard_state;
  end if;

  return jsonb_build_object(
    'metric', v_metric,
    'range', v_range,
    'limit', v_limit,
    'player_count', v_count,
    'week_start', v_week,
    'week_ends_at', ((v_week + 7)::timestamp at time zone 'America/New_York'),
    'top', v_top,
    'me', v_me
  );
end;
$$;

revoke execute on function public.afb_leaderboard_get(text, text, integer, text) from public;
grant execute on function public.afb_leaderboard_get(text, text, integer, text) to anon, authenticated;

-- Public career card. Curated gameplay-only fields; never returns private account data.
create or replace function public.afb_leaderboard_profile(p_account_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  v jsonb;
begin
  select jsonb_build_object(
    'account_id', st.account_id,
    'username', a.username,
    'grower_level', st.grower_level,
    'grower_xp', st.grower_xp,
    'reputation', st.reputation,
    'lifetime_revenue', st.lifetime_revenue,
    'sales', st.sales,
    'dealer_sales', st.dealer_sales,
    'harvests', st.harvests,
    'hybrids_created', st.hybrids_created,
    'raids_survived', st.raids_survived,
    'customers_known', st.customers_known,
    'days_played', greatest(st.days_played - 1, 0),
    'milestones_claimed', st.milestones_claimed,
    'career_score',
      (st.lifetime_revenue / 10)
      + st.sales * 20
      + st.dealer_sales * 15
      + st.harvests * 50
      + st.hybrids_created * 100
      + st.raids_survived * 250
      + greatest(st.days_played - 1, 0) * 25
  )
    into v
  from public.afb_leaderboard_state st
  join public.afb_player_accounts a on a.id = st.account_id
  where st.account_id = p_account_id;

  if v is null then
    raise exception 'leaderboard_profile_missing';
  end if;

  return v;
end;
$$;

revoke execute on function public.afb_leaderboard_profile(uuid) from public;
grant execute on function public.afb_leaderboard_profile(uuid) to anon, authenticated;
