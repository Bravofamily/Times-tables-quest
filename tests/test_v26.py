# v26: Parent Area test pages staged next to the game. Checks version, deploy URLs, service worker
# exclusions, and that WITHOUT ?parenttest=1 Home and Settings match v25 with no Supabase traffic.
# Usage: PWB=chromium|webkit [V25_DIR=/path/to/v25] python test_v26.py
import os,re,json,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V25=os.environ.get('V25_DIR','');BR=os.environ.get('PWB','chromium')
P=8891 if BR=='chromium' else 8893
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
def serve(d,port):
    s=http.server.ThreadingHTTPServer(('127.0.0.1',port),functools.partial(Q,directory=d));threading.Thread(target=s.serve_forever,daemon=True).start();return s
F=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c:F.append(m)
rd=lambda f:open(os.path.join(D,f),encoding='utf-8').read()
html=rd('index.html');ph=rd('parent.html');sw=rd('sw.js')
_av=re.search(r"const APP_VERSION='(\d+)'",html);ck(_av and int(_av.group(1))>=26 and _av.group(1)==json.load(open(os.path.join(D,'version.json')))['version'],'APP_VERSION and version.json match and are >= 26')
ck("const PARENT_BASE=''" in html and 'game/' not in re.search(r'/\* NRH-BEGIN \*/[\s\S]*?/\* NRH-END \*/',html).group(0),'game links parent pages in the same folder')
ck('<meta name="nr-game" content="./">' in ph,'parent.html links back to the game in the same folder')
ck("SITE+'parent.html'" in ph and "const SITE='https://bravofamily.github.io/Times-tables-quest/'" in ph and 'emailRedirectTo:REDIRECT' in ph,'emailRedirectTo is the live parent.html URL on GitHub Pages')
for f in ['vendor/supabase.js','vendor/qrcode.js','parent-about.html','supabase/setup.sql']: ck(os.path.exists(os.path.join(D,f)),f+' present')
for f in sorted(set(re.findall(r'fonts/[\w.-]+\.woff2',ph+rd('parent-about.html')))): ck(os.path.exists(os.path.join(D,f)),f+' resolves')
shell=re.search(r'const SHELL=\[(.*?)\]',sw).group(1)
ck('parent' not in shell and 'vendor' not in shell,'sw.js does not precache parent pages or vendor/')
ck(re.search(r"parent\[\^/\]\*\\\.html\$/\.test\(u\.pathname\)\|\|/\\/vendor\\//\.test\(u\.pathname\)\)return",sw) is not None,'sw.js skips parent*.html and vendor/')
s=serve(D,P);s2=serve(V25,P+1) if V25 else None
SNAP="""()=>{const a=document.body.cloneNode(true);a.querySelectorAll('script,style').forEach(e=>e.remove());return a.innerHTML.replace(/\\d{1,2}:\\d{2}/g,'T').replace(/NumiRealm v\\d+/g,'NumiRealm vN').replace(/Enter the realm\\. Master the math/gi,'TAGLINE') /* v27 capitalised the tagline */.replace(/(min-)?height: [\\d.]+px;?/g,'') /* measured heights vary with font-load timing */}"""
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    def page(port,q=''):
        c=b.new_context(viewport={'width':1100,'height':900});pg=c.new_page();pg.sb=[]
        pg.on('request',lambda r:pg.sb.append(r.url) if 'supabase' in r.url else None)
        pg.goto(f'http://127.0.0.1:{port}/index.html{q}');pg.wait_for_timeout(1300);return pg
    g=page(P)
    ck(g.locator('#nrParentHome').count()==1,'v30: Parent Login card on Home without the flag (public)')
    home=g.evaluate(SNAP);g.evaluate("settingsScreen()");g.wait_for_timeout(400)
    ck(g.locator('#parentLink,#plOpen').count()==0,'no parent link in Settings without the flag')
    sett=g.evaluate(SNAP);ck(g.sb==[],'no Supabase requests without the flag')
    ck(g.evaluate("typeof supabase")=='undefined','Supabase library not loaded by the game')
    if s2:
        o=page(P+1);h25=o.evaluate(SNAP);o.evaluate("settingsScreen()");o.wait_for_timeout(400);s25=o.evaluate(SNAP)
        ck(home==h25,'Home identical to v25 without the flag');ck(sett==s25,'Settings identical to v25 without the flag')
    else: print('SKIP v25 comparison (set V25_DIR)')
    f=page(P,'?parenttest=1');ck(f.locator('#nrParentHome').count()==1,'Parent Login card shown with ?parenttest=1')
    # gameURL from parent.html resolves to the site root
    pp=b.new_context().new_page();pp.route('**/*supabase.co/**',lambda r:r.abort());pp.goto(f'http://127.0.0.1:{P}/parent.html');pp.wait_for_timeout(500)
    ck(pp.evaluate("gameURL('ABC123')")==f'http://127.0.0.1:{P}/?parenttest=1&link=ABC123','QR/link URL is <site>/?parenttest=1&link=CODE')
    # service worker: parent.html must never be cached nor stored as index.html
    if BR=='chromium':
        c=b.new_context();w=c.new_page();w.goto(f'http://127.0.0.1:{P}/index.html');w.evaluate("navigator.serviceWorker.ready.then(()=>1)");w.wait_for_timeout(3000)
        w.goto(f'http://127.0.0.1:{P}/parent.html');w.wait_for_timeout(1500)
        r=w.evaluate("""async()=>{const out=[];for(const k of await caches.keys()){const c=await caches.open(k);for(const q of await c.keys())out.push(q.url);const i=await c.match(location.origin+'/index.html');out.push('IDX:'+(i?(await i.text()).includes('APP_VERSION'):'none'))}return out}""")
        ck(not any('parent' in u or 'vendor' in u for u in r),'service worker cached no parent page or vendor file')
        ck('IDX:true' in r or print(r),'cached index.html is still the game, not parent.html')
    b.close()
s.shutdown()
print('FAILURES',len(F));[print(' -',m) for m in F]
