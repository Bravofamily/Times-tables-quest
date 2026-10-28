import sys, os
from playwright.sync_api import sync_playwright
URL='file://'+os.path.abspath(os.path.join(os.path.dirname(__file__),'index.html'))
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
errors=[]
ABOUT={'sage':(7,'2'),'emi':(6,'1'),'blu':(1,'none'),'eshon':(6,'1'),'melrose':(8,'3'),'cayden':(10,'5')}
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


import json
LOG=[]
def lines(pg): 
    ls=pg.evaluate('TTQ.SC?TTQ.SC.lines.map(l=>[l.who,l.text]):[]'); h=pg.evaluate('TTQ.save.hero')
    for w,t in ls: LOG.append((h,w,t))
    return ls
_scene=scene
def scene(pg,shot=None,taps=True):
    pg.wait_for_selector('#bubble'); lines(pg); return _scene(pg,shot,taps)
V7_SAVE={"hero":"eshon","muted":False,"narrator":True,"profiles":{
 "emi":{"name":"Emi","stars":{"1":3},"hist":{},"rewards":["fcrown"],"eq":{"head":"fcrown"},"prologue":True,"age":6,"grade":"1"},
 "blu":{"name":"Blú","stars":{},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":1,"grade":"none"},
 "sage":{"name":"Sage","stars":{"1":2},"hist":{},"rewards":["teddy"],"eq":{"doll":"teddy"},"prologue":True,"age":7,"grade":"2"},
 "eshon":{"name":"Eshon","stars":{"1":3,"2":1},"hist":{},"rewards":["pencil","squiggle"],"eq":{"hand":"pencil"},"prologue":True,"age":6,"grade":"1"}}}
EXPECT={'melrose':dict(title='Melrose the Mermaid Fairy',sib='cayden',boss1='Sir Slime the Sea Snail',reward='wings',slot='back',closet='Dress-Up Closet',fx='.bubblefx',hc='rgb(192, 38, 211)',place='Fairy Glen',rel='big brother'),
        'cayden':dict(title='Cayden the Slam Dunk Hero',sib='melrose',boss1='Bouncy the Dribble Minion',reward='bball',slot='hand',closet='Sports Locker',fx='.speedfx',hc='rgb(220, 38, 38)',place='Backyard Court',rel='little sister')}
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---- old v7 save loads; new heroes get fresh profiles; old data untouched ----
    c0=b.new_context(viewport={'width':1100,'height':900}); p0=c0.new_page(); attach(p0,'v7save')
    p0.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.setItem('ttq-save-v2',%s);sessionStorage.setItem('seeded','1');}" % json.dumps(json.dumps(V7_SAVE)))
    p0.goto(URL); mult(p0)
    pr=p0.evaluate('TTQ.save.profiles')
    for k,v in V7_SAVE['profiles'].items():
        for f in ('name','stars','rewards','eq','age','grade'): assert pr[k][f]==v[f],(k,f,pr[k][f])
    for k in ('melrose','cayden'): assert pr[k]['name']==k.capitalize() and pr[k]['rewards']==[] and pr[k]['stars']=={},pr[k]
    assert p0.evaluate('TTQ.save.hero')=='eshon'
    print('v7 save migration ok')
    # ---- relationships ----
    rel=p0.evaluate("""()=>{const ids=Object.keys(HEROES),o={};for(const a of ids)for(const b of ids)if(a!==b)o[a+'>'+b]=relTo(a,b);return o;}""")
    for k,v in rel.items():
        a,bb=k.split('>')
        if {a,bb}=={'emi','blu'} or {a,bb}=={'melrose','cayden'}: continue
        assert v=='cousin',(k,v)
    assert rel['melrose>cayden']=='big brother' and rel['cayden>melrose']=='little sister' and rel['emi>blu']=='little brother' and rel['blu>emi']=='big sister'
    for x in ('emi','blu','sage','eshon'): assert rel['melrose>'+x]=='cousin' and rel[x+'>cayden']=='cousin'
    print('relationships ok')
    # static: every line a new hero could hear; sibling words only between melrose/cayden, cousin with the rest
    bad=p0.evaluate("""()=>{const out=[],keep=save.hero;const pools={SIDE,SIB_PROUD,LOSE_SIB,SIB_INTRO,ENC};
      for(const h of ['melrose','cayden']){save.hero=h;for(const sp of SIBS[h]){for(const [pn,pool] of Object.entries(pools))[].concat(pool[sp]||[]).forEach(t=>{const x=fillT(t,sp);
        if(/sister|brother/i.test(x)&&!['melrose','cayden'].includes(sp))out.push([h,sp,pn,x]);if(/friend\\b/i.test(x)&&/your friend|my friend/i.test(x))out.push([h,sp,pn,'friend?',x]);});}}
      save.hero=keep;return out;}""")
    assert bad==[],bad
    # every hero still has the same team as v7
    assert p0.evaluate("JSON.stringify({emi:SIBS.emi,blu:SIBS.blu,sage:SIBS.sage,eshon:SIBS.eshon})")==json.dumps({"emi":["blu","sage","eshon"],"blu":["emi","sage","eshon"],"sage":["emi","blu","eshon"],"eshon":["sage","emi","blu"]},separators=(',',':'))
    # data depth
    d=p0.evaluate("""()=>['melrose','cayden'].map(h=>[REWARDS[h].length,HPLACES[h].length,HPLACES[h].every(p=>p[h]&&p.name&&p.desc&&p.lost&&p.back&&p.props.length===7),Object.keys(HBOSS[h]).length,HCTX[h].length,SIDE[h].length,BRAVE[h].length,VICTORY[h].length,!!(HSTYLE[h]&&HERO_INTRO[h]&&SIB_INTRO[h]&&HERO_TEAM[h]&&OWL_WIN[h]&&ENC[h])])""")
    for x in d: assert x==[12,12,True,11,7,3,2,3,True],d
    # existing heroes' bosses and places unchanged
    assert p0.evaluate("save.hero='sage',[bossOf(1)[1],placeOf(1).name].join('|')")=='Slowpoke the Snail Minion|Flower Garden'
    p0.evaluate("save.hero='eshon'")
    print('static data ok')
    # ---- desktop: hero select with 6 heroes ----
    ctx=b.new_context(viewport={'width':1100,'height':900}); page=ctx.new_page(); attach(page,'desk')
    page.goto(URL); page.wait_for_selector('.herocard'); page.wait_for_timeout(700)
    ids=[e.get_attribute('data-hero') for e in page.query_selector_all('.herocard')]
    assert ids==['sage','emi','blu','eshon','melrose','cayden','zea'],ids
    bx=[page.query_selector(f'[data-hero={h}]').bounding_box() for h in ids]
    assert len(bx)==7 and page.locator('.hcar-dot').count()==7,bx
    assert page.evaluate('document.documentElement.scrollWidth')<=1100
    for h in ('melrose','cayden'): assert EXPECT[h]['title'] in page.inner_text(f'[data-hero={h}]')
    page.screenshot(path=os.path.join(D,'v9reg-f-hero-select.png'),full_page=True)
    for h in ('melrose','cayden'):
        E=EXPECT[h]
        page.evaluate('titleScreen()'); page.wait_for_selector('.herocard'); page.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",f'[data-hero={h}]')
        page.click('text=Start the adventure'); page.wait_for_selector('.about')
        page.screenshot(path=os.path.join(D,f'v9reg-f-{h}-about.png'))
        a,g=ABOUT[h]; page.click(f'[data-age="{a}"]'); page.click(f'[data-grade="{g}"]'); page.click('#abGo')
        page.wait_for_selector('#bubble')
        assert page.evaluate("document.body.className")=='theme-'+h
        assert page.evaluate("getComputedStyle(document.querySelector('#top')).borderBottomColor")==E['hc'],page.evaluate("getComputedStyle(document.querySelector('#top')).borderBottomColor")
        pro=lines(page); txt='\n'.join(f'{w}: {t}' for w,t in pro); print(txt)
        assert E['title'] in txt and E['rel'] in txt and 'cousin' in txt, 'prologue wording'
        assert page.query_selector('#c-sib svg.'+E['sib'])
        scene(page)
        mult(page); page.click('.lvl.next'); page.wait_for_selector('#bubble')
        assert E['place'] in page.inner_text('.scenetitle')
        n_props=len(page.query_selector_all('.prop')); assert n_props==7
        scene(page,f'v9reg-f-{h}-scene.png')
        learn(page)
        page.wait_for_selector('#q'); ans(page,True); page.wait_for_selector(E['fx'],timeout=1500); print(h,'power fx shown')
        page.wait_for_timeout(1150)
        for i in range(4): page.wait_for_selector('#q'); ans(page,True); page.wait_for_timeout(1150)
        page.click('button:has-text("Continue the story")')
        page.wait_for_selector('#bubble'); mid='\n'.join(t for w,t in lines(page)); assert E['boss1'] in mid,mid
        scene(page)
        boss(page,False,f'v9reg-f-{h}-boss.png')
        assert E['boss1'] in page.inner_text('.bname') if page.query_selector('.bname') else True
        scene(page)  # lose
        assert page.evaluate('TTQ.S.attempt')==2
        scene(page); learn(page); practice(page); scene(page)
        boss(page,True); scene(page)
        page.wait_for_selector('text=You WIN!'); assert E['boss1'] in page.inner_text('#app')
        assert page.evaluate(f"TTQ.save.profiles.{h}.rewards")==[E['reward']]
        page.click('button.pink'); page.wait_for_selector('text='+E['closet'])
        page.click(f"[data-item={E['reward']}]"); page.wait_for_timeout(250)
        assert page.evaluate(f"TTQ.save.profiles.{h}.eq.{E['slot']}")==E['reward']
        # unlock everything to check every item draws + map boss/place names
        page.evaluate(f"""()=>{{const p=TTQ.save.profiles.{h};p.rewards=REWARDS.{h}.map(r=>r.id);localStorage.setItem('ttq-save-v2',JSON.stringify(TTQ.save));}}""")
        page.click('#closetBtn'); page.wait_for_selector('.item')
        assert len(page.query_selector_all('.item.locked'))==0
        for r in page.evaluate(f"REWARDS.{h}.map(r=>r.id)"): page.click(f'[data-item={r}]'); page.wait_for_timeout(60)
        page.evaluate('window.scrollTo(0,0)'); page.click('#ch'); page.wait_for_timeout(1500)
        page.screenshot(path=os.path.join(D,f'v9reg-f-{h}-closet.png'),full_page=True)
        page.evaluate('mapScreen()'); mult(page); mp_txt=page.inner_text('#app'); assert E['place'] in mp_txt
        # final chapter: always the Muddle Monster + team line
        page.evaluate("S={n:12,attempt:1}"); fo='\n'.join(page.evaluate("outroScene(null).lines.map(l=>l.text)")); page.evaluate("S=null"); print(fo)
        assert 'Times Table Champions' in fo
        print(h,'flow ok')
    # ---- mobile 375 ----
    m=b.new_context(viewport={'width':375,'height':812},is_mobile=True,has_touch=True); mp=m.new_page(); attach(mp,'mobile')
    mp.goto(URL); mp.wait_for_selector('.herocard'); mp.wait_for_timeout(600)
    mp.screenshot(path=os.path.join(D,'v9reg-f-mobile-hero-select.png'),full_page=True)
    assert mp.evaluate('document.documentElement.scrollWidth')<=375
    xs=[mp.query_selector(f'[data-hero={h}]').bounding_box() for h in ('sage','emi','blu','eshon','melrose','cayden')]
    assert mp.locator('.hcar').count()==1,xs
    for h in ('melrose','cayden'):
        mp.evaluate('titleScreen()'); mp.wait_for_selector('.herocard'); mp.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",f'[data-hero={h}]'); start(mp); mp.wait_for_selector('#bubble'); mp.wait_for_timeout(700)
        assert mp.evaluate('document.documentElement.scrollWidth')<=375
        mp.screenshot(path=os.path.join(D,f'v9reg-f-mobile-{h}-scene.png'))
        scene(mp); mult(mp); mp.click('.lvl.next'); scene(mp); learn(mp); assert mp.evaluate('document.documentElement.scrollWidth')<=375
    b.close()
badr=[(h,w,t) for h,w,t in LOG if h in('melrose','cayden') and any(k in t.lower() for k in ('sister','brother')) and w not in ('sib','melrose','cayden','hero')]
assert not badr,badr
print('runtime lines',len(LOG),'sibling-word lines',len([1 for h,w,t in LOG if 'brother' in t.lower() or 'sister' in t.lower()]))
print('ERRORS:',errors if errors else 'none')
sys.exit(1 if errors else 0)
