-- NumiRealm v33 Part 7 (LOCAL DRAFT, not run in production). Idempotent: safe to run twice.
-- Part G (directives 9/10): save-lineage reconciliation for multi-device progress.
--   A device sends payload.lin = 'lin-<random>' kept with its local save. A backup restored onto another
--   device carries the same lin, so both snapshots form one lineage and the latest snapshot counts once
--   (no double-count). Different lineages still add up. Old clients without lin keep the v32 per-device sum.
-- Part H (directive 8): gn_rooms for Game Night host-only registration and room-end revocation (service role only).

alter table public.progress_by_device add column if not exists lineage text;
alter table public.progress_by_device drop constraint if exists progress_by_device_lineage_chk;
alter table public.progress_by_device add constraint progress_by_device_lineage_chk check (lineage is null or lineage ~ '^lin-[A-Za-z0-9_-]{8,40}$');
-- CR33-1: ordering never trusts device clocks. save_seq = per-lineage save counter sent by the client (travels with backups);
-- latest snapshot = highest save_seq, tie-break by server receive time (updated_at = now() on the server).
alter table public.progress_by_device add column if not exists save_seq bigint;
alter table public.progress_by_device drop constraint if exists progress_by_device_seq_chk;
alter table public.progress_by_device add constraint progress_by_device_seq_chk check (save_seq is null or save_seq between 1 and 2000000000);

create or replace function public.nr_progress_effective(p_kid uuid)
returns setof public.progress_by_device language sql stable security definer set search_path = public, pg_temp as $$
  select distinct on (coalesce(b.lineage, b.device_id::text)) b.*
  from public.progress_by_device b where b.kid_id = p_kid
  order by coalesce(b.lineage, b.device_id::text), b.save_seq desc nulls last, b.updated_at desc
$$;
revoke all on function public.nr_progress_effective(uuid) from public, anon, authenticated;

create or replace function public.push_progress(p_device_token text, p_payload jsonb)
returns json language plpgsql security definer set search_path = public, pg_temp as $$
declare d public.devices%rowtype; res json; p public.progress%rowtype; mr jsonb; ms jsonb; lin text; seq bigint;
begin
  res := public.push_progress_single(p_device_token, p_payload);   -- validates token + payload
  if coalesce((res->>'ok')::boolean, false) is not true then return res; end if;
  select * into d from public.devices where token_hash = public.nr_hash(p_device_token);
  -- v33: save lineage id from the device (copied along with a backup); junk is ignored
  lin := p_payload->>'lin'; if lin is null or lin !~ '^lin-[A-Za-z0-9_-]{8,40}$' then lin := null; end if;
  -- v33 CR33-1: save counter (1..2e9); anything else is ignored
  seq := case when coalesce(p_payload->>'seq','') ~ '^[0-9]{1,10}$' and (p_payload->>'seq')::bigint between 1 and 2000000000 then (p_payload->>'seq')::bigint end;
  select * into p from public.progress where kid_id = d.kid_id;
  -- this device's own latest snapshot
  insert into public.progress_by_device as b (device_id, kid_id, parent_id, realms, skills, time_played_sec,
     lanterns_used, examples_opened, client_updated_at, updated_at, lineage, save_seq)
  values (d.id, d.kid_id, d.parent_id, p.realms, p.skills, p.time_played_sec, p.lanterns_used, p.examples_opened, p.client_updated_at, now(), lin, seq)
  on conflict (device_id) do update set realms = excluded.realms, skills = excluded.skills,
     time_played_sec = excluded.time_played_sec, lanterns_used = excluded.lanterns_used,
     examples_opened = excluded.examples_opened, client_updated_at = excluded.client_updated_at, updated_at = now(), lineage = excluded.lineage, save_seq = excluded.save_seq
     -- a late retry of an older snapshot from the same device never rolls its row back
     where b.save_seq is null or excluded.save_seq is null or excluded.save_seq >= b.save_seq or b.lineage is distinct from excluded.lineage;
  -- realms: max per field across devices
  select coalesce(jsonb_object_agg(k, jsonb_build_object('chapters', mc, 'total', mt, 'stars', mst, 'max', mx)), '{}'::jsonb) into mr from (
    select e.key k, max((e.value->>'chapters')::int) mc, max((e.value->>'total')::int) mt,
           max((e.value->>'stars')::int) mst, max((e.value->>'max')::int) mx
    from public.nr_progress_effective(d.kid_id) b, jsonb_each(b.realms) e group by e.key) z;
  -- skills: attempts summed across devices
  select coalesce(jsonb_object_agg(k, jsonb_build_object('n', nm, 'r', least(sr, st), 't', st, 'l', sl)), '{}'::jsonb) into ms from (
    select e.key k, max(e.value->>'n') nm, sum((e.value->>'r')::int)::int sr, sum((e.value->>'t')::int)::int st, sum((e.value->>'l')::int)::int sl
    from public.nr_progress_effective(d.kid_id) b, jsonb_each(b.skills) e group by e.key) z;
  update public.progress set realms = mr, skills = ms,
     time_played_sec = (select sum(time_played_sec) from public.nr_progress_effective(d.kid_id)),
     lanterns_used   = (select sum(lanterns_used) from public.nr_progress_effective(d.kid_id)),
     examples_opened = (select sum(examples_opened) from public.nr_progress_effective(d.kid_id)),
     client_updated_at = (select max(client_updated_at) from public.nr_progress_effective(d.kid_id)),
     updated_at = now()
  where kid_id = d.kid_id;
  return res;
