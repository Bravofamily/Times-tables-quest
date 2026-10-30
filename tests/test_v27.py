# v27: 'Back to NumiRealm' on the parent pages (see test_parent.py), a 'Parent Login' pill in the game's
# top bar behind ?parenttest=1 and the grown-up gate, and the official tagline capitalisation.
# Usage: PWB=chromium|webkit [SHOTS=1 SHOTS_DIR=...] python test_v27.py
import os,re,json,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BR=os.environ.get('PWB','chromium');SH=os.environ.get('SHOTS')=='1';OUT=os.environ.get('SHOTS_DIR','/tmp/numirealm-v27-shots')
if SH: os.makedirs(OUT,exist_ok=True)
P=8895 if BR=='chromium' else 8896
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
ck(_av is not None and int(_av.group(1))>=27 and _vj==_av.group(1),'APP_VERSION and version.json match and are >=27')
ck(not re.search(r'Enter the realm|Master the math',html),'no lowercase "realm"/"math" tagline left in index.html')
for k,pat in [('meta description',r'<meta name="description" content="NumiRealm: Enter the Realm\. Master the Math\.">'),('og:description',r'<meta property="og:description" content="Enter the Realm\. Master the Math\.">'),
              ('splash tagline',r'<p class="nrsp-tag">Enter the Realm\. Master the Math\.</p>'),('Home banner',r'<span class="banner">Enter the Realm\. Master the Math\.</span>'),('NR_TAG',r"const NR_TAG='Enter the Realm\. Master the Math\.'")]:
    ck(re.search(pat,html) is not None,f'tagline capitalised: {k}')
