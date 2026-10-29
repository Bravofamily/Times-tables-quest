# v22 update of test_v19.py: same checks, adapted only for age groups, v22 version numbers and self-hosted fonts on file://
import os
# v19: one NumiRealm brand — titles/meta, favicon + touch icons, static loading screen, one logo component everywhere
import json,os,re,sys,base64,threading,http.server,functools,urllib.parse
from playwright.sync_api import sync_playwright

# ---- v22 test helpers (added by the v22 update of this suite) ----
def AR(a):
    """v22 stores an age group instead of an exact age; map an old exact age to its group key."""
    if isinstance(a,str) and '-' in a: return a
    a=int(a); return '4-5' if a<=5 else '6-7' if a<=7 else '8-10' if a<=10 else '11-14'
def MIG(o):
    """An old profile as v22 keeps it: identical except age -> age group."""
    o=dict(o)
    if 'age' in o: o['age']=AR(o['age'])
    return o
def _fontfile(m):
    """Chromium and WebKit block font loads from file:// pages (CORS); the game is served over https, where fonts load. Ignore only those."""
    try: u=(m.location or {}).get('url','')
    except Exception: u=''
    t=m.text
    return ("Access to font at 'file:" in t) or (u.endswith('.woff2') and 'ERR_FAILED' in t) or (u.endswith('.woff2') and 'Origin null is not allowed' in t) or (t=='Origin null is not allowed by Access-Control-Allow-Origin. Status code: 0' and not u)
import playwright.sync_api._generated as _pwg
for _cls in (_pwg.Page,_pwg.BrowserContext):
    _orig=_cls.on
    def _on(self,ev,f,_orig=_orig):
        if ev=='console':
            g=f; f=lambda m,g=g: None if _fontfile(m) else g(m)
        return _orig(self,ev,f)
    _cls.on=_on
# ---- end helpers ----
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))));PORT=8812;URL=f'http://127.0.0.1:{PORT}/index.html'
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(http.server.SimpleHTTPRequestHandler,directory=D));srv.RequestHandlerClass.log_message=lambda *a:None
threading.Thread(target=srv.serve_forever,daemon=True).start()
FAILS=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m);(None if c else FAILS.append(m))
HTML=open(D+'/index.html',encoding='utf-8').read()
SAVE={"muted":True,"narrator":False,"lastHero":"emi","profiles":{"emi":{"name":"Emi","stars":{"2":3,"3":3},"eq":{},"prologue":True,"age":6,"grade":"1"}}}
# ---------- static head checks ----------
ck('<title>NumiRealm</title>' in HTML,'static <title> is NumiRealm')
for k in ['<meta name="apple-mobile-web-app-title" content="NumiRealm">','<meta name="application-name" content="NumiRealm">','<meta property="og:title" content="NumiRealm">','<meta name="theme-color" content="#0A1F44">']:
    ck(k in HTML,'meta: '+k)
ck(not re.search(r'Times Table Quest|Number Kingdom',HTML,re.I),'no old brand strings anywhere in the HTML')
ck('standalone' not in HTML and 'display-mode' not in HTML,'manifest adds no standalone/display-mode strings')
links=re.findall(r'<link rel="(icon|apple-touch-icon|manifest)"([^>]*)>',HTML)
def href(a):return re.search(r'href="([^"]+)"',a).group(1)
svgi=[a for r,a in links if r=='icon' and 'svg+xml' in a]
ck(len(svgi)==1 and href(svgi[0]).startswith('data:image/svg+xml,') and '<svg' in urllib.parse.unquote(href(svgi[0])),'SVG favicon embedded as data URI')
def png(a):
    b=base64.b64decode(href(a).split(',',1)[1]);return b[:8]==b'\x89PNG\r\n\x1a\n' and int.from_bytes(b[16:20],'big')
ati=[a for r,a in links if r=='apple-touch-icon']
ck(len(ati)==1 and png(ati[0])==180 and 'sizes="180x180"' in ati[0],'180px PNG apple-touch-icon embedded')
p32=[a for r,a in links if r=='icon' and 'sizes="32x32"' in a];ck(len(p32)==1 and png(p32[0])==32,'32px PNG favicon embedded')
man=[a for r,a in links if r=='manifest']
m=json.loads(base64.b64decode(href(man[0]).split(',',1)[1])) if man else {}
ck(m.get('name')=='NumiRealm' and sorted(i['sizes'] for i in m.get('icons',[]))==['192x192','512x512'] and all(i['src'].startswith('data:image/png') for i in m['icons']),'inline manifest with 192/512 icons')
ck(not re.search(r'(src|href)="(?!https?://fonts\.|data:|#|https?://)[^"]+\.(png|svg|ico|webmanifest)"',HTML),'no extra icon/logo files referenced (all inline)')
ck(HTML.index('id="nrSplash"')<HTML.index('<script>'),'loading screen is static HTML (paints before the app script)')
ck("'ttq-save-v2'" in HTML,'save key ttq-save-v2 kept')
LOGO="""(sel)=>[...document.querySelectorAll(sel)].filter(e=>e.getClientRects().length).map(s=>{const r=s.getBoundingClientRect(),t=s.querySelector('text');
 return {w:r.width,h:r.height,txt:t.textContent,n:t.getNumberOfChars(),fill:t.getAttribute('fill'),tl:t.getAttribute('textLength'),right:r.right<=innerWidth+1,left:r.left>=-1}})"""
