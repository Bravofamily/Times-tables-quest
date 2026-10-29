-- =====================================================================
-- NumiRealm Parent Area: PHASE 1 (TEST) database setup
-- Paste all of this into Supabase > SQL Editor > New query > Run.
-- Safe to run again (idempotent). Does not touch auth.users data.
-- Minimal kid data only: nickname, age range, grade, progress summary.
-- =====================================================================

-- ---------- Tables ----------------------------------------------------

create table if not exists public.parents (
  id          uuid primary key references auth.users(id) on delete cascade,
  created_at  timestamptz not null default now()
);

-- Consent placeholder (NOT legal advice; lawyer review needed before real use)
create table if not exists public.parent_consent (
  id               bigint generated always as identity primary key,
  parent_id        uuid not null references public.parents(id) on delete cascade,
  consent_version  text not null check (char_length(consent_version) between 1 and 20),
  consent_text     text not null check (char_length(consent_text) between 1 and 2000),
  agreed_at        timestamptz not null default now()
);
create index if not exists parent_consent_parent_idx on public.parent_consent(parent_id);

create table if not exists public.kids (
  id          uuid primary key default gen_random_uuid(),
  parent_id   uuid not null references public.parents(id) on delete cascade,
  nickname    text not null check (char_length(btrim(nickname)) between 1 and 20),
  age_range   text not null check (age_range in ('4-5','6-7','8-10','11-14')),
  grade       text not null check (grade in ('PreK','K','1','2','3','4','5','6','7','8')),
  created_at  timestamptz not null default now()
);
create index if not exists kids_parent_idx on public.kids(parent_id);

create table if not exists public.devices (
  id            uuid primary key default gen_random_uuid(),
  parent_id     uuid not null references public.parents(id) on delete cascade,
  kid_id        uuid not null references public.kids(id) on delete cascade,
  device_name   text not null check (char_length(device_name) between 1 and 40),
  token_hash    text not null unique,          -- sha256 of the device token; the token itself is never stored
  created_at    timestamptz not null default now(),
  last_seen_at  timestamptz,
  revoked_at    timestamptz
);
create index if not exists devices_parent_idx on public.devices(parent_id);
create index if not exists devices_kid_idx on public.devices(kid_id);

create table if not exists public.link_codes (
  code        text primary key check (code ~ '^[A-Z0-9]{6}$'),
  parent_id   uuid not null references public.parents(id) on delete cascade,
  kid_id      uuid not null references public.kids(id) on delete cascade,
  created_at  timestamptz not null default now(),
  expires_at  timestamptz not null default now() + interval '10 minutes',
  used_at     timestamptz,
  device_id   uuid references public.devices(id) on delete set null
);
create index if not exists link_codes_parent_idx on public.link_codes(parent_id);

-- Brute-force protection for redeem_link_code (no policies: not readable by anyone via the API)
create table if not exists public.redeem_attempts (
  id            bigint generated always as identity primary key,
  client_key    text not null,
  ok            boolean not null,
  attempted_at  timestamptz not null default now()
);
create index if not exists redeem_attempts_key_idx on public.redeem_attempts(client_key, attempted_at);
create index if not exists redeem_attempts_time_idx on public.redeem_attempts(attempted_at);

-- One summary row per kid
create table if not exists public.progress (
  kid_id            uuid primary key references public.kids(id) on delete cascade,
  parent_id         uuid not null references public.parents(id) on delete cascade,
  hero              text check (hero is null or hero ~ '^[a-z]{2,12}$'),
  realms            jsonb not null default '{}'::jsonb,  -- {add:{chapters,total,stars,max}, ...}
  skills            jsonb not null default '{}'::jsonb,  -- {"mult:x7":{n,r,t,l}, ...}
  time_played_sec   integer not null default 0 check (time_played_sec >= 0),
  lanterns_used     integer not null default 0 check (lanterns_used >= 0),
  examples_opened   integer not null default 0 check (examples_opened >= 0),
  client_updated_at timestamptz,
  updated_at        timestamptz not null default now()
);

-- Small daily snapshot for trend graphs (1 row per kid per day, kept 400 days)
create table if not exists public.progress_events (
  kid_id        uuid not null references public.kids(id) on delete cascade,
  parent_id     uuid not null references public.parents(id) on delete cascade,
  day           date not null,
  stars_total   integer not null default 0,
  answers_right integer not null default 0,
  answers_total integer not null default 0,
  minutes       integer not null default 0,
  primary key (kid_id, day)
);
-- v28: optional per-day play-time log (see setup-part4.sql)
alter table public.progress add column if not exists play jsonb;
create index if not exists progress_events_parent_idx on public.progress_events(parent_id);

