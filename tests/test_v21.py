# v21: worked examples after a miss, spaced review queue, mastery checks + Realm Master badges,
# Mixed Math review (gradual mixing), offline play with a versioned service worker, v20 save compatibility.
import os,json,re,shutil,threading,http.server,functools,tempfile,time
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.abspath(__file__));URL='file://'+os.path.join(D,'index.html')
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
def attach(pg,tag):
    pg.on('console',lambda m: errs.append(f'[{tag}] {m.text}') if m.type=='error' and 'fonts.g' not in m.text and 'ERR_INTERNET_DISCONNECTED' not in m.text else None)
    pg.on('pageerror',lambda e: errs.append(f'[{tag}] PAGEERR {e}'))
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
ck("const APP_VERSION='21'" in html,'APP_VERSION is 21')
ck(json.load(open(os.path.join(D,'version.json')))['version']=='21','version.json is 21')
ck(os.path.exists(os.path.join(D,'sw.js')),'sw.js ships next to index.html')
sw=open(os.path.join(D,'sw.js')).read()
ck("'numirealm-v'+V" in sw and 'version\\.json' in sw and "cache:'no-cache'" in sw,'sw.js: versioned cache, version.json never cached, page network-first')
ck('standalone' not in html and 'display-mode' not in html,'no standalone/display-mode strings')
v21=html[html.index('/* ===== v21'):]
for w in ['practise','colour','favourite','centre','harbour','cosy','defence','behaviour','Brackets','Lighter skin','All six heroes']:
    ck(w not in v21,'US English in v21 code: no "%s"'%w)
for w in ['sign in','log in','account','cloud','sync','subscri','payment','premium','purchase','upgrade to','parent dashboard']:
    ck(w not in v21.lower(),'honest labels in v21 code: no "%s"'%w)
SEED={"muted":True,"narrator":False,"hero":"emi","profiles":{"emi":{"name":"Emi","prologue":True,"age":8,"grade":3,"stars":{"2":3,"5":2},"rewards":["fcrown"],
 "subj":{"add":{"stars":{"1":3,"2":3,"3":2,"4":3},"hist":{},"intro":True},"sub":{"stars":{"1":2},"hist":{},"intro":True},"frac":{"stars":{"1":1},"hist":{},"intro":True}},
 "weak":{"sub:2":{"m":1,"h":0,"ok":0,"sigs":[]}},"days":["2026-10-20"],"custom":{"keepme":[1,2,3]}}}}
