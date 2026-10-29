# v22 privacy update: self-hosted fonts (no third-party requests), age ranges + migration, old NR1 code import,
# name tip, Privacy page, footer, two-step "Reset all data on this device", progress-code note.
# Usage: PWB=chromium|webkit python test_v22.py   (screenshots go to /workspace/v22shots when SHOTS=1)
import os,json,re,threading,http.server,functools,urllib.parse
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))));BR=os.environ.get('PWB','chromium');SH=os.environ.get('SHOTS')=='1'
OUT='/workspace/v22shots';os.makedirs(OUT,exist_ok=True)
PORT=8832 if BR=='chromium' else 8833
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
H=functools.partial(Q,directory=D)
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),H);threading.Thread(target=srv.serve_forever,daemon=True).start()
BASE=f'http://127.0.0.1:{PORT}/';ORIG=f'127.0.0.1:{PORT}'
V21='file:///workspace/index-v21.html'
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c: fails.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
ck("const APP_VERSION='22'" in html,'APP_VERSION is 22')
ck(json.load(open(os.path.join(D,'version.json')))['version']=='22','version.json is 22')
sw=open(os.path.join(D,'sw.js')).read()
FONTS=['baloo2-latin-600-800.woff2','poppins-latin-400.woff2','poppins-latin-500.woff2','poppins-latin-600.woff2','poppins-latin-700.woff2']
ck(all(("'./fonts/"+f+"'") in sw for f in FONTS) and "'numirealm-v'+V" in sw,'sw.js precaches all 5 fonts, versioned cache')
ck(all(os.path.getsize(os.path.join(D,'fonts',f))>5000 for f in FONTS),'all 5 woff2 files ship in fonts/')
ck(all(os.path.exists(os.path.join(D,'fonts',f)) for f in ['OFL-Baloo2.txt','OFL-Poppins.txt']),'OFL license texts ship in fonts/')
ext=sorted(set(re.findall(r'https?://[A-Za-z0-9.-]+',html))-{'http://www.w3.org'})
ck(ext==[],'no third-party URLs in index.html (found %s)'%ext)
ck('googleapis' not in html and 'gstatic' not in html,'no Google Fonts references')
ck(html.count('@font-face')==5,'5 @font-face rules')
def prof(name,age,grade,stars):
    return {"name":name,"stars":stars,"hist":{},"rewards":["fcrown"],"eq":{},"prologue":True,"age":age,"grade":grade,"subj":{"add":{"stars":{"1":3,"2":2},"hist":{},"intro":True}}}
OLD={"muted":True,"narrator":False,"lastHero":"emi","profiles":{"emi":prof("Emi",6,"1",{"2":3,"5":2}),"melrose":prof("Melrose",8,"3",{"1":3}),
 "cayden":prof("Cayden",10,"5",{"1":3,"2":3}),"blu":prof("Bl\u00fa",1,"none",{}),"sage":prof("Sage","7","2",{"1":1}),"eshon":prof("Eshon",13,"6",{"3":2})}}
WANT={"emi":"6-7","melrose":"8-10","cayden":"8-10","blu":"4-5","sage":"6-7","eshon":"11-14"}
def attach(pg,tag):
    pg.on('console',lambda m: errs.append(f'[{tag}] {m.text}') if m.type=='error' and 'ERR_INTERNET_DISCONNECTED' not in m.text else None)
    pg.on('pageerror',lambda e: errs.append(f'[{tag}] PAGEERR {e}'))
