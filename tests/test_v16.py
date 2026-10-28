# v16: centered 3-up hero carousel on Home and on "Who is playing?"
import json,threading,http.server,functools,os
from playwright.sync_api import sync_playwright
os.environ.setdefault('GST_PLUGIN_PATH','/workspace/wkdeps/root/usr/lib/x86_64-linux-gnu/gstreamer-1.0')
D='/workspace/times-tables-quest'
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8798),functools.partial(http.server.SimpleHTTPRequestHandler,directory=D))
srv.RequestHandlerClass.log_message=lambda *a:None
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8798/index.html'
IDS=['sage','emi','blu','eshon','melrose','cayden','zea']
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
SAVE={"muted":True,"narrator":False,"lastHero":"emi","profiles":{"emi":{"name":"Emi","stars":{"2":3,"5":2},"hist":{"2x3":[1,1]},"rewards":["fcrown"],"eq":{},"prologue":True,"age":6,"grade":"1"}}}
def ctx(b,w,h,save=SAVE,touch=False,rm=None):
    kw=dict(viewport={'width':w,'height':h},has_touch=touch)
    if rm: kw['reduced_motion']=rm
    c=b.new_context(**kw)
    if save is not None: c.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('ttq-save-v2',%s)}"%json.dumps(json.dumps(save)))
    c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"21"}'))
    pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));pg.goto(URL);pg.wait_for_selector('.hcar');pg.wait_for_timeout(500);return c,pg