-- ---------- Max 2 kids per parent (enforced in the DB) ----------------

create or replace function public.enforce_kid_limit() returns trigger
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  -- lock the parent row so two inserts at once cannot both pass
  perform 1 from public.parents where id = new.parent_id for update;
  if (select count(*) from public.kids where parent_id = new.parent_id) >= 2 then
    raise exception 'kid_limit: a parent account can have at most 2 kids' using errcode = 'P0001';
  end if;
  return new;
end $$;
drop trigger if exists kids_limit on public.kids;
create trigger kids_limit before insert on public.kids
  for each row execute function public.enforce_kid_limit();

-- kids cannot be moved to another parent
create or replace function public.kids_keep_parent() returns trigger
language plpgsql set search_path = public, pg_temp as $$
begin
  if new.parent_id <> old.parent_id then raise exception 'parent_id cannot change'; end if;
  return new;
end $$;
drop trigger if exists kids_keep_parent on public.kids;
create trigger kids_keep_parent before update on public.kids
  for each row execute function public.kids_keep_parent();

-- ---------- Row Level Security ----------------------------------------

alter table public.parents         enable row level security;
alter table public.parent_consent  enable row level security;
alter table public.kids            enable row level security;
alter table public.devices         enable row level security;
alter table public.link_codes      enable row level security;
alter table public.redeem_attempts enable row level security;
alter table public.progress        enable row level security;
alter table public.progress_events enable row level security;

drop policy if exists parents_select on public.parents;
create policy parents_select on public.parents for select to authenticated using (id = (select auth.uid()));
drop policy if exists parents_insert on public.parents;
create policy parents_insert on public.parents for insert to authenticated with check (id = (select auth.uid()));

drop policy if exists consent_select on public.parent_consent;
create policy consent_select on public.parent_consent for select to authenticated using (parent_id = (select auth.uid()));
drop policy if exists consent_insert on public.parent_consent;
create policy consent_insert on public.parent_consent for insert to authenticated with check (parent_id = (select auth.uid()));

-- kids: only after consent is recorded
drop policy if exists kids_select on public.kids;
create policy kids_select on public.kids for select to authenticated using (parent_id = (select auth.uid()));
drop policy if exists kids_insert on public.kids;
create policy kids_insert on public.kids for insert to authenticated with check (
  parent_id = (select auth.uid())
  and exists (select 1 from public.parent_consent c where c.parent_id = (select auth.uid())));
drop policy if exists kids_update on public.kids;
create policy kids_update on public.kids for update to authenticated
  using (parent_id = (select auth.uid())) with check (parent_id = (select auth.uid()));
drop policy if exists kids_delete on public.kids;
create policy kids_delete on public.kids for delete to authenticated using (parent_id = (select auth.uid()));

drop policy if exists devices_select on public.devices;
create policy devices_select on public.devices for select to authenticated using (parent_id = (select auth.uid()));
drop policy if exists link_codes_select on public.link_codes;
create policy link_codes_select on public.link_codes for select to authenticated using (parent_id = (select auth.uid()));
drop policy if exists progress_select on public.progress;
create policy progress_select on public.progress for select to authenticated using (parent_id = (select auth.uid()));
drop policy if exists events_select on public.progress_events;
create policy events_select on public.progress_events for select to authenticated using (parent_id = (select auth.uid()));
-- redeem_attempts: intentionally no policies (deny all)

-- ---------- Explicit grants ("auto-expose new tables" is OFF) ---------

revoke all on public.parents, public.parent_consent, public.kids, public.devices, public.link_codes,
              public.redeem_attempts, public.progress, public.progress_events from anon, authenticated;
grant select, insert            on public.parents         to authenticated;
grant select, insert            on public.parent_consent  to authenticated;
grant select, insert, delete    on public.kids            to authenticated;
grant update (nickname, age_range, grade) on public.kids  to authenticated;
grant select                    on public.devices         to authenticated;
grant select                    on public.link_codes      to authenticated;
grant select                    on public.progress        to authenticated;
grant select                    on public.progress_events to authenticated;
-- anon gets NO table access; the kid device only uses the RPCs below.

-- ---------- Helpers ---------------------------------------------------

create or replace function public.nr_hash(p text) returns text
language sql immutable set search_path = public, pg_temp as $$
  select encode(sha256(convert_to(p, 'UTF8')), 'hex') $$;

