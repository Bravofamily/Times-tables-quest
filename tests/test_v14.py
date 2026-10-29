# v22 update of test_v14.py: same checks, adapted only for age groups, v22 version numbers and self-hosted fonts on file://
import os
# v14: Zea the Critter Flip Star (7th hero): select, About Me, story, Heroes Hall, rewards, banter, Grand Final, migration, hints, generator, layout.
import json,os,sys,re
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
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); URL='file://'+D+'/index.html'
errs=[];fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m,flush=True)
    if not c: fails.append(m)
T12={str(i):3 for i in range(1,13)}
V13SEED={"muted":True,"narrator":False,"hero":"emi","lastHero":"emi","voice":"","chv":13,"profiles":{
 "emi":{"name":"Emi","stars":T12,"hist":{},"rewards":["fcrown"],"eq":{"head":"fcrown"},"prologue":True,"age":8,"grade":"3",
  "subj":{"mult":{"stars":{"13":3,"14":2,"15":3},"hist":{},"intro":True},"mix":{"stars":{"1":3,"2":2,"3":3},"hist":{},"intro":True},"add":{"stars":{"10":3,"11":2},"hist":{},"intro":True}},
  "weak":{"mix:3":{"m":2,"h":0,"ok":0,"sigs":[]}},"hintLog":{"add":{"used":3,"qs":2,"ok":1,"ch":{"10":3}}},"hintTotal":3},
 "cayden":{"name":"Cayden","stars":{"1":3,"2":2},"hist":{},"rewards":["bball"],"eq":{},"prologue":True,"age":10,"grade":"5","subj":{"div":{"stars":{"1":3,"12":2},"hist":{},"intro":True}}},
 "melrose":{"name":"Melrose","stars":{},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":8,"grade":"3"}}}
ZSAVE={"muted":True,"narrator":False,"hero":"zea","lastHero":"zea","voice":"","chv":13,"profiles":{"zea":{"name":"Zea","stars":{"1":3,"2":3,"3":3},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":7,"grade":"2","subj":{"add":{"stars":{"1":3},"hist":{},"intro":True}}}}}
BAD=re.compile(r'undefined|NaN|\[object|\{(hero|rel|me|myrel|T|R|n|place|title)\}')
SIBW=re.compile(r'sister|brother',re.I)
def load(pg,seed):
    pg.goto(URL); pg.evaluate("s=>{localStorage.clear();if(s)localStorage.setItem('ttq-save-v2',JSON.stringify(s))}",seed); pg.reload(); pg.wait_for_timeout(400)
def noov(pg,w): return pg.evaluate("document.documentElement.scrollWidth")<=w+1
def drain(pg):
    out=[]
    for _ in range(80):
        if not pg.evaluate("!!TTQ.SC"): break
        out.append(pg.evaluate("(document.querySelector('#who')||{}).innerText+': '+(document.querySelector('#btext')||{}).innerText")); pg.evaluate("nextLine()"); pg.wait_for_timeout(30)
    return out
with sync_playwright() as p:
    b=getattr(p,os.environ.get('PWB','chromium')).launch(); c=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=c.new_page()
    pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.on('dialog',lambda d: d.accept())
    load(pg,None)
    ck(pg.evaluate("APP_VERSION")=='22','APP_VERSION is 22')
    ck(json.load(open(D+'/version.json'))=={"version":"22"},'version.json is {"version":"22"}')
    # ---------- data ----------
    d=pg.evaluate("""()=>({order:HERO_ORDER.join(),title:HEROES.zea.title,cfg:ZEA_CFG,rew:REWARDS.zea.length,pl:HPLACES.zea.length,plok:HPLACES.zea.every(p=>p.zea&&p.name&&p.desc&&p.lost&&p.back&&p.props.length===7),
      boss:Object.keys(HBOSS.zea).length,sibs:SIBS.zea,rel:HERO_ORDER.filter(x=>x!=='zea').map(x=>relTo('zea',x)+'/'+relTo(x,'zea')),
      keep:[relTo('emi','blu'),relTo('blu','emi'),relTo('melrose','cayden'),relTo('cayden','melrose')],
      others:JSON.stringify({emi:SIBS.emi,blu:SIBS.blu,sage:SIBS.sage,eshon:SIBS.eshon}),mc:[SIBS.melrose[0],SIBS.cayden[0]],
      h12:!!HERO12.zea,cp:BRAVE.zea[0],sub:['add','sub','mult','div','frac','mix'].every(s=>HSUB[s].zea&&HSUB[s].zea.length===2&&TEAM_SUB[s].zea&&TEAM_SUB[s].zea.length===2)})""")
    ck(d['order']=='sage,emi,blu,eshon,melrose,cayden,zea','HERO_ORDER: Zea is the 7th hero')
    ck(d['title']=='Zea the Critter Flip Star','title: Zea the Critter Flip Star')
    ck(d['cfg']['age']==7 and 'look' not in d['cfg'],'easy-to-change defaults in ZEA_CFG (age 7, no appearance text)')
    ck(d['rew']==12 and d['pl']==12 and d['plok'] and d['boss']==11,'12 Gym Bag rewards, 12 story places (7 props each), 11 friendly minions + final')
    ck(all(r=='cousin/cousin' for r in d['rel']) and d['keep']==['little brother','big sister','big brother','little sister'],'Zea is cousin to all; Emi&Blú and Melrose&Cayden unchanged')
    ck(d['others']==json.dumps({"emi":["blu","sage","eshon"],"blu":["emi","sage","eshon"],"sage":["emi","blu","eshon"],"eshon":["sage","emi","blu"]},separators=(',',':')) and d['mc']==['cayden','melrose'],'existing team lists unchanged (siblings still first)')
    ck(d['h12'] and d['sub'],'Heroes Hall data + intro/team lines in all 6 realms')
    ck(d['cp']=='Stick the landing, strike a pose! Critter Flip, GO! 🤸‍♀️','catchphrase')
    # ---------- no sibling words / friend words in anything Zea or her lines say ----------
    w=pg.evaluate("""()=>{const out=[];const pools={SIB_INTRO,HERO_INTRO,HERO_TEAM,SIDE,BRAVE,VICTORY,SIB_PROUD,LOSE_SIB,LOSE_HERO,RETRY_HERO,OWL_WIN,ENC,HTAUNTS};
      const add=(k,x)=>[].concat(x||[]).forEach(t=>{if(typeof t!=='string')t=JSON.stringify(t);if(/sister|brother/i.test(t)||/my friend|your friend/i.test(t))out.push([k,t]);});
      for(const [k,p] of Object.entries(pools))add(k,p.zea);for(const s of ['add','sub','mult','div','frac','mix']){add('HSUB'+s,HSUB[s].zea);add('TEAM'+s,TEAM_SUB[s].zea);}
      add('HPLACES',HPLACES.zea.map(p=>p.zea+p.desc+p.lost+p.back));add('HERO12',JSON.stringify(HERO12.zea));add('HEROES',HEROES.zea.blurb+HEROES.zea.title);return out;}""")
    ck(w==[],'no sister/brother/"my friend" in Zea text %s'%w[:3])
    # ---------- picker ----------
    pg.wait_for_selector('.herocard')
    ids=[e.get_attribute('data-hero') for e in pg.query_selector_all('.herocard')]
    ck(ids==['sage','emi','blu','eshon','melrose','cayden','zea'],'picker shows 7 heroes, Zea last: %s'%ids)
    ck('Zea the Critter Flip Star' in pg.inner_text('[data-hero=zea]') and pg.locator('[data-hero=zea] svg.hero.zea').count()==1,'Zea tile: title + SVG')
    zsvg=pg.inner_html('[data-hero=zea] .hsv'); ck('glasses' not in zsvg and 'aria-label="Zea"' in zsvg,'Zea SVG: no glasses, labelled')
    for wd in (320,360,390,430,560,600,768,1024,1440):
        pg.set_viewport_size({'width':wd,'height':900}); pg.evaluate("v16Go('zea')"); pg.wait_for_timeout(600)
        r=pg.evaluate("""()=>{const c=document.querySelector('.hslide[data-off="0"]').getBoundingClientRect(),g=document.querySelector('.hcar').getBoundingClientRect();
          return {zc:(c.left+c.right)/2,gc:(g.left+g.right)/2,cw:c.width,inside:c.left>=-1&&c.right<=innerWidth+1,n:document.querySelectorAll('.herocard').length,ctr:v16Center()};}""")
        ck(r['n']==7 and r['ctr']=='zea' and r['inside'] and noov(pg,wd) and abs(r['zc']-r['gc'])<3 and r['cw']>=170,'picker %dpx: carousel, Zea centered, not cramped, no overflow (%s)'%(wd,r))
    pg.set_viewport_size({'width':1440,'height':900}); pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(150)
    pg.locator('.herocards').screenshot(path=D+'/v14-hero-select.png')
    pg.set_viewport_size({'width':390,'height':844})
    # ---------- select Zea -> About Me -> prologue ----------
    pg.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=zea]'); pg.click('text=Start the adventure'); pg.wait_for_selector('.about [data-age]')
    ck(pg.inner_text('.abq').startswith('How old are you, Zea'),'first pick of Zea shows About Me')
    pg.click('[data-age="6-7"]'); pg.wait_for_selector('[data-grade]'); pg.click('[data-grade="2"]'); pg.wait_for_selector('#abGo')
    ck(pg.inner_text('.abq')=="Nice to meet you, Zea! Ages 6–7, in 2nd grade!",'About Me confirmation for Zea')
    s=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2')).profiles.zea"); ck(s['age']==AR(7) and s['grade']=='2' and s['name']=='Zea','Zea profile saved (age 7, grade 2)')
    pg.click('#abGo'); pg.wait_for_selector('#bubble'); lines=drain(pg); pg.wait_for_timeout(200)
    ck(pg.locator('.stile').count()==6 and pg.evaluate("document.body.classList.contains('theme-zea')"),'prologue -> Subject Select, Zea theme on')
    ck(not any(BAD.search(x) or SIBW.search(x) for x in lines) and any('Zea' in x for x in lines),'prologue lines OK (%d)'%len(lines))
    # ---------- 12-chapter times-table story ----------
    load(pg,ZSAVE); allb=[]
    pg.evaluate("TTQ.save.profiles.zea.stars=%s;persist()"%json.dumps(T12))
    for n in range(1,13):
        pg.evaluate("openLevel(%d)"%n if True else ""); pg.wait_for_timeout(120)
        ls=drain(pg); allb+=ls
        pl=pg.evaluate("HPLACES.zea[ORDER.indexOf(%d)].name"%n)
        ck(len(ls)>=4 and any(pl in x for x in ls) and not any(BAD.search(x) for x in ls),'story chapter ×%d: %s (%d lines)'%(n,pl,len(ls)))
        pg.evaluate("S=null;SC=null"); 
    ck(not any(SIBW.search(x) for x in allb),'no sibling words anywhere in Zea story scenes')
    pg.evaluate("openLevel(3)"); pg.wait_for_timeout(200); pg.evaluate("nextLine();nextLine()"); pg.wait_for_timeout(1800); pg.screenshot(path=D+'/v14-zea-story.png'); ck(pg.evaluate("getComputedStyle(document.querySelector('#btext')).color")=='rgb(30, 41, 59)','story bubble text is dark slate on cream (readable)'); drain(pg)
    props=pg.evaluate("[...document.querySelectorAll('.prop.critter')].length")
    # castle scene props include critters
    pg.evaluate("S=null;SC=null;openLevel(1)"); pg.wait_for_timeout(200)
    k=pg.evaluate("[...document.querySelectorAll('.prop')].map(e=>e.dataset.kind)")
    if pg.locator('.prop.critter').count():
        pg.locator('.prop.critter').first.click(); pg.wait_for_timeout(200)
    ck('critter' in k or len(k)==0,'critter props in Zea scenes and tappable: %s'%k)
    drain(pg)
    # ---------- subject realms: every chapter intro/mid/outro/lose scene + team banter ----------
    sc=pg.evaluate("""()=>{const bad=[];let n=0;save.hero='zea';
      for(const sb of SUBJ){const cnt=sb.id==='mult'?sCount('mult'):sb.ch.length;const start=sb.id==='mult'?13:1;
       for(let c=start;c<=cnt;c++){try{makeSS(sb.id,c);for(const f of [sIntroScene,sMidScene,()=>sOutroScene(null),sLoseScene]){const t=JSON.stringify(f());n++;if(/undefined|NaN|\\[object/.test(t))bad.push(sb.id+c+' '+t.slice(0,140));if(/sister|brother/i.test(t))bad.push('sib '+sb.id+c+' '+t.slice(0,200));}
        const tb=teamBubble();if(!tb||/undefined/.test(tb))bad.push('tb '+sb.id+c);}catch(e){bad.push(sb.id+c+' THROW '+e.message)}}}
      SS=null;return {n,bad:bad.slice(0,8)};}""")
    ck(sc['bad']==[],'Zea realm scenes (all realms, all chapters): %d scenes OK %s'%(sc['n'],sc['bad']))
    bt=pg.evaluate("""()=>{const r={};save.hero='zea';for(const s of ['add','sub','mult','div','frac','mix']){makeSS(s,s==='mult'?13:1);const it=JSON.stringify(sIntroScene().lines.map(l=>l.text));r[s]=[HSUB[s].zea.some(x=>it.includes(JSON.stringify(x).slice(1,-1))),SS.team,teamBubble()];}
      const z={};for(const h of ['melrose','cayden']){save.hero=h;for(const s of ['add','sub','mult','div','frac','mix']){for(let c=1;c<=8;c++){const cc=s==='mult'?12+c:c;makeSS(s,cc);if(SS.team==='zea'){z[h+s]=teamBubble();break;}}}}save.hero='zea';SS=null;return {r,z};}""")
    ck(all(v[0] for v in bt['r'].values()),'Zea intro line appears in every realm (add, sub, mult, div, frac, mix)')
    ck(all('cousin' in v[2] or 'Zea' in v[2] or len(v[2])>30 for v in bt['r'].values()),'teammates banter with Zea in every realm')
    ck(len(bt['z'])==12 and all('Zea' in v for v in bt['z'].values()),'Zea banters as a teammate for Melrose & Cayden in all 6 realms (%d)'%len(bt['z']))
    lm=bt['z'].get('melrosemult','')+bt['z'].get('caydenmult','')
    ck(pg.evaluate("TEAM_SUB.mult.zea.some(t=>/tens.*ones|Big numbers/i.test(t))"),'long-multiplication flavour in Zea mult banter')
    # ---------- Grand Final ----------
    for h in ['zea','emi','cayden']:
        pg.evaluate(f"save.hero='{h}';makeSS('mix',7)"); ex=pg.evaluate("sExtras(true)"); team=set(ex+[pg.evaluate("save.hero"),pg.evaluate("sibId()")])
        ck(len(ex)==5 and len(team)==7 and 'zea' in team,f'Grand Final as {h}: all 7 heroes incl. Zea')
    pg.evaluate("save.hero='zea';persist()")
    for wd in (320,1440):
        pg.set_viewport_size({'width':wd,'height':800}); pg.evaluate("SS=null;SC=null;openChapter('mix',7)"); pg.wait_for_timeout(300)
        r=pg.evaluate("(()=>{const c=[...document.querySelectorAll('.castm')];return {n:c.length,ok:c.every(e=>{const b=e.getBoundingClientRect();return b.left>=-1&&b.right<=innerWidth+1&&b.width>8})}})()")
        ck(r['n']>=7 and r['ok'] and noov(pg,wd),'Grand Final cast at %dpx: %s fits'%(wd,r))
        drain(pg)
    pg.set_viewport_size({'width':390,'height':844})
    # ---------- Heroes Hall + hero page ----------
    pg.evaluate("SS=null;S=null;titleScreen()"); pg.click('[data-tile=heroes]'); pg.wait_for_timeout(300)
    ck(pg.locator('[data-hall]').count()==8 and pg.locator('[data-hall=zea]').count()==1,'Heroes Hall: 7 heroes + Muddle Monster')
    pg.set_viewport_size({'width':1100,'height':1000}); pg.wait_for_timeout(200); hh=pg.evaluate("document.documentElement.scrollHeight"); pg.set_viewport_size({'width':1100,'height':hh}); pg.wait_for_timeout(300); pg.screenshot(path=D+'/v14-heroes-hall.png')
    ck(noov(pg,1100),'Heroes Hall 1100px no overflow')
    pg.set_viewport_size({'width':390,'height':844})
    pg.click('[data-hall=zea]'); pg.wait_for_timeout(300); t=pg.inner_text('#app')
    ck('Age 7' in t and 'Age 6' not in t and 'Violet' in t and 'Golden sparkle' in t and 'Lime' not in t and pg.locator('.power').count()==3 and pg.locator('.stat').count()==4 and pg.locator('.more').count()==1 and pg.locator('#playAs').count()==1 and 'Catchphrase' in t and 'Best team combo' in t and 'Favorite realm' in t,'Zea page: age, colours, 3 powers, 4 stats, read more, combo, fav realm, Play as')
    ck('Critter Flip Star' in t and 'Stick the landing' in t and 'Critter Count' in t and 'Balance Beam' in t and 'Runway Patterns' in t and 'glasses' not in t and 'cousin' in t.lower(),'Zea page: nickname, catchphrase, powers, no glasses, cousin')
    ck(not SIBW.search(t),'Zea page has no sibling words')
    pg.set_viewport_size({'width':768,'height':1100}); pg.wait_for_timeout(200); hh=pg.evaluate("document.documentElement.scrollHeight"); pg.set_viewport_size({'width':768,'height':hh}); pg.wait_for_timeout(300); pg.screenshot(path=D+'/v14-zea-hero-page.png'); ck(noov(pg,768),'Zea page 768px no overflow')
    for wd in (320,1440):
        pg.set_viewport_size({'width':wd,'height':900}); pg.wait_for_timeout(120); ck(noov(pg,wd),'Zea page %dpx no overflow'%wd)
    pg.set_viewport_size({'width':390,'height':844})
    CR="""(sel)=>{const e=document.querySelector(sel);if(!e)return 99;const p=c=>{const a=c.match(/[\\d.]+/g).map(Number);if(c.startsWith('color(')){const o=[a[0]*255,a[1]*255,a[2]*255];if(a.length>3)o.push(a[3]);return o;}return a;};const L=([r,g,b])=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(r)+.7152*f(g)+.0722*f(b)};
     const fg=p(getComputedStyle(e).color);let n=e,bg=null;while(n){if(n.classList&&n.classList.contains('hphero')){const t=document.createElement('i');t.style.cssText='background-color:color-mix(in srgb,var(--c1) 25%,#fff);position:absolute';n.appendChild(t);bg=p(getComputedStyle(t).backgroundColor);t.remove();break;}const c=getComputedStyle(n).backgroundColor;const a=p(c);if(a.length<4||a[3]>0.9){bg=a;break;}n=n.parentElement;}bg=bg||[255,255,255];const a=L(fg),b=L(bg);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);}"""
    for sel in ['.hpname','.hptitle','.hpnick','.hpers','.power p','.pmath','.chips span','.stat span']:
        r=pg.evaluate(CR,sel); ck(r>=4.5,f'contrast zea {sel} {r:.1f}:1')
    pg.click('#playAs'); pg.wait_for_timeout(400); ck(pg.evaluate("save.hero")=='zea','Play as Zea')
    # picker card title contrast
    pg.evaluate("go('pick')"); pg.wait_for_timeout(200)
    r=pg.evaluate("""(()=>{const e=document.querySelector('.herocard.zea .ht');const L=c=>{const a=c.match(/[\\d.]+/g).map(Number).slice(0,3).map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*a[0]+.7152*a[1]+.0722*a[2]};const f=L(getComputedStyle(e).color);return Math.min(...[[237,233,254],[221,214,254]].map(c=>{const b=L('rgb('+c.join(',')+')');return (Math.max(f,b)+.05)/(Math.min(f,b)+.05)}));})()""")
    ck(r>=4.5,'Zea tile title contrast on lavender card %.1f:1'%r)
    # ---------- rewards / closet / profile / progress ----------
    pg.evaluate("TTQ.save.profiles.zea.rewards=REWARDS.zea.map(r=>r.id);persist();closetScreen()"); pg.wait_for_timeout(300)
    ck(pg.locator('#app').inner_text().count('Gym Bag')>=1,'Gym Bag closet opens')
    eqs=pg.evaluate("""()=>{const base=heroSVGeq('zea',{},'');return REWARDS.zea.map(r=>{const s=heroSVGeq('zea',{[r.slot]:r.id},'');return [r.id,s!==base&&!/undefined|NaN/.test(s)];});}""")
    ck(all(x for _,x in eqs),'every Gym Bag item changes Zea\'s SVG: %s'%[i for i,x in eqs if not x])
    lime=pg.evaluate("""()=>{const L=/#(84cc16|a3e635|65a30d|4d7c0f|bef264|d9f99d|ecfccb|f7fee7|365314)/i;const all=REWARDS.zea.map(r=>heroSVGeq('zea',{[r.slot]:r.id},'')).join('')+heroSVGeq('zea',{},'');const css=[...document.styleSheets].flatMap(x=>{try{return [...x.cssRules]}catch(e){return []}}).map(r=>r.cssText).filter(t=>/zea/.test(t)).join('');return L.test(all)||L.test(css)||L.test(JSON.stringify(HPLACES.zea||''))||/lime/i.test(JSON.stringify(REWARDS.zea))}""")
    ck(not lime,'Zea uses NumiRealm palette (no lime accents in SVG/CSS/places/rewards)')
    top=pg.evaluate("""()=>{const d=document.createElement('div');d.innerHTML=heroSVGeq('zea',{},'');document.body.appendChild(d);const sv=d.querySelector('svg');sv.style.width='210px';sv.style.height='270px';const T=sv.getBoundingClientRect().top;const r=[...sv.querySelectorAll('circle,path,ellipse,rect')].filter(e=>!e.closest('defs')).map(e=>e.getBoundingClientRect().top-T).reduce((m,y)=>Math.min(m,y),999);d.remove();return r}""")
    ck(top>=0,'Zea ponytail stays inside the frame (top y=%.1f)'%top)
    pg.evaluate("TTQ.save.profiles.zea.eq={pet:'webby',head:'scrunchie',hand:'ribbon'};persist()")
    pg.evaluate("go('trophies')"); pg.wait_for_timeout(300); ck(pg.locator('#items .troph').count()==12,'Trophy Room shows 12 Zea items')
    pg.evaluate("go('profile')"); pg.wait_for_timeout(300); ck(pg.locator('[data-pcard]').count()==7 and pg.locator('[data-pcard=zea]').count()==1 and 'Zea' in pg.inner_text('[data-pcard=zea]'),'Profile: 7 cards incl. Zea')
    pg.click('[data-editabout=zea]'); pg.wait_for_timeout(300); ck(pg.evaluate("save.hero")=='zea' and 'About' in pg.inner_text('#app'),'Edit About Me for Zea')
    pg.evaluate("go('progress')"); pg.wait_for_timeout(300); t=pg.inner_text('#app'); ck('Zea' in t or pg.locator('#app .card').count()>=2,'Progress screen for Zea renders')
    # closeup
    pg.set_viewport_size({'width':600,'height':780}); pg.evaluate("show('<div style=\"display:flex;justify-content:center;gap:10px;background:linear-gradient(160deg,#1E3A8A,#0A1F44);border:2px solid rgba(0,194,255,.55);box-shadow:0 0 28px rgba(139,92,246,.6);border-radius:24px;padding:16px\" id=zc>'+heroSVGeq('zea',{},'idle')+'</div>')"); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('#zc svg').style.width='420px';document.querySelector('#zc svg').style.height='540px'"); pg.wait_for_timeout(200); pg.locator('#zc').screenshot(path=D+'/v14-zea-closeup.png')
    pg.set_viewport_size({'width':390,'height':844})
    # ---------- effects ----------
    pg.evaluate("subjectScreen()"); pg.wait_for_timeout(200)
    pg.evaluate("show('<div id=fx><div class=x>'+heroSVG('zea')+'</div></div>');heroRight('#fx .x')"); pg.wait_for_timeout(150)
    ck(pg.locator('.critterfx').count()==1 and 'flip' in pg.get_attribute('#fx svg.hero','class'),'right answer: flip animation + critter burst')
    # ---------- hint safety as Zea ----------
    NUMS=lambda s: set(int(x) for x in re.findall(r'(?<![\d.])\d+(?![\d.])',s))
    leaks=[];used=0
    for sid,cc in (('add',3),('div',3),('frac',2),('mult',14),('mix',2)):
        pg.evaluate(f"SS=null;SC=null;openChapter('{sid}',{cc})"); pg.wait_for_timeout(150); drain(pg); pg.evaluate("sPracticeStart()"); pg.wait_for_timeout(300)
        for qn in range(3):
            if pg.locator('#hintBtn').count()==0 or not pg.is_enabled('#hintBtn'): break
            pg.click('#hintBtn'); pg.wait_for_timeout(100); used+=1
            if pg.is_enabled('#hintBtn'): pg.click('#hintBtn'); pg.wait_for_timeout(100); used+=1
            a=pg.evaluate("String(SS.cur.ans)"); ht=pg.inner_text('#hintbox'); qn_nums=NUMS(pg.evaluate("String(SS.cur.text||'').replace(/<[^>]+>/g,' ')"))
            if a.isdigit() and int(a) in NUMS(ht) and int(a) not in qn_nums: leaks.append((sid,a,ht[:100]))
            pg.evaluate("SS.onAnswer&&SS.onAnswer(true)"); pg.wait_for_timeout(1300)
    ck(used>=3 and not leaks,'hints as Zea never give the answer (%d lanterns, leaks %s)'%(used,leaks[:2]))
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")>=0,'lantern limits still enforced')
    # ---------- generator: every chapter, every stage, as Zea ----------
    g=pg.evaluate("""()=>{const bad=[];let n=0;save.hero='zea';const chs=[];for(const sb of SUBJ){if(sb.id==='mult'){MLX.forEach((c,i)=>chs.push([sb,c,13+i]));continue;}sb.ch.forEach((c,i)=>chs.push([sb,c,i+1]));}
      for(const [sb,ch,ci] of chs){makeSS(sb.id,ci);for(const k of ['p','a','b'])for(let r=0;r<20;r++){n++;let q;try{q=ch.gen(k);}catch(e){bad.push(sb.id+ci+k+' THROW '+e.message);continue;}
       const t=(q.text||'')+(q.vis||'')+(q.explain||'')+(q.hint||'')+(q.lead||'');if(/undefined|NaN|\\[object/.test(t))bad.push(sb.id+ci+' '+t.slice(0,120));
       if(q.input==='mc'){if(!(q.opts&&q.opts.length>=2&&q.check(q.ans)))bad.push('mc '+sb.id+ci);}else if(q.input!=='ld'&&q.input!=='lm'&&q.input!=='wop'&&!q.check(q.ans))bad.push('check '+sb.id+ci);}}
      SS=null;return {n,bad:bad.slice(0,8),nb:bad.length};}""")
    ck(g['nb']==0,'generator as Zea: %d questions, %d bad %s'%(g['n'],g['nb'],g['bad']))
    # ---------- v13 save migrates intact ----------
    load(pg,V13SEED)
    sv=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))") if pg.evaluate("!!localStorage.getItem('ttq-save-v2')") else {}
    live=pg.evaluate("JSON.parse(JSON.stringify(TTQ.save))")
    for src in (live,):
        ck(src['profiles']['emi']['stars']==T12 and src['profiles']['emi']['subj']['mult']['stars']=={"13":3,"14":2,"15":3} and src['profiles']['emi']['subj']['mix']['stars']=={"1":3,"2":2,"3":3} and src['profiles']['emi']['subj']['add']['stars']=={"10":3,"11":2},'v13 save: Emi stars unchanged (castle, wing, tower, meadow)')
        ck(src['profiles']['emi']['rewards']==["fcrown"] and src['profiles']['emi']['eq']=={"head":"fcrown"} and src['profiles']['emi']['age']==AR(8) and src['profiles']['emi']['hintTotal']==3,'v13 save: Emi rewards/eq/age/hints unchanged')
        ck(src['profiles']['cayden']['stars']=={"1":3,"2":2} and src['profiles']['cayden']['subj']['div']['stars']=={"1":3,"12":2} and src['profiles']['cayden']['rewards']==["bball"],'v13 save: Cayden unchanged')
        ck(src.get('chv')==13 and src['hero']=='emi','v13 save: no re-migration (chv 13), hero kept')
        z=src['profiles'].get('zea',{}); ck(z.get('rewards')==[] and z.get('stars')=={} and z.get('name')=='Zea','Zea gets a fresh empty profile')
    pg.wait_for_selector('.herocard,.stile,#app',timeout=3000); ck(pg.evaluate("document.querySelector('#app').innerHTML.length")>100,'v13 save boots')
    # ---------- layout of Zea screens ----------
    load(pg,ZSAVE)
    for wd in (320,360,768,1440):
        pg.set_viewport_size({'width':wd,'height':900}); bad=[]
        for name,js in [('subjects',"subjectScreen()"),('castle',"mapScreen()"),('closet',"closetScreen()"),('hall',"go('heroes')"),('page',"go('hero','zea')"),('profile',"go('profile')"),('trophies',"go('trophies')"),('progress',"go('progress')"),('pick',"go('pick')"),('learn',"SS=null;makeSS('add',1);sLearn()"),('practice',"SS=null;SC=null;makeSS('mult',14);sLearn();sPracticeStart()")]:
            try: pg.evaluate(js)
            except Exception as e: bad.append(name+' '+str(e)[:60]); continue
            pg.wait_for_timeout(200)
            if not noov(pg,wd): bad.append(name)
        ck(not bad,'layout %dpx Zea screens: no overflow %s'%(wd,bad))
    ck(len(errs)==0,'no console errors: %s'%errs[:5])
    b.close()
print('RESULT','ALL PASS' if not fails else 'FAIL %d'%len(fails))
sys.exit(1 if fails else 0)