cen=lambda pg:pg.evaluate("v16Center()")
def offs(pg): return pg.evaluate("Object.fromEntries([...document.querySelectorAll('.hslide')].map(s=>[s.dataset.slide,+s.dataset.off]))")
with sync_playwright() as p:
    b=p.chromium.launch()
    c,pg=ctx(b,1280,900)
    ck(pg.locator('#app .herocards .herocard').count()==7 and pg.locator('.hcar').count()==1 and pg.locator('#app .herocards:not(.hcar-track)').count()==0,'Home: 7 hero cards live inside one carousel (no grid left)')
    ck([e.get_attribute('data-hero') for e in pg.query_selector_all('.herocard')]==IDS,'hero order kept')
    ck(cen(pg)=='emi','opens on last-played hero (Emi)')
    o=offs(pg);ck(sorted(k for k,v in o.items() if abs(v)<=1)==['blu','emi','sage'] and o['sage']==-1 and o['blu']==1,'3 visible: Sage | Emi | Blú (%s)'%o)
    r=pg.evaluate("""(()=>{const g=k=>document.querySelector(`.hslide[data-slide=${k}]`).getBoundingClientRect(),w=document.querySelector('.hcar').getBoundingClientRect();const e=g('emi'),s=g('sage'),u=g('blu');
      const cs=x=>getComputedStyle(document.querySelector(`.hslide[data-slide=${x}]`));return {cx:(e.left+e.right)/2,wx:(w.left+w.right)/2,ew:e.width,sw:s.width,uw:u.width,eo:+cs('emi').opacity,so:+cs('sage').opacity,
      sh:getComputedStyle(document.querySelector('.hslide[data-slide=emi] .herocard')).boxShadow,ov:s.right<=e.left+2&&e.right<=u.left+2,hid:+cs('zea').opacity}})()""")
    ck(abs(r['cx']-r['wx'])<3,'focused card centered (%s)'%r)
    ck(r['ew']>r['sw']*1.15 and abs(r['sw']-r['uw'])<1 and r['so']<r['eo'] and r['hid']==0,'center larger & brighter, sides smaller & dimmer, others hidden')
    ck('rgb(139, 92, 246)' in r['sh'] or '139, 92, 246' in r['sh'],'center glow uses hero color (%s)'%r['sh'][:60])
    ck(r['ov'],'3 cards do not overlap')
    ck(pg.locator('.hcar-arr.prev').count()==1 and pg.locator('.hcar-arr.next').count()==1,'left/right arrows')
    dots=pg.query_selector_all('.hcar-dot');ck(len(dots)==7 and [d.get_attribute('data-dot') for d in dots]==IDS,'7 dots')
    ck(len(set(pg.evaluate("[...document.querySelectorAll('.hcar-dot')].map(d=>getComputedStyle(d,'::before').backgroundColor)")))==7,'dots color-coded per hero')
    ck(pg.get_attribute('.hcar','aria-roledescription')=='carousel' and pg.get_attribute('.hslide[data-slide=emi]','aria-label')=='Hero 2 of 7: Emi' and pg.get_attribute('.hslide[data-slide=emi]','aria-roledescription')=='slide','aria carousel roles and "Hero 2 of 7: Emi"')
    # navigation
    pg.click('.hcar-arr.next');pg.wait_for_timeout(500);ck(cen(pg)=='blu','next -> Blú')
    pg.click('.hcar-arr.next');pg.wait_for_timeout(500);ck(cen(pg)=='eshon','next twice -> Eshon')
    ck(pg.get_attribute('.hcar-dot[data-dot=eshon]','aria-current')=='true' and pg.locator('.hcar-dot[aria-current=true]').count()==1,'active dot follows')
    ck('Hero 4 of 7' in pg.inner_text('#hcarLive'),'live region announces')
    pg.click('.hcar-dot[data-dot=zea]');pg.wait_for_timeout(500);ck(cen(pg)=='zea','dot jumps to Zea')
    o=offs(pg);ck(o['sage']==1 and o['cayden']==-1,'wrap: Sage shown after Zea (%s)'%o)
    pg.click('.hcar-arr.next');pg.wait_for_timeout(500);ck(cen(pg)=='sage','after Zea comes Sage')
    pg.click('.hcar-arr.prev');pg.wait_for_timeout(500);ck(cen(pg)=='zea','prev from Sage -> Zea')
    # keyboard
    pg.focus('.hslide[data-off="0"] .herocard');pg.keyboard.press('ArrowRight');pg.wait_for_timeout(300);ck(cen(pg)=='sage','ArrowRight wraps to Sage')
    pg.keyboard.press('ArrowLeft');pg.keyboard.press('ArrowLeft');pg.wait_for_timeout(300);ck(cen(pg)=='cayden','ArrowLeft x2 -> Cayden')
    ck(pg.evaluate("document.activeElement.dataset.hero")=='cayden','focus stays on centered card')
    ck(pg.evaluate("[...document.querySelectorAll('.herocard')].filter(b=>b.tabIndex===0).map(b=>b.dataset.hero)")==['cayden'],'only centered card is tabbable')
    pg.keyboard.press('Home');pg.wait_for_timeout(300);ck(cen(pg)=='sage','Home key -> first hero')
    # mouse drag swipe
    bx=pg.query_selector('.hcar-vp').bounding_box();y=bx['y']+bx['height']/2;x=bx['x']+bx['width']/2
    pg.mouse.move(x+120,y);pg.mouse.down();pg.mouse.move(x,y,steps=5);pg.mouse.move(x-120,y,steps=5);pg.mouse.up();pg.wait_for_timeout(500)
    ck(cen(pg)=='emi','drag left -> next hero (Emi), no pick (%s)'%cen(pg)); ck(pg.locator('.hcar').count()==1,'drag did not select')
    # tap side card brings to center; tap center selects
    pg.wait_for_timeout(400);pg.click('.hslide[data-slide=blu] .herocard');pg.wait_for_timeout(500)
    ck(cen(pg)=='blu' and pg.locator('.hcar').count()==1,'tap side card -> centers it, no selection')
    ck(pg.evaluate("TTQ.save.hero||null") in (None,'emi') ,'side tap did not change hero')
    # uniform cards
    st=pg.evaluate("[...document.querySelectorAll('.herocard')].map(b=>[...b.children].map(x=>x.className).join(','))")
    ck(len(set(st))==1 and st[0]=='hsv,hn,ht,hl,hl','cards uniform: portrait, name, title, line, stars (%s)'%set(st))
    t=pg.inner_text('.herocards');ck('🎒' not in t and '🎂' not in t and pg.locator('.abmini').count()==0,'no age/grade chip on any card')
    ck('5' in pg.inner_text('[data-hero=emi] .hl:last-child') and 'stars' in pg.inner_text('[data-hero=emi] .hl:last-child'),'stars per hero kept')
    hs=pg.evaluate("[...document.querySelectorAll('.hcar .herocard')].map(b=>b.style.minHeight)");ck(len(set(hs))==1,'equal card heights')
    ck(pg.locator('#hallLink').count()==1 and 'Meet the heroes' in pg.inner_text('#hallLink'),'"Meet the heroes" button kept')
    pg.evaluate("heroPrompt()");pg.wait_for_timeout(300)
    ck('Pick your hero first, then press Play!' in pg.inner_text('#heroTip') and pg.is_visible('#heroTip'),'"Pick your hero first, then press Play!" tip kept')
    ck(pg.evaluate("document.activeElement.dataset.hero")==cen(pg),'heroPrompt focuses centered card')
    pg.screenshot(path='/workspace/v16tmp/t-desk.png')
    # select centered -> same pick flow
    pg.click('.hslide[data-off="0"] .herocard');pg.wait_for_selector('#nm');ck(pg.evaluate("TTQ.save.hero")=='blu' and pg.is_visible('text=Start the adventure'),'tap center selects Blú -> name/Start screen as before')
    sv=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))");e=sv['profiles']['emi']
    ck(e['stars']=={"2":3,"5":2} and e['rewards']==['fcrown'] and e['age']==6 and e['grade']=='1' and sv['lastHero']=='blu','saves intact (Emi stars/rewards/about kept)')
    # Who is playing picker
    pg.evaluate("heroPickScreen()");pg.wait_for_timeout(300)
    ck(pg.locator('#app .hcar').count()==1 and pg.locator('#app .herocard').count()==7 and pg.locator('#heroes.hcar').count()==1,'"Who is playing?" uses the carousel')
    ck(cen(pg)=='blu','picker opens on selected hero')
    st2=pg.evaluate("[...document.querySelectorAll('.herocard')].map(b=>[...b.children].map(x=>x.className).join(','))");ck(len(set(st2))==1 and st2[0]=='hsv,hn,ht,hl,hl','picker cards uniform')
    pg.click('.hcar-dot[data-dot=melrose]');pg.wait_for_timeout(400);pg.click('.hslide[data-off="0"] .herocard');pg.wait_for_timeout(300)
    ck(pg.evaluate("TTQ.save.hero")=='melrose','picker: dot + tap center picks Melrose')
    c.close()
    # fresh device default Sage + reduced motion
    c,pg=ctx(b,1280,900,save=None,rm='reduce');ck(cen(pg)=='sage','fresh device opens on Sage')
    ck(float(pg.evaluate("getComputedStyle(document.querySelector('.hslide')).transitionDuration").split(',')[0].strip().rstrip('s') or '0')<0.01,'reduced motion: no slide transition');c.close()
    c,pg=ctx(b,1280,900,save=dict(SAVE,calm=True));ck('rm' in pg.get_attribute('.hcar','class'),'calm mode -> reduced motion class');c.close()
    # phones
    for w,h in ((390,844),(430,932),(360,780),(320,640)):
        c,pg=ctx(b,w,h,touch=True)
        r=pg.evaluate("""(()=>{const g=k=>document.querySelector(`.hslide[data-off="${k}"]`).getBoundingClientRect();const a=g(0),l=g(-1),r=g(1);return {cx:(a.left+a.right)/2,cw:a.width,lp:Math.min(l.right,innerWidth)-Math.max(l.left,0),rp:Math.min(r.right,innerWidth)-Math.max(r.left,0),sw:document.documentElement.scrollWidth,fs:parseFloat(getComputedStyle(document.querySelector('.hslide[data-off="0"] .hn')).fontSize)}})()""")
        ck(abs(r['cx']-w/2)<3 and r['sw']<=w,'%dpx: focused card centered, no overflow (%s)'%(w,r))
        ck(r['cw']>=min(170,w*.55) and r['fs']>=20,'%dpx: card not cramped'%w)
        ck(r['lp']>8 and r['rp']>8,'%dpx: neighbours peek at both edges'%w)
        if w==390:
            pg.evaluate("document.querySelector('.hcar').scrollIntoView({block:'center'})");pg.wait_for_timeout(300)
            bx=pg.query_selector('.hcar-vp').bounding_box();y=bx['y']+bx['height']/2;x=bx['x']+bx['width']/2
            cdp=c.new_cdp_session(pg)
            def sw(dx):
                cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
                for k in range(1,6): cdp.send('Input.dispatchTouchEvent',{'type':'touchMove','touchPoints':[{'x':x+dx*k/5,'y':y}]})
                cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});pg.wait_for_timeout(600)
            sw(-150);ck(cen(pg)=='blu','phone swipe left -> next (Blú)')
            sw(150);sw(150);ck(cen(pg)=='sage','phone swipe right x2 -> Sage')
            sw(150);ck(cen(pg)=='zea','phone swipe wraps to Zea')
            def tap(sel):
                bb=pg.query_selector(sel).bounding_box();cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':min(max(bb['x']+bb['width']/2,25),w-25),'y':bb['y']+bb['height']/2}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});pg.wait_for_timeout(800)
            pg.wait_for_timeout(900);tap('.hslide[data-off="1"] .herocard');ck(cen(pg)=='sage' and pg.locator('.hcar').count()==1,'phone tap on peeking card centers it, no selection')
            tap('.hslide[data-off="-1"] .herocard');ck(cen(pg)=='zea','phone tap left neighbour -> Zea')
            pg.wait_for_timeout(300);bb=pg.query_selector('.hslide[data-off="0"] .herocard').bounding_box();cdp.send('Input.dispatchTouchEvent',{'type':'touchStart','touchPoints':[{'x':bb['x']+bb['width']/2,'y':bb['y']+bb['height']/2}]});cdp.send('Input.dispatchTouchEvent',{'type':'touchEnd','touchPoints':[]});pg.wait_for_timeout(800);ck(pg.locator('#nm').count()==1 and pg.evaluate("TTQ.save.hero")=='zea','phone tap center selects Zea')
        c.close()
    b.close()
    # WebKit (iPhone engine) smoke
    try:
        wb=p.webkit.launch();c,pg=ctx(wb,390,844,touch=True)
        pg.click('.hcar-arr.next');pg.wait_for_timeout(600);ck(cen(pg)=='blu','WebKit: next works')
        pg.tap('.hslide[data-off="0"] .herocard');pg.wait_for_timeout(500);ck(pg.locator('#nm').count()==1,'WebKit: tap center selects');wb.close()
    except Exception as ex: ck(False,'WebKit run: %s'%ex)
ck(errs==[],'no page errors %s'%errs[:3])
print('FAILS',len(fails));raise SystemExit(1 if fails else 0)
