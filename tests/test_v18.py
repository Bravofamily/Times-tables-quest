# v22 update of test_v18.py: same checks, adapted only for age groups, v22 version numbers and self-hosted fonts on file://
import os
# v18: NumiRealm branding sweep, Star Path unlocks + migration, unlock UI, hero identity tokens, selection state
import json,os,re,sys,threading,http.server,functools
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
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))));PORT=8800;URL=f'http://127.0.0.1:{PORT}/index.html'
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(http.server.SimpleHTTPRequestHandler,directory=D));srv.RequestHandlerClass.log_message=lambda *a:None
threading.Thread(target=srv.serve_forever,daemon=True).start()
FAILS=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m);(None if c else FAILS.append(m))
HTML=open(D+'/index.html',encoding='utf-8').read()
OLD=re.compile(r'Times Table Quest|Number Kingdom|\bTTQ\b(?![_.\w])',re.I)
SAVE={"muted":True,"narrator":False,"lastHero":"emi","profiles":{
 "emi":{"name":"Emi","stars":{"2":3,"3":3,"4":3,"5":2,"10":3},"eq":{},"prologue":True,"age":6,"grade":"1"},
 "sage":{"name":"Sage","stars":{"2":3,"3":2},"eq":{},"prologue":True}}}
def ctx(p,save,w=1280,rm=False):
    c=getattr(p,os.environ.get('PWB','chromium')).launch().new_context(viewport={'width':w,'height':800},reduced_motion='reduce' if rm else 'no-preference')
    c.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.setItem('ttq-save-v2',%s);sessionStorage.setItem('seeded','1')}"%json.dumps(json.dumps(save)))
    c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"22"}'))
    pg=c.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)));pg.goto(URL);pg.wait_for_timeout(1400);return c,pg,errs