def sv(pg,k='ttq-save-v2'): return pg.evaluate(f"JSON.parse(localStorage.getItem('{k}')||'null')")
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    reqs=[]
    def ctx(w=1280,h=900,seed=None,raw=None,mobile=False):
        kw=dict(viewport={'width':w,'height':h})
        if mobile: kw.update(is_mobile=True,has_touch=True,device_scale_factor=2) if BR=='chromium' else kw.update(has_touch=True)
        c=b.new_context(**kw)
        init={}
        if seed is not None: init['ttq-save-v2']=json.dumps(seed)
        if raw: init.update(raw)
        if init: c.add_init_script("if(!sessionStorage.getItem('seeded')){sessionStorage.setItem('seeded','1');const o=%s;for(const k in o)localStorage.setItem(k,o[k]);}"%json.dumps(init))
        c.on('request',lambda r: reqs.append(r.url))
        return c
    def open_(c,url=BASE+'index.html',tag='p'):
        pg=c.new_page();attach(pg,tag);pg.goto(url);pg.wait_for_timeout(1200);return pg
    # ---- 1. no request leaves the origin; fonts load from /fonts/ ----
    c=ctx(seed=OLD);pg=open_(c,tag='net')
    pg.evaluate("go('settings')");pg.wait_for_timeout(300);pg.evaluate("go('privacy')");pg.wait_for_timeout(300);pg.evaluate("titleScreen()");pg.wait_for_timeout(800)
    fs=pg.evaluate("document.fonts.ready.then(()=>[...document.fonts].filter(f=>/Baloo 2|Poppins/.test(f.family)).map(f=>f.family+' '+f.weight+' '+f.status))")
    ck(any('Baloo 2' in f and 'loaded' in f for f in fs) and any('Poppins' in f and 'loaded' in f for f in fs),'webfonts loaded from the game (document.fonts: %s)'%fs)
    ck(pg.evaluate("document.fonts.check('800 20px \"Baloo 2\"') && document.fonts.check('400 16px Poppins')"),'document.fonts.check Baloo 2 800 and Poppins 400')
    hosts=sorted({urllib.parse.urlparse(u).netloc for u in reqs if not u.startswith(('data:','blob:','about:'))})
    ck(hosts==[ORIG],'every request stays on the game origin (hosts: %s)'%hosts)
    fr=sorted({urllib.parse.urlparse(u).path for u in reqs if u.endswith('.woff2')})
    ck(len(fr)>=2 and all(x.startswith('/fonts/') for x in fr),'fonts fetched from /fonts/ (%s)'%fr)
    cn=pg.evaluate("caches.keys().then(async ks=>{const out={};for(const k of ks){const c=await caches.open(k);out[k]=(await c.keys()).map(r=>new URL(r.url).pathname);}return out;})")
    ck('numirealm-v22' in cn and sum(1 for x in cn.get('numirealm-v22',[]) if x.endswith('.woff2'))==5,'SW cache numirealm-v22 holds the 5 fonts (%s)'%cn)
    # ---- 2. migration of an old (v21) save: exact ages -> ranges, progress kept, persisted ----
    s=sv(pg);pr=s['profiles']
    ck({k:pr[k].get('age') for k in WANT}==WANT,'old exact ages migrated to ranges: %s'%{k:pr[k].get('age') for k in WANT})
    ck(all(pr[k]['stars']==OLD['profiles'][k]['stars'] and pr[k]['grade']==OLD['profiles'][k]['grade'] and pr[k]['rewards']==['fcrown'] and pr[k]['subj']['add']['stars']=={"1":3,"2":2} for k in WANT),'stars, grades, rewards and realm progress kept after migration')
    ck(pr['blu']['name']=='Bl\u00fa','Bl\u00fa spelled as written')
    bk=sv(pg,'ttq-save-v2-backup')
    ck(bk is None or all(not isinstance(v.get('age'),int) for v in bk['profiles'].values()),'backup has no exact ages after the next save')
    ck(not re.search(r'"age":\s*\d',json.dumps(s)),'no numeric age anywhere in the stored save')
    c.close()
    # ---- 3. corrupt main save -> recovered from an old backup, ages migrated ----
    c=ctx(raw={'ttq-save-v2':'{broken','ttq-save-v2-backup':json.dumps(OLD)});pg=open_(c,tag='corrupt')
    s=sv(pg);ck(s and s['profiles']['melrose']['age']=='8-10' and s['profiles']['melrose']['stars']=={"1":3},'corrupt main save: recovered from backup, age migrated')
    ck(pg.evaluate("localStorage.getItem('ttq-save-v2-corrupt')")=='{broken','corrupt copy kept in ttq-save-v2-corrupt')
    c.close()
    # ---- 4. old NR1 code from live v21 imports, ages converted ----
    code=None
    if BR=='chromium':
        c=ctx(seed=OLD);pg=c.new_page();pg.goto(V21);pg.wait_for_timeout(1200)
        ck(pg.evaluate("APP_VERSION")=='21','reference v21 build loaded')
        code=pg.evaluate("pcMake()");c.close()
        open('/workspace/v22tmp/v21code.txt','w').write(code)
    else:
        code=open('/workspace/v22tmp/v21code.txt').read()
    ck(code.startswith('NR1.'),'v21 progress code made (%d chars)'%len(code))
    c=ctx(seed={"muted":True,"narrator":False,"lastHero":"emi","profiles":{"emi":prof("Emi","4-5","k",{})}});pg=open_(c,tag='import')
    pg.evaluate("go('settings')");pg.wait_for_selector('#pcIn');pg.fill('#pcIn',code);pg.click('#pcCheck');pg.wait_for_selector('#pcYes');pg.click('#pcYes');pg.wait_for_timeout(800)
    pr=sv(pg)['profiles']
    ck({k:pr[k].get('age') for k in WANT}==WANT and pr['eshon']['stars']=={"3":2},'old v21 NR1 code imported, ages converted to ranges, stars kept')
    # new code round-trips with ranges
    rt=pg.evaluate("(async()=>{const c=await pcMake();const r=await pcRead(c);return {age:r.save.profiles.cayden.age,grade:r.save.profiles.cayden.grade,name:r.save.profiles.cayden.name};})()")
    ck(rt=={'age':'8-10','grade':'5','name':'Cayden'},'v22 code carries name, age range and grade: %s'%rt)
    c.close()
    # ---- 5. name tip + age-range picker (desktop and phone) ----
    TIP='Tip: use a nickname or hero name, not a full name.'
    for w,h,tag,mob in ((1280,900,'desktop',False),(390,844,'phone',True)):
        c=ctx(w,h,mobile=mob);pg=open_(c,tag='new-'+tag)
        pg.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=emi]')
        pg.wait_for_selector('#nm');t=pg.inner_text('#nmTip')
        ck(TIP in t and pg.get_attribute('#nm','aria-describedby')=='nmTip','%s: name-field tip shown and linked (%s)'%(tag,t))
        ck(pg.evaluate("(()=>{const r=document.getElementById('nmTip').getBoundingClientRect();return r.width>0&&r.right<=innerWidth+1})()"),'%s: tip fits the screen'%tag)
        if SH: pg.locator('#nmTip').scroll_into_view_if_needed();pg.screenshot(path=f'{OUT}/{BR}-{tag}-name-tip.png')
        pg.fill('#nm','Starbean');pg.click('text=Start the adventure');pg.wait_for_selector('.about [data-age]')
        ages=pg.eval_on_selector_all('.about [data-age]','e=>e.map(x=>x.dataset.age+"|"+x.innerText.replace(/\\s+/g," "))')
        ck([a.split('|')[0] for a in ages]==['4-5','6-7','8-10','11-14'],'%s: 4 age-range buttons (%s)'%(tag,ages))
        ck(all(re.search(r'\d',a.split('|')[1]) and 'Ages' in a for a in ages),'%s: buttons read "Ages 4\u20135" etc.'%tag)
        ck(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),'%s: age picker has no sideways scroll'%tag)
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-age-range-picker.png')
        pg.click('[data-age="8-10"]');pg.wait_for_selector('[data-grade="3"]');pg.click('[data-grade="3"]');pg.wait_for_selector('#abGo')
        q=pg.inner_text('.abq');ck(q=='Nice to meet you, Starbean! Ages 8\u201310, in 3rd grade!','%s: confirmation uses the range: %s'%(tag,q))
        e=sv(pg)['profiles']['emi'];ck(e['age']=='8-10' and e['grade']=='3' and e['name']=='Starbean','%s: saved age range 8-10 / grade 3'%tag)
        pg.click('#abGo');pg.wait_for_timeout(600)
        rec=pg.evaluate("(()=>{const pf=P();const g=pf.grade;pf.grade='';const sb=SUBJ.find(s=>s.grades.includes(pf.grade))||(ageRangeOf(pf.age)&&SUBJ_BY[AGE_REALM[pf.age]]);pf.grade=g;return sb&&sb.id})()")
        ck(rec=='mult','%s: age range drives the starting-realm suggestion when no grade matches (8-10 -> %s)'%(tag,rec))
        c.close()
    # ---- 6. Privacy page, footer, links; progress-code note; reset all (desktop + phone) ----
    for w,h,tag,mob in ((1280,900,'desktop',False),(390,844,'phone',True)):
        c=ctx(w,h,seed=OLD,raw={'ttq-doodle-eshon':'{"x":1}','ttq-probe':'1'},mobile=mob);pg=open_(c,tag='priv-'+tag)
        pg.evaluate("titleScreen()");pg.wait_for_timeout(500)
        ck(pg.locator('#homePrivacy').count()==1 and pg.locator('#nrFoot #footPrivacy').count()==1,'%s: Privacy link on Home and in the footer'%tag)
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-home-fonts.png')
        pg.click('#footPrivacy');pg.wait_for_selector('.privpg');t=pg.evaluate("document.getElementById('app').textContent")
        need=['Privacy at NumiRealm','Last updated: Oct 28, 2026','BVO Global LLC','bvoglobalmarketing@gmail.com','No accounts','No ads','No analytics','GitHub','IP address','hosted with the game','progress code','Only share it with family','Reset all data on this device','age range']
        ck(all(x in t for x in need),'%s: Privacy page has all required points (missing %s)'%(tag,[x for x in need if x not in t]))
        bad=[x for x in ['complian','COPPA','GDPR','certified','guarantee','colour','favourite','practise'] if x.lower() in t.lower()]
        ck(bad==[],'%s: no compliance claims or UK spellings on the Privacy page (%s)'%(tag,bad))
        ck(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),'%s: Privacy page has no sideways scroll'%tag)
        if SH:
            pg.screenshot(path=f'{OUT}/{BR}-{tag}-privacy-top.png')
            pg.locator('[data-priv=code]').scroll_into_view_if_needed();pg.screenshot(path=f'{OUT}/{BR}-{tag}-privacy-lower.png')
        pg.click('#backBtn');pg.wait_for_timeout(300)
        pg.evaluate("go('profile')");pg.wait_for_timeout(300);ck(pg.locator('#profPrivacy').count()==1,'%s: Privacy link on Profile'%tag)
        pg.click('#profPrivacy');pg.wait_for_selector('.privpg');ck(True,'%s: Profile link opens Privacy'%tag)
        pg.evaluate("go('settings')");pg.wait_for_selector('#progressCard')
        pg.evaluate("pcDoCopy()");pg.wait_for_selector('#pcOut');pg.wait_for_selector('#pcNote')
        NOTE="This code includes your heroes' names, age ranges and grades. Only share it with family."
        ck(NOTE in pg.inner_text('#pcNote'),'%s: note shown with the progress code'%tag)
        if SH: pg.locator('#progressCard').scroll_into_view_if_needed();pg.screenshot(path=f'{OUT}/{BR}-{tag}-progress-code-note.png')
        pg.locator('#resetAllBtn').scroll_into_view_if_needed();pg.click('#resetAllBtn');pg.wait_for_selector('#resetAllC1')
        ck(pg.locator('#resetAllYes').count()==0,'%s: step 1 of the reset does not act yet'%tag)
        pg.click('#resetAllCancel');pg.wait_for_selector('#resetAllBtn');ck(sv(pg) is not None,'%s: cancel keeps the save'%tag)
        pg.click('#resetAllBtn');pg.click('#resetAllNext');pg.wait_for_selector('#resetAllC2')
        if SH: pg.locator('#resetAllCard').scroll_into_view_if_needed();pg.screenshot(path=f'{OUT}/{BR}-{tag}-reset-confirm.png')
        pg.evaluate("sessionStorage.setItem('ttq-reloaded-21','1');localStorage.setItem('nr-loaded','1')")
        with pg.expect_navigation(): pg.click('#resetAllYes')
        pg.wait_for_timeout(1000)
        left=pg.evaluate("({ls:Object.keys(localStorage),ss:Object.keys(sessionStorage).filter(k=>/^(ttq-|nr-)/.test(k))})")
        extra=[k for k in left['ls'] if k not in ('ttq-save-v2','ttq-save-v2-backup')]
        s=sv(pg)
        ck(extra==[] and left['ss']==[],'%s: all game keys removed (left %s)'%(tag,left))
        ck(s is None or all(not v.get('stars') for v in s.get('profiles',{}).values()),'%s: after the reset the game starts fresh'%tag)
        c.close()
    c=ctx(seed=OLD);pg=open_(c,tag='swreset');pg.wait_for_timeout(2500)
    before=pg.evaluate("caches.keys()");pg.evaluate("resetAllWipe()");after=pg.evaluate("caches.keys()");regs=pg.evaluate("navigator.serviceWorker.getRegistrations().then(r=>r.length)")
    ck('numirealm-v22' in before and [k for k in after if k.startswith('numirealm')]==[] and regs==0,'reset clears SW caches and unregisters the SW (before %s, after %s, regs %s)'%(before,after,regs))
    c.close()
    ck(errs==[],'no console errors (%s)'%errs[:5])
    b.close()
srv.shutdown()
print('FAILS',len(fails))
raise SystemExit(1 if fails else 0)
