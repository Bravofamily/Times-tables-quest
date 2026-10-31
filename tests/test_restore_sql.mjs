// v33 directive 9: multi-device restore scenarios against a local Postgres (PGlite). Synthetic data only.
// Usage: node test_restore_sql.mjs v32   -> setup..part6 (what production runs now); expect inflation (reported, not a failure)
//        node test_restore_sql.mjs v33   -> + part7 lineage reconciliation; expect no inflation
import { PGlite } from '@electric-sql/pglite'; import { pgcrypto } from '@electric-sql/pglite/contrib/pgcrypto'; import fs from 'fs';
const MODE = process.argv[2] || 'v33'; const S = new URL('../supabase/', import.meta.url).pathname;
const db = new PGlite({ extensions: { pgcrypto } });
await db.exec(`create role anon; create role authenticated; create role service_role; create schema auth; create table auth.users(id uuid primary key, email text);
create function auth.uid() returns uuid language sql as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
create function auth.jwt() returns jsonb language sql as $$ select '{}'::jsonb $$; create extension pgcrypto; create schema extensions;`);
const files = ['setup.sql','setup-part4.sql','setup-part5-v32.sql','setup-part6-v32-merge.sql'].concat(MODE === 'v33' ? ['setup-part7-v33.sql','setup-part7-v33.sql'] : []);
for (const f of files) { try { await db.exec(fs.readFileSync(S + f, 'utf8')); } catch (e) { console.log('ERR', f, e.message); process.exit(2); } }
const q = async (s, p) => (await db.query(s, p)).rows; let pass = 0, fail = 0; const out = [];
const ck = (c, m) => { c ? pass++ : fail++; console.log(c ? 'PASS' : 'FAIL', m); };
const P = '22222222-2222-2222-2222-222222222222';
await db.exec(`insert into auth.users values('${P}','synthetic@example.test'); insert into public.parents(id) values('${P}') on conflict do nothing; select set_config('request.jwt.claim.sub','${P}',false)`);
let NP = 0;
const newKid = async (n) => { const pid = '33333333-3333-3333-3333-' + String(++NP).padStart(12, '0');
  await db.exec(`insert into auth.users values('${pid}','synthetic${NP}@example.test'); insert into public.parents(id) values('${pid}') on conflict do nothing; select set_config('request.jwt.claim.sub','${pid}',false)`);
  return (await q(`insert into public.kids(parent_id,nickname,age_range,grade) values($1,$2,'8-10','3') returning id`, [pid, n]))[0].id; };
const link = async (k, name) => { const code = (await q(`select code from public.create_link_code($1)`, [k]))[0].code; return (await q(`select public.redeem_link_code($1,$2) r`, [code, name]))[0].r.device_token; };
const push = async (t, o, lin) => (await q(`select public.push_progress($1,$2) r`, [t, { realms: { mult: { chapters: 2, total: 10, stars: o.stars, max: 30 } },
  skills: { 'mult:x7': { n: 'x7', r: o.r, t: o.t, l: 0 } }, time_played_sec: o.sec, lanterns_used: 0, examples_opened: 0, ...(lin ? { lin } : {}), ...(o.seq !== undefined ? { seq: o.seq } : {}), client_at: new Date(Date.now() + (o.dt || 0)).toISOString() }]))[0].r;
const prog = async (k) => (await q(`select * from public.progress where kid_id=$1`, [k]))[0];
const report = (name, p, expT, expSec) => { const t = p.skills['mult:x7'].t, sec = p.time_played_sec; const infl = t > expT || sec > expSec;
  out.push({ scenario: name, attempts: t, true_attempts: expT, seconds: sec, true_seconds: expSec, inflated: infl }); return infl; };
const L1 = 'lin-aaaaaaaaaaaaaaaaaaaaaa', L2 = 'lin-bbbbbbbbbbbbbbbbbbbbbb';
// S1: iPad A plays (t=10). Its backup is restored onto iPad B, which is linked; B pushes the same counters, then plays 2 more.
{ const k = await newKid('Synth S1'); const a = await link(k, 'iPad A'); const b = await link(k, 'iPad B');
  await push(a, { stars: 9, r: 8, t: 10, sec: 600 }, L1); await push(b, { stars: 9, r: 8, t: 10, sec: 600, dt: 1000 }, L1); await push(b, { stars: 10, r: 10, t: 12, sec: 660, dt: 2000 }, L1);
  const i = report('S1 backup of A restored onto new device B', await prog(k), 12, 660); MODE === 'v33' ? ck(!i, 'S1 restore copy not double-counted') : out.at(-1); }