end $$;
revoke all on function public.push_progress(text, jsonb) from public;
grant execute on function public.push_progress(text, jsonb) to anon;

create table if not exists public.gn_rooms (
  code text primary key check (code ~ '^[A-Z0-9]{5}$'),
  token_hash text not null,
  exp timestamptz not null,
  ended_at timestamptz,
  created_at timestamptz not null default now()
);
alter table public.gn_rooms enable row level security;
revoke all on public.gn_rooms from public, anon, authenticated;

-- Part I (CR33-3): Game Night rate-limit buckets (service role only). No raw IPs: keys hold a salted hash prefix.
-- Fixed windows; rows expire at the end of their window and are purged on later calls. No permanent bans.
create table if not exists public.gn_rate (
  bucket text primary key check (length(bucket) <= 120),
  n integer not null default 0,
  expires_at timestamptz not null
);
create index if not exists gn_rate_exp on public.gn_rate (expires_at);
alter table public.gn_rate enable row level security;
revoke all on public.gn_rate from public, anon, authenticated;
create or replace function public.gn_rate_hit(p_key text, p_limit int, p_window_sec int, p_peek boolean default false)
returns json language plpgsql security definer set search_path = public, pg_temp as $$
declare w int := greatest(1, least(p_window_sec, 86400)); st timestamptz; b text; c int; e timestamptz;
begin
  if p_key is null or length(p_key) > 100 then return json_build_object('ok', false, 'retry', 60); end if;
  if random() < 0.02 then delete from public.gn_rate where expires_at < now() - interval '5 minutes'; end if;  -- purge old buckets
  st := to_timestamp(floor(extract(epoch from now()) / w) * w); e := st + make_interval(secs => w);
  b := p_key || '@' || floor(extract(epoch from st))::bigint;
  if p_peek then
    select n into c from public.gn_rate where bucket = b; c := coalesce(c, 0);
    return json_build_object('ok', c < p_limit, 'retry', ceil(extract(epoch from e - now()))::int);
  end if;
  insert into public.gn_rate as r (bucket, n, expires_at) values (b, 1, e)
    on conflict (bucket) do update set n = r.n + 1 where r.n < p_limit
    returning n into c;
  return json_build_object('ok', c is not null, 'retry', ceil(extract(epoch from e - now()))::int);
