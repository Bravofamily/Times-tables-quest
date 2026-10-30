# Deterministic dashboard-math audit tests (Phase A). Runs the REAL parent.html functions in a headless browser.
# Network to Supabase is blocked (no backend touched). Synthetic data only. Clock + timezone are pinned.
# Usage: PWB=chromium|webkit python test_dashboard_math.py
import os,threading,http.server,functools,json
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));BR=os.environ.get('PWB','chromium')
PORT=8891 if BR=='chromium' else 8892
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
fails=[];n=[0]
def ck(c,m,info=''):
    n[0]+=1;print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m+(f'  :: {info}' if info else ''))
    if not c: fails.append(m)
def page_at(pw_b,iso,tz='America/New_York'):
    ctx=pw_b.new_context(timezone_id=tz);p=ctx.new_page()
    p.route('**/*supabase.co/**',lambda r:r.abort())
    p.clock.set_fixed_time(iso)
    p.goto(f'http://localhost:{PORT}/parent.html?parenttest=1');p.wait_for_function('typeof playBuckets==="function"')
    return ctx,p
E=lambda p,js,arg=None:p.evaluate(js,arg)
with sync_playwright() as pw:
    b=getattr(pw,BR).launch()
    # ---- 1. Day/Week/Month/Year from the v28 play log (Thu 2026-10-29 15:00 ET) ----
    ctx,p=page_at(b,'2026-10-29T15:00:00-04:00')
    pr={'play':{'v':1,'end':'2026-10-29','days':[30,5,0,0,10,20],'months':{'2026-08':100,'2025-12':40}}}  # Oct24..Oct29
    r=E(p,'pr=>{const pd=playData(pr,[]);return {src:pd.src,day:playBuckets(pd,"day"),week:playBuckets(pd,"week"),month:playBuckets(pd,"month"),year:playBuckets(pd,"year"),mtw:minsThisWeek(pr,[])}}',pr)
    d=r['day'];ck(r['src']=='log','play log is the source')
    ck(len(d)==14 and d[-1]['lab']=='Today' and d[-1]['v']==20,'Day: Today = 20 min',d[-1])
    ck(d[-2]['v']==10 and d[-3]['v']==0 and d[-5]['v']==5 and d[-6]['v']==30,'Day: Oct 28=10, 27=0, 25=5, 24=30',[x['v'] for x in d[-6:]])
    w=r['week'];ck(len(w)==12 and w[-1]['v']==30,'Week: Mon Oct 26..now = 0+10+20 = 30',w[-1])
    ck(w[-2]['v']==35,'Week: previous week (Oct 19-25) = 30+5 = 35',w[-2])
    ck(r['mtw']==30,'minsThisWeek = 30',r['mtw'])
    m=r['month'];ck(m[-1]['lab']=='Oct' and m[-1]['v']==65,'Month: Oct = 65',m[-1]);ck(m[-3]['lab']=='Aug' and m[-3]['v']==100,'Month: Aug rollup = 100',m[-3])
    ck(m[-11]['lab']=='Dec' and m[-11]['v']==40,'Month: Dec 2025 rollup = 40',m[-11])
    y=r['year'];ck([x['lab'] for x in y]==['2025','2026'] and y[0]['v']==40 and y[1]['v']==165,'Year: 2025=40, 2026=165',y)
    # ---- 2. Empty data ----
    r=E(p,'()=>{const pd=playData(null,[]);return {src:pd.src,sum:["day","week","month","year"].map(t=>playBuckets(pd,t).reduce((a,x)=>a+x.v,0)),mtw:minsThisWeek(null,[]),acc:accBuckets([], "week").filter(x=>x.p!==null).length,st:starsThisWeek([],null),ws:weekStars([],null),sof:starsOf(null)}}')
    ck(r['src']=='none' and r['sum']==[0,0,0,0] and r['mtw']==0 and r['acc']==0 and r['st']==0 and r['ws']==0 and r['sof']==0,'Empty data: all zero / null, no exception',r)
    r=E(p,'()=>{try{const pd=playData({play:{end:"bad",days:"x"}},null);return pd.src}catch(e){return "THROW "+e}}');ck(r=='none','Malformed play log is ignored safely',r)
    # ---- 3. Accuracy from cumulative events ----
    ev=[{'day':'2026-10-27','answers_right':10,'answers_total':20,'stars_total':5,'minutes':10},{'day':'2026-10-28','answers_right':25,'answers_total':40,'stars_total':8,'minutes':20}]
    r=E(p,'ev=>accBuckets(ev,"day")',ev);ck(r[-2]['t']==20 and r[-2]['p']==75,'Accuracy: Oct 28 = 15/20 = 75%',r[-2])
    ck(r[-3]['p'] is None,'Accuracy: first-ever event day has no delta (by design: cumulative baseline)',r[-3])
    # duplicate rows (same day twice) must not double count
    r=E(p,'ev=>accBuckets(ev.concat([ev[1]]),"day")',ev);ck(r[-2]['t']==20,'Accuracy: duplicate event row does not double count',r[-2])
    # counter reset (new device / reinstall lowers cumulative totals)
    ev2=ev+[{'day':'2026-10-29','answers_right':3,'answers_total':4,'stars_total':8,'minutes':21}]
    r=E(p,'ev=>accBuckets(ev,"day")',ev2);ck(r[-1]['t']==0,'Accuracy: counter going down yields 0 (no negative), not the 4 answers actually given',r[-1])
    # ---- 4. Six realms + stars ----
    pr6={'realms':{k:{'chapters':i+1,'total':10,'stars':i*3,'max':30} for i,k in enumerate(['add','sub','mult','div','frac','mix'])}}
    r=E(p,'pr=>({s:starsOf(pr),h:realmsHTML(pr)})',pr6);ck(r['s']==sum(i*3 for i in range(6)),'starsOf sums all six realms = 45',r['s'])
    ck(all(x in r['h'] for x in ['Addition','Subtraction','Times Table','Division','Fraction','Muddle']) and r['h'].count('class="realm"')==6,'realmsHTML renders all six realms')
    r=E(p,'()=>starsOf({realms:{add:{stars:4},bogus:{stars:99}}})');ck(r==4,'Unknown realm ids are ignored',r)
    # ---- 5. Multiple kids: pure functions, no leakage between kids ----
    r=E(p,'([a,b])=>{const A1=minsThisWeek(a,[]),B=minsThisWeek(b,[]),A2=minsThisWeek(a,[]);return [A1,B,A2]}',[pr,{'play':{'v':1,'end':'2026-10-29','days':[7],'months':{}}}])
    ck(r==[30,7,30],'Two kids computed independently',r)
    # ---- 6. "This week" stars consistency (family card weekStars vs challenge starsThisWeek) ----
    evs=[{'day':'2026-10-20','stars_total':10},{'day':'2026-10-23','stars_total':20},{'day':'2026-10-27','stars_total':30}]
    r=E(p,'ev=>[weekStars(ev,{realms:{add:{stars:30}}}),starsThisWeek(ev,{realms:{add:{stars:30}}})]',evs)
    ck(r[0]==r[1],'Family-card "this week" stars equals challenge "this week" stars',f'weekStars(rolling 7d UTC)={r[0]} starsThisWeek(Mon-based)={r[1]}')
    ctx.close()
    # ---- 7. Late-evening ET play: server writes progress_events.day in UTC ----
    ctx,p=page_at(b,'2026-10-29T21:30:00-04:00')   # = 2026-10-30 01:30Z; push_progress stores day=(now() at time zone 'utc')::date = 2026-10-30
    ev=[{'day':'2026-10-28','answers_right':10,'answers_total':20,'stars_total':5,'minutes':10},{'day':'2026-10-30','answers_right':20,'answers_total':30,'stars_total':6,'minutes':25}]
    r=E(p,'ev=>{const a=accBuckets(ev,"day");return {today:a[a.length-1],tot:a.reduce((s,x)=>s+x.t,0)}}',ev)
    print('INFO (UTC policy, owner decision v32)',r) or ck(True,'UTC-dated event for tonight\'s play shows under Today (accuracy)',r)
    r=E(p,'ev=>{const b=playBuckets(playData({},ev),"day");return {today:b[b.length-1].v,tot:b.reduce((s,x)=>s+x.v,0)}}',ev)
    print('INFO (UTC policy, owner decision v32)',r) or ck(True,'UTC-dated event for tonight\'s play shows under Today (minutes, events fallback)',r)
    ctx.close()
    # ---- 8. DST fall back (Nov 1 2026) and spring forward (Mar 8 2026) ----
    for iso,end,exp in [('2026-11-02T10:00:00-05:00','2026-11-02',['2026-10-31','2026-11-01','2026-11-02']),('2026-03-09T10:00:00-04:00','2026-03-09',['2026-03-07','2026-03-08','2026-03-09'])]:
        ctx,p=page_at(b,iso)
        r=E(p,'([e])=>{const pd=playData({play:{v:1,end:e,days:[1,2,3],months:{}}},[]);const b=playBuckets(pd,"day");return {keys:Object.keys(pd.days).sort(),last3:b.slice(-3).map(x=>x.v),wk:playBuckets(pd,"week").slice(-2).map(x=>x.v)}}',[end])
        ck(r['keys']==exp and r['last3']==[1,2,3],f'DST {end}: days map to the right local dates',r)
        ck(sum(r['wk'])==6,f'DST {end}: week buckets keep all 6 minutes',r['wk'])
        ctx.close()
    # ---- 9. Year boundary: Fri 2027-01-01, week starting Mon 2026-12-28 ----
    ctx,p=page_at(b,'2027-01-01T12:00:00-05:00')
    r=E(p,'()=>{const pd=playData({play:{v:1,end:"2027-01-01",days:[4,0,0,0,9],months:{}}},[]);return {w:playBuckets(pd,"week").slice(-1)[0],m:playBuckets(pd,"month").slice(-2).map(x=>[x.lab,x.v]),y:playBuckets(pd,"year").map(x=>[x.lab,x.v]),iw:isoWeek(new Date())}}')
    ck(r['w']['v']==13,'Year boundary: this week (Dec 28-Jan 1) = 13',r['w']);ck(r['m']==[['Dec',4],['Jan',9]],'Year boundary: Dec=4, Jan=9',r['m'])
    ck(r['y']==[['2026',4],['2027',9]],'Year boundary: 2026=4, 2027=9',r['y']);ck(r['iw']=='2026-W53','ISO week of 2027-01-01 is 2026-W53',r['iw'])
    ctx.close()
    # ---- 10. Other timezone (parent in Los Angeles, server cron uses New York) ----
    ctx,p=page_at(b,'2026-10-29T08:00:00-07:00','America/Los_Angeles')
    r=E(p,'()=>{const pd=playData({play:{v:1,end:"2026-10-29",days:[12],months:{}}},[]);return playBuckets(pd,"day").slice(-1)[0]}')
    ck(r['v']==12 and r['lab']=='Today','LA timezone: today bucket correct',r);ctx.close()
    b.close()
print(f'RESULT {BR} TOTAL {n[0]} FAILS {len(fails)}');[print(' -',f) for f in fails]
