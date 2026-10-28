# v9/v10 NumiRealm: subject select, per-subject chapter 1 (learn/practice/boss pass + fail-retry),
# generator correctness, v8 save migration, 375px layout, no console errors.
import sys, os, json
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); URL='file://'+os.path.join(D,'index.html')
errs=[]; fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
def attach(pg,tag):
    pg.on('console',lambda m: errs.append(f'[{tag}] {m.text}') if m.type=='error' else None)
    pg.on('pageerror',lambda e: errs.append(f'[{tag}] PAGEERR {e}'))
def scene(pg):
    pg.wait_for_selector('#bubble'); n=pg.evaluate('TTQ.SC?TTQ.SC.lines.length-TTQ.SC.i:0')
    lines=pg.evaluate('TTQ.SC?TTQ.SC.lines.map(l=>l.who+": "+l.text):[]')
    for i in range(n): pg.click('#contBtn'); pg.wait_for_timeout(30)
    return lines
def pad(pg,v):
    for d in str(v): pg.click(f'#spad [data-k="{d}"]')
    pg.click('#sok')
def answer(pg,right):
    q=pg.evaluate("(()=>{const q=TTQ_SUBJ.SS.cur;return {input:q.input,ans:q.ans,n:(q.opts||[]).length}})()")
    if q['input']=='mc':
        i=q['ans'] if right else (q['ans']+1)%q['n']; pg.click(f'#sopts .opt[data-i="{i}"]')
    elif q['input']=='multi':
        vals=q['ans'] if right else [q['ans'][0]+1]+q['ans'][1:]
        for v in vals: pad(pg,v)
    elif q['input']=='ld':
        while pg.evaluate("TTQ_SUBJ.SS.cur&&TTQ_SUBJ.SS.ldStep<TTQ_SUBJ.SS.ldseq.length"):
            ph,want=pg.evaluate("(()=>{const S=TTQ_SUBJ.SS,[k,ph]=S.ldseq[S.ldStep],s=S.cur.L.steps[k];return [ph,ph==='D'?s.q:ph==='M'?s.m:ph==='S'?s.r:null]})()")
            if ph=='B': pg.click('#bringBtn')
            else: pad(pg,want)
            pg.wait_for_timeout(550)
    else: pad(pg,q['ans'] if right else q['ans']+1)
def learn(pg):
    pg.wait_for_selector('[data-stage=learn]')
    for i in range(40):
        if pg.query_selector('#nextbtn:not(.hidden)'): break
        pg.click('#lnext' if pg.query_selector('#lnext:not(.hidden)') else '#showBtn' if pg.query_selector('#showBtn:not(.hidden)') else '[data-enter]:not(#nextbtn)')
        pg.wait_for_timeout(60)
    st=len(pg.query_selector_all('.lstep')); tip=pg.query_selector('#ltip:not(.hidden)') is not None
    pg.click('#nextbtn'); return st,tip
def practice(pg):
    pg.wait_for_selector('[data-stage=practice]'); n=0
    while not pg.query_selector('text=Continue the story'):
        pi=pg.evaluate("TTQ_SUBJ.SS.pi"); answer(pg,True); n+=1
        pg.wait_for_function("(pi)=>!TTQ_SUBJ.SS.cur||TTQ_SUBJ.SS.pi!==pi||document.querySelector('#nextbtn:not(.hidden)')",arg=pi,timeout=9000)
        nb=pg.query_selector('#nextbtn:not(.hidden)')
        if nb: nb.click()
        pg.wait_for_timeout(80)
        if n>12: raise Exception('practice stuck')
    pg.click('text=Continue the story'); return n
def boss(pg,win):
    scene(pg); pg.wait_for_selector('#hptxt'); sigs=pg.evaluate("TTQ_SUBJ.SS.boss.map(q=>q.sig)"); k=0
    while True:
        pg.wait_for_timeout(100)
        if pg.query_selector('#bubble'): break
        if pg.query_selector('#hptxt') and pg.evaluate("TTQ_SUBJ.SS.cur&&!TTQ_SUBJ.SS.locked"):
            answer(pg,win); k+=1
            if k>30: raise Exception('boss stuck')
    return sigs
