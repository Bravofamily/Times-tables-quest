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

-- Small daily snapshot for trend graphs (1 row per kid per day, kept 180 days)
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

  insert into public.progress as p (kid_id, parent_id, hero, realms, skills, time_played_sec,
         lanterns_used, examples_opened, client_updated_at, updated_at)
  values (d.kid_id, d.parent_id, hero, realms, skills, secs,
         least(greatest(coalesce((p_payload->>'lanterns_used')::numeric, 0), 0), 1000000)::int,
         least(greatest(coalesce((p_payload->>'examples_opened')::numeric, 0), 0), 1000000)::int,
         cl, now())
  on conflict (kid_id) do update set
         hero = excluded.hero, realms = excluded.realms, skills = excluded.skills,
         time_played_sec = excluded.time_played_sec, lanterns_used = excluded.lanterns_used,
         examples_opened = excluded.examples_opened, client_updated_at = excluded.client_updated_at,
         updated_at = now();

  insert into public.progress_events as e (kid_id, parent_id, day, stars_total, answers_right, answers_total, minutes)
  values (d.kid_id, d.parent_id, (now() at time zone 'utc')::date, st, rt, tt, secs / 60)
  on conflict (kid_id, day) do update set stars_total = excluded.stars_total,
         answers_right = excluded.answers_right, answers_total = excluded.answers_total, minutes = excluded.minutes;
  delete from public.progress_events where kid_id = d.kid_id and day < (now() at time zone 'utc')::date - 180;

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
notify pgrst, 'reload schema';
