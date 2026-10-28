import sys, os
from playwright.sync_api import sync_playwright
URL='file://'+os.path.abspath(os.path.join(os.path.dirname(__file__),'index.html'))
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors=[]
ABOUT={'sage':(7,'2'),'emi':(6,'1'),'blu':(1,'none'),'eshon':(6,'1'),'melrose':(8,'3'),'cayden':(10,'5')}
PAIRS=[{'emi','blu'},{'melrose','cayden'}]
def sibpair(a,b): return any(a in p and b in p for p in PAIRS)
def start(pg):
    pg.click('text=Start the adventure')
    if pg.query_selector('.about') or pg.wait_for_timeout(150) or pg.query_selector('.about'):
        hero=pg.evaluate('TTQ.save.hero'); a,g=ABOUT[hero]
        pg.click(f'[data-age="{a}"]'); pg.wait_for_selector(f'[data-grade="{g}"]'); pg.click(f'[data-grade="{g}"]'); pg.click('#abGo')

def mult(pg):
    for _ in range(8):
        pg.wait_for_selector('.stile, .lvl, #bubble')
        if pg.query_selector('.lvl'): return
        if pg.query_selector('.stile'): pg.click('[data-subject=mult]'); pg.wait_for_timeout(150); continue
        n=pg.evaluate('TTQ.SC?TTQ.SC.lines.length-TTQ.SC.i:0')
        for i in range(n): pg.click('#contBtn'); pg.wait_for_timeout(40)
        pg.wait_for_timeout(150)
    raise Exception('could not reach mult map')

def attach(page,tag):
    page.on('pageerror',lambda e:errors.append(f'[{tag}] pageerror {e}'))
    page.on('console',lambda m:m.type=='error' and errors.append(f'[{tag}] console {m.text}'))
    page.on('dialog',lambda d:d.accept())
def scene(page,shot=None,taps=True):
    page.wait_for_selector('#bubble')
    if taps:
        for p in page.query_selector_all('.prop'): p.click(); page.wait_for_timeout(40)
    if shot: page.wait_for_timeout(900); page.screenshot(path=os.path.join(D,shot))
    n=page.evaluate('TTQ.SC.lines.length-TTQ.SC.i')
    for i in range(n): page.click('#contBtn'); page.wait_for_timeout(60)
    return n
def ans(page,correct):
    q=page.wait_for_selector('#q'); t=q.get_attribute('data-type'); a=int(q.get_attribute('data-answer'))
    if page.query_selector('#pad'):
        v=a if correct else a+1
        for d in str(v): page.click(f'#pad button:text-is("{d}")')
        page.click('#okBtn')
    else:
        opts=page.query_selector_all('#opts .opt')
        for o in opts:
            if (int(o.get_attribute('data-val'))==a)==correct: o.click(); break
    return q.get_attribute('data-sig')
def learn(page):
    page.wait_for_selector('#addbtn')
    while page.is_visible('#addbtn'): page.click('#addbtn'); page.wait_for_timeout(30)
    page.click('#nextbtn')
    while page.is_visible('#stepbtn'): page.click('#stepbtn'); page.wait_for_timeout(30)
    page.click('#nextbtn'); page.click('#flipbtn'); page.wait_for_selector('#nextbtn:visible'); page.click('#nextbtn')
def practice(page):
    for i in range(5):
        page.wait_for_selector('#q'); ans(page,True); page.wait_for_timeout(1150)
    page.click('button:has-text("Continue the story")')
def boss(page,win,shot=None):
    sigs=[]
    if shot:
        page.wait_for_selector('#q'); page.wait_for_timeout(500); page.screenshot(path=os.path.join(D,shot))
    if win:
        for i in range(8):
            sigs.append(ans(page,True)); page.wait_for_timeout(1100)
    else:
        for i in range(3):
            sigs.append(ans(page,False)); page.wait_for_timeout(2350)
    return sigs
def chapter_with_loss_then_win(page,hero,shot_scene=None,shot_boss=None):
    mult(page); page.click('.lvl.next')
    scene(page,shot_scene); learn(page); practice(page); scene(page)
    s1=boss(page,False,shot_boss)
    assert page.query_selector('#bubble'),'lose scene missing'
    scene(page)  # lose scene
    assert page.evaluate('TTQ.S.attempt')==2
    page.wait_for_selector('#bubble'); txt=page.inner_text('#btext'); scene(page)  # retry intro
    learn(page); practice(page); scene(page)
    boss(page,True)
    scene(page)  # outro
    page.wait_for_selector('text=You WIN!')
    print(hero,'chapter done; retry intro line:',txt)

