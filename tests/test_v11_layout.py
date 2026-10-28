# v11: responsive layout (320-1440, focus 360x780 / 768x1024 / 1440x900): no overflow, no console errors, tap targets;
# a v10 save loads intact; keyboard play on desktop; reduced motion + big text.
import json, os, copy
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); URL='file://'+os.path.join(D,'index.html'); errs=[]; fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m); fails.append(m) if not c else None
V10={"muted":True,"narrator":False,"hero":"cayden","lastSubj":"div","voice":"","profiles":{
 "melrose":{"name":"Melrose","stars":{"1":3,"2":2,"3":1},"hist":{"1":["a"]},"rewards":["fwand","mtail"],"eq":{"head":"fwand"},"prologue":True,"age":8,"grade":"3",
   "subj":{"add":{"stars":{"1":3,"2":3,"3":1},"hist":{"1":["a"]},"intro":True},"frac":{"stars":{"1":2},"hist":{},"intro":True}}},
 "cayden":{"name":"Cayden","stars":{"1":3},"hist":{},"rewards":["cape"],"eq":{},"prologue":True,"age":10,"grade":"5","subj":{"div":{"stars":{"1":3,"2":2},"hist":{},"intro":True},"sub":{"stars":{"1":1},"hist":{},"intro":True}}},
 "emi":{"name":"Emi","stars":{},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":6,"grade":"1"}}}
OVF="""(()=>{const W=innerWidth,bad=[];const de=document.documentElement;if(de.scrollWidth>W+1)bad.push('doc '+de.scrollWidth);
for(const e of document.querySelectorAll('#app *, #top *, #bnav *')){const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;
 let p=e.parentElement,clip=false;while(p&&p!==document.body){const s=getComputedStyle(p);if(/auto|scroll|hidden|clip/.test(s.overflowX)){clip=true;break;}p=p.parentElement;}
 if(clip)continue;if(r.right>W+1||r.left<-1)bad.push((e.id||e.className||e.tagName).toString().slice(0,30)+' '+Math.round(r.left)+'..'+Math.round(r.right));}
return bad.slice(0,6);})()"""
TAP="""(()=>{const bad=[];for(const e of document.querySelectorAll('#top button, #bnav button, #app .btn, #app .lanbtn, #app .tile, #app .tog, #app .stile, #app .scard, #app .realm, #app .qp, #app .pgtabs button')){const r=e.getBoundingClientRect();if(!r.width)continue;if(getComputedStyle(e).visibility==='hidden')continue;if(r.width<43.5||r.height<43.5)bad.push((e.id||e.textContent.trim().slice(0,14))+' '+Math.round(r.width)+'x'+Math.round(r.height));}return bad.slice(0,6);})()"""
SCREENS=[('home',"titleScreen()"),('quests',"pickHero('cayden',true);subjectScreen()"),('smap',"openSubject('div')"),('practice-subj',"SS=null;openChapter('div',2);sPracticeStart()"),
 ('hint',"useHint();useHint()"),('ld',"SS=null;openChapter('div',8);sPracticeStart();useHint()"),('fractions',"SS=null;openChapter('frac',1);sPracticeStart()"),('boss',"sBossStart();useHint()"),
 ('mult-map',"SS=null;mapScreen()"),('mult-practice',"S=makeSession(ORDER[0]);practiceStart();useHint()"),('progress',"S=null;progressScreen()"),('settings',"settingsScreen()"),('profile',"profileScreen()"),('practicehub',"practiceHub()"),('quickdone',"quickDone('add',3,4)")]
with sync_playwright() as p:
    b=p.chromium.launch()
    for (w,h,mob) in [(320,640,True),(360,780,True),(390,844,True),(768,1024,True),(1024,768,False),(1440,900,False)]:
        c=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob); pg=c.new_page(); tag=f'{w}x{h}'
        pg.on('console',lambda m,t=tag: errs.append(f'[{t}] {m.text}') if m.type=='error' else None); pg.on('pageerror',lambda e,t=tag: errs.append(f'[{t}] {e}'))
        pg.goto(URL); pg.evaluate("s=>localStorage.setItem('ttq-save-v2',JSON.stringify(s))",V10); pg.reload(); pg.wait_for_timeout(500)
        ob=[];tb=[]
        for nm,js in SCREENS:
            pg.evaluate(js); pg.wait_for_timeout(250)
            o=pg.evaluate(OVF); t=pg.evaluate(TAP)
            if o: ob.append((nm,o))
            if t: tb.append((nm,t))
        ck(not ob,f'{tag}: no horizontal overflow on {len(SCREENS)} screens {ob[:3]}')
        ck(not tb,f'{tag}: tap targets >=44px {tb[:3]}')
        bn=pg.evaluate("(()=>{titleScreen();return getComputedStyle(document.getElementById('bnav')).display})()"); nv=pg.evaluate("getComputedStyle(document.getElementById('navHome')).display")
        ck((bn!='none' and nv=='none') if w<900 else (bn=='none' and nv!='none'),f'{tag}: {"bottom nav" if w<900 else "top nav"} shown (bnav={bn}, nav={nv})')
        c.close()
    # ---- v10 save loads intact
    c=b.new_context(viewport={'width':390,'height':844}); pg=c.new_page(); pg.on('pageerror',lambda e: errs.append(f'[v10] {e}'))
    pg.goto(URL); pg.evaluate("s=>localStorage.setItem('ttq-save-v2',JSON.stringify(s))",V10); pg.reload(); pg.wait_for_timeout(600)
    sv=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))")
    def sub(a,b):  # every v10 key/value still present
        if isinstance(a,dict): return isinstance(b,dict) and all(k in b and sub(a[k],b[k]) for k in a)
        return a==b
    ok=all(sub(V10['profiles'][k],sv['profiles'][k]) for k in V10['profiles'])
    ck(ok,'v10 save: every profile field (stars, hist, rewards, eq, age, grade, subject progress) kept after load')
    ck(all(k in pg.evaluate("Object.keys(save.profiles)") for k in V10['profiles']) and pg.evaluate("save.lastSubj")=='div' and pg.evaluate("save.hero")=='cayden','v10 save: heroes, current hero and lastSubj kept')
    ck(pg.evaluate("HUB")=='quest' and 'Division Docks' in pg.inner_text('#app'),'v10 save: resumes straight onto Cayden\'s Division Docks map')
    pg.evaluate("titleScreen()"); pg.wait_for_timeout(200); pg.click('#playBtn'); pg.wait_for_timeout(500)
    ck(pg.evaluate("save.hero")=='cayden' and pg.locator('text=Division').count()>0 and pg.evaluate("HUB")=='quest' and 'Division Docks' in pg.inner_text('#app') ,'v10 save: PLAY resumes Cayden on his last subject (division) map')
    pg.evaluate("progressScreen('melrose')"); pg.wait_for_timeout(200)
    ck('3/' in pg.inner_text('.prow[data-psubj=add]') or '7/' in pg.inner_text('.prow[data-psubj=add]'),'v10 save: Melrose addition progress shown on Progress (%s)'%pg.inner_text('.prow[data-psubj=add]').replace('\n',' '))
    sv2=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))")
    ck(all(sub(V10['profiles'][k],sv2['profiles'][k]) for k in V10['profiles']),'v10 save: still intact after browsing')
    c.close()
    # ---- keyboard play (desktop)
    c=b.new_context(viewport={'width':1440,'height':900}); pg=c.new_page(); pg.on('pageerror',lambda e: errs.append(f'[kbd] {e}'))
    pg.goto(URL); pg.evaluate("s=>localStorage.setItem('ttq-save-v2',JSON.stringify(s))",V10); pg.reload(); pg.wait_for_timeout(500)
    pg.evaluate("titleScreen()"); pg.wait_for_timeout(300)
    found=False
    for i in range(30):
        pg.keyboard.press('Tab'); 
        if pg.evaluate("document.activeElement.id")=='playNowD': found=True; break
    ck(found,'Tab reaches PLAY NOW')
    ring=pg.evaluate("(()=>{const s=getComputedStyle(document.activeElement);return s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>=2})()")
    ck(ring,'visible focus ring on focused button')
    pg.keyboard.press('Enter'); pg.wait_for_timeout(500)
    ck(pg.evaluate("HUB")=='quest','Enter on PLAY NOW opens the quest map')
    pg.evaluate("subjectScreen()"); pg.wait_for_timeout(200)
    for i in range(40):
        pg.keyboard.press('Tab')
        if pg.evaluate("(document.activeElement.textContent||'').includes('Subtraction')"): break
    pg.keyboard.press('Enter'); pg.wait_for_timeout(400)
    ck(pg.evaluate("SS&&SS.sid||P().lastSubj")=='sub','keyboard: Tab + Enter on a subject card opens it')
    pg.evaluate("SS=null;openChapter('sub',1);SC=null;sPracticeStart()"); pg.wait_for_timeout(300)
    if pg.evaluate("SS.cur.input")=='mc': pg.evaluate("document.querySelectorAll('.opt')[SS.cur.ans].focus()"); pg.keyboard.press('Enter')
    else: pg.keyboard.type(pg.evaluate("String(SS.cur.ans)")); pg.keyboard.press('Enter')
    pg.wait_for_timeout(300)
    ck(pg.evaluate("SS.pRes[0]")==True,'keyboard: type the answer + Enter answers the question')
    pg.wait_for_timeout(1200)
    pg.evaluate("document.getElementById('hintBtn').focus()"); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    ck(pg.is_visible('#hintbox') and pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==2,'keyboard: Enter on the lantern gives a clue')
    pg.keyboard.press('Space'); pg.wait_for_timeout(200)
    ck(pg.locator('#hintbox .vis').count()==1,'keyboard: Space on the lantern gives the picture clue')
    c.close()
    # ---- reduced motion + big text
    c=b.new_context(viewport={'width':360,'height':780},reduced_motion='reduce'); pg=c.new_page(); pg.on('pageerror',lambda e: errs.append(f'[rm] {e}'))
    pg.goto(URL); pg.evaluate("s=>{s.bigText=true;localStorage.setItem('ttq-save-v2',JSON.stringify(s))}",V10); pg.reload(); pg.wait_for_timeout(400)
    an=pg.evaluate("(()=>{const e=document.querySelector('.fsym');return e?getComputedStyle(e).animationName:'none'})()")
    ck(an=='none' or pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.fsym')).animationDuration)")<0.02,'reduced motion: floating symbols stop (%s)'%an)
    ck(pg.evaluate("document.body.classList.contains('bigtext')"),'big text setting applied')
    for nm,js in SCREENS[:11]:
        pg.evaluate(js); pg.wait_for_timeout(150); o=pg.evaluate(OVF)
        if o: ck(False,'big text 360: overflow on %s %s'%(nm,o)); break
    else: ck(True,'big text at 360px: no overflow')
    c.close(); b.close()
real=[e for e in errs]
ck(not real,'no console errors (%s)'%real[:4])
print('RESULT','ALL PASS' if not fails else 'FAILS: %d'%len(fails))
