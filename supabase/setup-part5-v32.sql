-- NumiRealm v32: account deletion support. Safe to run more than once. No data is changed.
-- PART A (read-only check): run this first. Every row should say delete_rule = CASCADE
-- (except link_codes.device_id, which is SET NULL on purpose).
select c.conrelid::regclass as table_name, a.attname as column_name, c.confrelid::regclass as references_table,
       case c.confdeltype when 'c' then 'CASCADE' when 'n' then 'SET NULL' when 'a' then 'NO ACTION' when 'r' then 'RESTRICT' else c.confdeltype::text end as delete_rule
from pg_constraint c join pg_attribute a on a.attrelid = c.conrelid and a.attnum = c.conkey[1]
where c.contype = 'f' and c.connamespace = 'public'::regnamespace
order by 1, 2;

-- PART B (fix, only if PART A shows something other than CASCADE): makes every foreign key from a public
-- table to parents, kids or auth.users ON DELETE CASCADE (keeps link_codes.device_id as SET NULL).
do $$
declare r record;
begin
  for r in
    select c.conname, c.conrelid::regclass as tbl, a.attname as col, c.confrelid::regclass as ref, fa.attname as refcol
    from pg_constraint c
    join pg_attribute a  on a.attrelid = c.conrelid  and a.attnum = c.conkey[1]
    join pg_attribute fa on fa.attrelid = c.confrelid and fa.attnum = c.confkey[1]
    where c.contype = 'f' and c.connamespace = 'public'::regnamespace and c.confdeltype <> 'c'
      and c.confrelid in ('public.parents'::regclass, 'public.kids'::regclass, 'auth.users'::regclass)
  loop
    execute format('alter table %s drop constraint %I', r.tbl, r.conname);
    execute format('alter table %s add constraint %I foreign key (%I) references %s(%I) on delete cascade', r.tbl, r.conname, r.col, r.ref, r.refcol);
    raise notice 'fixed % . %', r.tbl, r.col;
  end loop;
end $$;
-- The Delete my account button itself needs NO new grants: the nr-delete-account function uses the service role.

-- =====================================================================
-- PART C (v32, CR-03): parent opt-in for AI-written summaries. OFF by default.
-- nr-weekly reads this with the service role; a parent can change only their own row (existing notify_prefs RLS).
-- =====================================================================
alter table public.notify_prefs add column if not exists ai_summaries boolean not null default false;

-- =====================================================================
-- PART D (v32, CR-04): server-enforced, versioned consent records. PREPARED ONLY.
-- Real-family sign-up stays disabled (test banner) until counsel approves the text and the verification method.
-- Parents can INSERT their own acknowledgment and READ it. They cannot UPDATE or DELETE it, and they cannot
-- set verification fields (only the service role / an admin process can, after a counsel-approved method).
-- =====================================================================
create table if not exists public.consent_versions (
  version     text primary key,
  status      text not null check (status in ('draft_for_legal_review','approved','retired')),
  body        text not null,
  created_at  timestamptz not null default now()
);
alter table public.consent_versions enable row level security;
drop policy if exists consent_versions_read on public.consent_versions;
create policy consent_versions_read on public.consent_versions for select to authenticated using (true);
-- no insert/update/delete policies: only the service role can manage versions.

insert into public.consent_versions(version,status,body) values ('2026-10-30-draft','draft_for_legal_review',
$t$I confirm that I am the parent or legal guardian of the child profile(s) I am authorizing in NumiRealm.

I have reviewed the NumiRealm Privacy Notice and understand the information the service collects, how it is used, how long it is retained, and which service providers may process it to operate Parent Center features.

I authorize NumiRealm to collect and use the child-related learning information described in the Privacy Notice for the purposes I select. I understand that I may review my child's information, withdraw consent, request deletion, or stop further collection as described in the Privacy Notice.

Any optional processing, such as AI-written learning summaries or other disclosures requiring separate consent, will be presented separately and will not be enabled merely because I accept this general notice.

I understand that checking this box records my acknowledgment, but that NumiRealm may require an additional verification step before treating this consent as verified parental consent.

Parent/guardian acknowledgment: I have read and understood this notice.
Consent version: [approved version]
Verification method and status: [recorded by NumiRealm after verification]$t$)
on conflict (version) do nothing;

create table if not exists public.consent_records (
  id                  uuid primary key default gen_random_uuid(),
  parent_id           uuid not null references auth.users(id) on delete cascade,
  version             text not null references public.consent_versions(version),
  scope               text not null check (scope in ('general','ai_summaries')),
  acknowledged_at     timestamptz not null default now(),
  verification_method text,          -- PLACEHOLDER: set by the service role only, method chosen by counsel
  verification_status text not null default 'unverified' check (verification_status in ('unverified','verified','revoked')),
  verified_at         timestamptz
);
alter table public.consent_records enable row level security;
drop policy if exists consent_records_read on public.consent_records;
create policy consent_records_read on public.consent_records for select to authenticated using (parent_id = auth.uid());
drop policy if exists consent_records_insert on public.consent_records;
create policy consent_records_insert on public.consent_records for insert to authenticated
  with check (parent_id = auth.uid() and verification_method is null and verification_status = 'unverified' and verified_at is null);
-- no update/delete policies for parents: records are append-only. Withdrawal = a new row with the service role setting status 'revoked'.
revoke update, delete on public.consent_records from anon, authenticated;
