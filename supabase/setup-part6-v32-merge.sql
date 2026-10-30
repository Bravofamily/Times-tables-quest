-- =====================================================================
-- NumiRealm v32 Part E (PC-06): multi-device progress MERGE.
-- Before: each device's push overwrote the kid's single progress row,
-- so a second iPad could wipe the first one's stars.
-- After: every device keeps its own latest snapshot; the kid's row is
-- rebuilt from all linked devices:
--   stars / chapters  = MAX across devices
--   attempts (r,t,l)  = SUM across devices (each device counted once)
--   play time         = SUM across devices
--   timestamps        = LATEST
-- Safe to run more than once. No personal data added.
-- =====================================================================
create table if not exists public.progress_by_device (
  device_id  uuid not null references public.devices(id) on delete cascade,
  kid_id     uuid not null references public.kids(id) on delete cascade,
  parent_id  uuid not null references public.parents(id) on delete cascade,
  realms     jsonb not null default '{}'::jsonb,
  skills     jsonb not null default '{}'::jsonb,
  time_played_sec integer not null default 0,
  lanterns_used   integer not null default 0,
  examples_opened integer not null default 0,
  client_updated_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (device_id)
);
alter table public.progress_by_device enable row level security;
revoke all on public.progress_by_device from anon, authenticated;
drop policy if exists pbd_owner_read on public.progress_by_device;
create policy pbd_owner_read on public.progress_by_device for select to authenticated using (parent_id = auth.uid());
grant select on public.progress_by_device to authenticated;

-- one-time: keep today's progress by giving it to each kid's most recently seen device
insert into public.progress_by_device (device_id, kid_id, parent_id, realms, skills, time_played_sec, lanterns_used, examples_opened, client_updated_at)
select distinct on (p.kid_id) d.id, p.kid_id, p.parent_id, p.realms, p.skills, p.time_played_sec, p.lanterns_used, p.examples_opened, p.client_updated_at
from public.progress p join public.devices d on d.kid_id = p.kid_id and d.revoked_at is null
order by p.kid_id, d.last_seen_at desc nulls last, d.created_at desc
on conflict (device_id) do nothing;

-- keep the old (validated) function, renamed, as the single-device writer
do $$ begin
  if not exists (select 1 from pg_proc where proname = 'push_progress_single') then
    alter function public.push_progress(text, jsonb) rename to push_progress_single;
  end if;
end $$;
revoke all on function public.push_progress_single(text, jsonb) from public, anon, authenticated;

create or replace function public.push_progress(p_device_token text, p_payload jsonb)
returns json language plpgsql security definer set search_path = public, pg_temp as $$
declare d public.devices%rowtype; res json; p public.progress%rowtype; mr jsonb; ms jsonb;
begin
  res := public.push_progress_single(p_device_token, p_payload);   -- validates token + payload
  if coalesce((res->>'ok')::boolean, false) is not true then return res; end if;
  select * into d from public.devices where token_hash = public.nr_hash(p_device_token);
  select * into p from public.progress where kid_id = d.kid_id;
  -- this device's own latest snapshot
  insert into public.progress_by_device as b (device_id, kid_id, parent_id, realms, skills, time_played_sec,
     lanterns_used, examples_opened, client_updated_at, updated_at)
  values (d.id, d.kid_id, d.parent_id, p.realms, p.skills, p.time_played_sec, p.lanterns_used, p.examples_opened, p.client_updated_at, now())
  on conflict (device_id) do update set realms = excluded.realms, skills = excluded.skills,
     time_played_sec = excluded.time_played_sec, lanterns_used = excluded.lanterns_used,
     examples_opened = excluded.examples_opened, client_updated_at = excluded.client_updated_at, updated_at = now();
  -- realms: max per field across devices
  select coalesce(jsonb_object_agg(k, jsonb_build_object('chapters', mc, 'total', mt, 'stars', mst, 'max', mx)), '{}'::jsonb) into mr from (
    select e.key k, max((e.value->>'chapters')::int) mc, max((e.value->>'total')::int) mt,
           max((e.value->>'stars')::int) mst, max((e.value->>'max')::int) mx
    from public.progress_by_device b, jsonb_each(b.realms) e where b.kid_id = d.kid_id group by e.key) z;
  -- skills: attempts summed across devices
  select coalesce(jsonb_object_agg(k, jsonb_build_object('n', nm, 'r', least(sr, st), 't', st, 'l', sl)), '{}'::jsonb) into ms from (
    select e.key k, max(e.value->>'n') nm, sum((e.value->>'r')::int)::int sr, sum((e.value->>'t')::int)::int st, sum((e.value->>'l')::int)::int sl
    from public.progress_by_device b, jsonb_each(b.skills) e where b.kid_id = d.kid_id group by e.key) z;
  update public.progress set realms = mr, skills = ms,
     time_played_sec = (select sum(time_played_sec) from public.progress_by_device where kid_id = d.kid_id),
     lanterns_used   = (select sum(lanterns_used)   from public.progress_by_device where kid_id = d.kid_id),
     examples_opened = (select sum(examples_opened) from public.progress_by_device where kid_id = d.kid_id),
     client_updated_at = (select max(client_updated_at) from public.progress_by_device where kid_id = d.kid_id),
     updated_at = now()
  where kid_id = d.kid_id;
  return res;
end $$;
revoke all on function public.push_progress(text, jsonb) from public, anon, authenticated;
grant execute on function public.push_progress(text, jsonb) to anon;
notify pgrst, 'reload schema';
-- NOTE: play-day log ("play") stays last-writer for now (minor; listed in CHANGES.md).

-- =====================================================================
-- v32 Part F (CR-02): Game Night signing key store for the nr-gn function.
-- Only the service role (the Edge Function) can read it. Nobody else.
-- =====================================================================
create table if not exists public.gn_keys (id int primary key check (id = 1), jwk jsonb not null, created_at timestamptz not null default now());
alter table public.gn_keys enable row level security;
revoke all on public.gn_keys from public, anon, authenticated;
notify pgrst, 'reload schema';