create or replace function public.nr_client_key() returns text
language plpgsql stable set search_path = public, pg_temp as $$
declare h json; ip text;
begin
  begin h := nullif(current_setting('request.headers', true), '')::json;
  exception when others then h := null; end;
  ip := coalesce(h->>'cf-connecting-ip', split_part(coalesce(h->>'x-forwarded-for',''), ',', 1), h->>'x-real-ip');
  return coalesce(nullif(btrim(ip), ''), 'unknown');
end $$;

-- ---------- RPC: parent makes a 10-minute, one-time link code ---------

create or replace function public.create_link_code(p_kid_id uuid)
returns table (code text, expires_at timestamptz)
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  uid uuid := auth.uid();
  alphabet constant text := 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';  -- 32 chars, no I/O/0/1
  c text; b bytea; i int; tries int := 0;
begin
  if uid is null then raise exception 'not_signed_in' using errcode = '28000'; end if;
  if not exists (select 1 from public.kids k where k.id = p_kid_id and k.parent_id = uid) then
    raise exception 'kid_not_found' using errcode = 'P0002'; end if;
  delete from public.link_codes l where l.parent_id = uid and (l.expires_at < now() - interval '1 day');
  if (select count(*) from public.link_codes l where l.parent_id = uid and l.used_at is null and l.expires_at > now()) >= 5 then
    raise exception 'too_many_codes: wait for a code to expire' using errcode = 'P0001'; end if;
  loop
    tries := tries + 1;
    b := uuid_send(gen_random_uuid());
    c := '';
    for i in 0..5 loop c := c || substr(alphabet, (get_byte(b, i) % 32) + 1, 1); end loop;
    begin
      insert into public.link_codes(code, parent_id, kid_id) values (c, uid, p_kid_id);
      exit;
    exception when unique_violation then
      if tries > 8 then raise; end if;
    end;
  end loop;
  return query select l.code, l.expires_at from public.link_codes l where l.code = c;
end $$;

-- ---------- RPC: kid device redeems a code (anon) ---------------------
-- Returns json. Errors are returned (not raised) so failed attempts are recorded.

create or replace function public.redeem_link_code(p_code text, p_device_name text)
returns json
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  k text := public.nr_client_key();
  c text := upper(regexp_replace(coalesce(p_code, ''), '[^A-Za-z0-9]', '', 'g'));
  dn text := left(btrim(regexp_replace(coalesce(p_device_name, ''), '[[:cntrl:]<>]', '', 'g')), 40);
  lc public.link_codes%rowtype;
  tok text; dev uuid; nick text;
begin
  delete from public.redeem_attempts where attempted_at < now() - interval '1 day';
  if (select count(*) from public.redeem_attempts a where a.client_key = k and not a.ok
        and a.attempted_at > now() - interval '15 minutes') >= 10
     or (select count(*) from public.redeem_attempts a where not a.ok
        and a.attempted_at > now() - interval '1 minute') >= 300 then
    return json_build_object('ok', false, 'error', 'rate_limited');
  end if;
  if dn = '' then dn := 'Kid device'; end if;

  select * into lc from public.link_codes l
   where l.code = c and l.used_at is null and l.expires_at > now() for update;
  if not found then
    insert into public.redeem_attempts(client_key, ok) values (k, false);
    return json_build_object('ok', false, 'error', 'invalid_or_expired');
  end if;
  if (select count(*) from public.devices d where d.kid_id = lc.kid_id and d.revoked_at is null) >= 5 then
    return json_build_object('ok', false, 'error', 'too_many_devices');
  end if;

  tok := replace(gen_random_uuid()::text || gen_random_uuid()::text || gen_random_uuid()::text, '-', '');  -- 96 hex chars
  insert into public.devices(parent_id, kid_id, device_name, token_hash)
    values (lc.parent_id, lc.kid_id, dn, public.nr_hash(tok)) returning id into dev;
  update public.link_codes set used_at = now(), device_id = dev where code = lc.code;
  insert into public.redeem_attempts(client_key, ok) values (k, true);
  select nickname into nick from public.kids where id = lc.kid_id;
  return json_build_object('ok', true, 'device_token', tok, 'device_id', dev, 'kid_id', lc.kid_id, 'nickname', nick);
end $$;

-- ---------- RPC: kid device pushes its progress summary (anon) --------

create or replace function public.push_progress(p_device_token text, p_payload jsonb)
returns json
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  d public.devices%rowtype;
  realms jsonb := '{}'::jsonb; skills jsonb := '{}'::jsonb;
  r record; n int := 0; v jsonb;
  st int := 0; rt int := 0; tt int := 0; secs int;
  hero text;
  cl timestamptz;
  pl jsonb := null; pd jsonb := '[]'::jsonb; pm jsonb := '{}'::jsonb; pe date;
