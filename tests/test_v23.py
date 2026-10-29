# v23: "Get the NumiRealm app" card on Home + real manifest/icons (installable PWA).
# Usage: PWB=chromium|webkit python test_v23.py   (SHOTS=1 -> /workspace/v23shots)
import os,json,threading,http.server,functools,struct
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))));BR=os.environ.get('PWB','chromium');SH=os.environ.get('SHOTS')=='1'
OUT='/workspace/v23shots';os.makedirs(OUT,exist_ok=True)
PORT=8842 if BR=='chromium' else 8843
class Q(http.server.SimpleHTTPRequestHandler):
    extensions_map={**http.server.SimpleHTTPRequestHandler.extensions_map,'.webmanifest':'application/manifest+json'}
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
BASE=f'http://localhost:{PORT}/'
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c: fails.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
ck("const APP_VERSION='23'" in html and json.load(open(os.path.join(D,'version.json')))['version']=='23','version 23 everywhere')
ck('<link rel="manifest" href="manifest.webmanifest">' in html and 'data:application/manifest' not in html,'real manifest link, no data: manifest')
ck('<link rel="apple-touch-icon" sizes="180x180" href="icons/apple-touch-icon-180.png">' in html,'apple-touch-icon is a real 180 PNG file')
sw=open(os.path.join(D,'sw.js')).read()
NEW=['manifest.webmanifest','icons/icon-192.png','icons/icon-512.png','icons/icon-maskable-512.png','icons/apple-touch-icon-180.png']
ck(all("'./%s'"%f in sw for f in NEW),'sw.js precaches manifest and icons')
m=json.load(open(os.path.join(D,'manifest.webmanifest'),encoding='utf-8'))
ck(m['name']=='NumiRealm' and m['short_name']=='NumiRealm' and m['start_url']=='./' and m['scope']=='./' and m['display']=='standalone' and m['theme_color'] and m['background_color'],'manifest fields')
def pngsize(p):
    b=open(os.path.join(D,p),'rb').read(24);return b[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',b[16:24])
for ic in m['icons']:
    w,h=map(int,ic['sizes'].split('x'));ck(pngsize(ic['src'])==(w,h),'icon %s is a %s PNG (%s)'%(ic['src'],ic['sizes'],ic.get('purpose')))
ck(any(i.get('purpose')=='maskable' for i in m['icons']),'has maskable icon');ck(pngsize('icons/apple-touch-icon-180.png')==(180,180),'apple-touch-icon 180x180')
SAVE={"muted":True,"narrator":False,"lastHero":"emi","profiles":{"emi":{"name":"Emi","stars":{"2":3},"hist":{},"rewards":["fcrown"],"eq":{},"prologue":True,"age":"6-7","grade":"1"}}}
UA={'ios':'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1',
 'android':'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36',
 'desktop':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'}
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    def page(w=1280,h=900,ua=None,mobile=False,init=''):
        kw=dict(viewport={'width':w,'height':h},service_workers='block')
        if ua: kw['user_agent']=ua
        if mobile: kw.update(has_touch=True,**({'is_mobile':True,'device_scale_factor':2} if BR=='chromium' else {}))
        c=b.new_context(**kw);c.add_init_script("localStorage.setItem('ttq-save-v2',%s);"%json.dumps(json.dumps(SAVE))+init)
        pg=c.new_page();tag=f'{w}'
        pg.on('console',lambda x: errs.append(f'[{tag}] {x.text}') if x.type=='error' else None);pg.on('pageerror',lambda e: errs.append(f'[{tag}] PAGEERR {e}'))
        pg.goto(BASE+'index.html');pg.wait_for_timeout(1300);pg.evaluate("titleScreen()");pg.wait_for_timeout(500);return c,pg
    for w,h,tag,mob,pf in ((1280,900,'desktop',False,'desktop'),(390,844,'phone',True,'ios')):
        c,pg=page(w,h,UA[pf],mob)
        ck(pg.locator('#app #nrApp').count()==1,f'{tag}: card on Home')
        last=pg.evaluate("(()=>{const a=document.getElementById('app');return a.lastElementChild&&a.lastElementChild.id})()")
        ck(last=='nrApp','%s: card is the last thing on Home (%s)'%(tag,last))
        ck(pg.evaluate("document.getElementById('nrApp').getBoundingClientRect().bottom<=document.getElementById('nrFoot').getBoundingClientRect().top+1"),f'{tag}: card sits above the footer')
        ck(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),f'{tag}: no sideways scroll')
        ck(pg.locator('#nrInstallBtn').is_hidden(),f'{tag}: no install button without beforeinstallprompt')
        t=pg.inner_text('#nrApp');ck('offline' in t and 'device' in t,f'{tag}: mentions offline and on-device progress')
        pg.click('#nrAppDet summary');pg.wait_for_timeout(200)
        first=pg.evaluate("document.querySelector('#nrApp .nrtab').dataset.k");ck(first==pf,f'{tag}: own platform tab first ({first})')
        ck(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),f'{tag}: expanded card no sideways scroll')
        if SH:
            pg.locator('#nrApp').scroll_into_view_if_needed();pg.evaluate("scrollTo(0,document.body.scrollHeight)");pg.wait_for_timeout(300)
            pg.screenshot(path=f'{OUT}/{BR}-{tag}-home-bottom-{pf}.png');pg.locator('#nrApp').screenshot(path=f'{OUT}/{BR}-{tag}-card-expanded-{pf}.png')
            pg.click('.nrtab[data-k=android]');pg.wait_for_timeout(200);pg.locator('#nrApp').screenshot(path=f'{OUT}/{BR}-{tag}-card-android.png')
        c.close()
    EXP={'ios':['Safari','Share','Add to Home Screen'],'android':['Chrome','⋮','Install app'],'desktop':['Edge','install icon','Install NumiRealm']}
    for pf in ('ios','android','desktop'):
        c,pg=page(390 if pf!='desktop' else 1280,844,UA[pf],pf!='desktop');pg.click('#nrAppDet summary')
        t=pg.inner_text('#nrSteps');ck(all(x in t for x in EXP[pf]) and pg.evaluate("document.querySelector('#nrApp .nrtab').dataset.k")==pf,f'{pf} UA: {pf} steps shown first')
        if pf=='ios': ck('App Store' not in pg.inner_text('#nrApp').replace('app store','') ,'no App Store claim')
        c.close()
    c,pg=page(390,844,UA['ios'],True,init="Object.defineProperty(navigator,'standalone',{get:()=>true});")
    ck(pg.locator('#nrDet,#nrAppDet').count()==0 and "app version" in pg.inner_text('#nrApp'),'standalone (navigator.standalone): steps hidden, "You\'re playing the app version"');c.close()
    c,pg=page(init="const _mm=window.matchMedia.bind(window);window.matchMedia=q=>/display-mode: *standalone/.test(q)?{matches:true,media:q,addListener(){},removeListener(){},addEventListener(){},removeEventListener(){}}:_mm(q);")
    ck(pg.locator('#nrAppDet').count()==0 and "app version" in pg.inner_text('#nrApp'),'standalone (display-mode): app-version message');c.close()
    c,pg=page()
    pg.evaluate("window.__p=0;const e=new Event('beforeinstallprompt',{cancelable:true});e.prompt=()=>{window.__p++};e.userChoice=Promise.resolve({outcome:'accepted'});window.dispatchEvent(e)");pg.wait_for_timeout(200)
    ck(pg.locator('#nrInstallBtn').is_visible(),'install button appears on beforeinstallprompt')
    pg.click('#nrInstallBtn');pg.wait_for_timeout(300);ck(pg.evaluate("window.__p")==1 and pg.locator('#nrInstallBtn').is_hidden(),'install button calls prompt() and hides')
    pg.evaluate("titleScreen()");pg.wait_for_timeout(300);ck(pg.locator('#nrApp').count()==1,'card re-renders once after returning Home')
    for f in NEW:
        r=pg.request.get(BASE+f);ck(r.ok,f'{f} fetchable over http')
    ck(pg.evaluate("fetch('manifest.webmanifest').then(r=>r.json()).then(j=>j.name)")=='NumiRealm','manifest parses in page')
    if BR=='chromium':
        s=c.new_cdp_session(pg);ie=s.send('Page.getInstallabilityErrors')['installabilityErrors'];ck(ie==[],'Chromium installability errors: %s'%ie)
        mf=s.send('Page.getAppManifest');ck(not mf.get('errors') and mf['url'].endswith('manifest.webmanifest'),'Chromium parsed manifest without errors (%s)'%mf.get('errors'))
    c.close();b.close()
ck(errs==[],'no console errors (%s)'%errs[:5])
print('RESULT',BR,'FAILS',len(fails));raise SystemExit(1 if fails else 0)