// S2: same iPad re-linked (app reinstalled from backup, new device token); old device row is left behind.
{ const k = await newKid('Synth S2'); const a = await link(k, 'iPad'); await push(a, { stars: 6, r: 5, t: 8, sec: 300 }, L1);
  const a2 = await link(k, 'iPad (relinked)'); await push(a2, { stars: 7, r: 7, t: 9, sec: 330, dt: 1000 }, L1);
  const i = report('S2 same device re-linked, old row kept', await prog(k), 9, 330); MODE === 'v33' ? ck(!i, 'S2 relink not double-counted') : 0; }
// S3: two genuinely different devices (different save lineages) must still add up.
{ const k = await newKid('Synth S3'); const a = await link(k, 'iPad'); const b = await link(k, 'Phone');
  await push(a, { stars: 6, r: 5, t: 8, sec: 300 }, L1); await push(b, { stars: 3, r: 2, t: 4, sec: 100, dt: 1000 }, L2);
  const p = await prog(k); report('S3 two independent devices', p, 12, 400); ck(p.skills['mult:x7'].t === 12 && p.time_played_sec === 400, 'S3 independent devices summed (12 attempts, 400 s)'); ck(p.realms.mult.stars === 6, 'S3 stars = max'); }
// S4: old clients that send no lineage keep v32 behaviour (per-device sum)
{ const k = await newKid('Synth S4'); const a = await link(k, 'Old iPad'); const b = await link(k, 'Old phone');
  await push(a, { stars: 2, r: 1, t: 3, sec: 50 }); await push(b, { stars: 1, r: 1, t: 2, sec: 40, dt: 1000 });
  const p = await prog(k); ck(p.skills['mult:x7'].t === 5 && p.time_played_sec === 90, 'S4 no-lineage clients: per-device sum as v32'); }
// S5: an older snapshot from the same lineage arriving late does not roll counters back
if (MODE === 'v33') { const k = await newKid('Synth S5'); const a = await link(k, 'iPad'); const b = await link(k, 'iPad copy');
  await push(a, { stars: 8, r: 9, t: 20, sec: 800, seq: 9 }, L1); await push(b, { stars: 5, r: 3, t: 5, sec: 200, seq: 3 }, L1);
  const p = await prog(k); ck(p.skills['mult:x7'].t === 20 && p.time_played_sec === 800, 'S5 stale copy of the same lineage ignored (max)'); }
// S6: lineage text is bounded/validated
if (MODE === 'v33') { const k = await newKid('Synth S6'); const a = await link(k, 'iPad');
  const r = await push(a, { stars: 1, r: 1, t: 1, sec: 1 }, 'x'.repeat(500)); const row = (await q(`select lineage from public.progress_by_device where kid_id=$1`, [k]))[0];
  ck(r.ok && (row.lineage === null), 'S6 junk lineage ignored (treated as none)'); }

// ---- CR33-1 regression: diverging restored devices + ordering without trusting device clocks ----
const sk = async (k) => { const p = await prog(k); return { t: p.skills['mult:x7'].t, sec: p.time_played_sec }; };
// S7: A at seq 5 (t=10) is backed up and restored onto B (seq 5). Both keep playing: A -> seq 7 (t=14, +4), B -> seq 6 (t=13, +3).
//     Truth = 17. Interim rule counts only the newest branch (A: 14): documented UNDERCOUNT, never a double-count (27).
if (MODE === 'v33') { const k = await newKid('Synth S7'); const a = await link(k, 'iPad A'); const b = await link(k, 'iPad B (restored)');
  await push(a, { stars: 5, r: 8, t: 10, sec: 500, seq: 5 }, L1); await push(b, { stars: 5, r: 8, t: 10, sec: 500, seq: 5 }, L1);
  await push(a, { stars: 7, r: 11, t: 14, sec: 700, seq: 7 }, L1); await push(b, { stars: 6, r: 10, t: 13, sec: 650, seq: 6 }, L1);
  const x = await sk(k); out.push({ scenario: 'S7 diverging restored branches', attempts: x.t, true_attempts: 17, undercount: 17 - x.t });
  ck(x.t === 14 && x.sec === 700, 'S7 diverging restore: newest branch only (14 of 17 true, known undercount 3), no double-count (27)');
  ck(x.t <= 17, 'S7 never above the truth'); }