end $$;
revoke all on function public.gn_rate_hit(text, int, int, boolean) from public, anon, authenticated;
grant execute on function public.gn_rate_hit(text, int, int, boolean) to service_role;

-- Part J (v33.1, CR33-1 audit): non-destructive retention of superseded snapshots.
-- Every time a device snapshot is overwritten or its device row is removed (unlink cascades), the OLD snapshot is copied
-- here first, so an excluded branch (e.g. a restored device that lost the "newest branch" rule) can be recovered by hand.
-- Service role only (no RLS policies). Bounded: newest 30 rows per device, 180 days. Kid/account deletion still erases it (cascade).
create table if not exists public.progress_snapshot_history (
  id bigserial primary key,
  kid_id uuid not null references public.kids(id) on delete cascade,
  parent_id uuid not null,
  device_id uuid not null,
  lineage text, save_seq bigint,
  realms jsonb, skills jsonb, time_played_sec integer, lanterns_used integer, examples_opened integer,
  snap_updated_at timestamptz, superseded_at timestamptz not null default now(),
  reason text not null check (reason in ('overwritten','device_removed'))
);
create index if not exists psh_kid on public.progress_snapshot_history (kid_id, superseded_at desc);
create index if not exists psh_dev on public.progress_snapshot_history (device_id, id desc);
alter table public.progress_snapshot_history enable row level security;
revoke all on public.progress_snapshot_history from public, anon, authenticated;
revoke all on sequence public.progress_snapshot_history_id_seq from public, anon, authenticated;

create or replace function public.nr_keep_snapshot() returns trigger language plpgsql security definer set search_path = public, pg_temp as $$
begin
  if tg_op = 'UPDATE' and old.skills is not distinct from new.skills and old.realms is not distinct from new.realms
     and old.time_played_sec is not distinct from new.time_played_sec and old.save_seq is not distinct from new.save_seq then return new; end if;
  if tg_op = 'DELETE' and not exists (select 1 from public.kids where id = old.kid_id) then return old; end if; -- kid being deleted: keep nothing
  insert into public.progress_snapshot_history (kid_id, parent_id, device_id, lineage, save_seq, realms, skills, time_played_sec,
     lanterns_used, examples_opened, snap_updated_at, reason)
  values (old.kid_id, old.parent_id, old.device_id, old.lineage, old.save_seq, old.realms, old.skills, old.time_played_sec,
     old.lanterns_used, old.examples_opened, old.updated_at, case when tg_op = 'DELETE' then 'device_removed' else 'overwritten' end);
  delete from public.progress_snapshot_history h where h.device_id = old.device_id and h.id not in
     (select id from public.progress_snapshot_history where device_id = old.device_id order by id desc limit 30);
  if random() < 0.02 then delete from public.progress_snapshot_history where superseded_at < now() - interval '180 days'; end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;
revoke all on function public.nr_keep_snapshot() from public, anon, authenticated;
drop trigger if exists nr_keep_snapshot on public.progress_by_device;
create trigger nr_keep_snapshot before update or delete on public.progress_by_device for each row execute function public.nr_keep_snapshot();

-- Audit helper (service role / SQL editor only): every branch of a kid, which one counts, and what is excluded.
create or replace function public.nr_branch_report(p_kid uuid)
returns table (lineage_key text, device_id uuid, save_seq bigint, attempts bigint, seconds integer, updated_at timestamptz, counted boolean)
language sql stable security definer set search_path = public, pg_temp as $$
  select coalesce(b.lineage, b.device_id::text), b.device_id, b.save_seq,
         (select coalesce(sum((e.value->>'t')::int),0) from jsonb_each(b.skills) e), b.time_played_sec, b.updated_at,
         exists (select 1 from public.nr_progress_effective(p_kid) x where x.device_id = b.device_id)
  from public.progress_by_device b where b.kid_id = p_kid order by 1, 7 desc, 3 desc nulls last
$$;
revoke all on function public.nr_branch_report(uuid) from public, anon, authenticated;
