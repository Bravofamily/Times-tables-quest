# v12: new screens at 320/360/768/1440 - no horizontal overflow, >=44px tap targets, no console errors; reduced motion stops hero animations.
import os
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.abspath(__file__)); URL='file://'+os.path.join(D,'index.html'); errs=[]; fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m, flush=True); fails.append(m) if not c else None
import importlib.util,re
src=open(os.path.join(D,'test_v12_screens.py')).read(); SEED=eval(re.search(r"SEED=(\{.*?\}\}\})\n",src,re.S).group(1).replace('True','True').replace('None','None'))
OVF="""(()=>{const W=innerWidth,bad=[];const de=document.documentElement;if(de.scrollWidth>W+1)bad.push('doc '+de.scrollWidth);
for(const e of document.querySelectorAll('#app *, #top *, #bnav *')){const r=e.getBoundingClientRect();if(!r.width||!r.height)continue;
 let p=e.parentElement,clip=false;while(p&&p!==document.body){const s=getComputedStyle(p);if(/auto|scroll|hidden|clip/.test(s.overflowX)){clip=true;break;}p=p.parentElement;}
 if(clip)continue;if(r.right>W+1||r.left<-1)bad.push((e.id||e.className||e.tagName).toString().slice(0,30)+' '+Math.round(r.left)+'..'+Math.round(r.right));}
return bad.slice(0,6);})()"""
TAP="""(()=>{const bad=[];for(const e of document.querySelectorAll('#top button, #bnav button, #app button, #app select, #app summary')){const r=e.getBoundingClientRect();if(!r.width)continue;
 if(getComputedStyle(e).visibility==='hidden'||e.closest('.hidden'))continue;if(e.classList.contains('mini'))continue;if(r.height<44-0.5||r.width<44-0.5)bad.push((e.id||e.className||e.tagName).toString().slice(0,24)+' '+Math.round(r.width)+'x'+Math.round(r.height));}return bad.slice(0,6);})()"""
SCREENS=[('home',"titleScreen()"),('realms',"titleScreen();go('realms')"),('chapter-div',"go('chapter','div',3)"),('chapter-frac',"go('chapter','frac',6)"),('chapter-mult',"go('chapter','mult',4)"),
 ('training',"titleScreen();go('training')"),('training-mult',"go('training',null,'mult')"),('drill',"drillStart([{sid:'div',c:8}],false)"),('drill-frac',"drillStart([{sid:'frac',c:3}],false)"),('drilldone',"DR.over=true;drillDone()"),
 ('trophies',"titleScreen();go('trophies')"),('guide',"titleScreen();go('guide')"),('profile',"titleScreen();go('profile')"),('heroes',"titleScreen();go('heroes')"),
 ('hero-emi',"go('hero','emi')"),('hero-blu',"go('hero','blu')"),('hero-sage',"go('hero','sage')"),('hero-eshon',"go('hero','eshon')"),('hero-melrose',"go('hero','melrose')"),('hero-cayden',"go('hero','cayden')"),('villain',"go('villain')"),
 ('settings',"titleScreen();go('settings')"),('reset-confirm',"resetAsk('cayden')"),('progress',"titleScreen();go('progress')"),('pick',"titleScreen();save.lastHero=null;go('pick')")]