ck(html.count('const SHOW_HOME=true;')==1 and 'if(SHOW_HOME){if(document.readyState' in html,'top-bar pill uses the same one-line SHOW_HOME switch as the Home card')
def hide_splash(pg): pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())")
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    def page(w,q,h=844):
        c=b.new_context(viewport={'width':w,'height':h});pg=c.new_page();pg.sb=[]
        pg.on('request',lambda r:pg.sb.append(r.url) if 'supabase' in r.url else None)
        pg.on('pageerror',lambda e:errs.append(str(e)))
        pg.route('**/*supabase.co/**',lambda r:r.abort())
        pg.goto(f'{HOST}/index.html{q}');pg.wait_for_timeout(1500);hide_splash(pg);return pg
    noscroll=lambda pg:pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    def bar(pg): return pg.evaluate("""(()=>{const t=document.getElementById('nrhTop'),m=document.getElementById('muteBtn'),ti=document.getElementById('topTitle');if(!t)return null;const r=t.getBoundingClientRect(),mr=m.getBoundingClientRect(),
      kids=[...document.querySelectorAll('#top > *')].filter(e=>e.offsetParent&&e.id!=='nrhTop').map(e=>e.getBoundingClientRect().right);
      return {h:r.height,w:r.width,mh:mr.height,top:r.top,mtop:mr.top,left:r.left,right:r.right,vw:innerWidth,afterAll:kids.every(x=>x<=r.left+0.5),
      label:t.getAttribute('aria-label'),txt:t.innerText.trim(),lines:Math.round(r.height/parseFloat(getComputedStyle(t).lineHeight||20)),titleW:ti.getBoundingClientRect().width,inTop:t.parentNode.id==='top'}})()""")
    for w,tag in [(390,'phone'),(1280,'desktop')]:
        n=page(w,'');tw0=n.evaluate("document.getElementById('topTitle').getBoundingClientRect().width")
        ck(n.locator('#nrhTop').count()==1,f'{tag}: v30: top-bar Parent button shown without the flag')
        ck(n.inner_text('.banner').strip()=='Enter the Realm. Master the Math.' if n.locator('.banner').count() else True,f'{tag}: Home banner shows the official tagline')
        if SH: n.screenshot(path=f'{OUT}/{BR}-{tag}-topbar-noflag.png',clip={'x':0,'y':0,'width':w,'height':110})
        n.evaluate("settingsScreen()");n.wait_for_timeout(300);ck(n.locator('#nrhTop').count()==1 and n.sb==[],f'{tag}: v30: top-bar button on Settings, still no Supabase requests without the flag')
        g=page(w,'?parenttest=1');r=bar(g)
        ck(bool(r) and r['inTop'] and r['afterAll'],f'{tag}: Parent button is in the top bar, right of the stars/owl/sound buttons ({r})')
        ck(r and abs(r['h']-r['mh'])<0.5 and abs(r['top']-r['mtop'])<0.5 and r['h']>=44 and r['w']>=44,f'{tag}: same height as the sound button, >=44px')
        ck(r and r['right']<=r['vw'] and noscroll(g),f'{tag}: fits, no sideways scroll')
        ck(r and r['label']=='Parent Login (grown-ups)',f'{tag}: aria-label set')
        if tag=='phone': ck(r and r['txt']=='🔑' and abs(r['titleW']-tw0)<1,f'phone: icon-only pill, NumiRealm title keeps its width ({r["titleW"]} vs {tw0})')
        else: ck(r and r['txt'].replace('\n',' ')=='🔑 Parent Login' and r['h']<50,f'desktop: "🔑 Parent Login" on one line')
        if SH: g.screenshot(path=f'{OUT}/{BR}-{tag}-topbar-flag.png',clip={'x':0,'y':0,'width':w,'height':110})
        for scr in ['settingsScreen()']:
            g.evaluate(scr);g.wait_for_timeout(300);ck(g.locator('#nrhTop').is_visible(),f'{tag}: Parent button also on {scr}')
        for nav in ['#navLevels','#navPractice','#navHome']:
            if g.locator(nav).is_visible(): g.click(nav);g.wait_for_timeout(300);ck(g.locator('#nrhTop').count()==1 and g.locator('#nrhTop').is_visible(),f'{tag}: Parent button on {nav} screen')
        # gate
        g.click('#nrhTop');ck(g.locator('#nrhTopGate [role=dialog]').is_visible() and g.locator('#nrtGate').count()==1,f'{tag}: grown-up gate opens')
        if SH and tag=='phone': g.screenshot(path=f'{OUT}/{BR}-{tag}-topbar-gate.png')
        ck(not g.evaluate("[...document.querySelectorAll('#nrhTopGate button')].some(b=>b.getBoundingClientRect().height<44)") and noscroll(g),f'{tag}: gate buttons >=44px, no sideways scroll')
        g.click('#nrtCancel');ck(g.locator('#nrhTopGate').count()==0,f'{tag}: gate cancel closes it')
        g.click('#nrhTop');g.fill('#nrtGate','2');g.click('#nrtGo');ck(g.locator('#nrtErr').count()==1 and '/index.html' in g.url,f'{tag}: wrong answer stays in the game')
        a,bb,cc=map(int,re.findall(r'\d+',g.inner_text('#nrtQ'))[:3]);g.fill('#nrtGate',str(a*bb+cc));g.press('#nrtGate','Enter')
        g.wait_for_url('**/parent.html*',timeout=8000);ck(g.url==f'{HOST}/parent.html?parenttest=1#login',f'{tag}: correct answer opens parent.html login with the flag ({g.url})')
        g.wait_for_selector('#nrBack');ck(g.get_attribute('#nrBack','href')=='./?parenttest=1',f'{tag}: parent page Back button keeps the flag')
        g.click('#nrBack');g.wait_for_timeout(1200);ck(g.url==f'{HOST}/?parenttest=1' and g.locator('#nrhTop').count()==1,f'{tag}: back in the test game with the Parent button')
        g.context.close();n.context.close()
    # very narrow: icon only, still fits
    v=page(320,'?parenttest=1');r=bar(v);ck(r and r['txt']=='🔑' and r['right']<=320 and noscroll(v),f'320px: icon only, fits ({r})')
    b.close()
ck(not errs,f'no page errors {errs}')
srv.shutdown()
print('RESULT',BR,'FAILS',len(F));[print(' -',m) for m in F]