LOG=[]
def grab(page,hero):
    ls=page.evaluate('TTQ.SC?TTQ.SC.lines.map(l=>[l.who,l.text]):[]')
    for w,t in ls: LOG.append((hero,w,t))
    return ls
_scene=scene
def scene(page,shot=None,taps=True,hero=None):
    page.wait_for_selector('#bubble')
    grab(page,page.evaluate('TTQ.save.hero'))
    return _scene(page,shot,taps)
OLD_V3_SAVE={"hero":"sage","muted":False,"narrator":True,"profiles":{
 "emi":{"name":"Emi","stars":{"1":3,"2":2},"hist":{},"rewards":["fcrown","jacket"],"eq":{"head":"fcrown"},"prologue":True},
 "blu":{"name":"Blu","stars":{"1":1},"hist":{},"rewards":["bronze"],"eq":{"badge":"bronze"},"prologue":True},
 "sage":{"name":"Sage","stars":{"1":3},"hist":{},"rewards":["teddy"],"eq":{"doll":"teddy"},"prologue":True}}}
import json
def pixels(page):
    return page.evaluate("""()=>{const c=document.getElementById('pad-c'),d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;let n=0,g=0,o=0;for(let i=0;i<d.length;i+=4)if(d[i+3]>0){n++;if(d[i+1]>d[i]+40&&d[i+1]>d[i+2]+40)g++;else o++;}return {n,g,o};}""")
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---- migration from a v3 save (emi+blu+sage, no eshon) ----
    c0=b.new_context(viewport={'width':1100,'height':900}); p0=c0.new_page(); attach(p0,'migrate')
    p0.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.setItem('ttq-save-v2',%s);sessionStorage.setItem('seeded','1');}" % json.dumps(json.dumps(OLD_V3_SAVE)))
    p0.goto(URL); mult(p0)
    pr=p0.evaluate('TTQ.save.profiles')
    for k in ('emi','blu','sage'):
        for f in ('name','stars','rewards','eq'): assert pr[k][f]==OLD_V3_SAVE['profiles'][k][f],(k,f,pr[k][f])
    assert pr['eshon']['name']=='Eshon' and pr['eshon']['rewards']==[]
    p0.click('#homeBtn') if p0.query_selector('#homeBtn:visible') else None
    p0.evaluate('titleScreen()'); p0.wait_for_selector('.herocard')
    assert len(p0.query_selector_all('.herocard'))==7
    assert pr['melrose']['name']=='Melrose' and pr['cayden']['rewards']==[]
    p0.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=sage]'); start(p0); mult(p0)
    assert p0.evaluate("TTQ.save.profiles.sage.eq.doll")=='teddy'
    print('migration ok')
    # ---- static data check: sister/brother only between Emi/Blu and Melrose/Cayden (Melrose/Cayden only ever join each other's team) ----
    bad=p0.evaluate("""()=>{const out=[],keep=save.hero,ids=Object.keys(HEROES);
      const pools={SIDE,SIB_PROUD,LOSE_SIB,SIB_INTRO,ENC};const own={BRAVE,VICTORY,LOSE_HERO,RETRY_HERO,HERO_INTRO,HERO_TEAM,OWL_WIN};
      for(const h of ids){save.hero=h;
        for(const sp of ids){if(sp===h)continue;if(['melrose','cayden'].includes(sp)&&!SIBS[h].includes(sp))continue;for(const [pn,pool] of Object.entries(pools)){[].concat(pool[sp]||[]).forEach(t=>{const x=fillT(t,sp);if(/sister|brother/i.test(x)&&!((['emi','blu'].includes(h)&&['emi','blu'].includes(sp))||(['melrose','cayden'].includes(h)&&['melrose','cayden'].includes(sp))))out.push([h,sp,pn,x]);});}}
        for(const [pn,pool] of Object.entries(own)){[].concat(pool[h]||[]).forEach(t=>{const x=fillT(t,'hero');if(/sister|brother/i.test(x)&&!['emi','blu','melrose','cayden'].includes(h))out.push([h,'hero',pn,x]);});}
        PLACES.forEach(pl=>{const x=fillT(pl[h],'hero');if(/sister|brother/i.test(x)&&!['emi','blu'].includes(h))out.push([h,'place',x]);});
        [HEROES[h].title].concat(['melrose','cayden'].includes(h)?[]:[HEROES[h].blurb]).forEach(x=>{if(/sister|brother/i.test(x))out.push([h,'blurb',x]);});}
      save.hero=keep;return out;}""")
    assert bad==[],bad
    assert p0.evaluate("['emi','blu','sage','eshon'].every(h=>!SIBS[h].includes('melrose')&&!SIBS[h].includes('cayden'))")
    print('static sister/brother check ok')
    # ---- desktop: 4-hero select + Eshon chapter 1 ----
    ctx=b.new_context(viewport={'width':1100,'height':900}); page=ctx.new_page(); attach(page,'main')
    page.goto(URL); page.wait_for_selector('.herocard'); page.wait_for_timeout(700)
    assert [e.get_attribute('data-hero') for e in page.query_selector_all('.herocard')]==['sage','emi','blu','eshon','melrose','cayden','zea']
    bx=[page.query_selector(f'[data-hero={h}]').bounding_box() for h in ('sage','emi','blu','eshon','melrose','cayden')]
    assert page.locator('.hcar .hslide[data-off="0"],.hcar .hslide[data-off="1"],.hcar .hslide[data-off="-1"]').count()==3, 'v16 carousel shows 3'
    sw=page.evaluate('document.documentElement.scrollWidth'); assert sw<=1100
    page.screenshot(path=os.path.join(D,'v9reg-hero-select.png'),full_page=True)
    page.query_selector('[data-hero=emi]').screenshot(path=os.path.join(D,'v9reg-emi-select.png'))
    assert page.evaluate("heroSVG('emi').includes('#c98d63')&&!heroSVG('emi').includes('cx=\"196\" cy=\"90\"')"), 'emi skin/bob not applied'
    page.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=eshon]'); start(page)
    page.wait_for_selector('#c-x-emi'); assert page.query_selector('#c-sib') and page.query_selector('#c-x-blu')
    assert page.evaluate("getComputedStyle(document.querySelector('#top')).borderBottomColor")=='rgb(22, 163, 74)'
    pro=page.evaluate('TTQ.SC.lines.map(l=>l.who+": "+l.text)'); print('\n'.join(pro))
    assert any('cousin' in l for l in pro)
    scene(page)
    mult(page); page.click('.lvl.next'); page.wait_for_selector('#bubble')
    assert page.query_selector('#c-x-emi'), 'Emi extra sidekick missing for Eshon'
    print('\n'.join(page.evaluate('TTQ.SC.lines.map(l=>l.who+": "+l.text)')))
    scene(page,'v9reg-eshon-scene.png')
    learn(page)
    page.wait_for_selector('#q'); ans(page,True); page.wait_for_selector('.doodlefx',timeout=1500); print('doodle fx shown')
    page.wait_for_timeout(1150)
    for i in range(4): page.wait_for_selector('#q'); ans(page,True); page.wait_for_timeout(1150)
    page.click('button:has-text("Continue the story")')
    page.wait_for_selector('#bubble'); print('\n'.join(page.evaluate('TTQ.SC.lines.map(l=>l.who+": "+l.text)'))); scene(page)
    boss(page,False,'v9reg-eshon-boss.png')
    assert page.query_selector('#bubble'),'lose scene missing'
    print('\n'.join(page.evaluate('TTQ.SC.lines.map(l=>l.who+": "+l.text)'))); scene(page)
    assert page.evaluate('TTQ.S.attempt')==2
    page.wait_for_selector('#bubble'); print('\n'.join(page.evaluate('TTQ.SC.lines.map(l=>l.who+": "+l.text)'))); scene(page)
    learn(page); practice(page); scene(page)
    boss(page,True)
    page.wait_for_selector('#bubble'); print('\n'.join(page.evaluate('TTQ.SC.lines.map(l=>l.who+": "+l.text)'))); scene(page)
    page.wait_for_selector('text=You WIN!')
    assert page.evaluate("TTQ.save.profiles.eshon.rewards")==['pencil']
    # ---- Art Studio + Doodle Pad ----
    page.click('button.pink'); page.wait_for_selector('text=Art Studio')
    page.click('[data-item=pencil]'); page.wait_for_timeout(200)
    assert page.evaluate("TTQ.save.profiles.eshon.eq.hand")=='pencil'
    assert len(page.query_selector_all('.sw:not(.lockd)'))==2
    page.evaluate("""()=>{const p=TTQ.save.profiles.eshon;p.rewards=['pencil','squiggle','colors','beret','bloop','palette','cape','zigzag','easel','neon'];p.eq={hand:'pencil',buddy:'squiggle',pocket:'colors',head:'beret',back:'cape',stage:'easel'};localStorage.setItem('ttq-save-v2',JSON.stringify(TTQ.save));}""")
    page.click('#closetBtn'); page.wait_for_selector('#pad-c')
    assert len(page.query_selector_all('.sw:not(.lockd)'))==10 and len(page.query_selector_all('.sw.lockd'))==1
    page.click('#padClear')
    c=page.query_selector('#pad-c'); page.evaluate("document.getElementById('pad-c').scrollIntoView({block:'center'})"); bb=c.bounding_box()
    def stroke(pts):
        page.mouse.move(bb['x']+pts[0][0]*bb['width'],bb['y']+pts[0][1]*bb['height']); page.mouse.down()
        for x,y in pts[1:]: page.mouse.move(bb['x']+x*bb['width'],bb['y']+y*bb['height'],steps=6)
        page.mouse.up()
    # a green smiley character
    import math
    stroke([(0.5+0.18*math.cos(t/20*2*math.pi),0.5+0.27*math.sin(t/20*2*math.pi)) for t in range(21)])
    px=pixels(page); assert px['g']>500 and px['o']<px['g'],px
    page.click('.sw[data-col="#3b82f6"]')
    stroke([(0.43,0.42),(0.44,0.44)]); stroke([(0.56,0.42),(0.57,0.44)])
    page.click('.sw[data-col="#ec4899"]')
    stroke([(0.4,0.58),(0.45,0.64),(0.5,0.66),(0.55,0.64),(0.6,0.58)])
    px2=pixels(page); assert px2['o']>100,px2
    page.wait_for_timeout(200)
    page.click('[data-item=bloop]'); page.wait_for_timeout(500)  # re-render must keep drawing
    px3=pixels(page); assert px3['n']>=px2['n']*0.95,(px2,px3)
    assert page.evaluate("localStorage.getItem('ttq-doodle-eshon')").startswith('data:image/png')
    page.click('[data-item=bloop]'); page.wait_for_timeout(500)
    page.evaluate('window.scrollTo(0,0)'); page.click('#ch'); page.wait_for_timeout(1900)
    page.screenshot(path=os.path.join(D,'v9reg-eshon-rewards.png'),full_page=True)
    # touch drawing on a phone
    print('art studio + doodle pad ok', px, px2, px3)
    # ---- regression: sage (fresh), emi, blu ----
    for hero in ('sage','emi','blu'):
        page.click('#homeBtn'); page.click('text=Switch hero'); page.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",f'[data-hero={hero}]'); start(page)
        page.wait_for_selector('#bubble'); pl=page.evaluate('TTQ.SC.lines.map(l=>l.who+": "+l.text)'); print('\n'.join(pl))
        others=[x for x in ('sage','emi','blu','eshon') if x!=hero]
        assert page.query_selector('#c-sib') and len(page.query_selector_all('.castm.side2'))==2
        scene(page)
        chapter_with_loss_then_win(page,hero,shot_scene='v9reg-emi-scene.png' if hero=='emi' else None)
        page.wait_for_timeout(300)
    # ---- final chapter scenes + champion map with all four (eshon) ----
    page.evaluate("""()=>{const p=TTQ.save.profiles.eshon;[1,2,10,5,3,4,9,6,7,8,11].forEach(n=>p.stars[n]=3);localStorage.setItem('ttq-save-v2',JSON.stringify(TTQ.save));}""")
    page.click('#homeBtn'); page.click('text=Switch hero'); page.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=eshon]'); start(page)
    mult(page); page.click('.lvl.next'); scene(page); learn(page); page.screenshot(path=os.path.join(D,'v9reg-eshon-learn.png')); practice(page)
    page.wait_for_selector('#bubble'); grab(page,'eshon'); page.click('#contBtn'); page.wait_for_timeout(900); page.screenshot(path=os.path.join(D,'v9reg-eshon-final-boss-scene.png'))
    page.evaluate("""()=>{const p=TTQ.save.profiles.eshon;p.stars[12]=3;localStorage.setItem('ttq-save-v2',JSON.stringify(TTQ.save));}""")
    page.evaluate('mapScreen()'); page.wait_for_selector('.winheroes')
    assert len(page.query_selector_all('.winheroes > div'))==4
    # outro line check for the final chapter
    page.evaluate("S={n:12,attempt:1}"); fo=page.evaluate("outroScene(null).lines.map(l=>l.who+': '+l.text)"); print('\n'.join(fo))
    assert any('Eshon, Sage, Emi and Blú are true Times Table Champions' in l for l in fo)
    page.evaluate("S=null")
    # ---- mobile ----
    m=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); mp=m.new_page(); attach(mp,'mobile')
    mp.goto(URL); mp.wait_for_selector('.herocard'); mp.wait_for_timeout(600)
    mp.screenshot(path=os.path.join(D,'v9reg-mobile-hero-select.png'),full_page=True)
    sw=mp.evaluate('document.documentElement.scrollWidth'); assert sw<=390,('horizontal overflow',sw)
    xs=[mp.query_selector(f'[data-hero={h}]').bounding_box() for h in ('sage','emi','blu','eshon','melrose','cayden')]
    assert mp.locator('.hcar').count()==1, 'v16 carousel on mobile'
    mp.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=eshon]'); start(mp); mp.wait_for_selector('#bubble'); mp.wait_for_timeout(900)
    mp.screenshot(path=os.path.join(D,'v9reg-mobile-eshon-scene.png'))
    sw=mp.evaluate('document.documentElement.scrollWidth'); assert sw<=390,('horizontal overflow scene',sw)
    mp.evaluate("""()=>{const p=TTQ.save.profiles.eshon;p.rewards=['pencil','colors'];localStorage.setItem('ttq-save-v2',JSON.stringify(TTQ.save));}""")
    mp.evaluate('closetScreen()'); mp.wait_for_selector('#pad-c'); mp.evaluate("document.getElementById('pad-c').scrollIntoView({block:'center'})"); mp.wait_for_timeout(200)
    bb=mp.query_selector('#pad-c').bounding_box()
    assert bb['x']+bb['width']<=390
    cdp=m.new_cdp_session(mp)
    pts=[(bb['x']+bb['width']*(0.2+0.06*i),bb['y']+bb['height']*(0.5+0.2*((-1)**i))) for i in range(11)]
    cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':pts[0][0],'y':pts[0][1]}]})
    for x,y in pts[1:]: cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x,'y':y}]}); mp.wait_for_timeout(16)
    cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]})
    mp.wait_for_timeout(200); tp=pixels(mp); print('touch pixels',tp); assert tp['g']>300,tp
    sw=mp.evaluate('document.documentElement.scrollWidth'); assert sw<=390,('overflow closet',sw)
    mp.screenshot(path=os.path.join(D,'v9reg-mobile-eshon-studio.png'),full_page=True)
    # ---- no TTS ----
    c2=b.new_context(); p2=c2.new_page(); attach(p2,'noTTS')
    p2.add_init_script("delete window.speechSynthesis; delete window.SpeechSynthesisUtterance; Object.defineProperty(window,'speechSynthesis',{value:undefined}); Object.defineProperty(window,'SpeechSynthesisUtterance',{value:undefined});")
    p2.goto(URL); assert p2.evaluate('TTQ.hasTTS()')==False
    p2.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=eshon]'); start(p2); p2.wait_for_selector('#bubble')
    for i in range(4): p2.click('#narrBtn'); p2.click('#replayBtn')
    scene(p2); mult(p2); p2.click('.lvl.next'); scene(p2); print('no-TTS flow ok')
    b.close()
# ---- runtime sister/brother check over every line shown ----
badr=[(h,w,t) for h,w,t in LOG if any(k in t.lower() for k in ('sister','brother')) and not (h in('emi','blu') and w in ('sib','emi','blu','hero')) and not (h in('melrose','cayden') and w in ('sib','melrose','cayden','hero'))]
assert not badr, badr
sb=[(h,w,t) for h,w,t in LOG if any(k in t.lower() for k in ('sister','brother'))]
print('runtime lines checked:',len(LOG),'sibling-word lines (all emi/blu):',len(sb))
print('ERRORS:',errors if errors else 'none')
sys.exit(1 if errors else 0)
