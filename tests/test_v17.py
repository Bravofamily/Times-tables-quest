# v22 update of test_v17.py: same checks, adapted only for age groups, v22 version numbers and self-hosted fonts on file://
import os
# v17: one Home layout on desktop and phone (phone = responsive desktop)
import json,threading,http.server,functools,os
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
os.environ.setdefault('GST_PLUGIN_PATH','/workspace/wkdeps/root/usr/lib/x86_64-linux-gnu/gstreamer-1.0')
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8799),functools.partial(http.server.SimpleHTTPRequestHandler,directory=D))
srv.RequestHandlerClass.log_message=lambda *a:None
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8799/index.html'
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
HTML=open(D+'/index.html').read()
ck("const APP_VERSION='22'" in HTML and json.load(open(D+'/version.json'))=={"version":"22"},'APP_VERSION and version.json are 22')
ck('display-mode' not in HTML and 'standalone' not in HTML and 'hplay mob' not in HTML and 'subjcards dsk' not in HTML,'no standalone-only or phone-only Home markup/styles left')
def save(last):
    return {"muted":True,"narrator":False,"lastHero":last,"profiles":{"emi":{"name":"Emi","stars":{"2":3},"hist":{"2x3":[1,1]},"eq":{},"prologue":True,"age":6,"grade":"1"},
            "sage":{"name":"Sage","stars":{"5":1},"eq":{},"prologue":True,"age":6,"grade":"1"}}}
def ctx(b,w,h,last='emi',touch=False):
    c=b.new_context(viewport={'width':w,'height':h},has_touch=touch)
    c.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('ttq-save-v2',%s)}"%json.dumps(json.dumps(save(last))))
    c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"22"}'))
    pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));pg.goto(URL);pg.wait_for_selector('.hhero');pg.wait_for_timeout(500);return c,pg
LOGO="""(()=>{const l=document.querySelector('.hhero .logo'),r=l.getBoundingClientRect(),h=document.querySelector('.hhero').getBoundingClientRect(),
 fs=parseFloat(getComputedStyle(l).fontSize),sv=l.querySelector('svg.nrlogo'),tx=sv.querySelector('text'),tb=tx.getBBox();
 return {txt:l.textContent,lines:l.getClientRects().length,h:r.height,fs,inside:r.left>=h.left-1&&r.right<=h.right+1,
 noOverflow:document.documentElement.scrollWidth<=innerWidth,clip:tx.getAttribute('fill').startsWith('url(')&&tx.getNumberOfChars()===9?'text':'no',img:tb.width>tb.height*2.5}})()"""
ORDER="""[...document.querySelectorAll('#app .hhero, #app .hplay, #app .tiles, #app h2.quest, #app .subjcards, #app .realms, #app .herosec')]
 .filter(e=>e.getClientRects().length&&getComputedStyle(e).display!=='none'&&e.offsetHeight>0).map(e=>e.classList.contains('hhero')?'banner':e.classList.contains('hplay')?'play':
 e.classList.contains('tiles')?'tiles':e.classList.contains('quest')?'questh':e.classList.contains('subjcards')?'quest':e.classList.contains('realms')?'realms':'heroes')"""