// S8: B's clock is a year ahead but its counter is lower -> A (higher seq) still wins
if (MODE === 'v33') { const k = await newKid('Synth S8'); const a = await link(k, 'iPad'); const b = await link(k, 'Clock-skewed copy');
  await push(a, { stars: 4, r: 6, t: 9, sec: 400, seq: 8 }, L1); await push(b, { stars: 2, r: 2, t: 3, sec: 90, seq: 2, dt: 365 * 864e5 }, L1);
  const x = await sk(k); ck(x.t === 9 && x.sec === 400, 'S8 device clock ignored: highest save counter wins'); }
// S9: equal counters -> the snapshot the server received last wins
if (MODE === 'v33') { const k = await newKid('Synth S9'); const a = await link(k, 'iPad'); const b = await link(k, 'Copy');
  await push(a, { stars: 3, r: 3, t: 6, sec: 300, seq: 4, dt: 1e9 }, L1); await new Promise(r => setTimeout(r, 20)); await push(b, { stars: 3, r: 4, t: 7, sec: 320, seq: 4, dt: -1e9 }, L1);
  const x = await sk(k); ck(x.t === 7, 'S9 tie on counter: later server receive time wins (client clock ignored)'); }
// S10: a late retry of an older snapshot from the SAME device does not roll its row back
if (MODE === 'v33') { const k = await newKid('Synth S10'); const a = await link(k, 'iPad');
  await push(a, { stars: 6, r: 9, t: 12, sec: 600, seq: 10 }, L1); await push(a, { stars: 2, r: 2, t: 4, sec: 100, seq: 6 }, L1);
  const x = await sk(k); const row = (await q(`select save_seq from public.progress_by_device where kid_id=$1`, [k]))[0];
  ck(x.t === 12 && x.sec === 600 && Number(row.save_seq) === 10, 'S10 same-device stale retry ignored'); }
// S11: invalid counters are ignored (stored as null), never break the push
if (MODE === 'v33') { const k = await newKid('Synth S11'); const a = await link(k, 'iPad'); let okAll = true;
  for (const bad of [-1, 0, 3e9, 'abc', 1.5]) { const r = await push(a, { stars: 1, r: 1, t: 1, sec: 1, seq: bad }, L1); okAll = okAll && r.ok; }
  const row = (await q(`select save_seq from public.progress_by_device where kid_id=$1`, [k]))[0]; ck(okAll && row.save_seq === null, 'S11 invalid save counters ignored'); }
// S12: two independent devices that were each restored once: branches per lineage still add up across lineages
if (MODE === 'v33') { const k = await newKid('Synth S12'); const a = await link(k, 'iPad'); const a2 = await link(k, 'iPad restored'); const b = await link(k, 'Phone');
  await push(a, { stars: 3, r: 4, t: 5, sec: 200, seq: 3 }, L1); await push(a2, { stars: 3, r: 5, t: 6, sec: 240, seq: 4 }, L1); await push(b, { stars: 2, r: 2, t: 4, sec: 100, seq: 2 }, L2);
  const x = await sk(k); ck(x.t === 10 && x.sec === 340, 'S12 restored lineage counted once, other device added (10 attempts, 340 s)'); }

// ---- v33.1 audit: simultaneous restores, receive time only as tie-breaker, retention of excluded branches ----
// S13: one backup (seq 5) restored onto 3 devices at the same moment; each plays on (seq 6). Never above the truth, never a double count.
if (MODE === 'v33') { const k = await newKid('Synth S13'); const d = [await link(k, 'iPad A'), await link(k, 'iPad B'), await link(k, 'Phone C')];
  await Promise.all(d.map(t => push(t, { stars: 5, r: 8, t: 10, sec: 500, seq: 5 }, L1)));
  await Promise.all(d.map((t, i) => push(t, { stars: 6, r: 9 + i, t: 11 + i, sec: 520 + 10 * i, seq: 6 }, L1)));
  const x = await sk(k); const truth = 10 + 1 + 2 + 3; out.push({ scenario: 'S13 three simultaneous restores', attempts: x.t, true_attempts: truth, undercount: truth - x.t });
  ck([11, 12, 13].includes(x.t) && x.t <= truth, `S13 simultaneous restores: one branch counts (${x.t} of ${truth}), never a double count (${10 * 3 + 6})`);
  const br = await q(`select * from public.nr_branch_report($1)`, [k]); ck(br.length === 3 && br.filter(r => r.counted).length === 1, 'S13 branch report: 3 branches, exactly 1 counted, 2 visible as excluded'); }