with sync_playwright() as p:
    b=p.chromium.launch()
    def page(w=1280,seed=SEED,url=URL,**kw):
        c=b.new_context(viewport={'width':w,'height':900},**kw)
        if seed is not None: c.add_init_script("if(!sessionStorage.getItem('seeded')){sessionStorage.setItem('seeded','1');localStorage.setItem('ttq-save-v2',%s)}"%json.dumps(json.dumps(seed)))
        pg=c.new_page();attach(pg,'w%d'%w);pg.goto(url);pg.wait_for_timeout(900);return c,pg
    c,pg=page()
    # ---- 1. worked examples: every chapter generator, every stage, 300 samples each ----
    res=pg.evaluate("""(()=>{const bad=[],ops={};let n=0;SUBJ.forEach(s=>s.ch.forEach((ch,i)=>{if(!ch)return;['p','b','a'].forEach(k=>{for(let t=0;t<300;t++){const q=ch.gen(k);const w=worked21(q);n++;const op=(q.m&&q.m.op)||q.input;ops[op]=(ops[op]||0)+1;
      if(!w){bad.push('null '+s.id+(i+1)+' '+op);continue;}const txt=w.join(' ');if(w.length<2||w.length>3||/NaN|undefined|null|Infinity/.test(txt))bad.push(s.id+(i+1)+' '+op+': '+txt.slice(0,120));
      const nums=(txt.replace(/<[^>]+>/g,' ').match(/-?\\d+(\\.\\d+)?/g)||[]);if(nums.some(x=>x.includes('.')||+x<0))bad.push('non-integer/negative '+s.id+(i+1)+' '+op+': '+txt.slice(0,100));
      const a=Array.isArray(q.ans)?null:q.ans;if(q.input==='pad'&&!['frpart'].includes(op)&&a!=null&&!nums.includes(String(a)))bad.push('answer not reached '+s.id+(i+1)+' '+op+' ans='+a+': '+txt.slice(0,100));}})}));return {n,bad:bad.slice(0,12),nb:bad.length,ops:Object.keys(ops).length}})()""")
    ck(res['nb']==0,'worked example for every generated question (%d samples, %d ops), no NaN/negatives, pad answers reached: %s'%(res['n'],res['ops'],res['bad']))
    # ---- 2. worked example shows after a wrong answer in practice, not in boss, not as a hint ----
    import sys;sys.path.insert(0,'/workspace/v18tmp');import importlib.util
    spec=importlib.util.spec_from_file_location('ap','/workspace/v18tmp/audit_play.py')
    src=open('/workspace/v18tmp/audit_play.py').read();src=src[:src.index('def practice')]
    ns={};exec(compile(src.split('ENGS=')[0]+'\n'+src[src.index('def pad'):],'ap','exec'),ns)
    pg.evaluate("openChapter('add',2)");ns['scene'](pg);ns['learn'](pg);pg.wait_for_selector('[data-stage=practice]')
    pg.wait_for_function("TTQ_SUBJ.SS&&TTQ_SUBJ.SS.cur",timeout=10000)
    ck(not pg.query_selector('#wex'),'no worked example before answering')
    hint_html=pg.evaluate("(document.getElementById('hint')||{}).innerHTML||''")
    pg.evaluate("(()=>{const q=TTQ_SUBJ.SS.cur;if(q.input==='mc')document.querySelector('#sopts .opt[data-i=\"'+((q.ans+1)%q.opts.length)+'\"]').click();else{String(q.ans+1).split('').forEach(d=>document.querySelector('#spad [data-k=\"'+d+'\"]').click());document.getElementById('sok').click()}})()")
    pg.wait_for_timeout(400)
    ck(pg.is_visible('#wex') and pg.eval_on_selector_all('#wex li','e=>e.length')>=2,'practice miss: "How to solve it" steps shown')
    ck('Not quite!' in pg.inner_text('#fb'),'existing feedback line kept')
    pg.screenshot(path='/tmp/v21_wex.png')
    pg.click('#nextbtn');pg.wait_for_timeout(300)
    ck(not pg.query_selector('#wex'),'worked example cleared on the next question')
    # boss: no worked example during the boss
    pg.evaluate("TTQ_SUBJ.SS.inBoss=true");pg.evaluate("(()=>{const fb=document.getElementById('fb');fb.className='fb bad';})()");pg.wait_for_timeout(200)
    ck(not pg.query_selector('#wex'),'no worked example while a boss fight is on')
    pg.evaluate("TTQ_SUBJ.SS.inBoss=false;document.getElementById('fb').className='fb'")
    # ---- 3. Training Grounds cards ----
    pg.evaluate("go('training')");pg.wait_for_timeout(300)
    ids=pg.evaluate("[...document.querySelectorAll('#app .card')].map(e=>e.id).filter(Boolean)")
    ck(ids.index('reviewQueue')<ids.index('needsWork')<ids.index('mixReview'),'practice order: review queue, needs-work, Mixed Math review (%s)'%ids)
    ck(pg.is_visible('#masteryCard') and pg.is_visible('#mcStart'),'mastery check unlocked for Addition (4 chapters done)')
    ck(pg.evaluate("document.querySelector('#reviewQueue [data-rv=\"sub-2\"]')!==null") and pg.is_enabled('#rvStart'),'review queue lists the needs-work item, Start review enabled')
    pg.evaluate("SFX.tap();V12.tRealm='div';runScr({n:'training',a:[]})");pg.wait_for_timeout(200)
    ck(pg.is_visible('#mcLocked') and not pg.query_selector('#mcStart'),'mastery check locked for a realm with < 2 chapters done')
    # ---- 4. spaced review: clear -> box 1 (+1 day) -> due -> box 2 (+3 days); miss drops it back to needs-work ----
    r=pg.evaluate("""(()=>{const pf=P(),out={};DR={mix:true,items:[]};const q={sig:'x1',text:'t'};noteAns('sub',2,q,true,0);noteAns('sub',2,q,true,0);DR=null;
      const R=pf.review['sub:2'];out.cleared=!pf.weak['sub:2'];out.box=R&&R.box;out.days=R&&Math.round((R.due-Date.now())/864e5);
      const dn=()=>rvQueue(pf).filter(x=>x.dueNow&&x.sid==='sub'&&x.c===2).length;out.dueBefore=dn();R.due=Date.now()-1000;out.dueAfter=dn();
      DR={kind:'review',mix:true,items:[]};noteAns('sub',2,q,true,0);out.box2=pf.review['sub:2'].box;out.days2=Math.round((pf.review['sub:2'].due-Date.now())/864e5);
      noteAns('sub',2,q,true,0);out.box2b=pf.review['sub:2'].box;
      pf.review['sub:2'].due=0;noteAns('sub',2,q,false,0);out.gone=!pf.review['sub:2'];out.backWeak=!!pf.weak['sub:2'];DR=null;
      pf.review['add:3']={box:4,due:0};DR={kind:'review',mix:true,items:[]};noteAns('add',3,q,true,0);out.grad=!pf.review['add:3']&&pf.reviewDone>=1;DR=null;persist();
      out.saved=JSON.parse(localStorage.getItem('ttq-save-v2')).profiles.emi.reviewDone;return out})()""")
    ck(r['cleared'] and r['box']==1 and r['days']==1,'cleared needs-work item enters review box 1, due in 1 day: %s'%r)
    ck(r['dueBefore']==0 and r['dueAfter']==1,'item is not due until its day arrives')
    ck(r['box2']==2 and r['days2']==3,'due review answered right -> box 2, next in 3 days')
    ck(r['box2b']==2,'not-yet-due review does not advance early (spacing kept)')
    ck(r['gone'] and r['backWeak'],'a miss sends it back to the needs-work list')
    ck(r['grad'] and r['saved']>=1,'finishing box 4 graduates the skill; saved')
    # review round UI
    pg.evaluate("P().weak['sub:2']={m:1,h:0,ok:0,sigs:[]};persist();go('training')");pg.wait_for_timeout(200);pg.click('#rvStart');pg.wait_for_timeout(300)
    ck('Review' in pg.inner_text('.drlab') and 'Question 1 of' in pg.inner_text('#drTime'),'review round: labeled, counted questions, no countdown')
    pg.evaluate("DR.over=true;drillDone()");pg.wait_for_timeout(200)
    ck(pg.is_visible('#rvResult'),'review round summary shown')
    # ---- 5. mastery check ----
    def run_mc(right):
        pg.evaluate("masteryStart('add')");pg.wait_for_timeout(300)
        ck(pg.evaluate("DR.lan")==0 and pg.evaluate("DR.count")==8,'mastery check: 8 questions, no lanterns')
        seen=set()
        for i in range(8):
            seen.add(pg.evaluate("TTQ_SUBJ.SS.c"))
            pg.evaluate("""(ok)=>{const S=TTQ_SUBJ.SS;S.onAnswer(ok,0)}""",right)
            pg.wait_for_timeout(50);pg.evaluate("drillNext()");pg.wait_for_timeout(80)
        return seen
    seen=run_mc(False)
    ck(pg.is_visible('#mcResult') and 'Not yet' in pg.inner_text('#mcResult'),'mastery check fail: "Not yet" result')
    ck(pg.evaluate("P().mastery.add.pass")==False,'failed check is not a pass')
    seen=run_mc(True)
    ck(seen<= {1,2,3,4} and len(seen)==4,'mastery questions cover every finished chapter (%s)'%seen)
    ck('passed' in pg.inner_text('#mcResult'),'mastery check pass shown')
    m=pg.evaluate("P().mastery.add");ck(m['pass'] and m['upto']==4 and m['best']==8,'mastery saved: %s'%m)
    pg.screenshot(path='/tmp/v21_mc.png')
    pg.evaluate("go('trophies')");pg.wait_for_timeout(300)
    ck(pg.is_visible('#masteryBadges') and 'Passed through Ch. 4' in pg.inner_text('[data-mb=add]'),'Trophy Room shows mastery progress under the Star Path')
    pg.evaluate("for(let c=1;c<=sCount('add');c++)SP('add').stars[c]=3;persist();masteryStart('add')");pg.wait_for_timeout(200)
    for i in range(8): pg.evaluate("TTQ_SUBJ.SS.onAnswer(true,0)");pg.evaluate("drillNext()");pg.wait_for_timeout(60)
    ck('Realm Master' in pg.inner_text('#mcResult'),'passing after all chapters: Realm Master')
    pg.evaluate("go('trophies')");pg.wait_for_timeout(200)
    ck('Realm Master' in pg.inner_text('[data-mb=add]') and '(1 of 6)' in pg.inner_text('#masteryBadges h2'),'Realm Master badge earned (1 of 6)')
    # ---- 6. Mixed Math review: only mastered skills, starts with 2, mixes in more after 2 right in a row ----
    r=pg.evaluate("""(()=>{const ms=masteredSkills(P());return {n:ms.length,ok:ms.every(x=>chStars(x.sid,x.c,P())>=2),fr:ms.some(x=>x.sid==='frac')}})()""")
    ck(r['ok'] and not r['fr'],'Mixed Math review draws only from chapters with 2+ stars (%s)'%r)
    pg.evaluate("mixStart()");pg.wait_for_timeout(200)
    st=[pg.evaluate("DR.stage")];realms=set()
    for i in range(10):
        realms.add(pg.evaluate("TTQ_SUBJ.SS.sid"))
        pg.evaluate("TTQ_SUBJ.SS.onAnswer(true,0)");pg.evaluate("if(DR)drillNext()");pg.wait_for_timeout(60)
        st.append(pg.evaluate("DR?DR.stage:-1"))
    ck(st[0]==2 and max(st)>=6,'gradual mixing: starts at 2 skills, grows with right answers (%s)'%st)
    ck(len(realms)>=2,'review mixes realms (%s)'%realms)
    ck(pg.is_visible('#mxResult'),'Mixed Math review summary shown')
    pg.evaluate("mixStart()");pg.wait_for_timeout(200)
    for i in range(4): pg.evaluate("TTQ_SUBJ.SS.onAnswer(i%2===0,0)".replace('i%2',str(i%2)));pg.evaluate("drillNext()");pg.wait_for_timeout(50)
    ck(pg.evaluate("DR.stage")==2,'misses keep the mix where it is (no jump)')
    pg.evaluate("DR.over=true;drillDone()")
    # drill miss shows worked example
    pg.evaluate("drillStart([{sid:'frac',c:6}],false)");pg.wait_for_timeout(200);pg.evaluate("TTQ_SUBJ.SS.onAnswer(false,0)");pg.wait_for_timeout(200)
    ck(pg.is_visible('#wex'),'skill drill miss: worked example shown')
    pg.evaluate("DR.over=true;drillDone()")
    # layout at 390
    c2,pg2=page(390)
    for scr in ['training','trophies']:
        pg2.evaluate(f"go('{scr}')");pg2.wait_for_timeout(300)
        ck(not pg2.evaluate("document.documentElement.scrollWidth>innerWidth"),f'390px: {scr} has no sideways scroll')
    c2.close()
    # ---- 7. v20 save loads intact (unknown fields kept, same key) ----
    c3,pg3=page(seed=SEED)
    s=pg3.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))")
    e=s['profiles']['emi'];ck(e['subj']['add']['stars']=={"1":3,"2":3,"3":2,"4":3} and e['custom']=={"keepme":[1,2,3]} and e['rewards']==['fcrown'] and e['weak']['sub:2']['m']==1,'v20 save loads intact in v21 (stars, rewards, needs-work, unknown fields)')
    ck(pg3.evaluate("Object.keys(localStorage).includes('ttq-save-v2')"),'save key is still ttq-save-v2')
    c3.close();c.close()
    # ---- 8. service worker: offline after first visit, update v20 -> v21 -> forced v22 ----
    tmp=tempfile.mkdtemp();
    v20=os.path.join(os.path.dirname(D),'index-v20.html')
    if not os.path.exists(v20): v20='/workspace/index-v20.html'
    shutil.copy(v20,tmp+'/index.html');open(tmp+'/version.json','w').write('{"version":"20"}')
    srv=http.server.ThreadingHTTPServer(('127.0.0.1',8828),functools.partial(http.server.SimpleHTTPRequestHandler,directory=tmp))
    http.server.SimpleHTTPRequestHandler.log_message=lambda *a:None
    threading.Thread(target=srv.serve_forever,daemon=True).start();U='http://127.0.0.1:8828/index.html'
    cx=b.new_context(viewport={'width':1280,'height':900});cx.add_init_script("if(!localStorage.getItem('ttq-save-v2'))localStorage.setItem('ttq-save-v2',%s)"%json.dumps(json.dumps(SEED)))
    pw=cx.new_page();attach(pw,'sw');pw.goto(U);pw.wait_for_timeout(1500)
    ck(pw.evaluate("TTQ_VERSION.app")=='20' and pw.evaluate("!navigator.serviceWorker.controller"),'v20 running, no service worker')
    # release v21
    shutil.copy(os.path.join(D,'index.html'),tmp+'/index.html');shutil.copy(os.path.join(D,'sw.js'),tmp+'/sw.js');open(tmp+'/version.json','w').write('{"version":"21"}')
    pw.evaluate("document.dispatchEvent(new Event('visibilitychange'))");pw.wait_for_timeout(2500)
    ck(pw.evaluate("TTQ_VERSION.app")=='21','v20 -> v21 auto-update reloads into v21')
    pw.evaluate("navigator.serviceWorker.ready.then(()=>1)");pw.wait_for_timeout(1500);pw.reload();pw.wait_for_timeout(1500)
    ck(pw.evaluate("!!navigator.serviceWorker.controller"),'v21 service worker controls the page')
    ck('numirealm-v21' in pw.evaluate("caches.keys()"),'cache named numirealm-v21')
    s=pw.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2')).profiles.emi");ck(s['subj']['add']['stars']['4']==3 and s['custom']=={"keepme":[1,2,3]},'save intact across v20 -> v21 update')
    # offline
    cx.set_offline(True);pw.reload();pw.wait_for_timeout(1500)
    ck(pw.evaluate("TTQ_VERSION.app")=='21' and pw.query_selector('.herocard,#app h1') is not None,'offline reload: game loads from the cache')
    ck(pw.is_visible('#offNote'),'offline notice shown')
    pw.screenshot(path='/tmp/v21_offline.png')
    pw.evaluate("pickHero('emi');SP('add').stars[5]=2;persist()")
    ck(JSON.parse if False else pw.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2')).profiles.emi.subj.add.stars['5']")==2,'offline progress still saves')
    cx.set_offline(False);pw.wait_for_timeout(300);pw.evaluate("window.dispatchEvent(new Event('online'))");pw.wait_for_timeout(200)
    ck(not pw.query_selector('#offNote'),'offline notice hides when back online')
    # forced next version v22 with the SW in place
    h22=open(os.path.join(D,'index.html'),encoding='utf-8').read().replace("const APP_VERSION='21'","const APP_VERSION='22'")
    open(tmp+'/index.html','w',encoding='utf-8').write(h22);open(tmp+'/version.json','w').write('{"version":"22"}')
    pw.evaluate("go('home')");pw.wait_for_timeout(200);pw.evaluate("TTQ_VERSION.check(true)");pw.wait_for_timeout(3000)
    ck(pw.evaluate("TTQ_VERSION.app")=='22','with the service worker present, a new release (v22) still arrives through auto-update')
    pw.wait_for_timeout(2500)
    ks=pw.evaluate("caches.keys()");ck('numirealm-v22' in ks and 'numirealm-v21' not in ks,'old cache cleared after update (%s)'%ks)
    ck(pw.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2')).profiles.emi.subj.add.stars['5']")==2,'save intact across v21 -> v22 update')
    cx.close();srv.shutdown();shutil.rmtree(tmp,True)
    b.close()
ck(not errs,'no console errors: %s'%errs[:5])
print('RESULT','PASS' if not fails else 'FAIL',len(fails),'FAILS')