with sync_playwright() as p:
    for eng in ['chromium','webkit']:
        b=getattr(p,eng).launch()
        for w in [390,1280]:
            for rm in [False,True]:
                c=b.new_context(viewport={'width':w,'height':844 if w<500 else 800},reduced_motion='reduce' if rm else 'no-preference')
                c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"22"}'))
                pg=c.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
                tag=f'{eng} {w}px{" reduced-motion" if rm else ""}'
                # pass 1: same page with the dismissal held (test-only route patch) so the loading screen can be inspected
                held=HTML.replace('function nrSplashDone(){','function nrSplashDone(){return;',1)
                c.route('**/index.html',lambda r:r.fulfill(status=200,content_type='text/html',body=held))
                pg.goto(URL);pg.wait_for_timeout(500)
                sp=pg.evaluate(LOGO,'#nrSplash svg.nrlogo')
                ck(len(sp)==1 and sp[0]['txt']=='NumiRealm' and sp[0]['h']<sp[0]['w'] and sp[0]['right'] and sp[0]['left'],f'{tag}: loading screen shows the logo on one line {sp}')
                ck('Enter the realm. Master the math.' in pg.inner_text('#nrSplash') and pg.locator('#nrSplash .nrsp-load i').count()==3,f'{tag}: tagline + loader')
                an=pg.evaluate("getComputedStyle(document.querySelector('#nrSplash .nrsp-load i')).animationName")
                ck((an=='none')==rm,f'{tag}: loader animation {"off" if rm else "on"} ({an})')
                ck(pg.evaluate("getComputedStyle(document.getElementById('nrSplash')).pointerEvents")=='none',f'{tag}: loading screen never blocks taps')
                # pass 2: real page — the loading screen must go away on its own
                c.unroute('**/index.html');pg.goto(URL,wait_until='commit');t0=pg.evaluate('performance.now()')
                pg.wait_for_function("!document.getElementById('nrSplash')",timeout=2500,polling=50)
                ms=pg.evaluate('performance.now()')-t0
                ck(ms<1700,f'{tag}: loading screen dismissed on its own after {ms:.0f}ms')
                pg.wait_for_timeout(300)
                ck(pg.title()=='NumiRealm · Home',f'{tag}: tab title "{pg.title()}"')
                for sel,nm in [('.hhero .logo svg.nrlogo','welcome logo'),('#topTitle svg.nrlogo','top bar wordmark')]:
                    L=pg.evaluate(LOGO,sel)
                    ck(len(L)==1 and L[0]['txt']=='NumiRealm' and L[0]['n']==9 and L[0]['fill'].startswith('url(') and L[0]['tl'] and L[0]['w']>L[0]['h']*2.5 and L[0]['right'] and L[0]['left'],f'{tag}: {nm} renders as one word on one line {L}')
                if w==1280: ck(pg.locator('#top .toplogo svg.nrmark').is_visible(),f'{tag}: emblem shown in the top bar')
                ck(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),f'{tag}: no horizontal overflow')
                ck(not errs,f'{tag}: no JS errors {errs}')
                c.close()
        if True:
            pg=b.new_page();pg.set_content('<img id=f src="%s">'%href(svgi[0]).replace('"','&quot;'));pg.wait_for_timeout(300)
            ck(pg.evaluate("document.getElementById('f').naturalWidth")>0,f'{eng}: SVG favicon data URI decodes as an image');pg.close()
        # game header + save/auto-update unaffected
        c=b.new_context(viewport={'width':390,'height':844})
        c.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.setItem('ttq-save-v2',%s);sessionStorage.setItem('seeded','1')}"%json.dumps(json.dumps(SAVE)))
        c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"22"}'))
        pg=c.new_page();pg.goto(URL);pg.wait_for_timeout(1500)
        sv=json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))
        ck(sv['profiles']['emi']['stars'].get('2')==3 and sv['profiles']['emi']['name']=='Emi',f'{eng}: v18 save loads unchanged')
        pg.evaluate("go('realms')");pg.wait_for_timeout(400)
        ck(pg.title().startswith('NumiRealm · '),f'{eng}: per-screen title "{pg.title()}"')
        ck(pg.locator('.nrstrip [data-brand] svg.nrlogo').count()==1,f'{eng}: realm strip uses the same logo component')
        L=pg.evaluate(LOGO,'#topTitle svg.nrlogo');ck(len(L)==1 and L[0]['right'],f'{eng}: game header wordmark fits {L}')
        ck(pg.evaluate("document.querySelectorAll('svg.nrlogo, svg.nrmark').length>=2 && [...document.querySelectorAll('[id^=nrw]')].length===new Set([...document.querySelectorAll('[id^=nrw]')].map(e=>e.id)).size"),f'{eng}: unique gradient ids per logo instance')
        c.close();b.close()
# spelling of new copy
for w in ['practise','colour','favourite','centre','harbour','cosy','defence','behaviour','Brackets','Lighter skin','All six heroes']:
    ck(w not in HTML,'US spelling: no '+w)
new=' '.join(re.findall(r'aria-label="([^"]*NumiRealm[^"]*)"',HTML))+' Loading NumiRealm Enter the realm. Master the math. Level complete Home'
words=set(re.findall(r'[A-Za-z]+',new));ok={'NumiRealm','Loading','Enter','the','realm','Master','math','Level','complete','Home','Welcome','to','Main','playing','as','Map','The','a','between','castle','floating','full','glowing','of','sky','symbols','two','under','waterfalls'}
print('new-copy words:',sorted(words));ck(words<=ok|set(['Emi','Sage','Cayden','Zea','Eshon']),'new copy spell-checked (only known words)')
print('RESULT','PASS' if not FAILS else 'FAIL',len(FAILS));sys.exit(1 if FAILS else 0)
