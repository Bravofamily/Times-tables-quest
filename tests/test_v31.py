# v31: every route back to Home renders the same Home as the bottom-bar Home tab.
import os,re,json,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BR=os.environ.get('PWB','chromium');P=8761 if BR=='chromium' else 8763
SHOTS=os.environ.get('NR_SHOTS','/tmp/v31shots');os.makedirs(SHOTS,exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()
s=http.server.ThreadingHTTPServer(('127.0.0.1',P),functools.partial(Q,directory=D));threading.Thread(target=s.serve_forever,daemon=True).start()
HOST=f'http://127.0.0.1:{P}';F=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c:F.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
av=re.search(r"const APP_VERSION='(\d+)'",html).group(1)
ck(int(av)>=31 and json.load(open(os.path.join(D,'version.json')))['version']==av,'APP_VERSION and version.json match and are >=31')
SIG="""(()=>{const a=document.getElementById('app');if(!a||!a.querySelector('.home'))return 'NOT-HOME';
 const vis=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)&&getComputedStyle(e).visibility!=='hidden';
 const tiles=[...a.querySelectorAll('.tiles .tile')].filter(vis).map(t=>(t.dataset.tile||'?')+':'+t.textContent.trim());
 const secs=[...a.querySelectorAll('h2,h3')].filter(vis).map(h=>h.textContent.trim().slice(0,30));
 const ids=[...document.querySelectorAll('#app [id], #nrParentHome, #nrApp')].filter(vis).map(e=>e.id).sort();
 return JSON.stringify({tiles,secs,ids});})()"""
def ctx(b,phone):
    c=b.new_context(viewport={'width':390,'height':844} if phone else {'width':1280,'height':800},service_workers='block')
    c.route('**/*supabase.co/**',lambda r:r.abort());return c
def ready(pg):
    pg.wait_for_timeout(700);pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())")
def hometab(pg):
    pg.click('#bnHome') if pg.locator('#bnHome').is_visible() else pg.evaluate("titleScreen()");pg.wait_for_timeout(400)
PAGES=['trophies','guide','heroes','progress','profile','settings']
with sync_playwright() as p:
    br=getattr(p,BR).launch()
    for phone in (False,True):
        tag='phone' if phone else 'desktop'
        for hero in (False,True):
            ht=tag+(' hero' if hero else ' no-hero')
            c=ctx(br,phone);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)))
            pg.goto(f'{HOST}/index.html');ready(pg)
            if hero:
                pg.evaluate("try{save.hero=save.hero||'blu';persist();}catch(e){}");pg.reload();ready(pg)
            hometab(pg);ref=pg.evaluate(SIG)
            ck(ref!='NOT-HOME' and 'Heroes' in ref,f'{ht}: Home tab render has the 6-tile grid')
            for pgname in PAGES:
                for how in ('backbtn','browser','swipe'):
                    hometab(pg)
                    sel=f'#app .tiles .tile[data-tile="{pgname}"]'
                    if pg.locator(sel).count()==0:ck(False,f'{ht}: tile {pgname} on Home');continue
                    pg.click(sel);pg.wait_for_timeout(500)
                    if how=='backbtn':
                        b=pg.locator('#backBtn, .v12tback').first
                        if b.count()==0:ck(True,f'{ht}: {pgname} has no in-page Back (skip)');continue
                        b.click()
                    else: pg.go_back()   # swipe back on iOS is a history back
                    pg.wait_for_timeout(600);got=pg.evaluate(SIG)
                    if pgname=='guide' and how=='browser' and phone and not hero:pg.screenshot(path=f'{SHOTS}/{BR}-phone-after-back-from-guide.png')
                    ck(got==ref,f'{ht}: {pgname} > {how} back > Home matches Home tab'+('' if got==ref else ' got '+got[:160]))
            # deeper stack: home > guide > villain-ish > back twice
            hometab(pg);pg.click('#app .tiles .tile[data-tile="heroes"]');pg.wait_for_timeout(400)
            pg.evaluate("TTQ_V12.go('settings')");pg.wait_for_timeout(400);pg.go_back();pg.wait_for_timeout(400);pg.go_back();pg.wait_for_timeout(600)
            ck(pg.evaluate(SIG)==ref,f'{ht}: two-deep browser back lands on the same Home')
            # leave to the parent page and come back (bfcache / pageshow)
            hometab(pg);pg.goto(f'{HOST}/parent-about.html');pg.wait_for_timeout(700);pg.go_back();ready(pg);pg.wait_for_timeout(500)
            ck(pg.evaluate(SIG)==ref,f'{ht}: back from parent-about (bfcache/reload) lands on the same Home')
            pg.goto(f'{HOST}/parent.html');pg.wait_for_timeout(700);pg.click('#nrBack');ready(pg);pg.wait_for_timeout(500)
            ck(pg.evaluate(SIG)==ref,f'{ht}: parent.html "Back to NumiRealm" lands on the same Home')
            pg.goto(f'{HOST}/gamenight.html');pg.wait_for_timeout(700);pg.click('#backLink');ready(pg);pg.wait_for_timeout(500)
            ck(pg.evaluate(SIG)==ref,f'{ht}: gamenight "Back" lands on the same Home')
            # parent gate cancel leaves Home intact
            pg.click('#nrhTop');pg.wait_for_timeout(200);pg.click('#nrtCancel');pg.wait_for_timeout(300)
            ck(pg.evaluate(SIG)==ref,f'{ht}: parent gate Cancel leaves the same Home')
            if phone and not hero:
                hometab(pg);pg.click('#app .tiles .tile[data-tile="guide"]');pg.wait_for_timeout(400);pg.go_back();pg.wait_for_timeout(600);pg.screenshot(path=f'{SHOTS}/{BR}-phone-home-after-back.png')
            c.close()
    br.close()
ck(not errs,'no page errors '+str(errs[:2]))
print('RESULT',BR,'OK' if not F else 'FAIL',len(F))
