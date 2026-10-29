# v28: the game keeps a compact local log of ACTIVE play minutes per hero per local day (silent, no UI),
# sends it inside the existing push_progress snapshot when linked, and parent.html graphs it (see test_parent.py).
# Usage: PWB=chromium|webkit python test_v28.py
import os,re,json,threading,http.server,functools,datetime
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BR=os.environ.get('PWB','chromium')
P=8897 if BR=='chromium' else 8898
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',P),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
HOST=f'http://127.0.0.1:{P}'
F=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c:F.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
_av=re.search(r"const APP_VERSION='(\d+)'",html);_vj=json.load(open(os.path.join(D,'version.json')))['version']
ck(_av and int(_av.group(1))>=28 and _vj==_av.group(1),'APP_VERSION and version.json match and are >=28')
ck("register('sw.js?v='+encodeURIComponent(APP_VERSION)" in html and "'numirealm-v'+V" in open(os.path.join(D,'sw.js')).read().replace('"',"'"),'service worker cache name follows APP_VERSION')
ck('playBox' not in html and 'Time played' not in html and 'nr-pc-' not in html,'no portal UI in the game')
sql4=open(os.path.join(D,'supabase','setup-part4.sql'),encoding='utf-8').read().lower() if os.path.exists(os.path.join(D,'supabase','setup-part4.sql')) else ''
ck(all(k in sql4 for k in ['create table if not exists public.quests','enable row level security','public.get_home','public.quest_progress','400']) and 'interval \'180 days\'' not in sql4,'setup-part4.sql: Parent Center tables, RLS, RPCs, 400-day log')
sql4=open(os.path.join(D,'supabase/setup-part4.sql'),encoding='utf-8').read()
ck(all(ord(c)<128 for c in sql4) and 'add column if not exists play jsonb' in sql4 and 'create or replace function public.push_progress' in sql4 and 'coalesce(excluded.play, p.play)' in sql4,'setup-part4.sql: ASCII-only, idempotent, keeps the old log when a device sends none')
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    for q in ['','?parenttest=1']:
        tag='flag' if q else 'noflag'
        c=b.new_context(viewport={'width':390,'height':844});pg=c.new_page();sb=[]
        pg.on('request',lambda r:sb.append(r.url) if 'supabase' in r.url else None)
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.route('**/*supabase.co/**',lambda r:r.abort())
        pg.clock.install()
        pg.goto(f'{HOST}/index.html{q}');pg.clock.run_for(2000)
        pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())")
        pg.evaluate("void((!save.hero||!save.profiles[save.hero])&&pickHero(Object.keys(HEROES)[0]))");pg.clock.run_for(500)
        hero=pg.evaluate("save.hero");pg.evaluate("void(localStorage.removeItem('nr-playlog'))")
        today=pg.evaluate("NRT.dkey(new Date())")
        sec=lambda:pg.evaluate(f"((JSON.parse(localStorage.getItem('nr-playlog')||'{{}}')[{json.dumps(hero)}]||{{}}).d||{{}})[{json.dumps(today)}]||0")
        ck(today==datetime.date.today().isoformat(),f'{tag}: day key is the LOCAL date ({today})')
        pg.clock.run_for(90000);ck(sec()==0,f'{tag}: no touches -> idle, nothing recorded')
        pg.evaluate("void(dispatchEvent(new Event('pointerdown')))");pg.clock.run_for(30000);s1=sec()
        ck(20<=s1<=30,f'{tag}: active play recorded silently ({s1}s after 30s)')
        pg.clock.run_for(180000);s2=sec()
        ck(s2-s1<=60 and s2<=90,f'{tag}: stops counting once idle >60s ({s2}s total after 3 more idle minutes)')
        pg.evaluate("void(document.dispatchEvent(new KeyboardEvent('keydown',{key:'a'})))");pg.clock.run_for(10000);ck(sec()>s2,f'{tag}: keyboard counts as activity')
        # prune / roll-up
        pg.evaluate(f"void(NRT.add({json.dumps(hero)},600,new Date(Date.now()-450*864e5)))");pg.evaluate(f"void(NRT.add({json.dumps(hero)},60,new Date()))")
        raw=pg.evaluate(f"NRT.raw()[{json.dumps(hero)}]");old=(datetime.date.today()-datetime.timedelta(days=450)).isoformat()
        ck(old not in raw['d'] and min(raw['d'])>=(datetime.date.today()-datetime.timedelta(days=400)).isoformat() and raw['m'].get(old[:7],0)>=600,f'{tag}: days older than 400 roll into months')
        # payload (what push_progress would send)
        pl=pg.evaluate(f"NRP.payload(save,{json.dumps(hero)}).play")
        ck(pl and pl['end']==today and pl['days'] and pl['days'][-1]==round(sec()/60) and all(isinstance(x,int) for x in pl['days']),f'{tag}: payload carries play log, minutes per day ending today ({pl and pl["days"][-3:]})')
        # worst case size: 400 full days + 10 years of months still far under the 20 kB server limit
        pg.evaluate(f"""void((()=>{{const a=JSON.parse(localStorage.getItem('nr-playlog'));const o=a[{json.dumps(hero)}];for(let i=0;i<400;i++){{o.d[NRT.dkey(new Date(Date.now()-i*864e5))]=86400;}}
          for(let i=14;i<140;i++){{const d=new Date();d.setMonth(d.getMonth()-i);o.m[NRT.dkey(d).slice(0,7)]=99999999;}}localStorage.setItem('nr-playlog',JSON.stringify(a));}})())""")
        pl=pg.evaluate(f"NRP.payload(save,{json.dumps(hero)})");n=len(json.dumps(pl['play'],separators=(',',':')))
        ck(len(pl['play']['days'])==400 and n<9000 and len(json.dumps(pl,separators=(',',':')))<12000,f'{tag}: full log stays compact ({n} bytes)')
        pg.evaluate("void(localStorage.setItem('nr-playlog','not json'))");pg.evaluate("void(dispatchEvent(new Event('pointerdown')))");pg.clock.run_for(10000)
        ck(pg.evaluate("typeof NRT.summary(save.hero).days")=='object',f'{tag}: corrupt log is reset, no crash')
        ck(sb==[],f'{tag}: unlinked device makes no Supabase requests')
        ck(pg.locator('#playBox').count()==0,f'{tag}: nothing new on screen')
        pg.evaluate("titleScreen()");pg.clock.run_for(500)
        ck(pg.locator('#nrQuest:visible').count()==0 and not pg.evaluate("localStorage.getItem('nr-parent-home')"),f'{tag}: no quest scroll and no Parent Center data on an unlinked device')
        ck((pg.locator('#nrQuest').count()==0)==(tag=='noflag'),f'{tag}: quest slot only exists with the test flag')
        pg.evaluate("NRQ.onAns('mult:x7',true)");ck(not pg.evaluate("localStorage.getItem('nr-parent-qp')"),f'{tag}: answers not tracked for quests when unlinked')
        c.close()
    # parent page helpers (pure functions) on a page with Supabase blocked
    c=b.new_context();pg=c.new_page();pg.route('**/*supabase.co/**',lambda r:r.abort());pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto(f'{HOST}/parent.html');pg.wait_for_timeout(800)
    r=pg.evaluate("""(()=>{const out={};
      out.none=playData(null,null).src; out.junk=playData({play:{days:'x',end:5}},[]).src; out.emptyLog=playData({play:{v:1,end:'2026-01-01',days:[],months:{}}},null).src;
      out.ev=playData(null,[{day:'2099-01-03',minutes:30},{day:'2099-01-01',minutes:10},{day:'2099-01-02',minutes:4}]);
      out.html=playHTML(undefined,undefined,'year').includes('playEmpty');
      out.fmt=[fmtMin(0),fmtMin(59),fmtMin(60),fmtMin(85)];
      const pd={days:{},months:{}};const t=new Date();t.setHours(12);pd.days[dk(t)]=7;
      out.lens=['day','week','month','year'].map(k=>playBuckets(pd,k).length);out.last=['day','week','month','year'].map(k=>playBuckets(pd,k).slice(-1)[0].v);return out;})()""")
    ck(r['none']=='none' and r['junk']=='none' and r['emptyLog']=='none' and r['html'],'parent: missing/garbled/empty logs show the empty state, no crash')
    ck(r['ev']['src']=='events' and r['ev']['days']=={'2099-01-01':10,'2099-01-03':26},f'parent: estimate from daily totals clamps resets to 0 ({r["ev"]["days"]})')
    ck(r['fmt']==['0 min','59 min','1 h','1 h 25 min'],f'parent: total formatting {r["fmt"]}')
    ck(r['lens'][:3]==[14,12,12] and r['lens'][3]>=1 and r['last']==[7,7,7,7],f'parent: bucket counts {r["lens"]} and today lands in every current bucket')
    c.close();b.close()
ck(not errs,f'no page errors {errs[:3]}')
print(f'\n{BR}: {"ALL PASS" if not F else str(len(F))+" FAIL"}')
srv.shutdown();raise SystemExit(1 if F else 0)