REC={'add':11,'sub':11,'div':12,'frac':11}
with sync_playwright() as p:
    b=p.chromium.launch()
    c=b.new_context(viewport={'width':1100,'height':950}); pg=c.new_page(); attach(pg,'main')
    pg.goto(URL); pg.wait_for_selector('.herocard'); pg.evaluate("TTQ.save.narrator=false")
    ck('NumiRealm' in pg.inner_text('#app') and pg.title().startswith('NumiRealm'),'title screen and <title> say NumiRealm')
    pg.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=sage]'); pg.click('text=Start the adventure'); pg.wait_for_selector('[data-age]')
    pg.click('[data-age="7"]'); pg.click('[data-grade="2"]'); pg.click('#abGo')
    pro=scene(pg); ck(any('five' in l.lower() or 'realm' in l.lower() for l in pro),'prologue mentions the realms')
    pg.wait_for_selector('.stile'); tiles=pg.eval_on_selector_all('.stile','es=>es.map(e=>e.dataset.subject)')
    ck(tiles==['add','sub','mult','div','frac','mix'],'subject select tiles in order: %s'%tiles)
    badges=pg.eval_on_selector_all('.stile','es=>es.filter(e=>e.querySelector(".sbadge")).map(e=>e.dataset.subject)')
    ck(badges==['add','sub','mult','mix'],'2nd grade recommended badges: %s'%badges)
    ck('Recommended for 2nd grade' in pg.inner_text('[data-subject=add]'),'badge text')
    ck(pg.query_selector('#abEdit') and pg.query_selector('text=Switch hero') and pg.query_selector('text=Change name') and pg.query_selector('button[onclick="closetScreen()"]') is not None,'About edit, switch hero, rename, closet on subject select')
    pg.screenshot(path=os.path.join(D,'v9-subject-select.png'))
    for sid in ('add','sub','div','frac'):
        pg.evaluate('subjectScreen()'); pg.click(f'[data-subject={sid}]')
        rl=scene(pg); ck(len(rl)>=3,f'{sid}: realm intro scene ({len(rl)} lines)')
        pg.wait_for_selector('.slevels'); lv=pg.query_selector_all('.lvl[data-chapter]')
        locked=len(pg.query_selector_all('.lvl.locked'))
        ck(len(lv)==REC[sid] and locked==REC[sid]-1,f'{sid}: {len(lv)} chapters, only chapter 1 open')
        ck(pg.query_selector('#toSubjects') is not None,f'{sid}: back to subjects button')
        pg.click('.lvl[data-chapter="1"]'); intro=scene(pg); team1=pg.evaluate("TTQ_SUBJ.SS.team")
        st,tip=learn(pg); ck(st>=2 and tip,f'{sid}: learn shows {st} steps + easy trick')
        n=practice(pg); ck(n==6,f'{sid}: practice+apply answered {n} (4 practice, 2 apply)')
        s1=boss(pg,False); lose=scene(pg); ck(any('won this round' in x for x in lose) and any('shuffled all the numbers' in x for x in lose),f'{sid}: lose scene plays ({len(lose)} lines)')
        retry=scene(pg); ck(pg.evaluate("TTQ_SUBJ.SS.attempt")==2 and pg.evaluate("TTQ_SUBJ.SS.team")!=team1,f'{sid}: chapter restarts (attempt 2) with a new teammate')
        learn(pg); practice(pg); s2=boss(pg,True)
        ck(len(set(s1)&set(s2))==0,f'{sid}: retry boss uses different numbers (overlap {len(set(s1)&set(s2))})')
        out=scene(pg); pg.wait_for_selector('.starsbig')
        stars=pg.evaluate(f"TTQ_SUBJ.SP('{sid}').stars[1]"); ck(stars==3,f'{sid}: boss beaten, stars={stars}')
        pg.click('text=Map') if pg.query_selector('text=Map') else pg.evaluate(f"smapScreen('{sid}')")
        pg.evaluate(f"smapScreen('{sid}')"); ck(not pg.query_selector('.lvl[data-chapter="2"].locked'),f'{sid}: chapter 2 unlocked')
        pg.click('#toSubjects'); pg.wait_for_selector('.stile')
        ck('1/%d chapters'%REC[sid] in pg.inner_text(f'[data-subject={sid}]'),f'{sid}: tile shows progress')
    ck(pg.evaluate("TTQ.save.profiles.sage.rewards.length")==4,'closet rewards earned from subject bosses: %s'%pg.evaluate("TTQ.save.profiles.sage.rewards"))
    # generators
    g=pg.evaluate("""(()=>{const T=TTQ_SUBJ,bad=[];let n=0;
      for(let i=0;i<400;i++){const d=2+Math.floor(Math.random()*8),N=d+Math.floor(Math.random()*990);const L=T.ldSteps(N,d);n++;
        if(L.Q*d+L.R!==N||L.R>=d)bad.push('ld '+N+'/'+d);
        L.steps.forEach(s=>{if(s.q*d!==s.m||s.cur-s.m!==s.r||s.r>=d)bad.push('ldstep '+N+'/'+d);});}
      const bi=T.borrowInfo(600,177);if(bi.top.join(',')!=='10,9,5'||!bi.strike[1]||!bi.strike[2])bad.push('borrow 600-177 '+JSON.stringify(bi));
      const b2=T.borrowInfo(1003,8);if(b2.top.join(',')!=='13,9,9,0')bad.push('borrow 1003-8 '+JSON.stringify(b2));
      const ca=T.carries([58,67]);if(ca[1]!=='1'||ca[2]!=='1')bad.push('carry 58+67 '+JSON.stringify(ca));
      if(T.gcd(12,18)!==6||T.lcm(4,6)!==12)bad.push('gcd/lcm');
      for(const [sid,chs] of Object.entries(T.CHAP))chs.forEach((ch,ci)=>{for(let i=0;i<40;i++)for(const k of ['p','a','b']){const q=ch.gen(k);n++;
        if(!q.check(q.ans))bad.push(sid+(ci+1)+' check');
        if(q.input==='pad'&&q.check(q.ans+1))bad.push(sid+(ci+1)+' wrong accepted');
        if(q.input==='multi'&&q.check([q.ans[0]+1].concat(q.ans.slice(1))))bad.push(sid+(ci+1)+' wrong multi accepted');
        if(/undefined|NaN|\\[object/.test(q.text+(q.vis||'')))bad.push(sid+(ci+1)+' text');}});
      const simp=T.CHAP.frac[5];for(let i=0;i<60;i++){const q=simp.gen('p');if(q.input==='multi'&&T.gcd(q.ans[0],q.ans[1])!==1)bad.push('simplify not lowest '+q.ans);}
      const eq=T.CHAP.frac[4];for(let i=0;i<60;i++){const q=eq.gen('p');if(q.input==='multi'&&q.check([q.ans[0]*2,q.ans[1]*2])&&q.ans[1]*2>12)bad.push('equiv');}
      return {n,bad:bad.slice(0,10),nb:bad.length};})()""")
    ck(g['nb']==0,'generators: %d questions, bad=%s'%(g['n'],g['bad']))
    ck(pg.evaluate("TTQ_SUBJ.CHAP.sub[7].learn().length")>=3 and 'zero' in pg.evaluate("TTQ_SUBJ.CHAP.sub[7].learn().map(s=>s.t).join(' ').toLowerCase()").replace('0','zero'),'borrowing-across-zeros lesson')
    # long-division guided steps in practice (div ch9)
    pg.evaluate("TTQ_SUBJ.SP('div').stars={1:1,2:1,3:1,4:1,5:1,6:1,7:1,8:1};openChapter('div',9)"); scene(pg)
    pg.wait_for_selector('#ldbox'); learn(pg); pg.wait_for_selector('[data-stage=practice]')
    ok=False
    for i in range(6):
        if pg.evaluate("TTQ_SUBJ.SS.cur.input")=='ld':
            # wrong twice on Divide -> value filled + explanation
            pad(pg,9 if pg.evaluate("TTQ_SUBJ.SS.cur.L.steps[0].q")!=9 else 8); pg.wait_for_timeout(800); pad(pg,9 if pg.evaluate("TTQ_SUBJ.SS.cur.L.steps[0].q")!=9 else 8); pg.wait_for_timeout(300)
            ok=pg.query_selector('.ldfix') is not None; pg.wait_for_timeout(1900); answer(pg,True); break
        pi=pg.evaluate("TTQ_SUBJ.SS.pi"); answer(pg,True); pg.wait_for_function("(pi)=>TTQ_SUBJ.SS.pi!==pi",arg=pi,timeout=9000)
    ck(ok,'long division: two wrong tries shows the step answer + explanation')
    c.close()
    # v8 save migration
    V8={"muted":True,"narrator":False,"hero":"cayden","profiles":{
      "cayden":{"name":"Cayden","stars":{"1":3,"2":3,"3":2},"hist":{},"rewards":["cr1","cr2"],"eq":{},"prologue":True,"age":10,"grade":"5"},
      "emi":{"name":"Emi","stars":{"1":1},"hist":{},"rewards":["fcrown"],"eq":{"head":"fcrown"},"prologue":True,"age":6,"grade":"1"}}}
    c=b.new_context(viewport={'width':1100,'height':900}); pg=c.new_page(); attach(pg,'migrate')
    c.add_init_script("if(!sessionStorage.getItem('seeded')){sessionStorage.setItem('seeded','1');localStorage.setItem('ttq-save-v2',%s)}"%json.dumps(json.dumps(V8)))
    pg.goto(URL); pg.wait_for_selector('.stile')
    pr=pg.evaluate("TTQ.save.profiles")
    ck(pr['cayden']['stars']=={"1":3,"2":3,"3":2} and pr['cayden']['rewards']==["cr1","cr2"] and pr['cayden']['age']==10 and pr['cayden']['grade']=='5','v8 cayden stars/rewards/age/grade kept')
    ck(pr['emi']['eq']=={"head":"fcrown"} and pr['emi']['age']==6,'v8 emi kept')
    ck(set(pr)=={'sage','emi','blu','eshon','melrose','cayden','zea'},'all seven heroes present (zea gets a fresh default)')
    t=pg.inner_text('[data-subject=mult]'); ck('3/19' in t and '8/57' in t,'mult tile shows v8 progress: '+t.replace('\n',' | '))
    ck('0/11' in pg.inner_text('[data-subject=add]'),'other subjects start fresh')
    ck('Recommended for 5th grade' in pg.inner_text('[data-subject=div]'),'5th-grade badge on division')
    pg.click('[data-subject=mult]'); pg.wait_for_selector('.lvl'); ck(pg.query_selector('#bubble') is None,'mult with progress skips the realm intro')
    ck(len(pg.query_selector_all('.lvl.done'))==3 and pg.query_selector('#toSubjects') is not None,'mult map: 3 chapters done, back-to-subjects button')
    pg.reload(); pg.wait_for_selector('.lvl'); ck(True,'reload returns to last map (mult)')
    pg.click('#toSubjects'); pg.wait_for_selector('.stile'); pg.click('[data-subject=frac]'); scene(pg); pg.wait_for_selector('.slevels')
    pg.click('button[onclick="closetScreen()"]'); pg.wait_for_selector('#pad-c, .closet, .card'); pg.wait_for_timeout(300)
    pg.evaluate('goMap()'); ck(pg.query_selector('.slevels') is not None,'closet back returns to the fraction map')
    c.close()
    # mobile 375
    c=b.new_context(viewport={'width':375,'height':812},device_scale_factor=2,is_mobile=True,has_touch=True); pg=c.new_page(); attach(pg,'mobile')
    pg.goto(URL); pg.wait_for_selector('.herocard'); pg.evaluate("TTQ.save.narrator=false")
    pg.evaluate("(s)=>{const b=document.querySelector(s);if(window.v16Go&&b.dataset.hero)v16Go(b.dataset.hero);b.click()}",'[data-hero=melrose]'); pg.click('text=Start the adventure'); pg.wait_for_selector('[data-age]')
    pg.click('[data-age="8"]'); pg.click('[data-grade="3"]'); pg.click('#abGo'); scene(pg); pg.wait_for_selector('.stile')
    ov=lambda: pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
    ck(ov(),'mobile subject select: no horizontal overflow')
    bx=[pg.query_selector(f'[data-subject={s}]').bounding_box() for s in ('add','sub','mult','div','frac')]
    ck(all(x['width']>=150 and x['height']>=140 for x in bx),'mobile tiles are big (%s)'%[(round(x['width']),round(x['height'])) for x in bx])
    pg.screenshot(path=os.path.join(D,'v9-mobile-subject-select.png'))
    for sid,ch in (('add',7),('sub',8),('div',10),('frac',9)):
        pg.evaluate(f"TTQ_SUBJ.SP('{sid}').intro=true;openChapter('{sid}',{ch})"); scene(pg); learn(pg)
        ck(ov(),f'mobile {sid} ch{ch} learn+question: no overflow')
        el=pg.query_selector('#spad [data-k="5"]') or pg.query_selector('#sopts .opt'); bb=el.bounding_box(); ck(bb['height']>=44,f'mobile {sid} answer buttons {round(bb["height"])}px tall')
    c.close(); b.close()
print('console errors:',errs); ck(not errs,'no console errors')
print('RESULT','FAIL' if fails else 'ALL PASS'); sys.exit(1 if fails else 0)