TILES=[('trophies','trophies'),('guide','guide'),('heroes','heroes'),('progress','progress'),('profile','profile'),('settings','settings')]
cur=lambda pg:pg.evaluate("HUB||''")+'|'+pg.evaluate("(document.querySelector('#app [data-screen]')||{}).dataset?.screen||''")
with sync_playwright() as p:
    orders={};heroes={}
    for eng in ['chromium','webkit']:
        b=getattr(p,eng).launch()
        for w in [320,360,390,430,768,1280]:
            c,pg=ctx(b,w,800)
            L_=pg.evaluate(LOGO)
            ck(L_['txt']=='NumiRealm' and L_['lines']==1 and L_['h']<L_['fs']*2.6 and L_['inside'] and L_['noOverflow'],f'{eng} {w}px: wordmark is one unbroken word that fits ({L_})')
            ck(L_['clip']=='text' and L_['img'],f'{eng} {w}px: the "i" is painted with the same gradient (no gap on iPhone)')
            orders[(eng,w)]=pg.evaluate(ORDER)
            heroes[(eng,w)]=pg.evaluate("[...document.querySelectorAll('.hhero .chars .c')].map(e=>e.dataset.h)")
            pb=pg.locator('#playNowD:visible, #playBtn:visible')
            ck(pb.count()==1 and 'play now' in pb.inner_text().lower(),f'{eng} {w}px: exactly one PLAY NOW visible')
            ck(pg.locator('.tiles [data-tile]:visible').count()==6 and pg.locator('.subjcards > *:visible').count()>=6,f'{eng} {w}px: 6 quick buttons and all quest cards shown')
            c.close()
        b.close()
    want=['banner','play','tiles','questh','quest','realms','heroes']
    for k,v in orders.items(): ck(v==want,f'{k}: section order {v}')
    ck(all(v==['blu','emi','sage'] for v in heroes.values()),f'hero order Blú, Emi, Sage everywhere {set(map(tuple,heroes.values()))}')
    b=getattr(p,os.environ.get('PWB','chromium')).launch()
    c,pg=ctx(b,390,844,last='sage'); ck(pg.evaluate("[...document.querySelectorAll('.hhero .chars .c')].map(e=>e.dataset.h)")==['blu','emi','sage'],'hero order does not change with last-played hero'); c.close()
    # phone layout specifics
    c,pg=ctx(b,390,844)
    g=pg.evaluate("(()=>{const t=[...document.querySelectorAll('.tiles [data-tile]')].map(e=>e.getBoundingClientRect());const s=document.querySelector('.subjcards');const pb=document.querySelector('#playBtn').getBoundingClientRect();return {cols:new Set(t.map(r=>Math.round(r.left))).size,rows:new Set(t.map(r=>Math.round(r.top))).size,swipe:s.scrollWidth>s.clientWidth+20&&getComputedStyle(s).overflowX=='auto',pw:pb.width}})()")
    ck(g['cols']==3 and g['rows']==2,f'phone: quick buttons are a 3x2 grid {g}')
    ck(g['swipe'],'phone: Choose your quest is a horizontal swipe row')
    ck(g['pw']>=300,'phone: PLAY NOW is full-width under the banner')
    ck(pg.locator('#bnQuest').is_visible() and pg.locator('#bnPractice').is_visible(),'phone: Levels (Quests) and Practice in bottom tab bar')
    c.close()
    c,pg=ctx(b,1280,800)
    ck(pg.locator('#navLevels').is_visible() and pg.locator('#navPractice').is_visible(),'desktop: Levels and Practice in top nav')
    c.close()
    for w,touch in [(1280,False),(390,True)]:
        c,pg=ctx(b,w,844,touch=touch)
        pg.click('#playNowD:visible, #playBtn:visible'); pg.wait_for_timeout(400)
        ck(pg.evaluate("HUB")!='home' and pg.locator('.hhero').count()==0,f'{w}px: PLAY NOW starts play (HUB={pg.evaluate("HUB")})')
        for t,want in TILES:
            pg.evaluate("titleScreen()"); pg.wait_for_timeout(150); pg.click(f'[data-tile={t}]'); pg.wait_for_timeout(250)
            ck(pg.locator('.hhero').count()==0 and pg.locator('#backBtn').count()>0,f'{w}px: quick button {t} opens its screen')
        for sel in (['#navLevels','#navPractice'] if w>900 else ['#bnQuest','#bnPractice']):
            pg.evaluate("titleScreen()"); pg.wait_for_timeout(150); pg.click(sel); pg.wait_for_timeout(250)
            ck(pg.locator('.hhero').count()==0,f'{w}px: {sel} opens its screen')
        s=json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))
        ck(s['profiles']['emi']['stars'].get('2')==3 and s['profiles']['emi']['hist'].get('2x3')==[1,1],f'{w}px: saves intact')
        c.close()
    ck(not errs,f'no page errors {errs[:3]}')
print('RESULT',('FAIL %d'%len(fails)) if fails else 'PASS')
exit(1 if fails else 0)