begin
  if p_device_token is null or char_length(p_device_token) <> 96 then
    return json_build_object('ok', false, 'error', 'unlinked'); end if;
  select * into d from public.devices where token_hash = public.nr_hash(p_device_token);
  if not found or d.revoked_at is not null then
    return json_build_object('ok', false, 'error', 'unlinked'); end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' or octet_length(p_payload::text) > 20000 then
    return json_build_object('ok', false, 'error', 'bad_payload'); end if;

  -- realms: only the six known realm ids, small non-negative integers
  for r in select * from jsonb_each(coalesce(p_payload->'realms', '{}'::jsonb)) loop
    if r.key in ('add','sub','mult','div','frac','mix') and jsonb_typeof(r.value) = 'object' then
      v := jsonb_build_object(
        'chapters', least(greatest(coalesce((r.value->>'chapters')::numeric, 0), 0), 100)::int,
        'total',    least(greatest(coalesce((r.value->>'total')::numeric, 0), 0), 100)::int,
        'stars',    least(greatest(coalesce((r.value->>'stars')::numeric, 0), 0), 300)::int,
        'max',      least(greatest(coalesce((r.value->>'max')::numeric, 0), 0), 300)::int);
      realms := realms || jsonb_build_object(r.key, v);
      st := st + (v->>'stars')::int;
    end if;
  end loop;

  -- skills: up to 80 entries, key like "mult:x7" or "frac:c3"
  for r in select * from jsonb_each(coalesce(p_payload->'skills', '{}'::jsonb)) loop
    exit when n >= 80;
    if r.key ~ '^[a-z]{2,5}:[a-z0-9]{1,6}$' and jsonb_typeof(r.value) = 'object' then
      v := jsonb_build_object(
        'n', left(coalesce(r.value->>'n', r.key), 40),
        'r', least(greatest(coalesce((r.value->>'r')::numeric, 0), 0), 1000000)::int,
        't', least(greatest(coalesce((r.value->>'t')::numeric, 0), 0), 1000000)::int,
        'l', least(greatest(coalesce((r.value->>'l')::numeric, 0), 0), 1000000)::int);
      if (v->>'r')::int > (v->>'t')::int then v := jsonb_set(v, '{r}', v->'t'); end if;
      skills := skills || jsonb_build_object(r.key, v);
      rt := rt + (v->>'r')::int; tt := tt + (v->>'t')::int; n := n + 1;
    end if;
  end loop;

  secs := least(greatest(coalesce((p_payload->>'time_played_sec')::numeric, 0), 0), 100000000)::int;
  hero := case when coalesce(p_payload->>'hero','') ~ '^[a-z]{2,12}$' then p_payload->>'hero' end;
  begin cl := (p_payload->>'client_at')::timestamptz; exception when others then cl := null; end;

  -- v28 play-time log (optional): minutes per local day, oldest first, ending on 'end'; older months rolled up
  if jsonb_typeof(p_payload->'play') = 'object' then
    begin pe := (p_payload->'play'->>'end')::date; exception when others then pe := null; end;
    if pe is not null and pe between current_date - 2 and current_date + 2 then
      if jsonb_typeof(p_payload->'play'->'days') = 'array' then
        select coalesce(jsonb_agg(least(greatest(case when jsonb_typeof(x) = 'number' then x::text::numeric else 0 end, 0), 1440)::int order by o), '[]'::jsonb)
          into pd from (select x, o from jsonb_array_elements(p_payload->'play'->'days') with ordinality as t(x, o)
                        order by o desc limit 400) z;
      end if;
      if jsonb_typeof(p_payload->'play'->'months') = 'object' then
        select coalesce(jsonb_object_agg(k, least(greatest(case when jsonb_typeof(x) = 'number' then x::text::numeric else 0 end, 0), 44640)::int), '{}'::jsonb)
          into pm from (select key k, value x from jsonb_each(p_payload->'play'->'months')
                        where key ~ '^[0-9]{4}-[0-9]{2}$' order by key desc limit 130) z;
      end if;
      pl := jsonb_build_object('v', 1, 'end', pe::text, 'days', pd, 'months', pm);
    end if;
  end if;

  insert into public.progress as p (kid_id, parent_id, hero, realms, skills, time_played_sec,
         lanterns_used, examples_opened, play, client_updated_at, updated_at)
  values (d.kid_id, d.parent_id, hero, realms, skills, secs,
         least(greatest(coalesce((p_payload->>'lanterns_used')::numeric, 0), 0), 1000000)::int,
         least(greatest(coalesce((p_payload->>'examples_opened')::numeric, 0), 0), 1000000)::int,
         pl, cl, now())
  on conflict (kid_id) do update set
         hero = excluded.hero, realms = excluded.realms, skills = excluded.skills,
         time_played_sec = excluded.time_played_sec, lanterns_used = excluded.lanterns_used,
         examples_opened = excluded.examples_opened, play = coalesce(excluded.play, p.play), client_updated_at = excluded.client_updated_at,
         updated_at = now();

  insert into public.progress_events as e (kid_id, parent_id, day, stars_total, answers_right, answers_total, minutes)
  values (d.kid_id, d.parent_id, (now() at time zone 'utc')::date, st, rt, tt, secs / 60)
  on conflict (kid_id, day) do update set stars_total = excluded.stars_total,
         answers_right = excluded.answers_right, answers_total = excluded.answers_total, minutes = excluded.minutes;
  delete from public.progress_events where kid_id = d.kid_id and day < (now() at time zone 'utc')::date - 400;

  update public.devices set last_seen_at = now() where id = d.id;
  return json_build_object('ok', true);
