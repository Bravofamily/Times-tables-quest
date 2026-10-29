# v22 update of test_v12_screens.py: same checks, adapted only for age groups, v22 version numbers and self-hosted fonts on file://
import os
# v12: every home button / tile / nav item opens its own real screen (not the hero picker), each reflects a seeded save;
# Realm Map + chapter detail, Training Grounds drills + needs-work mix, Trophy Room, Guide, Profiles, Heroes Hall (6 heroes + villain,
# play-as), Settings reset-confirm, Progress parent tip, Back + browser back, no console errors.
import json, os, copy, re
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
    print(('PASS ' if c else 'FAIL ')+m, flush=True); fails.append(m) if not c else None
SEED={"muted":True,"narrator":False,"hero":None,"lastHero":"cayden","lastSubj":"div","voice":"","profiles":{
 "melrose":{"name":"Melrose","stars":{"1":3,"2":2,"3":1},"hist":{},"rewards":["wings","tail"],"eq":{},"prologue":True,"age":8,"grade":"3",
   "subj":{"add":{"stars":{"1":3,"2":3,"3":1},"hist":{},"intro":True},"frac":{"stars":{"1":2},"hist":{},"intro":True}}},
 "cayden":{"name":"Cayden","stars":{"1":3},"hist":{},"rewards":["bball"],"eq":{},"prologue":True,"age":10,"grade":"5","lastSubj":"div",
   "subj":{"div":{"stars":{"1":3,"2":2},"hist":{},"intro":True},"sub":{"stars":{"1":1},"hist":{},"intro":True}},
   "weak":{"div:2":{"m":2,"h":1,"ok":0,"sigs":[]},"mult:1":{"m":1,"h":0,"ok":0,"sigs":["m1x7"]}},"hintLog":{"div":{"used":4,"qs":3,"ok":2,"ch":{"2":4}}},"hintTotal":4},
 "emi":{"name":"Emi","stars":{},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":6,"grade":"1"}}}
FACTS={'emi':(6,'Purple',True),'blu':(1,'Blue',False),'sage':(7,'Pink',False),'eshon':(6,'Green',False),'melrose':(8,'Pink',False),'cayden':(10,'Red',True)}
def load(pg,seed=SEED):
    pg.goto(URL); pg.evaluate("s=>localStorage.setItem('ttq-save-v2',JSON.stringify(s))",seed); pg.reload(); pg.wait_for_timeout(400)
def cur(pg): return pg.evaluate("TTQ_V12.CUR&&TTQ_V12.CUR.n")
def nopicker(pg): return pg.locator('#app .herocard').count()==0
with sync_playwright() as p:
    b=getattr(p,os.environ.get('PWB','chromium')).launch(); c=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=c.new_page()
    pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.on('dialog',lambda d: d.accept())
    load(pg)
    ck(pg.evaluate("APP_VERSION")=='22','APP_VERSION is 22')
    ck(pg.evaluate("HUB")=='home' and pg.evaluate("save.hero") is None,'seed with no active hero boots to home')
    # ---- every home control goes to its own screen ----
    targets=[('#bnQuest:visible, #navLevels:visible','realms'),('#bnPractice:visible, #navPractice:visible','training'),('[data-tile=trophies]','trophies'),('[data-tile=guide]','guide'),('[data-tile=heroes]','heroes'),
             ('[data-tile=progress]','progress'),('[data-tile=profile]','profile'),('[data-tile=settings]','settings')]
    seen=set()
    for sel,want in targets:
        pg.evaluate("titleScreen()"); pg.wait_for_timeout(120); pg.click(sel); pg.wait_for_timeout(250)
        n=cur(pg); seen.add(n)
        ck(n==want and nopicker(pg) and pg.locator('#backBtn').count()>0, f'home {sel} opens {want} (got {n}), no hero picker, has Back')
        pg.click('#backBtn'); pg.wait_for_timeout(200)
        ck(pg.evaluate("HUB")=='home','Back from %s returns home'%want)
    ck(len(seen)==len(targets),'all %d home controls open different screens'%len(targets))
    pg.evaluate("titleScreen()"); ck(pg.locator('#app .tiles .tile').count()==6,'home has 6 tiles incl. Heroes')
    pg.evaluate("titleScreen()"); pg.locator('#app .realm').nth(3).click(); pg.wait_for_timeout(250)
    ck(cur(pg)=='realms' and nopicker(pg),'home realm art opens the Realm Map (not the picker)')
    # ---- Realm Map ----
    pg.evaluate("titleScreen()"); pg.click('#bnQuest:visible, #navLevels:visible'); pg.wait_for_timeout(250)
    ck(pg.locator('.rcard').count()==6 and all(pg.locator(f'.rcard[data-realm={s}] .rline').count()==1 for s in ['add','sub','mult','div','frac','mix']),'Realm Map: 6 realms each with a one-line description')
    cls=lambda s: pg.get_attribute(f'[data-stone="{s}"]','class')
    ck('done' in cls('div-1') and 'done' in cls('div-2') and 'current' in cls('div-3') and 'locked' in cls('div-5'),'Realm Map reflects Cayden\'s save: div 1-2 done, 3 current, 5 locked')
    ck('★★★' in pg.inner_text('[data-stone="div-1"]') and '★★☆' in pg.inner_text('[data-stone="div-2"]'),'stones show real stars (3 and 2)')
    ck(pg.locator('[data-stone]').count()==sum(pg.evaluate("SUBJ.map(s=>sCount(s.id))")),'a stone for every chapter')
    pg.click('[data-stone="div-3"]'); pg.wait_for_timeout(250)
    ck(cur(pg)=='chapter' and pg.locator('[data-chd="div-3"]').count()==1 and pg.locator('.chdbox.ex .qeq').count()==1,'tapping a chapter shows skill + example question')
    ck('Play this chapter' in pg.inner_text('#playCh') and nopicker(pg),'chapter detail has Play this chapter (still no picker)')
    pg.click('#backBtn'); pg.wait_for_timeout(200); ck(cur(pg)=='realms','Back from chapter detail returns to Realm Map')
    pg.click('[data-stone="div-6"]'); pg.wait_for_timeout(200)
    ck('Locked' in pg.inner_text('.chdstate') and 'Chapter 3 instead' in pg.inner_text('#playCh'),'locked chapter: says beat Ch.3 first, offers current one')
    pg.go_back(); pg.wait_for_timeout(300); ck(cur(pg)=='realms','browser back returns to Realm Map')
    pg.click('[data-stone="div-3"]'); pg.wait_for_timeout(200); pg.click('#playCh'); pg.wait_for_timeout(400)
    ck(pg.evaluate("save.hero")=='cayden' and pg.evaluate("SS&&SS.sid")=='div' and pg.evaluate("SS.c")==3,'Play this chapter starts Cayden (last hero, no picker) on division ch.3')
    pg.evaluate("titleScreen()"); pg.click('#bnQuest:visible, #navLevels:visible'); pg.wait_for_timeout(200); pg.click('[data-vhero=melrose]'); pg.wait_for_timeout(200)
    ck('done' in cls('add-3') and 'current' in cls('add-4') and 'done' in cls('frac-1'),'hero tabs: Realm Map switches to Melrose\'s stars')
    pg.click('[data-stone="mult-2"]'); pg.wait_for_timeout(200); ck('×2' in pg.inner_text('.chdhead') or '×' in pg.inner_text('.chdbox.ex'),'mult chapter detail shows a times-table example')
    # ---- Training Grounds ----
    pg.evaluate("titleScreen()"); pg.click('#bnPractice:visible, #navPractice:visible'); pg.wait_for_timeout(250)
    ck(pg.locator('.drill').count()>=10 and all('Builds' in t for t in pg.locator('.drill small').all_inner_texts()),'Training Grounds: drill cards say what they build')
    ck(pg.locator('#mixBtn').count()==1 and pg.locator('[data-weak="div-2"]').count()==1 and pg.locator('[data-weak="mult-1"]').count()==1,'needs-work mix lists Cayden\'s seeded weak spots')
    pg.click('[data-mins="1"]'); ck(pg.evaluate("save.drillMins")==1 and pg.get_attribute('[data-mins="1"]','aria-pressed')=='true','round length 1 min selectable and saved')
    pg.click('[data-trealm=frac]'); pg.wait_for_timeout(150); ck(pg.locator('[data-drill^="frac-"]').count()==11,'realm tabs switch drills to fractions')
    pg.click('[data-drill="frac-1"]'); pg.wait_for_timeout(300)
    ck(pg.evaluate("SS&&SS.drill")==True and pg.locator('#drTime').count()==1 and pg.evaluate("TTQ_V11.lanLeft()")==3,'drill starts: timer + 3 lanterns, no picker')
    def answer(ok=True):
        q=pg.evaluate("({i:SS.cur.input,a:SS.cur.ans})")
        if q['i']=='mc': pg.evaluate("document.querySelectorAll('.opt')[%d].click()"%(q['a'] if ok else (q['a']+1)%len(pg.evaluate("SS.cur.opts")) ))
        elif q['i']=='ld': pg.evaluate("SS.onAnswer(%s,0)"%('true' if ok else 'false'))
        else:
            pg.keyboard.type(str(q['a']) if ok else '9999'); pg.keyboard.press('Enter')
        pg.wait_for_timeout(250)
    answer(True); ck(pg.evaluate("TTQ_V12.DR.score")==1,'correct drill answer scores')
    pg.wait_for_timeout(1100); ck(pg.evaluate("TTQ_V12.DR.total")==1 and pg.evaluate("!!SS.cur&&!SS.locked"),'auto-advances to the next question')
    pg.evaluate("useHint()"); pg.wait_for_timeout(150); ck(pg.evaluate("TTQ_V11.lanLeft()")==2,'lantern works in drills')
    answer(False); w=pg.evaluate("P().weak['frac:1']")
    ck(w and w['m']>=1 and w['h']>=1,'a missed + lantern question lands in needs-work (frac:1 %s)'%w)
    pg.click('#nextbtn'); pg.wait_for_timeout(250); ck(pg.evaluate("TTQ_V11.lanLeft()")==2,'lanterns carry across the round (2 left)')
    pg.evaluate("TTQ_V12.DR.end=Date.now()-10"); pg.wait_for_timeout(800)
    ck('Time' in pg.inner_text('#drTime'),'timer runs out')
    answer(True); pg.wait_for_timeout(1300)
    ck(pg.locator('#drDone').count()==1 and pg.evaluate("P().drills")==1,'round ends after the current question with a results card')
    pg.click('#drAgain'); pg.wait_for_timeout(250); ck(pg.evaluate("SS&&SS.drill")==True,'Go again restarts the drill')
    pg.click('#drEnd'); pg.wait_for_timeout(200); ck(pg.locator('#drDone').count()==1,'End round button works')
    pg.evaluate("go('training',null,'mult')"); pg.wait_for_timeout(200); pg.click('[data-drill="mult-3"]'); pg.wait_for_timeout(250)
    ck(pg.evaluate("SS.sid")=='mult' and pg.evaluate("SS.cur.input")=='pad' and pg.evaluate("SS.n")==10,'mult drill uses the times-table generator (×10, typed answers)')
    pg.evaluate("useHint();useHint()"); hb=pg.inner_text('#hintbox'); ans=str(pg.evaluate("SS.cur.ans")); qtx=str(pg.evaluate("SS.cur.text"))
    ck(len(hb)>5 and (re.search(r'(?<!\d)'+ans+r'(?!\d)',qtx) or not re.search(r'(?<!\d)'+ans+r'(?!\d)',hb)),'mult drill lantern clues never show the answer (unless it is already in the question)')
    answer(True); ck(pg.evaluate("TTQ_V12.DR.score")==1,'mult drill answer scores')
    pg.evaluate("go('training')"); pg.wait_for_timeout(200); pg.click('#mixBtn'); pg.wait_for_timeout(250)
    ck(pg.evaluate("TTQ_V12.DR.mix")==True and pg.evaluate("[SS.sid+':'+SS.c]")[0] in ['div:2','mult:1','frac:1']+list(pg.evaluate("Object.keys(weakOf(P()))")),'needs-work mix pulls questions from weak chapters')
    for i in range(6):
        if pg.evaluate("SS&&SS.cur&&!SS.locked"): answer(True); pg.wait_for_timeout(1000)
    ck(pg.evaluate("TTQ_V12.DR&&TTQ_V12.DR.score")>=4,'mix answers score')
    # ---- needs-work from regular play ----
    pg.evaluate("SS=null;openChapter('add',1);SC=null;sPracticeStart()"); pg.wait_for_timeout(250); answer(False)
    ck((pg.evaluate("P().weak['add:1']") or {}).get('m',0)>=1,'misses in normal chapters are tracked for the mix')
    pg.evaluate("S=null;SS=null;S=makeSession(ORDER[1]);practiceStart()"); pg.wait_for_timeout(250)
    pg.evaluate("useHint()"); ck((pg.evaluate("P().weak['mult:2']") or {}).get('h',0)>=1,'lantern use in mult practice is tracked')
    # ---- Trophy Room ----
    pg.evaluate("titleScreen()"); pg.click('[data-tile=trophies]'); pg.wait_for_timeout(250)
    ck(pg.locator('#badges .troph').count()>=10 and pg.locator('#items .troph').count()==12,'Trophy Room shows badges + 12 closet items')
    ck('got' in pg.get_attribute('[data-item=bball]','class') and 'lock' in pg.get_attribute('#items .troph:nth-child(2)','class'),'Cayden\'s earned basketball unlocked; others locked')
    ck('Win' in pg.inner_text('#items .troph:nth-child(2) small'),'locked items say how to earn them')
    ck('got' in pg.get_attribute('[data-badge="First Steps"]','class'),'badges reflect save (First Steps earned)')
    pg.click('[data-vhero=melrose]'); pg.wait_for_timeout(200); ck('got' in pg.get_attribute('[data-item=wings]','class'),'Trophy Room switches to Melrose\'s items')
    pg.click('#openCloset'); pg.wait_for_timeout(300); ck(pg.evaluate("save.hero")=='melrose' and pg.evaluate("HUB")!='home','Open closet goes to Melrose\'s closet')
    # ---- Guide ----
    pg.evaluate("titleScreen()"); pg.click('[data-tile=guide]'); pg.wait_for_timeout(250); g=pg.inner_text('#app')
    ck(pg.locator('[data-guide]').count()==6 and pg.locator('.gtab tbody tr').count()==6 and 'Muddle Monster' in g and 'NEVER give the answer' in g and 'Boss' in g,'Guide: story, Learn→Practice→Boss, stars, lanterns, realms by grade')
    ck(pg.locator('.spk').count()==6 and pg.locator('#readAll').count()==1,'Guide read-aloud buttons')
    # ---- Profiles ----
    pg.evaluate("titleScreen()"); pg.click('[data-tile=profile]'); pg.wait_for_timeout(250)
    ck(pg.locator('[data-pcard]').count()==7,'Profile: 7 hero cards')
    t=pg.inner_text('[data-pcard=cayden]'); ck('10' in t and '5th grade' in t and 'Division Docks' in t and 'Lanterns used' in t,'Cayden card: age 10, 5th grade, favourite realm Division Docks, lanterns')
    pg.click('[data-editabout=melrose]'); pg.wait_for_timeout(300); ck(pg.evaluate("save.hero")=='melrose' and 'About' in pg.inner_text('#app'),'Edit About Me opens Melrose\'s About Me')
    # ---- Heroes Hall ----
    pg.evaluate("titleScreen()"); pg.click('[data-tile=heroes]'); pg.wait_for_timeout(300)
    ck(pg.locator('[data-hall]').count()==8 and pg.locator('[data-hall=muddle]').count()==1,'Heroes Hall: 7 heroes + the Muddle Monster')
    for hid,(age,col,gl) in FACTS.items():
        pg.evaluate("go('hero','%s')"%hid); pg.wait_for_timeout(150); t=pg.inner_text('#app')
        ck(f'Age {age}' in t and col in t and pg.locator('.power').count()==3 and pg.locator('.stat').count()==4 and pg.locator('.more').count()==1 and pg.locator('#playAs').count()==1
           and 'skin' not in t and 'Catchphrase' in t and 'Best team combo' in t and 'Favorite realm' in t,f'{hid} page: age {age}, {col}, 3 powers, 4 stats, read more, combo, glasses={gl}')
    pg.evaluate("go('hero','emi')"); t=pg.inner_text('#app'); ck('Lighter skin' not in t and 'chin-length bob' not in t and 'Bloom Star' in t and 'brother' in t,'Emi: no appearance text (v15), title, Blú is her brother')
    pg.evaluate("go('hero','blu')"); t=pg.inner_text('#app'); ck('Blú' in t and pg.evaluate("HERO12.blu.realName")=='Khílo','Blú page keeps Blú; real name Khílo kept in data')
    pg.evaluate("go('hero','melrose')"); t=pg.inner_text('#app'); ck('Mermaid Fairy' in t and 'brother' in t and 'Cayden' in t,'Melrose: Mermaid Fairy, combo with brother Cayden')
    pg.evaluate("go('hero','eshon')"); t=pg.inner_text('#app'); ck('cousin' in t and 'locs' not in t,'Eshon: cousin combo, no appearance text (v15)')
    pg.evaluate("go('villain')"); ck(pg.locator('[data-hpage=muddle]').count()==1 and 'Weakness' in pg.inner_text('#app'),'villain card page')
    pg.evaluate("titleScreen()"); pg.click('[data-tile=heroes]'); pg.wait_for_timeout(200); pg.click('[data-hall=emi]'); pg.wait_for_timeout(250); pg.click('summary'); 
    ck(pg.evaluate("document.querySelector('.more').open"),'Read more expands')
    pg.click('#backBtn'); pg.wait_for_timeout(200); ck(cur(pg)=='heroes','Back from hero page returns to Heroes Hall')
    pg.click('[data-hall=emi]'); pg.wait_for_timeout(200); pg.click('#playAs'); pg.wait_for_timeout(400)
    ck(pg.evaluate("save.hero")=='emi' and pg.evaluate("HUB")=='quest','Play as Emi switches to Emi and starts playing')
    pg.evaluate("titleScreen()"); pg.wait_for_timeout(100)
    pg.evaluate("go('hero','sage')"); pg.click('#playAs'); pg.wait_for_timeout(300)
    ck(pg.evaluate("save.hero")=='sage' or 'About' in pg.inner_text('#app') or pg.evaluate("HUB")=='quest','Play as Sage (no About Me yet) goes through About Me / play, not a dead end')
    # ---- Settings ----
    pg.evaluate("titleScreen()"); pg.click('[data-tile=settings]'); pg.wait_for_timeout(250)
    for k in ['sound','narrator','calm','bigText']: ck(pg.locator('#tg-'+k).count()==1,'settings toggle '+k)
    ck(pg.locator('#voiceSel').count()+pg.locator('#noVoices').count()+pg.locator('#voiceLoading').count()==1,'voice choice (or a note when there are no voices)')
    pg.click('#tg-calm'); ck(pg.evaluate("save.calm")==True and pg.evaluate("document.body.classList.contains('calm')"),'reduced motion toggle')
    pg.click('#tg-calm')
    st0=pg.evaluate("JSON.stringify(save.profiles.melrose.stars)")
    pg.click('[data-reset=melrose]'); pg.wait_for_timeout(200); ck(pg.locator('#resetConfirm').count()==1 and 'Reset Melrose?' in pg.inner_text('#resetConfirm'),'reset asks to confirm first')
    pg.click('#resetNo'); pg.wait_for_timeout(200); ck(pg.locator('#resetConfirm').count()==0 and pg.evaluate("JSON.stringify(save.profiles.melrose.stars)")==st0,'Cancel keeps Melrose\'s progress')
    pg.click('[data-reset=melrose]'); pg.wait_for_timeout(150); pg.click('#resetYes'); pg.wait_for_timeout(200)
    m=pg.evaluate("save.profiles.melrose"); cy=pg.evaluate("allStars(save.profiles.cayden)")
    ck(pg.evaluate("allStars(save.profiles.melrose)")==0 and m['name']=='Melrose' and m['age']==AR(8) and m['grade']=='3' and cy>0 and pg.locator('#resetMsg').count()==1,'Yes resets only Melrose (name/age/grade kept, Cayden untouched)')
    sv=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))"); ck(allz:=sum(sum(x.get('stars',{}).values()) for x in sv['profiles']['melrose'].get('subj',{}).values())==0,'reset persisted')
    # ---- Progress tip ----
    pg.evaluate("titleScreen()"); pg.click('[data-tile=progress]'); pg.wait_for_timeout(250)
    ck(pg.locator('#parentTip').count()==1 and 'practice next' in pg.inner_text('#parentTip'),'Progress: parent "what to practice next" tip')
    pg.evaluate("progressScreen('cayden')"); pg.wait_for_timeout(150); ck('Ch.' in pg.inner_text('#parentTip'),'tip names Cayden\'s weakest chapter')
    pg.click('#tipGo'); pg.wait_for_timeout(200); ck(cur(pg)=='training','tip opens Training Grounds')
    # ---- bottom nav ----
    pg.evaluate("titleScreen()")
    for bid,want in [('bnQuest','realms'),('bnPractice','training'),('bnHeroes','heroes'),('bnProgress','progress'),('bnSettings','settings')]:
        pg.evaluate("titleScreen()"); pg.click('#'+bid); pg.wait_for_timeout(200); ck(cur(pg)==want and nopicker(pg),f'bottom nav {bid} -> {want}')
    pg.click('#bnHeroes'); ck('on' in (pg.get_attribute('#bnHeroes','class') or ''),'Heroes nav highlights')
    for sc in ['realms','training','heroes','settings','guide','trophies','profile']:
        pg.evaluate("titleScreen()"); pg.evaluate(f"go('{sc}')"); ck(pg.evaluate("TTQ_VERSION.safe")==True,f'auto-update treats {sc} as a safe moment')
    pg.evaluate("drillStart([{sid:'add',c:1}],false)"); pg.wait_for_timeout(200); ck(pg.evaluate("TTQ_VERSION.safe")==False,'auto-update waits during a drill')
    pg.evaluate("titleScreen()")
    # ---- fresh device: picker only when actually playing ----
    pg.evaluate("localStorage.clear()"); pg.reload(); pg.wait_for_timeout(400)
    pg.click('#bnPractice:visible, #navPractice:visible'); pg.wait_for_timeout(200); ck(cur(pg)=='training' and nopicker(pg),'fresh device: Practice opens Training Grounds, no picker')
    pg.click('[data-drill="add-1"]'); pg.wait_for_timeout(200); ck(cur(pg)=='pick' and pg.locator('#app .herocard').count()==7,'fresh device: picker appears only when a drill starts')
    pg.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'#app .herocard[data-hero=blu]'); pg.wait_for_timeout(200); pg.evaluate("startAdventure()"); pg.wait_for_timeout(200)
    ck('About' in pg.inner_text('#app') or pg.evaluate("SS&&SS.drill")==True,'after picking, About Me / prologue lead into the drill')
    b.close()
ck(not errs,'no console errors '+str(errs[:5]))
print('RESULT', 'FAIL %d'%len(fails) if fails else 'ALL PASS')