with sync_playwright() as p:
    b=p.chromium.launch()
    for (w,h,mob) in [(320,640,True),(360,780,True),(768,1024,True),(1440,900,False)]:
        c=b.new_context(viewport={'width':w,'height':h},is_mobile=mob,has_touch=mob); pg=c.new_page(); tag=f'{w}x{h}'
        pg.on('console',lambda m,t=tag: errs.append(f'[{t}] {m.text}') if m.type=='error' else None); pg.on('pageerror',lambda e,t=tag: errs.append(f'[{t}] {e}'))
        pg.goto(URL); pg.evaluate("s=>localStorage.setItem('ttq-save-v2',JSON.stringify(s))",SEED); pg.reload(); pg.wait_for_timeout(400)
        ob=[];tb=[]
        for nm,js in SCREENS:
            pg.evaluate(js); pg.wait_for_timeout(300)
            o=pg.evaluate(OVF); t=pg.evaluate(TAP)
            if o: ob.append(f'{nm}: {o}')
            if t: tb.append(f'{nm}: {t}')
        ck(not ob,f'{tag}: no overflow on {len(SCREENS)} v12 screens {ob[:3]}')
        ck(not tb,f'{tag}: all buttons >=44px {tb[:3]}')
        pg.evaluate("titleScreen()"); vis=pg.evaluate("[...document.querySelectorAll('#app .tiles .tile')].filter(e=>e.getBoundingClientRect().width>0).length")
        ck(vis==6,f'{tag}: 6 home tiles visible (incl. Heroes)')
        if w>=900:
            ck(pg.is_visible('#navHeroes'),f'{tag}: Heroes in the top nav')
            pg.click('#navHeroes'); pg.wait_for_timeout(200); ck(pg.evaluate("TTQ_V12.CUR.n")=='heroes','top nav Heroes opens Heroes Hall')
            pg.click('#navLevels'); pg.wait_for_timeout(200); ck(pg.evaluate("TTQ_V12.CUR.n")=='realms','top nav Levels opens the Realm Map')
            pg.click('#navPractice'); pg.wait_for_timeout(200); ck(pg.evaluate("TTQ_V12.CUR.n")=='training','top nav Practice opens Training Grounds')
            pg.click('#navProfile'); pg.wait_for_timeout(200); ck(pg.evaluate("TTQ_V12.CUR.n")=='profile','top nav Profile opens hero profiles')
            nb=pg.evaluate("(()=>{const r=[...document.querySelectorAll('#top > *')].filter(e=>e.getBoundingClientRect().width>0).map(e=>e.getBoundingClientRect());let o=0;for(let i=1;i<r.length;i++)if(r[i].left<r[i-1].right-1&&Math.abs(r[i].top-r[i-1].top)<10)o++;return o;})()")
            ck(nb==0,f'{tag}: top bar items do not overlap')
        else:
            ck(pg.is_visible('#bnHeroes') or w>=900,f'{tag}: Heroes in the bottom nav')
        c.close()
    # keyboard: Tab to a stepping stone and open it with Enter
    c=b.new_context(viewport={'width':1440,'height':900}); pg=c.new_page(); pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate("s=>localStorage.setItem('ttq-save-v2',JSON.stringify(s))",SEED); pg.reload(); pg.wait_for_timeout(300)
    pg.evaluate("go('realms')"); pg.evaluate("document.querySelector('[data-stone=\"add-1\"]').focus()"); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    ck(pg.evaluate("TTQ_V12.CUR.n")=='chapter','keyboard: Enter on a stepping stone opens chapter detail')
    ring=pg.evaluate("(()=>{document.getElementById('playCh').focus();const s=getComputedStyle(document.activeElement);return s.outlineStyle!=='none'&&parseFloat(s.outlineWidth)>=2})()")
    ck(ring,'focus ring visible on new buttons')
    pg.evaluate("save.calm=true;persist();go('hero','cayden')"); pg.wait_for_timeout(200)
    an=pg.evaluate("getComputedStyle(document.querySelector('.hpsvg')).animationName"); ck(an=='none' and not pg.is_visible('.spark'),'reduced motion: hero page entrance/sparkles off (%s)'%an)
    pg.evaluate("save.calm=false;persist();go('heroes')"); pg.wait_for_timeout(100)
    ck(pg.evaluate("getComputedStyle(document.querySelector('.hallcard')).animationName")!='none','animations on when motion allowed')
    # contrast spot-check of key text on new screens
    CR="""(sel)=>{const e=document.querySelector(sel);const p=c=>{const a=c.match(/[\\d.]+/g).map(Number);if(c.startsWith('color(')){const o=[a[0]*255,a[1]*255,a[2]*255];if(a.length>3)o.push(a[3]);return o;}return a;};const L=([r,g,b])=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(r)+.7152*f(g)+.0722*f(b)};
     const fg=p(getComputedStyle(e).color);let n=e,bg=null;while(n){if(n.classList&&n.classList.contains('hphero')){const t=document.createElement('i');t.style.cssText='background-color:color-mix(in srgb,var(--c1) 25%,#fff);position:absolute';n.appendChild(t);bg=p(getComputedStyle(t).backgroundColor);t.remove();break;}const c=getComputedStyle(n).backgroundColor;const a=p(c);if(a.length<4||a[3]>0.9){bg=a;break;}n=n.parentElement;}bg=bg||[255,255,255];const a=L(fg),b=L(bg);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);}"""
    for hid in ['emi','blu','sage','eshon','melrose','cayden','zea']:
        pg.evaluate(f"go('hero','{hid}')"); pg.wait_for_timeout(50)
        for sel in ['.hpname','.hptitle','.hpnick','.hpers','.power p','.pmath','.chips span','.stat span']:
            if pg.evaluate(f"!!document.querySelector('{sel}')"):
                r=pg.evaluate(CR,sel); ck(r>=4.5,f'contrast {hid} {sel} {r:.1f}:1')
    pg.evaluate("go('realms')")
    for sel in ['.rline','.rmeta span','.stone.locked .sn','.stone.current .sn','.stone.done .sn','.sedge']:
        r=pg.evaluate(CR,sel); ck(r>=4.5,f'contrast {sel} {r:.1f}:1')
    pg.evaluate("go('training')")
    for sel in ['.drill small','.dtag','.mpill.on','.rtab.on']:
        r=pg.evaluate(CR,sel); ck(r>=4.5,f'contrast {sel} {r:.1f}:1')
    b.close()
ck(not errs,'no console errors '+str(errs[:5]))
print('RESULT', 'FAIL %d'%len(fails) if fails else 'ALL PASS')