// S14: server receive time is ONLY a tie-breaker: higher counter received FIRST still beats a lower counter received later
if (MODE === 'v33') { const k = await newKid('Synth S14'); const a = await link(k, 'iPad'); const b = await link(k, 'Copy');
  await push(a, { stars: 4, r: 6, t: 9, sec: 400, seq: 9 }, L1); await new Promise(r => setTimeout(r, 30)); await push(b, { stars: 2, r: 5, t: 8, sec: 380, seq: 7 }, L1);
  const x = await sk(k); ck(x.t === 9 && x.sec === 400, 'S14 receive order does not beat a higher save counter'); }
// S15: an excluded branch survives in history after its device is overwritten AND after it is unlinked (recoverable)
if (MODE === 'v33') { const k = await newKid('Synth S15'); const a = await link(k, 'iPad A'); const b = await link(k, 'iPad B (restored)');
  await push(a, { stars: 5, r: 8, t: 10, sec: 500, seq: 5 }, L1); await push(b, { stars: 5, r: 8, t: 10, sec: 500, seq: 5 }, L1);
  await push(a, { stars: 7, r: 11, t: 14, sec: 700, seq: 7 }, L1); await push(b, { stars: 6, r: 10, t: 13, sec: 650, seq: 6 }, L1);
  const bid = (await q(`select device_id from public.progress_by_device where kid_id=$1 and save_seq=6`, [k]))[0].device_id;
  await q(`delete from public.devices where id=$1`, [bid]);
  const h = await q(`select reason, save_seq, (skills->'mult:x7'->>'t')::int t from public.progress_snapshot_history where kid_id=$1 and device_id=$2 order by id`, [k, bid]);
  ck(h.some(r => r.reason === 'device_removed' && r.t === 13 && Number(r.save_seq) === 6), 'S15 excluded branch (13 attempts, seq 6) kept in history after unlink');
  ck(h.some(r => r.reason === 'overwritten' && Number(r.save_seq) === 5), 'S15 overwritten snapshot (seq 5) kept in history');
  const x = await sk(k); ck(x.t === 14, 'S15 totals unchanged by retention (14)'); }
// S16: retention is bounded (newest 30 per device)
if (MODE === 'v33') { const k = await newKid('Synth S16'); const a = await link(k, 'iPad');
  for (let i = 1; i <= 40; i++) await push(a, { stars: 1, r: i, t: i, sec: i * 10, seq: i }, L1);
  const n = (await q(`select count(*)::int c from public.progress_snapshot_history where kid_id=$1`, [k]))[0].c; ck(n === 30, `S16 history capped at 30 per device (${n})`); }
// S17: deleting the kid (Delete my account / remove child) erases history too
if (MODE === 'v33') { const k = await newKid('Synth S17'); const a = await link(k, 'iPad'); await push(a, { stars: 1, r: 1, t: 1, sec: 10, seq: 1 }, L1); await push(a, { stars: 1, r: 2, t: 2, sec: 20, seq: 2 }, L1);
  await q(`delete from public.kids where id=$1`, [k]); const n = (await q(`select count(*)::int c from public.progress_snapshot_history where kid_id=$1`, [k]))[0].c; ck(n === 0, 'S17 kid deletion leaves no history behind'); }
// S18: history and branch report are not reachable by anon / authenticated
if (MODE === 'v33') { const r = await q(`select has_table_privilege('anon','public.progress_snapshot_history','select') a, has_table_privilege('authenticated','public.progress_snapshot_history','select') u, has_function_privilege('anon','public.nr_branch_report(uuid)','execute') f, has_function_privilege('authenticated','public.nr_branch_report(uuid)','execute') g`);
  ck(!r[0].a && !r[0].u && !r[0].f && !r[0].g, 'S18 history + branch report closed to anon and signed-in parents'); }
console.log('INFLATION', JSON.stringify(out));
console.log(`RESULT restore-${MODE} ${pass}/${pass + fail}`);
