# v33 CR33-4 offline mode audit: every page, network log, 0 non-localhost requests, no version check,
# Game Night + Parent Area disabled with a clear message, save counter (seq) in the payload. Synthetic data only.
# Usage: PWB=chromium|webkit python test_v33_offline.py   (writes /tmp/v33/offline-net-<browser>.json and screenshots)
import os,threading,http.server,functools,json
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));BR=os.environ.get('PWB','chromium')
PORT=int(os.environ.get('NR_PORT') or (8897 if BR=='chromium' else 8898))
SH=os.environ.get('SHOTS_DIR','/workspace/v33shots/offline');os.makedirs(SH,exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
fails=[];B=f'http://127.0.0.1:{PORT}/'
def ck(c,m,info=''):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m+(f'  :: {info}' if info else ''))
    if not c: fails.append(m)
LINK=json.dumps({'token':'t'*40,'hero':'x','kid':'k','dev':'test'})
PAGES=['index.html','gamenight.html','parent.html','parent-about.html','./']
audit={}
with sync_playwright() as p:
    br=getattr(p,BR).launch()
    for vp,(w,h) in {'desktop':(1280,860),'phone':(390,844)}.items():
        ctx=br.new_context(viewport={'width':w,'height':h},is_mobile=(vp=='phone' and BR=='chromium'),has_touch=(vp=='phone'))
        log=[]
        ctx.on('request',lambda r: log.append(r.url))
        ctx.route('**/*',lambda r: r.abort() if not r.request.url.startswith(B) and not r.request.url.startswith(('data:','blob:')) else r.continue_())
        pg=ctx.new_page()
        # first visit ONLINE (installs the service worker), then switch offline mode on
        pg.goto(B+'index.html');pg.wait_for_timeout(1200)
        log.clear()
        pg.goto(B+'index.html?localonly=1');pg.wait_for_timeout(1000)
        pg.evaluate(f"()=>localStorage.setItem('nr-parent-link',{json.dumps(LINK)})")
        for pgname in PAGES:
            before=len(log);pg.goto(B+pgname);pg.wait_for_timeout(1500)
            if pgname=='index.html':
                pg.evaluate("async()=>{try{TTQ_VERSION.check(true);}catch(e){} try{NRP.queue();}catch(e){} try{await NRP.flush();}catch(e){}}");pg.wait_for_timeout(3000)
                ck(pg.evaluate('window.NR_LOCALONLY')==True,f'{vp} {pgname}: offline flag on')
                s1=pg.evaluate("()=>NRP.payload(save,save.hero||Object.keys(save.profiles)[0]).seq");s2=pg.evaluate("()=>NRP.payload(save,save.hero||Object.keys(save.profiles)[0]).seq")
                ck(isinstance(s1,int) and s2==s1+1,f'{vp}: save counter seq goes up by one per snapshot',f'{s1}->{s2}')
            ext=[u for u in log[before:] if not u.startswith(B) and not u.startswith(('data:','blob:'))]
            ver=[u for u in log[before:] if 'version.json' in u]
            audit.setdefault(vp,{})[pgname]={'requests':len(log)-before,'non_localhost':ext,'version_checks':ver,'blocked_in_page':pg.evaluate('window.NR_OFFLINE_BLOCKED||[]')}
            ck(len(ext)==0,f'{vp} {pgname}: 0 non-localhost requests',str(ext[:3]))
            ck(len(ver)==0,f'{vp} {pgname}: no version.json check')
            ck(pg.locator('#nrOfflineBadge').count()==1,f'{vp} {pgname}: offline badge shown')
            ck(pg.locator('text=🏠 Back to NumiRealm').count()>=1 or pgname in ('index.html','./'),f'{vp} {pgname}: Back to NumiRealm button')
            if pgname=='gamenight.html':
                ck(pg.locator('#gnOffline').is_visible() and pg.locator('#joinBtn').count()==0 and pg.locator('#hostBtn').count()==0,f'{vp}: Game Night disabled with a clear message')
                ck(pg.locator('text=Enter the Realm. Master the Math.').count()>=1,f'{vp}: tagline on Game Night')
                pg.screenshot(path=f'{SH}/{BR}-{vp}-gamenight-offline.png')
                sw=pg.evaluate("()=>document.documentElement.scrollWidth<=innerWidth+1");ck(sw,f'{vp}: Game Night offline card fits the screen (no sideways scroll)')
            if pgname=='parent.html':
                ck(pg.locator('#pOffline').is_visible(),f'{vp}: Parent Area disabled with a clear message')
                pg.screenshot(path=f'{SH}/{BR}-{vp}-parent-offline.png')
            if pgname=='index.html': pg.screenshot(path=f'{SH}/{BR}-{vp}-home-offline.png')
        # direct fetch attempts are refused in the page
        r=pg.evaluate("async()=>{const o=[];for(const u of ['https://uuigasrelqbwxopvqoib.supabase.co/rest/v1/','https://fonts.googleapis.com/css','version.json']){try{await fetch(u);o.push('sent')}catch(e){o.push('blocked')}}try{new WebSocket('wss://example.com/x');o.push('sent')}catch(e){o.push('blocked')}return o}")
        ck(r==['blocked']*4,f'{vp}: page-level guard blocks Supabase, fonts CDN, version.json and WebSockets',str(r))
        # Game Night join link cannot bypass the gate
        before=len(log);pg.goto(B+'gamenight.html?join=ABCDE');pg.wait_for_timeout(1500)
        ext=[u for u in log[before:] if not u.startswith(B)];ck(len(ext)==0 and pg.locator('#gnOffline').count()==1,f'{vp}: Game Night ?join link stays offline',str(ext[:3]))
        # turning off restores normal behavior
        pg.goto(B+'index.html?localonly=0');pg.wait_for_timeout(600)
        ck(pg.evaluate('window.NR_LOCALONLY')==False and pg.locator('#nrOfflineBadge').count()==0,f'{vp}: ?localonly=0 turns offline mode off')
        pg.goto(B+'gamenight.html');pg.wait_for_timeout(800);ck(pg.locator('#joinBtn').count()==1,f'{vp}: Game Night back when offline mode is off')
        ctx.close()
    br.close()
json.dump(audit,open(f'/tmp/v33/offline-net-{BR}.json','w'),indent=1)
print(f'RESULT v33-offline [{BR}] fails={len(fails)}')
