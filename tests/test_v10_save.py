# v22 update of test_v10_save.py: same checks, adapted only for age groups, v22 version numbers and self-hosted fonts on file://
import os
# v10: a v9 save (with subject progress) loads unchanged; title/name checks; title screenshots.
import json, os, sys
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
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); URL='file://'+os.path.join(D,'index.html'); errs=[]; fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m); fails.append(m) if not c else None
V9={"muted":True,"narrator":False,"hero":"melrose","lastSubj":"frac","profiles":{
 "melrose":{"name":"Melrose","stars":{"1":3,"2":2},"hist":{},"rewards":["fwand","mtail"],"eq":{"head":"fwand"},"prologue":True,"age":8,"grade":"3",
   "subj":{"add":{"stars":{"1":3,"2":3,"3":1},"hist":{"1":["a"]},"intro":True},"frac":{"stars":{"1":2},"hist":{},"intro":True}}},
 "cayden":{"name":"Cayden","stars":{},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":10,"grade":"5","subj":{"div":{"stars":{"1":3},"hist":{},"intro":True}}}}}
with sync_playwright() as p:
    b=getattr(p,os.environ.get('PWB','chromium')).launch()
    def att(pg,t):
        pg.on('console',lambda m: errs.append(f'[{t}] {m.text}') if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(f'[{t}] {e}'))
    c=b.new_context(viewport={'width':1024,'height':800}); pg=c.new_page(); att(pg,'fresh')
    pg.goto(URL); pg.wait_for_selector('.herocard')
    ck(pg.title()=='NumiRealm · Home','<title> is NumiRealm · Home: '+pg.title())
    ck(pg.get_attribute('meta[name=apple-mobile-web-app-title]','content')=='NumiRealm' and pg.get_attribute('meta[name=application-name]','content')=='NumiRealm','home-screen meta names')
    ck(pg.inner_text('#topTitle').lower()=='numirealm' and pg.inner_text('h1').lower()=='numirealm' and pg.get_attribute('h1','aria-label')=='NumiRealm','header + logo heading (logo is CSS-uppercased; aria-label keeps NumiRealm)')
    body=pg.inner_text('body'); ck('Times Table Quest' not in body and 'Kingdom' not in body,'no old names on title screen')
    ck(pg.evaluate("APP_VERSION")=='22' if pg.evaluate("typeof APP_VERSION!=='undefined'") else pg.evaluate("TTQ_VERSION.app")=='22','APP_VERSION 22 (v22 release)')
    pg.screenshot(path=os.path.join(D,'v10-title.png')); c.close()
    c=b.new_context(viewport={'width':375,'height':812},device_scale_factor=2,is_mobile=True,has_touch=True); pg=c.new_page(); att(pg,'mobile')
    pg.goto(URL); pg.wait_for_selector('.herocard'); ck(pg.evaluate("document.documentElement.scrollWidth")<=375,'mobile title no overflow')
    pg.screenshot(path=os.path.join(D,'v10-mobile-title.png')); c.close()
    c=b.new_context(viewport={'width':1024,'height':800}); pg=c.new_page(); att(pg,'v9save')
    c.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('ttq-save-v2',%s)}"%json.dumps(json.dumps(V9)))
    pg.goto(URL); pg.wait_for_selector('.slevels')
    ck(pg.evaluate("TTQ_SUBJ.lastMap")=='frac' or 'Fraction' in pg.inner_text('#app'),'v9 save resumes on the fraction map')
    pr=pg.evaluate("TTQ.save.profiles")
    ck(pr['melrose']['subj']['add']['stars']=={"1":3,"2":3,"3":1} and pr['melrose']['rewards']==["fwand","mtail"] and pr['melrose']['age']==AR(8) and pr['cayden']['subj']['div']['stars']=={"1":3},'v9 progress, rewards, age kept')
    ck(json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))['profiles']['melrose']['subj']['add']['stars']['3']==1,'same localStorage key ttq-save-v2')
    pg.click('#toSubjects'); pg.wait_for_selector('.stile')
    ck('3/11 chapters' in pg.inner_text('[data-subject=add]') and '7/33' in pg.inner_text('[data-subject=add]'),'addition tile shows v9 progress')
    ck('2/19' in pg.inner_text('[data-subject=mult]'),'mult tile shows v9 progress')
    ck('NumiRealm' in pg.inner_text('#app'),'subject select says NumiRealm')
    c.close(); b.close()
print('console errors:',errs); ck(not errs,'no console errors')
print('RESULT','FAIL' if fails else 'ALL PASS'); sys.exit(1 if fails else 0)