with sync_playwright() as p:
    # ---------- 1. branding ----------
    ck(not OLD.search(re.sub(r'TTQ_VERSION|TTQ\.|const TTQ|window\.TTQ','',HTML).replace("ttq-save-v2","").replace("'ttq-","")) ,'no old game names in the HTML')
    ck("'ttq-save-v2'" in HTML,'storage key ttq-save-v2 kept')
    ck('<meta property="og:title" content="NumiRealm">' in HTML and 'content="Enter the realm. Master the math."' in HTML,'og title + tagline meta')
    c,pg,errs=ctx(p,SAVE)
    ck(pg.locator('#nrSplash').count()==0,'splash auto-removed and never blocks')
    ck(pg.title()=='NumiRealm · Home','tab title NumiRealm · Home')
    screens=[("go('realms')",'Levels'),("go('training')",'Practice'),("go('trophies','emi')",'Star Path & Rewards'),("go('guide')",'How NumiRealm works'),
             ("go('heroes')",'Heroes Hall'),("go('hero','zea')",'Zea'),("go('villain')",'The Muddle Monster'),("go('settings')",'Settings'),("go('progress','emi')",'Progress'),
             ("go('pick')",'Who is playing?'),("save.hero='emi';go('smapScreen','add')",'Addition Meadow'),("go('profile')",'Hero profiles'),("titleScreen()",'Home')]
    for js,t in screens:
        pg.evaluate(js);pg.wait_for_timeout(350)
        txt=pg.evaluate("document.body.innerText+' '+[...document.querySelectorAll('[aria-label],[title],[alt]')].map(e=>(e.getAttribute('aria-label')||'')+' '+(e.getAttribute('title')||'')+' '+(e.getAttribute('alt')||'')).join(' ')")
        ck(not OLD.search(txt),f'{t}: no old names in text/aria')
        ck(pg.title()=='NumiRealm · '+t,f'{t}: tab title "{pg.title()}"')
        ck(pg.inner_text('#topTitle').strip().lower()=='numirealm','%s: compact NumiRealm wordmark in top bar'%t)
        ck(pg.is_visible('#heroChip') and 'Emi' in pg.get_attribute('#heroChip','aria-label'),f'{t}: current hero chip in top bar')
    pg.evaluate("go('realms')");pg.wait_for_timeout(300)
    ck(pg.locator('#app .nrstrip [data-brand] .nrtag').inner_text()=='Enter the realm. Master the math.','realm map: wordmark + tagline strip')
    pg.evaluate("save.hero='emi';go('smapScreen','div')");pg.wait_for_timeout(300)
    ck(pg.locator('#app .nrstrip [data-brand]').count()==1 and pg.evaluate("getComputedStyle(document.querySelector('#app .nrstrip')).borderBottomColor")=='rgb(37, 99, 235)','realm intro: wordmark + realm color accent header')
    pg.evaluate("go('realms')");pg.wait_for_timeout(300)
    css=pg.evaluate("(()=>{const e=document.querySelector('.nrword svg.nrlogo text');return [e.textContent,e.getAttribute('fill')]})()")
    ck(css[0]=='NumiRealm' and css[1].startswith('url('),'wordmark is one SVG text with one gradient (Safari-safe)')
    # ---------- 3. tokens ----------
    tokv=pg.evaluate("HERO_ORDER.map(id=>[id,HERO_ID[id].c,HERO_ID[id].a,HERO_ID[id].e,HERO_ID[id].title,V16C[id]])")
    ck(len(tokv)==7 and len({t[1] for t in tokv})==7 and len({t[3] for t in tokv})==7,'7 heroes with unique primary colors and emblems')
    ck(all(t[1]==t[5] for t in tokv),'carousel colors come from the tokens')
    T={t[0]:t for t in tokv}
    ck(T['sage'][1]!=T['melrose'][1] and T['sage'][2]!=T['melrose'][2] and T['sage'][3]!=T['melrose'][3],'Sage vs Melrose distinct')
    ck(T['emi'][1]!=T['zea'][1] and T['emi'][2]!=T['zea'][2] and T['emi'][3]!=T['zea'][3],'Emi vs Zea distinct')
    pg.evaluate("go('heroes')");pg.wait_for_timeout(1200)
    hc=pg.evaluate("[...document.querySelectorAll('.hallcard[data-hall]')].filter(e=>HEROES[e.dataset.hall]).map(e=>[e.dataset.hall,getComputedStyle(e).getPropertyValue('--hc').trim().toUpperCase(),!!e.querySelector('.hemb')])")
    ck(len(hc)==7 and all(h[1]==T[h[0]][1].upper() and h[2] for h in hc),'Heroes Hall: token color + emblem on every card %s'%hc)
    ck(pg.locator('.hallcard.sel').count()==1 and pg.get_attribute('.hallcard.sel','data-hall')=='emi' and pg.get_attribute('.hallcard.sel','aria-current')=='true' and 'Playing as' in pg.inner_text('.hallcard.sel .selbadge'),'Heroes Hall: selected hero ring + ✓ Playing as + aria-current')
    pg.evaluate("go('pick')");pg.wait_for_timeout(400)
    ck(pg.locator('.herocard.sel').count()==1 and pg.get_attribute('.herocard.sel','aria-pressed')=='true' and pg.locator('.herocard[aria-pressed=false]').count()>=6,'Who is playing?: one selected (aria-pressed) and the rest not')
    pg.evaluate("titleScreen()");pg.wait_for_timeout(700)
    car=pg.evaluate("(()=>{const s=document.querySelector('.hcar .herocard.sel');return s?[s.dataset.hero,s.getAttribute('aria-pressed'),s.querySelector('.selbadge').textContent,getComputedStyle(s).boxShadow.length>10]:null})()")
    ck(car and car[0]=='emi' and car[1]=='true' and 'Playing as' in car[2] and car[3],'carousel: selected hero ring + badge (%s)'%car)
    pg.evaluate("document.querySelector('.hcar-dot[data-dot=zea]')&&document.querySelector('.hcar-dot[data-dot=zea]').click()");pg.wait_for_timeout(700)
    foc=pg.evaluate("(()=>{const f=document.querySelector('.hcar .hslide[data-off=\"0\"] .herocard');return f?[f.dataset.hero,f.classList.contains('sel'),getComputedStyle(f).outlineStyle]:null})()")
    ck(foc and (foc[0]!='zea' or (not foc[1] and foc[2]=='dashed')),'carousel: focused (dashed) is distinct from selected (%s)'%foc)
    ck(pg.locator('.hcar .herocard.sel').count()==1,'carousel: selected stays on Emi while browsing')
    # ---------- 2. Star Path + migration ----------
    sp=pg.evaluate("SPATH.map(m=>[m.k,m.scope,m.need,m.badge||''])")
    ck(sp==[['f-lanterns','family',10,''],['f-silver','family',30,''],['f-shower','family',60,''],['f-teamup','family',100,''],['f-gold','family',150,''],['f-rainbow','family',200,'grand'],
            ['h-shiny','hero',5,''],['h-sparkle','hero',15,''],['h-crown','hero',30,''],['h-riddle','hero',45,'finisher']],'Star Path thresholds')
    saved=json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))
    ck(saved['profiles']['emi']['stars']==SAVE['profiles']['emi']['stars'] and saved['profiles']['sage']['stars']==SAVE['profiles']['sage']['stars'],'migration: stars intact')
    ck(saved.get('spv')==18 and sorted(saved['spSeen'])==sorted(['f-lanterns','h-shiny:emi','h-shiny:sage']),'migration: unlocks computed from existing stars (%s)'%saved.get('spSeen'))
    ck(pg.evaluate("famStars()")==19 and pg.evaluate("spOn('f-lanterns')") and not pg.evaluate("spOn('f-silver')"),'family total 19 ⭐ unlocks Lantern Path only')
    pg.evaluate("go('trophies','emi')");pg.wait_for_timeout(400)
    ck(pg.locator('#starPath .spitem').count()==10 and pg.locator('#starPath .spitem.got').count()==2,'Star Path card: 10 milestones, 2 unlocked')
    ck('🔒' in pg.inner_text('[data-sp=h-sparkle]') and '14/15 ⭐ to unlock' in pg.inner_text('[data-sp=h-sparkle]'),'locked item: padlock + "14/15 ⭐ to unlock"')
    ck('Realm Finisher' in pg.inner_text('[data-sp=h-riddle]'),'riddle room shows its badge requirement')
    ck(pg.locator('#spCele').count()==0,'no celebration replay for migrated unlocks')
    names=pg.evaluate("badgesOf('emi').map(b=>b.k)")
    ck(all(k in names for k in ['finisher','tables','nolan','streak10','missing','grand']),'new learning badges present')
    ck(pg.evaluate("badgesOf('emi').find(b=>b.k==='tables').got"),'Times Table Master earned (3 tables at 3 stars)')
    pg.evaluate("titleScreen()");pg.wait_for_timeout(400)
    ck('Next unlock' in pg.inner_text('#nextUnlock') and pg.get_attribute('#nextUnlock','data-next')=='h-sparkle','Home: next unlock hint')
    pg.evaluate("go('progress','emi')");pg.wait_for_timeout(400)
    ck(pg.locator('#nextUnlock').count()==1,'Progress: next unlock hint')
    # streak + no-lantern tracking
    pg.evaluate("pickHero('emi')");pg.wait_for_timeout(300)
    pg.evaluate("for(let i=0;i<10;i++)noteAns('add',1,{a:1,b:1},true,0)")
    ck(pg.evaluate("badgesOf('emi').find(b=>b.k==='streak10').got"),'Hot Streak after 10 correct in a row')
    # win -> new unlock celebration
    pg.evaluate("save.profiles.emi.stars['6']=3;persist()")
    pg.evaluate("openLevel(1)");pg.wait_for_timeout(500);pg.evaluate("winScreen(3,null)");pg.wait_for_timeout(500)
    ck(pg.locator('#spCele').count()==1 and 'Victory Sparkles' in pg.inner_text('#spCele'),'win: unlock celebration names Victory Sparkles')
    ck(pg.locator('#app .nrresult [data-brand]').count()==1 and pg.locator('#app .nrresult #nextUnlock').count()==1,'results: wordmark + next unlock')
    ck(pg.title()=='NumiRealm · Level complete','results tab title')
    ck(pg.evaluate("spOn('h-sparkle','emi')") and 'h-sparkle:emi' in pg.evaluate("save.spSeen"),'unlock recorded')
    ck(not errs,'no page errors %s'%errs);c.close()
    # reduced motion: celebration is still
    s2=json.loads(json.dumps(SAVE));s2['spv']=18;s2['spSeen']=[]
    c,pg,errs=ctx(p,s2,390,True)
    pg.evaluate("pickHero('emi')");pg.wait_for_timeout(300);pg.evaluate("openLevel(1)");pg.wait_for_timeout(400);pg.evaluate("winScreen(2,null)");pg.wait_for_timeout(400)
    ck(pg.is_visible('#topTitle .tth') and 'Emi' in pg.inner_text('#topTitle .tth') and 'playing as Emi' in pg.get_attribute('#navProfile','aria-label'),'390: current hero shown in top bar under the wordmark')
    ck(pg.evaluate("(()=>{const t=document.querySelector('#topTitle .ttb');return t.scrollWidth<=t.clientWidth+1})()"),'390: NumiRealm wordmark not truncated')
    ck(pg.locator('#spCele.still').count()==1 and pg.evaluate("getComputedStyle(document.querySelector('#spCele')).animationName")=='none','reduced motion: celebration without animation')
    ck(pg.evaluate("document.documentElement.scrollWidth<=innerWidth"),'390: no horizontal overflow on results')
    ck(not errs,'390 no page errors %s'%errs);c.close()
    # fresh save: no hero chip, no crash
    c,pg,errs=ctx(p,{"muted":True,"profiles":{}})
    ck(pg.locator('#heroChip.hidden').count()==1 and pg.title()=='NumiRealm · Home','fresh save: chip hidden, title ok')
    ck(not errs,'fresh no errors %s'%errs);c.close()
# spelling
low=HTML
for w in ['practise','colour','favourite','centre','harbour','cosy','defence','behaviour','Brackets','Lighter skin','All six heroes']:
    ck(w not in low,'US spelling: no '+w)
print('RESULT','PASS' if not FAILS else 'FAIL',len(FAILS));sys.exit(1 if FAILS else 0)
