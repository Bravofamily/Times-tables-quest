import { PGlite } from '@electric-sql/pglite'; import { pgcrypto } from '@electric-sql/pglite/contrib/pgcrypto'; import fs from 'fs';
const db = new PGlite({ extensions: { pgcrypto } }); const S='/workspace/v32-repo/supabase/';
await db.exec(`create role anon; create role authenticated; create role service_role; create schema auth; create table auth.users(id uuid primary key, email text);
create function auth.uid() returns uuid language sql as $$ select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
create function auth.jwt() returns jsonb language sql as $$ select '{}'::jsonb $$; create extension pgcrypto; create schema extensions;`);
for (const f of ['setup.sql','setup-part4.sql','setup-part5-v32.sql','setup-part6-v32-merge.sql']) {
  try { await db.exec(fs.readFileSync(S+f,'utf8')); console.log('OK',f); } catch(e){ console.log('ERR',f,e.message); }
}
const q=async(s,p)=>(await db.query(s,p)).rows; let pass=0,fail=0; const ck=(c,m)=>{c?pass++:fail++;console.log(c?'PASS':'FAIL',m)};
const P='11111111-1111-1111-1111-111111111111';
await db.exec(`insert into auth.users values('${P}','x@example.test'); insert into public.parents(id) values('${P}') on conflict do nothing;`);
const k=(await q(`insert into public.kids(parent_id,nickname,age_range,grade) values($1,'TestKid','8-10','3') returning id`,[P]))[0].id;
await db.exec(`select set_config('request.jwt.claim.sub','${P}',false)`);
const tok=[];for(let i=0;i<2;i++){const code=(await q(`select code from public.create_link_code($1)`,[k]))[0].code; const r=(await q(`select public.redeem_link_code($1,$2) r`,[code,'iPad'+i]))[0].r; tok.push(r.device_token);}
ck(tok.every(t=>t&&t.length==96),'two devices linked');
const push=async(t,stars,r,tt,sec)=>(await q(`select public.push_progress($1,$2) r`,[t,{realms:{mult:{chapters:stars>5?3:1,total:10,stars,max:30}},skills:{'mult:x7':{n:'x7',r,t:tt,l:0}},time_played_sec:sec,client_at:new Date().toISOString()}]))[0].r;
ck((await push(tok[0],20,8,10,600)).ok,'device A push ok');
ck((await push(tok[1],3,2,5,100)).ok,'device B push (fewer stars) ok');
let p=(await q(`select * from public.progress where kid_id=$1`,[k]))[0];
ck(p.realms.mult.stars===20,'stars = max (20), not overwritten by B: '+p.realms.mult.stars);
ck(p.realms.mult.chapters===3,'chapters = max');
ck(p.skills['mult:x7'].t===15&&p.skills['mult:x7'].r===10,'attempts summed 10+5, right 8+2: '+JSON.stringify(p.skills['mult:x7']));
ck(p.time_played_sec===700,'time summed');
await push(tok[0],22,9,12,650); p=(await q(`select * from public.progress where kid_id=$1`,[k]))[0];
ck(p.realms.mult.stars===22&&p.skills['mult:x7'].t===17,'repeat push from A not double-counted (t=12+5)');
ck((await q(`select public.push_progress($1,$2) r`,['x'.repeat(96),{}]))[0].r.ok===false,'bad token still rejected');
const g=await q(`select has_function_privilege('anon','public.push_progress_single(text,jsonb)','execute') a`); ck(g[0].a===false,'anon cannot call old single writer');
const gk=await q(`select has_table_privilege('anon','public.gn_keys','select') a, has_table_privilege('authenticated','public.gn_keys','select') b`);ck(!gk[0].a&&!gk[0].b,'gn_keys not readable by anon/authenticated');
const pb=await q(`select has_table_privilege('anon','public.progress_by_device','select') a`);ck(!pb[0].a,'progress_by_device not readable by anon');
console.log(`RESULT merge ${pass}/${pass+fail}`);