exception when invalid_text_representation or numeric_value_out_of_range then
  return json_build_object('ok', false, 'error', 'bad_payload');
end $$;

-- ---------- RPC: unlink ------------------------------------------------

-- parent removes a device from the dashboard
create or replace function public.unlink_device(p_device_id uuid)
returns json
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  if auth.uid() is null then raise exception 'not_signed_in' using errcode = '28000'; end if;
  update public.devices set revoked_at = coalesce(revoked_at, now())
   where id = p_device_id and parent_id = auth.uid();
  if not found then return json_build_object('ok', false, 'error', 'not_found'); end if;
  return json_build_object('ok', true);
end $$;

-- the kid device unlinks itself (gated Settings), proving it holds the token
create or replace function public.unlink_this_device(p_device_token text)
returns json
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  update public.devices set revoked_at = coalesce(revoked_at, now())
   where token_hash = public.nr_hash(coalesce(p_device_token, '')) and revoked_at is null;
  return json_build_object('ok', true);
end $$;

-- ---------- Function privileges ---------------------------------------

revoke all on function public.enforce_kid_limit()               from public, anon, authenticated;
revoke all on function public.kids_keep_parent()                from public, anon, authenticated;
revoke all on function public.nr_hash(text)                     from public, anon, authenticated;
revoke all on function public.nr_client_key()                   from public, anon, authenticated;
revoke all on function public.create_link_code(uuid)            from public, anon, authenticated;
revoke all on function public.redeem_link_code(text, text)      from public, anon, authenticated;
revoke all on function public.push_progress(text, jsonb)        from public, anon, authenticated;
revoke all on function public.unlink_device(uuid)               from public, anon, authenticated;
revoke all on function public.unlink_this_device(text)          from public, anon, authenticated;

grant execute on function public.create_link_code(uuid)         to authenticated;
grant execute on function public.unlink_device(uuid)            to authenticated;
grant execute on function public.redeem_link_code(text, text)   to anon;
grant execute on function public.push_progress(text, jsonb)     to anon;
grant execute on function public.unlink_this_device(text)       to anon;

-- tell the API to reload its schema cache
-- =====================================================================
-- v28 Parent Center: quests from home, fix-it plans, rewards, alerts
-- preferences and family challenges. Parents only see their own rows
-- (row level security). Kid devices only use the token-checked RPCs
-- get_home and quest_progress. No new personal data about kids.
-- =====================================================================

create table if not exists public.quests (
  id           uuid primary key default gen_random_uuid(),
  parent_id    uuid not null references public.parents(id) on delete cascade,
  kid_id       uuid not null references public.kids(id) on delete cascade,
  skill        text not null check (skill ~ '^[a-z]{2,5}:(x[0-9]{1,2}|c[0-9]{1,2})$'),
  title        text not null check (char_length(btrim(title)) between 1 and 60),
  message      text not null default '' check (char_length(message) <= 120),
  goal         integer not null default 10 check (goal between 3 and 30),
  source       text not null default 'parent' check (source in ('parent','suggested','fixit')),
  plan_id      uuid,
  status       text not null default 'active' check (status in ('active','done','cancelled')),
  right_count  integer not null default 0 check (right_count >= 0),
  total_count  integer not null default 0 check (total_count >= 0),
  created_at   timestamptz not null default now(),
  done_at      timestamptz
);
create index if not exists quests_kid_idx on public.quests(kid_id, status);
create index if not exists quests_parent_idx on public.quests(parent_id);

