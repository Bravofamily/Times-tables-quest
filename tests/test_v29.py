# v29: the parent test flag survives round trips (home > Parent Login > back) and the update flow upgrades an old install.
# Usage: PWB=chromium|webkit python test_v29.py
import os,re,json,shutil,tempfile,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BR=os.environ.get('PWB','chromium');P=8741 if BR=='chromium' else 8743
SHOTS=os.environ.get('NR_SHOTS','/tmp/v29shots');os.makedirs(SHOTS,exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()
def serve(d,port):
    s=http.server.ThreadingHTTPServer(('127.0.0.1',port),functools.partial(Q,directory=d));threading.Thread(target=s.serve_forever,daemon=True).start();return s
serve(D,P);HOST=f'http://127.0.0.1:{P}'
F=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c:F.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
av=re.search(r"const APP_VERSION='(\d+)'",html).group(1)
ck(int(av)>=29 and json.load(open(os.path.join(D,'version.json')))['version']==av,'APP_VERSION and version.json match and are >=29')
sw=open(os.path.join(D,'sw.js')).read()
ck("updateViaCache:'none'" in html and 'skipWaiting' in sw and 'clients.claim' in sw and "cache:'no-store'" in sw,'SW: no HTTP cache, skipWaiting, clientsClaim, network-first pages')
def btn(pg):
    pg.wait_for_timeout(900);return pg.locator('#nrhTop').count()>0 and pg.locator('#nrhTop').is_visible()
def ctx(b,phone=False):
    c=b.new_context(viewport={'width':390,'height':844} if phone else {'width':1280,'height':800},service_workers='block')
    c.route('**/*supabase.co/**',lambda r:r.abort());return c
def home(pg,q=''):
    pg.goto(f'{HOST}/index.html{q}');pg.wait_for_timeout(1200)
    pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())")
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    c=ctx(b);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)))
    home(pg);ck(not btn(pg),'no flag ever: Parent Login hidden')
    home(pg,'?parenttest=1');ck(btn(pg),'?parenttest=1: Parent Login shown')
    for page,backid in [('parent.html','#nrBack'),('parent-about.html','#nrBack'),('gamenight.html','#backLink')]:
        for q in ['?parenttest=1','']:  # '' = arrived without the query (sign-in redirect, email link, new tab)
            pg.goto(f'{HOST}/{page}{q}');pg.wait_for_timeout(900)
            href=pg.get_attribute(backid,'href');ck(href=='./?parenttest=1',f'{page}{q or " (no query)"}: back link keeps the flag ({href})')
            pg.click(backid);pg.wait_for_load_state();pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())")
            ck(btn(pg),f'{page}{q or " (no query)"} > Back: Parent Login still visible')
    # real tap path: Parent Login gate > parent.html > back
    home(pg);pg.click('#nrhTop');g=pg.evaluate("document.getElementById('nrtQ').textContent")
    a,bb,cc=map(int,re.findall(r'\d+',g));pg.fill('#nrtGate',str(a*bb+cc));pg.click('#nrtGo');pg.wait_for_url('**/parent.html*');pg.wait_for_timeout(700)
    pg.click('#nrBack');pg.wait_for_load_state();ck(btn(pg),'tap Parent Login > gate > parent.html > Back to NumiRealm: button stays')
    pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())");pg.wait_for_timeout(500)
    pg.screenshot(path=f'{SHOTS}/{BR}-desktop-roundtrip-home.png')
    pg.goto(f'{HOST}/'); pg.wait_for_timeout(900);ck(btn(pg),'start_url ./ (installed app) with the remembered flag: button shown')
    home(pg,'?parenttest=0');ck(not btn(pg),'?parenttest=0 clears the flag');home(pg);ck(not btn(pg),'stays cleared after reload')
    c.close()
    c=ctx(b,True);pg=c.new_page();home(pg,'?parenttest=1')
    pg.goto(f'{HOST}/gamenight.html');pg.wait_for_timeout(800);pg.click('#backLink');pg.wait_for_load_state()
    pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())")
    ck(btn(pg),'phone: gamenight > back keeps the button');pg.screenshot(path=f'{SHOTS}/{BR}-phone-roundtrip-home.png');c.close()
    # linked device without the flag still sees the Game Night card logic unchanged
    c=ctx(b);pg=c.new_page();home(pg);pg.evaluate("localStorage.setItem('nr-parent-link',JSON.stringify({dev:'x',code:'ABC123'}))");home(pg)
    ck(pg.evaluate("NRP.link()!=null") and not btn(pg),'linked device without flag: SHOW_HOME stays off (unchanged)');c.close()
    # update reload keeps the query
    c=ctx(b);pg=c.new_page();c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"999"}'))
    pg.goto(f'{HOST}/index.html?parenttest=1&link=ABC123');pg.wait_for_timeout(2500)
    ck('parenttest=1' in pg.url and 'v=999' in pg.url,'auto-update reload keeps ?parenttest ('+pg.url.split('/')[-1]+')');c.close()
    # update flow with a real service worker: old v28 install + new version.json upgrades
    if BR=='chromium':
        old=os.environ.get('NR_OLD','/workspace/v28-repo');T=tempfile.mkdtemp();site=os.path.join(T,'s');shutil.copytree(old,site,ignore=shutil.ignore_patterns('tests'))
        serve(site,P+10);H2=f'http://127.0.0.1:{P+10}'
        c=b.new_context();pg=c.new_page();pg.goto(H2+'/index.html');pg.wait_for_timeout(3000)
        ck(pg.evaluate("navigator.serviceWorker.controller!=null")and pg.evaluate("TTQ_VERSION.app")=='28','old v28 install is SW-controlled')
        for f in ['index.html','sw.js','version.json','parent.html','parent-about.html','gamenight.html','manifest.webmanifest']:shutil.copy(os.path.join(D,f),os.path.join(site,f))
        pg.goto(H2+'/index.html');pg.wait_for_timeout(4000)
        ck(pg.evaluate("TTQ_VERSION.app")==av,f'after release the app runs v{av} ({pg.evaluate("TTQ_VERSION.app")})')
        ks=pg.evaluate("caches.keys()");ck(f'numirealm-v{av}' in ks and 'numirealm-v28' not in ks,f'old cache removed {ks}')
        c.close()
    b.close()
ck(not errs,'no page errors '+str(errs[:3]))
print('RESULT',BR,'FAIL' if F else 'OK',len(F))