create table if not exists public.fixit_plans (
  id          uuid primary key default gen_random_uuid(),
  parent_id   uuid not null references public.parents(id) on delete cascade,
  kid_id      uuid not null references public.kids(id) on delete cascade,
  plan_key    text not null check (plan_key ~ '^[a-z0-9_]{2,24}$'),
  day_done    integer not null default 0 check (day_done between 0 and 5),
  before_acc  integer check (before_acc between 0 and 100),
  after_acc   integer check (after_acc between 0 and 100),
  status      text not null default 'active' check (status in ('active','done','stopped')),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists fixit_kid_idx on public.fixit_plans(kid_id);
create index if not exists fixit_parent_idx on public.fixit_plans(parent_id);

create table if not exists public.rewards (
  id           uuid primary key default gen_random_uuid(),
  parent_id    uuid not null references public.parents(id) on delete cascade,
  kid_id       uuid not null references public.kids(id) on delete cascade,
  title        text not null check (char_length(btrim(title)) between 1 and 60),
  goal_type    text not null check (goal_type in ('stars','minutes','quests')),
  goal         integer not null check (goal between 1 and 10000),
  start_value  integer not null default 0 check (start_value >= 0),
  status       text not null default 'active' check (status in ('active','earned','given','cancelled')),
  created_at   timestamptz not null default now(),
  earned_at    timestamptz
);
create index if not exists rewards_kid_idx on public.rewards(kid_id);
create index if not exists rewards_parent_idx on public.rewards(parent_id);

create table if not exists public.notify_prefs (
  parent_id     uuid primary key references public.parents(id) on delete cascade,
  events        jsonb not null default '{}'::jsonb check (jsonb_typeof(events) = 'object' and octet_length(events::text) <= 1000),
  quiet_start   smallint not null default 20 check (quiet_start between 0 and 23),
  quiet_end     smallint not null default 7 check (quiet_end between 0 and 23),
  idle_days     smallint not null default 3 check (idle_days between 1 and 30),
  daily_goal    smallint not null default 30 check (daily_goal between 5 and 240),
  updated_at    timestamptz not null default now()
);

create table if not exists public.challenge_done (
  kid_id      uuid not null references public.kids(id) on delete cascade,
  parent_id   uuid not null references public.parents(id) on delete cascade,
  week        text not null check (week ~ '^[0-9]{4}-W[0-9]{2}$'),
  ckey        text not null check (ckey ~ '^[a-z0-9_]{2,24}$'),
  done_at     timestamptz not null default now(),
  primary key (kid_id, week)
);
create index if not exists challenge_parent_idx on public.challenge_done(parent_id);

-- limits: at most 5 active quests and 3 active rewards per kid
create or replace function public.nr_pc_limits() returns trigger
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  perform 1 from public.kids where id = new.kid_id for update;
  if tg_table_name = 'quests' then
    if (select count(*) from public.quests where kid_id = new.kid_id and status = 'active') >= 5 then
      raise exception 'quest_limit: at most 5 active quests per kid' using errcode = 'P0001'; end if;
  elsif tg_table_name = 'rewards' then
    if (select count(*) from public.rewards where kid_id = new.kid_id and status in ('active','earned')) >= 3 then
      raise exception 'reward_limit: at most 3 open rewards per kid' using errcode = 'P0001'; end if;
  elsif tg_table_name = 'fixit_plans' then
    if (select count(*) from public.fixit_plans where kid_id = new.kid_id and status = 'active') >= 2 then
      raise exception 'plan_limit: at most 2 active fix-it plans per kid' using errcode = 'P0001'; end if;
  end if;
  return new;
end $$;
drop trigger if exists quests_limit on public.quests;
create trigger quests_limit before insert on public.quests for each row execute function public.nr_pc_limits();
drop trigger if exists rewards_limit on public.rewards;
create trigger rewards_limit before insert on public.rewards for each row execute function public.nr_pc_limits();
drop trigger if exists fixit_limit on public.fixit_plans;
create trigger fixit_limit before insert on public.fixit_plans for each row execute function public.nr_pc_limits();

alter table public.quests         enable row level security;
alter table public.fixit_plans    enable row level security;
alter table public.rewards        enable row level security;
alter table public.notify_prefs   enable row level security;
alter table public.challenge_done enable row level security;

-- parent owns the row AND the kid
drop policy if exists quests_all on public.quests;
create policy quests_all on public.quests for all to authenticated
  using (parent_id = (select auth.uid()))
  with check (parent_id = (select auth.uid()) and exists (select 1 from public.kids k where k.id = kid_id and k.parent_id = (select auth.uid())));
drop policy if exists fixit_all on public.fixit_plans;
create policy fixit_all on public.fixit_plans for all to authenticated
  using (parent_id = (select auth.uid()))
  with check (parent_id = (select auth.uid()) and exists (select 1 from public.kids k where k.id = kid_id and k.parent_id = (select auth.uid())));
drop policy if exists rewards_all on public.rewards;
create policy rewards_all on public.rewards for all to authenticated
  using (parent_id = (select auth.uid()))
  with check (parent_id = (select auth.uid()) and exists (select 1 from public.kids k where k.id = kid_id and k.parent_id = (select auth.uid())));
drop policy if exists challenge_all on public.challenge_done;
create policy challenge_all on public.challenge_done for all to authenticated
  using (parent_id = (select auth.uid()))
  with check (parent_id = (select auth.uid()) and exists (select 1 from public.kids k where k.id = kid_id and k.parent_id = (select auth.uid())));
drop policy if exists prefs_all on public.notify_prefs;
create policy prefs_all on public.notify_prefs for all to authenticated
  using (parent_id = (select auth.uid())) with check (parent_id = (select auth.uid()));

revoke all on public.quests, public.fixit_plans, public.rewards, public.notify_prefs, public.challenge_done from anon, authenticated;
grant select, insert, delete on public.quests to authenticated;
grant update (status) on public.quests to authenticated;
grant select, insert, delete on public.fixit_plans to authenticated;
grant update (day_done, after_acc, status, updated_at) on public.fixit_plans to authenticated;
grant select, insert, delete on public.rewards to authenticated;
grant update (status, earned_at) on public.rewards to authenticated;
grant select, insert, update, delete on public.notify_prefs to authenticated;
grant select, insert, delete on public.challenge_done to authenticated;
-- anon gets NO table access here either.

-- RPC: the kid device reads its active quests, open rewards and badge count
create or replace function public.get_home(p_device_token text)
returns json
language plpgsql security definer set search_path = public, pg_temp as $$
declare d public.devices%rowtype; q json; rw json; b int; st int; mn int; qd int;
begin
  if p_device_token is null or char_length(p_device_token) <> 96 then
    return json_build_object('ok', false, 'error', 'unlinked'); end if;
  select * into d from public.devices where token_hash = public.nr_hash(p_device_token);
  if not found or d.revoked_at is not null then
    return json_build_object('ok', false, 'error', 'unlinked'); end if;
  select coalesce(sum(coalesce((v.value->>'stars')::int, 0)), 0), coalesce(max(p.time_played_sec), 0) / 60
    into st, mn
    from public.progress p left join lateral jsonb_each(p.realms) v on true where p.kid_id = d.kid_id;
  select coalesce(json_agg(json_build_object('id', x.id, 'skill', x.skill, 'title', x.title, 'message', x.message,
           'goal', x.goal, 'right', x.right_count, 'total', x.total_count, 'status', x.status) order by x.created_at), '[]'::json)
    into q from public.quests x
    where x.kid_id = d.kid_id and (x.status = 'active' or (x.status = 'done' and x.done_at > now() - interval '2 days'));
  select coalesce(json_agg(json_build_object('id', r.id, 'title', r.title, 'goal_type', r.goal_type, 'goal', r.goal,
           'have', greatest(0, case r.goal_type when 'stars' then coalesce(st, 0)
                                  when 'minutes' then coalesce(mn, 0)
                                  else (select count(*) from public.quests z where z.kid_id = d.kid_id and z.status = 'done' and z.done_at >= r.created_at)::int end
                               - case when r.goal_type = 'quests' then 0 else r.start_value end),
           'status', r.status) order by r.created_at), '[]'::json)
    into rw from public.rewards r where r.kid_id = d.kid_id and r.status in ('active','earned');
  select count(*) into b from public.challenge_done where kid_id = d.kid_id;
  return json_build_object('ok', true, 'quests', q, 'rewards', rw, 'badges', b);
end $$;

-- RPC: the kid device reports quest progress (counts only go up; done at goal)
create or replace function public.quest_progress(p_device_token text, p_quest_id uuid, p_right int, p_total int)
returns json
language plpgsql security definer set search_path = public, pg_temp as $$
declare d public.devices%rowtype; x public.quests%rowtype;
begin
  if p_device_token is null or char_length(p_device_token) <> 96 then
    return json_build_object('ok', false, 'error', 'unlinked'); end if;
  select * into d from public.devices where token_hash = public.nr_hash(p_device_token);
  if not found or d.revoked_at is not null then
    return json_build_object('ok', false, 'error', 'unlinked'); end if;
  select * into x from public.quests where id = p_quest_id and kid_id = d.kid_id for update;
  if not found then return json_build_object('ok', false, 'error', 'not_found'); end if;
  if x.status <> 'active' then return json_build_object('ok', true, 'status', x.status); end if;
  update public.quests set
    total_count = least(x.goal, greatest(x.total_count, coalesce(p_total, 0))),
    right_count = least(least(x.goal, greatest(x.total_count, coalesce(p_total, 0))), greatest(x.right_count, coalesce(p_right, 0))),
    status = case when greatest(x.total_count, coalesce(p_total, 0)) >= x.goal then 'done' else 'active' end,
    done_at = case when greatest(x.total_count, coalesce(p_total, 0)) >= x.goal then now() else null end
  where id = x.id returning * into x;
  return json_build_object('ok', true, 'status', x.status);
end $$;

revoke all on function public.nr_pc_limits() from public, anon, authenticated;
revoke all on function public.get_home(text) from public, anon, authenticated;
revoke all on function public.quest_progress(text, uuid, int, int) from public, anon, authenticated;
grant execute on function public.get_home(text) to anon;
grant execute on function public.quest_progress(text, uuid, int, int) to anon;

-- ---------- v28: weekly summary + weekly email (Edge Function nr-weekly) ----------
-- Opt-in only: email_weekly is off until the parent turns it on. unsub_token powers the
-- unsubscribe link and can not be changed by the parent from the browser.
alter table public.notify_prefs add column if not exists email_weekly boolean not null default false;
alter table public.notify_prefs add column if not exists email_day smallint not null default 0;
alter table public.notify_prefs add column if not exists unsub_token uuid not null default gen_random_uuid();
do $$ begin
  alter table public.notify_prefs add constraint notify_prefs_email_day_chk check (email_day between 0 and 6);
exception when duplicate_object then null; end $$;
create unique index if not exists notify_prefs_unsub_idx on public.notify_prefs(unsub_token);

-- one summary per kid per week; written only by the Edge Function (service role)
create table if not exists public.weekly_summaries (
  kid_id      uuid not null references public.kids(id) on delete cascade,
  parent_id   uuid not null references public.parents(id) on delete cascade,
  week        text not null check (week ~ '^[0-9]{4}-W[0-9]{2}$'),
  source      text not null check (source in ('ai', 'template')),
  body        text not null check (char_length(body) between 1 and 1200),
  stats       jsonb not null default '{}'::jsonb check (octet_length(stats::text) <= 4000),
  created_at  timestamptz not null default now(),
  primary key (kid_id, week)
);
create index if not exists weekly_summaries_parent_idx on public.weekly_summaries(parent_id);

-- sent-email log: weekly email at most once per parent per week; previews limited per day
create table if not exists public.email_log (
  id         bigint generated always as identity primary key,
  parent_id  uuid not null references public.parents(id) on delete cascade,
  kind       text not null check (kind in ('weekly', 'preview')),
  week       text not null check (week ~ '^[0-9]{4}-W[0-9]{2}$'),
  sent_at    timestamptz not null default now()
);
create unique index if not exists email_log_weekly_once on public.email_log(parent_id, week) where kind = 'weekly';
create index if not exists email_log_parent_idx on public.email_log(parent_id, sent_at);

alter table public.weekly_summaries enable row level security;
alter table public.email_log        enable row level security;
drop policy if exists summaries_read on public.weekly_summaries;
create policy summaries_read on public.weekly_summaries for select to authenticated
  using (parent_id = (select auth.uid()));
-- email_log: no policies, so only the Edge Function (service role) can use it

revoke all on public.weekly_summaries, public.email_log from anon, authenticated;
grant select on public.weekly_summaries to authenticated;
revoke insert, update on public.notify_prefs from authenticated;
grant insert (parent_id, events, quiet_start, quiet_end, idle_days, daily_goal, email_weekly, email_day, updated_at) on public.notify_prefs to authenticated;
grant update (parent_id, events, quiet_start, quiet_end, idle_days, daily_goal, email_weekly, email_day, updated_at) on public.notify_prefs to authenticated;

notify pgrst, 'reload schema';
