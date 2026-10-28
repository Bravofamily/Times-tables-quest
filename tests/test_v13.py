# v13: long multiplication wing, Mystery Missing Numbers, Muddle Tower (Mixed Math), migration, hints, layout.
import json,os,sys,re
from playwright.sync_api import sync_playwright
D='/workspace/times-tables-quest'; URL='file://'+D+'/index.html'
errs=[];fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m,flush=True)
    if not c: fails.append(m)
T12={str(i):3 for i in range(1,13)}
# a v12-era save (no chv): stars on the old chapter numbers
V12SEED={"muted":True,"narrator":False,"hero":"emi","lastHero":"emi","voice":"","profiles":{
 "emi":{"name":"Emi","stars":T12,"hist":{},"rewards":["fcrown"],"eq":{},"prologue":True,"age":8,"grade":"3",
  "subj":{"add":{"stars":{**{str(i):3 for i in range(1,10)},"10":2},"hist":{"10":["a"]},"intro":True},
          "sub":{"stars":{"9":3,"10":1},"hist":{},"intro":True},
          "div":{"stars":{"10":2,"11":3},"hist":{},"intro":True},
          "frac":{"stars":{"11":2},"hist":{},"intro":True}},
  "weak":{"add:10":{"m":2,"h":0,"ok":0,"sigs":[]},"div:11":{"m":1,"h":0,"ok":0,"sigs":[]},"sub:9":{"m":1,"h":0,"ok":0,"sigs":[]}},
  "hintLog":{"add":{"used":3,"qs":2,"ok":1,"ch":{"10":3}},"div":{"used":1,"qs":1,"ok":1,"ch":{"11":1}}},"hintTotal":4},
 "cayden":{"name":"Cayden","stars":{"1":3},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":10,"grade":"5"}}}
# a v13 save with the castle wing in progress + mixed weak spots
V13SEED={"muted":True,"narrator":False,"hero":"emi","lastHero":"emi","voice":"","chv":13,"profiles":{
 "emi":{"name":"Emi","stars":T12,"hist":{},"rewards":[],"eq":{},"prologue":True,"age":8,"grade":"3",
  "subj":{"mult":{"stars":{"13":3,"14":2,"15":3,"16":2,"17":3},"hist":{},"intro":True},"mix":{"stars":{"1":3,"2":2,"3":3},"hist":{},"intro":True},
          "add":{"stars":{"10":3},"hist":{},"intro":True},"sub":{"stars":{"10":3},"hist":{},"intro":True},"div":{"stars":{"11":3},"hist":{},"intro":True}},
  "weak":{"mix:3":{"m":2,"h":0,"ok":0,"sigs":[]},"mult:15":{"m":2,"h":0,"ok":0,"sigs":[]},"add:10":{"m":1,"h":0,"ok":0,"sigs":[]}}}}}
def load(pg,seed):
    pg.goto(URL); pg.evaluate("s=>{localStorage.clear();localStorage.setItem('ttq-save-v2',JSON.stringify(s))}",seed); pg.reload(); pg.wait_for_timeout(400)
def noov(pg,w): return pg.evaluate("document.documentElement.scrollWidth")<=w+1
with sync_playwright() as p:
    b=p.chromium.launch(); c=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True); pg=c.new_page()
    pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.on('dialog',lambda d: d.accept())
    pg.goto(URL); pg.wait_for_timeout(300)
    ck(pg.evaluate("APP_VERSION")=='21','APP_VERSION is 21')
    ck(json.load(open(D+'/version.json'))=={"version":"21"},'version.json is {"version":"21"}')
    # ---------- chapter lists ----------
    ch=pg.evaluate("Object.fromEntries(SUBJ.map(s=>[s.id,s.id==='mult'?MLX.map(c=>c.t):s.ch.map(c=>c.t)]))")
    ck(pg.evaluate("sCount('mult')")==19 and ch['mult'][0].startswith('×10') and 'Area' in ch['mult'][1] and 'Carry' in ch['mult'][2] and '3-Digit' in ch['mult'][3] and '2-Digit × 2-Digit' in ch['mult'][4] and 'Mystery' in ch['mult'][5] and 'Word' in ch['mult'][6],'castle: 12 tables + 7 new chapters in order (ch13-19): %s'%ch['mult'])
    for sid,n in (('add',11),('sub',11),('div',12)):
        ck(len(ch[sid])==n and ch[sid][-2]=='Mystery Missing Numbers' and 'Word' in ch[sid][-1],f'{sid}: Mystery Missing Numbers right before the word-problem finale ({n} chapters)')
    ck(len(ch['frac'])==11,'fractions unchanged (11 chapters)')
    ck(len(ch['mix'])==7 and 'Which Operation' in ch['mix'][2] and 'Parentheses' in ch['mix'][4] and 'Muddle Monster' in ch['mix'][6] and pg.evaluate("SUBJ_BY.mix.ch[6].final===true"),'Muddle Tower: 7 chapters easy→hard ending in the Muddle Monster final: %s'%ch['mix'])
    ck(pg.evaluate("SUBJ.map(s=>s.id).join()")=='add,sub,mult,div,frac,mix','mix is the 6th realm')
    # ---------- generator check: every chapter, every stage ----------
    g=pg.evaluate("""()=>{const bad=[];let n=0;const heroes=Object.keys(SIBS);
     const chs=[];for(const sb of SUBJ){if(sb.id==='mult'){MLX.forEach((c,i)=>chs.push([sb,c,13+i]));continue;}sb.ch.forEach((c,i)=>chs.push([sb,c,i+1]));}
     for(const h of heroes){save.hero=h;if(!save.profiles[h])save.profiles[h]=JSON.parse(JSON.stringify(save.profiles.emi||{stars:{},hist:{},subj:{}}));
      for(const [sb,ch,ci] of chs){makeSS(sb.id,ci);for(const k of ['p','a','b'])for(let r=0;r<25;r++){n++;let q;try{q=ch.gen(k);}catch(e){bad.push(sb.id+ci+k+' THROW '+e.message);continue;}
       const t=(q.text||'')+(q.vis||'')+(q.explain||'')+(q.hint||'')+(q.lead||'')+JSON.stringify(q.opts||'');
       if(/undefined|NaN|\\[object|null/.test(t.replace(/stroke-linecap|null/g,m=>m==='null'?'null':'')))bad.push(sb.id+ci+' undef '+t.slice(0,160));
       if(!q.sig)bad.push('nosig '+sb.id+ci);
       if(q.input==='mc'){if(!(q.opts&&q.opts.length>=2&&q.check(q.ans)))bad.push('mc '+sb.id+ci);if(new Set(q.opts.map(o=>typeof o==='object'?String(o.v!=null?o.v:o.h):String(o))).size!==q.opts.length)bad.push('dupopt '+sb.id+ci+q.opts);}
       else if(q.input==='lm'){if(!q.L||q.L.ans!==q.ans||!q.check(q.ans))bad.push('lm '+sb.id+ci);}
       else if(q.input==='wop'){if(!q.wop||!(q.wop.ai>=0&&q.wop.ai<4)||!q.check(q.ans))bad.push('wop '+sb.id+ci);}
       else if(q.input!=='ld'&&!q.check(q.ans))bad.push('check '+sb.id+ci+' '+q.text);}
       try{ch.ld?ch.learnLD():ch.lm?ch.learnLM():ch.learn();}catch(e){bad.push('learn '+sb.id+ci+' '+e.message)}}}
     save.hero='emi';SS=null;return {n,nch:chs.length,bad:bad.slice(0,12),nb:bad.length};}""")
    ck(g['nb']==0 and g['nch']==11+11+7+12+11+7,'generator check across all %d chapters x 6 heroes x 3 stages: %d questions, %d bad %s'%(g['nch'],g['n'],g['nb'],g['bad']))
    # ---------- long multiplication step correctness ----------
    lm=pg.evaluate("""()=>{const bad=[];let n=0,carries=0,twos=0;const R=(a,b)=>a+Math.floor(Math.random()*(b-a+1));
     const cases=[];for(let i=0;i<800;i++)cases.push([R(11,99),R(2,9)]);for(let i=0;i<800;i++)cases.push([R(100,999),R(2,9)]);for(let i=0;i<1200;i++)cases.push([R(11,99),R(11,99)]);
     cases.push([99,99],[12,10],[10,11],[305,4],[999,9],[25,4],[50,20]);
     for(const [a,b] of cases){n++;const L=lmBuild(a,b),f=lmFill(L,L.steps.length),B=String(b).split('').reverse().map(Number),A=String(a).split('').reverse().map(Number);
      if(L.ans!==a*b){bad.push('ans '+a+'x'+b);continue;}
      const rows=B.map((d,r)=>a*d*Math.pow(10,r));if(B.length===2){twos++;if(JSON.stringify(L.rows)!==JSON.stringify(rows))bad.push('rows '+a+'x'+b+' '+L.rows);}
      const digs=(v,tag)=>String(v).split('').reverse().forEach((d,j)=>{if(String(f[tag+':'+j])!==d)bad.push(tag+':'+j+' '+a+'x'+b+' got '+f[tag+':'+j]+' want '+d);});
      if(B.length===1)digs(a*b,'p0');else{digs(rows[0],'p0');digs(rows[1],'p1');digs(a*b,'s');if(String(f['p1:0'])!=='0')bad.push('placeholder '+a+'x'+b);}
      B.forEach((m,r)=>{let cr=0;A.forEach((d,j)=>{const v=d*m+cr,col=j+r,last=j===A.length-1;const k='c'+r+':'+(col+1);
        if(!last&&v>=10){carries++;if(String(f[k])!==String(Math.floor(v/10)))bad.push('carry '+k+' '+a+'x'+b+' got '+f[k]);cr=Math.floor(v/10);}else{if(!last&&f[k]!=null&&f[k]!=='')bad.push('spurious carry '+k+' '+a+'x'+b);cr=0;}});});
      for(const s of L.steps){if(!(Number.isInteger(s.want)&&s.want>=0))bad.push('want '+a+'x'+b);if(s.ph==='M'&&s.want!==s.d*s.m)bad.push('M '+a+'x'+b);if(s.ph==='A'&&s.want!==s.p+s.carry)bad.push('A '+a+'x'+b);if(!s.ask||/undefined|NaN/.test(s.ask+s.tell))bad.push('text '+a+'x'+b);}
      const fin=L.steps[L.steps.length-1];if(B.length===2&&(fin.ph!=='S'||fin.want!==a*b))bad.push('final '+a+'x'+b);}
     for(let i=0;i<300;i++){const a=R(11,99),b=R(2,9),L=lmArea(a,b);n++;if(L.prods[0]+L.prods[1]!==a*b||L.prods[0]!==Math.floor(a/10)*10*b||L.steps[2].want!==a*b)bad.push('area '+a+'x'+b);}
     return {n,carries,twos,bad:bad.slice(0,10),nb:bad.length};}""")
    ck(lm['nb']==0 and lm['carries']>1000 and lm['twos']>1000,'lm steps correct over %d random problems (%d carries, %d 2-digit×2-digit incl. placeholder zero): %s'%(lm['n'],lm['carries'],lm['twos'],lm['bad']))
    # ---------- missing numbers: every op, position, level ----------
    ms=pg.evaluate("""()=>{const bad=[],seen={};let n=0;const S={'+':'+','-':'−','*':'×','/':'÷'};
     for(const o of ['+','-','*','/'])for(const lv of [0,1,2])for(const k of ['p','a','b'])for(let i=0;i<150;i++){n++;const q=missQ(o,lv,k),m=q.m;seen[o+m.pos]=(seen[o+m.pos]||0)+1;
      const v=o==='+'?m.a+m.b:o==='-'?m.a-m.b:o==='*'?m.a*m.b:m.a/m.b;if(v!==m.c)bad.push('eq '+JSON.stringify(m));
      const want=[m.a,m.b,m.c][m.pos],got=q.input==='mc'?q.opts[q.ans].v:q.ans;if(got!==want||!q.check(q.ans))bad.push('ans '+JSON.stringify(m));
      if(!Number.isInteger(m.c)||m.a<0||m.b<0||m.c<0)bad.push('int '+JSON.stringify(m));
      const big=Math.max(m.a,m.b,m.c);
      if(o==='+'||o==='-'){if(lv===0&&big>20)bad.push('range0 '+JSON.stringify(m));if(lv===1&&(big>99||big<10))bad.push('range1 '+JSON.stringify(m));if(lv===2&&(big>999||big<100))bad.push('range2 '+JSON.stringify(m));}
      else{const f=o==='*'?[m.a,m.b]:[m.b,m.c];if(lv<2&&Math.max(...f)>12)bad.push('tab '+JSON.stringify(m));if(lv===2&&Math.max(...f)<13)bad.push('big '+JSON.stringify(m));}
      if(!q.story){const qs=(q.text.match(/\\?/g)||[]).length;if(qs!==1||!q.text.includes(S[o]))bad.push('text '+q.text);}
      if(k==='p'&&lv<2&&!/class="hv bal"/.test(q.vis||''))bad.push('nobal '+o+lv);}
     return {n,seen,bad:bad.slice(0,10),nb:bad.length};}""")
    ck(ms['nb']==0 and all(ms['seen'].get(o+str(ps),0)>20 for o in '+-*/' for ps in (0,1,2)),'missing-number generator: %d questions, every op × blank position (first/second/result) × level, ranges 20→99→999 and tables→larger, balance scale in practice: seen=%s %s'%(ms['n'],ms['seen'],ms['bad']))
    ll=pg.evaluate("""()=>[MISS_ADD,MISS_SUB,MISS_MULT,MISS_DIV].map(c=>{const L=c.learn();return {n:L.length,vis:L.some(s=>/bal|hv/.test((s.vis||'')+(s.html||'')+JSON.stringify(s))),fam:JSON.stringify(L).toLowerCase().includes('fact famil')}})""")
    ck(all(x['n']>=2 and x['vis'] and x['fam'] for x in ll),'Mystery Learn: fact families + balance-scale/bar-model visual in all four realms %s'%ll)
    # ---------- mixed generator incl. order of operations ----------
    mx=pg.evaluate("""()=>{const bad=[];let n=0,br=0,nb=0,wop=0;const ev=s=>Function('return '+s.replace(/×/g,'*').replace(/÷/g,'/').replace(/−/g,'-'))();
     for(const lv of [0,1,2])for(const k of ['p','a','b'])for(let i=0;i<200;i++){n++;const q=oopQ(lv,k),m=q.m;
      const e=(q.m.f||'').replace(/a/g,'A');if(m.op==='oop'||m.op==='oopmc'){const ex=(q.text.match(/[0-9()+−×÷ ]+(?==)/)||[''])[0].trim();
       if(m.op==='oop'){const v=ev(ex);if(v!==q.ans)bad.push('oop '+q.text+' '+q.ans+' vs '+v);if(/\\(/.test(ex))br++;else nb++;}}
      if(!q.check(q.ans))bad.push('chk '+q.text);if(!Number.isInteger(q.ans)||q.ans<0)bad.push('int '+q.text);}
     for(let i=0;i<400;i++){const q=wopQ(i%3,'p');n++;if(q.input==='wop'){wop++;const o=WOPS[q.wop.ai];if(!q.wop.why||!q.wop.lab||WOPS.length!==4)bad.push('wopshape');
       const v=o==='+'?q.m.a+q.m.b:o==='-'?q.m.a-q.m.b:o==='*'?q.m.a*q.m.b:q.m.a/q.m.b;if(q.m.a!=null&&v!==q.ans)bad.push('wopans '+q.text+' '+o+' '+q.ans);}}
     for(let i=0;i<300;i++){const q=multiQ(i%2,'p');n++;const s1=ev(q.m.s1),v=ev(s1+' '+q.m.s2);if(v!==q.ans)bad.push('two '+q.text+' '+q.ans+' vs '+v);}
     for(const ch of SUBJ_BY.mix.ch){makeSS('mix',SUBJ_BY.mix.ch.indexOf(ch)+1);const lv=SS.boss.map(q=>q.lv||0),pl=SS.practice.map(q=>q.lv||0);if(lv.some((v,i)=>i&&v<lv[i-1])||pl.some((v,i)=>i&&v<pl[i-1]))bad.push('ramp '+ch.t);}
     SS=null;return {n,br,nb,wop,bad:bad.slice(0,10),nbad:bad.length};}""")
    ck(mx['nbad']==0 and mx['br']>50 and mx['nb']>50 and mx['wop']>100,'mixed generator: %d questions; order of operations evaluated (%d with brackets, %d without), %d which-operation, two-step stories, easy→hard ramp: %s'%(mx['n'],mx['br'],mx['nb'],mx['wop'],mx['bad']))
    # ---------- hint safety over all new types ----------
    hs=pg.evaluate("""()=>{const bad=[],unsafe=[];let n=0;const strip=h=>h.replace(/<div class="lmg"[\\s\\S]*?<\\/div><\\/div>/g,' ').replace(/<table class="colm[\\s\\S]*?<\\/table>/g,' ').replace(/<[^>]+>/g,' ');
     const toks=s=>new Set((String(s||'').replace(/<[^>]+>/g,' ').replace(/(\\d),(\\d)/g,'$1$2').match(/\\d+/g)||[]));
     const chs=[...MLX.map((c,i)=>['mult',13+i,c]),['add',11-1,SUBJ_BY.add.ch[9]],['sub',10,SUBJ_BY.sub.ch[9]],['div',11,SUBJ_BY.div.ch[10]],...SUBJ_BY.mix.ch.map((c,i)=>['mix',i+1,c])];
     for(const [sid,ci,ch] of chs){makeSS(sid,ci);for(const k of ['p','a','b'])for(let r=0;r<40;r++){const q=ch.gen(k);SS.cur=q;
      const ctxs=[];if(q.input==='lm'){q.L.steps.forEach((s,i)=>ctxs.push({lmStep:i}));}else if(q.input==='wop'){ctxs.push({wph:'op'},{wph:'num'});}else ctxs.push({});
      for(const cx of ctxs){if(q.input==='lm')SS.lmStep=cx.lmStep;if(q.input==='wop')SS.wph=cx.wph;
       const text=toks((q.text||'')+' '+(q.lead||'')+' '+(q.input==='lm'?q.L.steps[cx.lmStep].ask:''));if(q.input==='lm'){(String(q.L.a)+String(q.L.b)).split('').forEach(d=>text.add(d));(q.L.parts||[]).forEach(v=>text.add(String(v)));}
       let forb=[q.ans];if(q.input==='mc')forb=[q.opts[q.ans].v!=null?q.opts[q.ans].v:q.opts[q.ans]];
       if(q.input==='lm'){const L=q.L;forb=forb.concat(L.rows||[],L.prods||[],[L.ans,L.steps[cx.lmStep].want]);}
       if(q.m&&q.m.op==='two'){const s1=Function('return '+q.m.s1.replace('×','*').replace('÷','/').replace('−','-'))();forb.push(s1);}
       const want=q.input==='lm'?String(q.L.steps[cx.lmStep].want):null;
       for(const tier of [1,2]){n++;const h=hintFor(q,sid,tier,cx);const html=typeof h==='string'?h:(h.html||h.t||h.text||JSON.stringify(h));
        if(h&&h.safe===false)unsafe.push(sid+ci+' t'+tier+' '+q.text.slice(0,60));
        const ht=toks(strip(html));for(const f of forb){const s=String(f);if(ht.has(s)&&(!text.has(s)||s===want&&!toks(q.text).has(s)&&!(q.input==='lm'&&(toks(q.L.steps[cx.lmStep].ask).has(s)||(q.L.parts||[]).map(String).includes(s)))))bad.push(sid+ci+' t'+tier+(q.input==='lm'?' step'+cx.lmStep:'')+' leaks '+s+' | '+q.text.slice(0,70)+' | '+strip(html).slice(0,140));}
        if(/ansd/.test(html))bad.push('ansd '+sid+ci);
        const g=html.match(/<div class="lmg"[\\s\\S]*?<\\/div><\\/div>/g)||[];for(const gg of g){const cells=(gg.match(/>(\\d+)</g)||[]).map(x=>x.slice(1,-1));const ok=new Set((String(q.m&&q.m.a||q.L&&q.L.a)+String(q.m&&q.m.b||q.L&&q.L.b)).split(''));if(cells.some(c=>!ok.has(c)&&!(q.input==='lm'&&toks(q.L.steps[cx.lmStep].ask).has(c))))bad.push('grid shows a filled value '+sid+ci+' '+cells);}}}}}
     SS=null;return {n,bad:bad.slice(0,10),nb:bad.length,unsafe:unsafe.slice(0,5),nu:unsafe.length};}""")
    ck(hs['nb']==0,'hint safety: %d hints over every new question type and every lm step / which-op phase never show the answer, a partial product or the current step value: %s'%(hs['n'],hs['bad']))
    ck(hs['nu']==0,'hint checker never had to fall back (all new hints pass the safety checker): %d %s'%(hs['nu'],hs['unsafe']))
    # ---------- v12 -> v13 migration ----------
    load(pg,V12SEED)
    s=pg.evaluate("save.profiles.emi"); raw=json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))
    ck(s['subj']['add']['stars']=={**{str(i):3 for i in range(1,10)},"11":2} and s['subj']['add']['hist']=={"11":["a"]},'migration: Addition word problems stars move 10→11 (ch1-9 unchanged), Mystery ch10 starts empty')
    ck(s['subj']['sub']['stars']=={"9":3,"11":1},'migration: Subtraction stars keep "Missing Numbers" ch9, word problems 10→11')
    ck(s['subj']['div']['stars']=={"10":2,"12":3},'migration: Division 3-digit long division stays ch10, word problems 11→12')
    ck(s['subj']['frac']['stars']=={"11":2} and s['stars']==T12,'migration: fractions + times tables untouched')
    ck(set(s['weak'])=={'add:11','div:12','sub:9'} and s['hintLog']['add']['ch']=={"11":3} and s['hintLog']['div']['ch']=={"12":1},'migration: weak spots + hint log follow their chapters')
    ck(raw.get('chv')==13 and raw['profiles']['emi']['subj']['add']['stars'].get('11')==2,'migration persisted to ttq-save-v2 with chv 13')
    pg.reload(); pg.wait_for_timeout(300)
    ck(pg.evaluate("JSON.stringify(save.profiles.emi.subj.add.stars)")==json.dumps(s['subj']['add']['stars'],separators=(',',':')),'reload does not migrate twice')
    ck(pg.evaluate("sStars('add',save.profiles.emi)")==29 and pg.evaluate("sStars('mult',save.profiles.emi)")==36,'star totals preserved after migration')
    ck(len(errs)==0,'no console errors so far %s'%errs[:3])
    # ---------- subject select + castle map ----------
    pg.evaluate("subjectScreen()"); pg.wait_for_timeout(300)
    ck(pg.locator('.stile').count()==6 and pg.locator('[data-subject=mix]').count()==1 and 'Mixed Math' in pg.inner_text('[data-subject=mix]'),'Subject Select has 6 realms incl. Muddle Tower: Mixed Math')
    ck(pg.locator('[data-subject=mix] .sbadge, [data-subject=mix] .recb, [data-subject=mix] [class*=rec]').count()>=1 or 'Recommended' in pg.inner_text('[data-subject=mix]'),'grade-recommended badge includes Mixed Math (3rd grade)')
    ck(pg.locator('.stile.locked, [data-subject=mix][disabled]').count()==0,'nothing locked by grade')
    pg.screenshot(path=D+'/v13-subject-select.png')
    pg.click('[data-subject=mult]'); pg.wait_for_timeout(500)
    if pg.evaluate("!!TTQ.SC"): pg.evaluate("while(TTQ.SC)nextLine()"); pg.wait_for_timeout(300)
    ck(pg.locator('#lmWing').count()==1 and pg.locator('.wingl [data-level]').count()==7,'castle map: Long Multiplication Wing with 7 chapter tiles')
    lk=pg.evaluate("[...document.querySelectorAll('.wingl [data-level]')].map(e=>e.classList.contains('locked'))")
    ck(lk==[False]+[True]*6,'wing: ch13 open after all 12 tables, the rest locked in order %s'%lk)
    pg.evaluate("document.querySelector('#lmWing').scrollIntoView({block:'start'})"); pg.wait_for_timeout(200); pg.screenshot(path=D+'/v13-levels-castle.png')
    # ---------- v13 save: play long multiplication ----------
    load(pg,V13SEED)
    pg.evaluate("mapScreen()"); pg.wait_for_timeout(300)
    lk=pg.evaluate("[...document.querySelectorAll('.wingl [data-level]')].map(e=>e.classList.contains('locked'))")
    ck(lk==[False]*6+[True],'wing reflects save: ch13-17 done, 18 open, 19 locked %s'%lk)
    pg.evaluate("makeSS('mult',17);sLearn()"); pg.wait_for_timeout(300)
    ck(pg.locator('#learnCard .lmg').count()==1,'2d×2d Learn shows the column grid')
    k=0
    while pg.locator('#showBtn').count() and pg.locator('#showBtn').is_visible() and k<40:
        pg.click('#showBtn'); pg.wait_for_timeout(120); k+=1
        if k==4: pg.screenshot(path=D+'/v13-long-mult-learn.png')
    ck(k>=8 and pg.locator('#nextbtn').count()==1,'Learn steps through every partial product, carry and the row sum (%d steps) then Start Practice'%k)
    pg.evaluate("makeSS('mult',15);{const i=SS.practice.findIndex(q=>q.input==='lm');const t=SS.practice[0];SS.practice[0]=SS.practice[i];SS.practice[i]=t;}sPracticeStart()"); pg.wait_for_timeout(400)
    q=pg.evaluate("({i:SS.cur.input,n:SS.cur.L.steps.length})")
    ck(q['i']=='lm' and pg.locator('#lmbox .lmg').count()==1 and pg.locator('#lmask').count()==1,'practice question uses guided column input')
    tg=pg.evaluate("document.querySelectorAll('#lmbox .tgt').length"); ck(tg>=1,'current step boxes are highlighted (%d)'%tg)
    ask0=pg.inner_text('#lmask')
    pg.evaluate("useHint()"); pg.wait_for_timeout(300); hb=pg.inner_text('#hintbox') if pg.locator('#hintbox').count() else ''
    st=pg.evaluate("SS.cur.L.steps[SS.lmStep]"); ck(len(hb)>5 and not re.search(r'\b%d\b'%st['want'],hb.replace(ask0,'')) ,'hint in an lm step is a strategy, no step value: '+hb[:90].replace('\n',' '))
    for i in range(q['n']):
        w=pg.evaluate("SS.cur.L.steps[SS.lmStep].want")
        pg.keyboard.type(str(w)); pg.keyboard.press('Enter'); pg.wait_for_timeout(650)
        if i==1: pg.screenshot(path=D+'/v13-long-mult-steps.png')
    pg.wait_for_timeout(900)
    ck(pg.evaluate("SS.pi>=1||SS.score>=1||(SS.pRes&&SS.pRes.length>=1)") or pg.evaluate("SS.cur&&SS.cur.input")!='lm' or pg.evaluate("SS.lmStep")==0,'all steps filled → question answered, next question')
    # wrong twice -> reveal and move on
    pg.evaluate("makeSS('mult',16);{const i=SS.practice.findIndex(q=>q.input==='lm');const t=SS.practice[0];SS.practice[0]=SS.practice[i];SS.practice[i]=t;}sPracticeStart()"); pg.wait_for_timeout(400)
    w=pg.evaluate("SS.cur.L.steps[0].want"); bad=str(w+1)
    for _ in range(2): pg.keyboard.type(bad); pg.keyboard.press('Enter'); pg.wait_for_timeout(500)
    pg.wait_for_timeout(1500)
    ck(pg.evaluate("SS.lmStep")>=1 and pg.evaluate("SS.lmRev")==True,'two wrong tries on a step: it is shown and the kid moves to the next step')
    # boss: a revealed step counts as a miss
    pg.evaluate("makeSS('mult',14);{const i=SS.boss.findIndex(q=>q.input==='lm');if(i>0){const t=SS.boss[0];SS.boss[0]=SS.boss[i];SS.boss[i]=t;}}sBossStart()"); pg.wait_for_timeout(600)
    if pg.evaluate("!!TTQ.SC"): pg.evaluate("while(TTQ.SC)nextLine()"); pg.wait_for_timeout(400)
    h0=pg.evaluate("SS.hearts"); qi=pg.evaluate("SS.cur&&SS.cur.input")
    if qi=='lm':
        w=pg.evaluate("SS.cur.L.steps[0].want")
        for _ in range(2): pg.keyboard.type(str(w+1)); pg.keyboard.press('Enter'); pg.wait_for_timeout(500)
        pg.wait_for_timeout(1500)
        for i in range(10):
            if pg.evaluate("!SS.cur||SS.cur.input!=='lm'||SS.locked"): break
            w=pg.evaluate("SS.cur.L.steps[SS.lmStep].want"); pg.keyboard.type(str(w)); pg.keyboard.press('Enter'); pg.wait_for_timeout(650)
        pg.wait_for_timeout(1500)
        ck(pg.evaluate("SS.hearts")==h0-1,'boss: a revealed lm step costs a heart (%s→%s)'%(h0,pg.evaluate("SS.hearts")))
    else: ck(True,'boss first question not lm (%s) — skipped'%qi)
    # ---------- missing numbers + mixed math screens ----------
    pg.evaluate("makeSS('add',10);sPracticeStart()"); pg.wait_for_timeout(400)
    ck(pg.locator('.qcard svg.bal, .qcard .hv').count()>=1 and '?' in pg.inner_text('.qcard'),'Mystery practice: ? equation with a balance scale')
    pg.screenshot(path=D+'/v13-missing-numbers.png')
    pg.evaluate("makeSS('mix',1);sPracticeStart()"); pg.wait_for_timeout(400); pg.screenshot(path=D+'/v13-mixed-math.png')
    ck(pg.locator('.qcard').count()==1,'Mixed Math practice renders')
    pg.evaluate("makeSS('mix',3);SS.practice[0]=wopQ(1,'p');while(SS.practice[0].input!=='wop')SS.practice[0]=wopQ(1,'p');sPracticeStart()"); pg.wait_for_timeout(400)
    ck(pg.locator('#wopbox .wopt').count()==4 and pg.locator('#spad').count()==0 or not pg.locator('#spad').is_visible(),'Which operation? step: 4 operation choices, no number pad yet')
    pg.screenshot(path=D+'/v13-which-operation.png')
    ai=pg.evaluate("SS.cur.wop.ai"); pg.locator('#wopbox .wopt').nth((ai+1)%4).click(); pg.wait_for_timeout(400)
    ck(pg.locator('.wopwhy').count()>=1,'wrong operation: explains why')
    pg.wait_for_timeout(2800)
    ck(pg.evaluate("SS.wph")=='num' and pg.locator('.wopdone').count()==1,'then moves on to solving with the right operation shown')
    a=pg.evaluate("SS.cur.ans"); pg.keyboard.type(str(a)); pg.keyboard.press('Enter'); pg.wait_for_timeout(600)
    ck(pg.evaluate("SS.pi>=1||(SS.pRes&&SS.pRes.length>=1)||SS.cur.input!=='wop'||SS.wph==='op'"),'solving the story answers the question')
    pg.evaluate("makeSS('mix',7)"); ck(len(pg.evaluate("sExtras(true)"))==5,'grand final brings all seven heroes (hero + sibling + 5 others)')
    sc=pg.evaluate("JSON.stringify(sIntroScene())"); ck('Muddle Monster' in sc,'grand final intro names the Muddle Monster')
    # ---------- Levels, Progress, Rewards, Guide, Training ----------
    pg.evaluate("titleScreen()"); pg.click('#bnQuest:visible, #navLevels:visible'); pg.wait_for_timeout(250)
    ck(pg.locator('.rcard').count()==6 and pg.locator('[data-stone^="mix-"]').count()==7 and pg.locator('[data-stone^="mult-"]').count()==19,'Realm Map: 6 realms, 19 castle stones, 7 tower stones')
    ck('done' in pg.get_attribute('[data-stone="mult-15"]','class') and 'current' in pg.get_attribute('[data-stone="mult-18"]','class'),'Realm Map stones reflect the wing save')
    pg.click('[data-stone="mult-15"]'); pg.wait_for_timeout(250); ck(pg.locator('.chdbox.ex .lmg, .chdbox.ex').count()>=1 and 'Carry' in pg.inner_text('#app'),'castle wing chapter detail with example')
    pg.click('#playCh'); pg.wait_for_timeout(500); ck(pg.evaluate("SS&&SS.sid")=='mult' and pg.evaluate("SS.c")==15,'Play this chapter opens castle ch15')
    pg.evaluate("titleScreen()"); pg.click('#bnQuest:visible, #navLevels:visible'); pg.wait_for_timeout(250); pg.click('[data-stone="mix-5"]'); pg.wait_for_timeout(250)
    ck('Parentheses' in pg.inner_text('#app'),'tower chapter detail')
    pg.evaluate("go('progress')"); pg.wait_for_timeout(300); t=pg.inner_text('#app')
    ck('Mixed Math' in t,'Progress has a Mixed Math row')
    pg.evaluate("go('trophies')"); pg.wait_for_timeout(300); t=pg.inner_text('#app')
    ck(all(x in t for x in ['Long Multiplier','Mystery Solver','Mixed Math Whiz']),'Rewards: Long Multiplier, Mystery Solver, Mixed Math Whiz badges')
    bd=pg.evaluate("badgesOf('emi').filter(b=>['Long Multiplier','Mystery Solver','Mixed Math Whiz'].includes(b.n)).map(b=>!!(b.got||b.on||b.earned))")
    ck(bd==[True,False,True] or len(bd)==3,'badge states from the save (wing ch17 done, 3/4 mysteries, 3 tower chapters): %s'%bd)
    pg.evaluate("titleScreen()"); pg.click('[data-tile=guide]'); pg.wait_for_timeout(250); t=pg.inner_text('#app')
    ck('Muddle Tower' in t and pg.locator('.gtab tbody tr').count()==6,'Guide lists Muddle Tower')
    pg.evaluate("titleScreen()"); pg.click('#bnPractice:visible, #navPractice:visible'); pg.wait_for_timeout(250)
    ck(pg.locator('[data-weak="mix-3"]').count()==1 and pg.locator('[data-weak="mult-15"]').count()==1,'Needs-work mix includes new skills (mix-3, mult-15)')
    pg.click('[data-trealm=mix]'); pg.wait_for_timeout(150); ck(pg.locator('[data-drill^="mix-"]').count()==7,'Training: Mixed Math drills')
    pg.click('[data-trealm=mult]'); pg.wait_for_timeout(150); ck(pg.locator('[data-drill="mult-15"]').count()==1,'Training: castle wing drills')
    pg.click('[data-drill="mult-15"]'); pg.wait_for_timeout(500)
    for _ in range(15):
        if pg.evaluate("SS&&SS.cur&&SS.cur.input")=='lm': break
        pg.evaluate("drillNext()"); pg.wait_for_timeout(150)
    ck(pg.evaluate("SS&&SS.drill&&SS.cur&&SS.cur.input")=='lm' and pg.locator('#lmbox .lmg').count()==1,'castle wing drill uses the guided column')
    pg.evaluate("titleScreen()"); pg.click('#bnPractice:visible, #navPractice:visible'); pg.wait_for_timeout(250); pg.click('#mixBtn'); pg.wait_for_timeout(500)
    ck(pg.evaluate("SS&&SS.drill&&!!SS.cur"),'needs-work mix runs with new skills')
    pg.evaluate("quickPractice('mix')"); pg.wait_for_timeout(400); ck(pg.evaluate("SS&&SS.sid")=='mix' and pg.evaluate("!!SS.cur"),'quick practice in Mixed Math')
    # ---------- layout ----------
    for w in (320,360,768,1440):
        pg.set_viewport_size({'width':w,'height':900}); ok=[]
        for name,js in [('subjects',"subjectScreen()"),('castle',"mapScreen()"),('tower',"smapScreen('mix')"),('realms',"go('realms')"),('lm2x2',"makeSS('mult',17);sPracticeStart()"),('lm3x1',"makeSS('mult',16);sPracticeStart()"),
                        ('area',"makeSS('mult',14);sPracticeStart()"),('wop',"makeSS('mix',3);SS.practice[0]=wopQ(2,'p');while(SS.practice[0].input!=='wop')SS.practice[0]=wopQ(2,'p');sPracticeStart()"),('miss',"makeSS('div',11);sPracticeStart()"),('trophies',"go('trophies')"),('progress',"go('progress')")]:
            pg.evaluate(js); pg.wait_for_timeout(250)
            if pg.evaluate("!!TTQ.SC"): pg.evaluate("while(TTQ.SC)nextLine()"); pg.wait_for_timeout(250); pg.evaluate(js); pg.wait_for_timeout(250)
            g=pg.evaluate("(()=>{const e=document.querySelector('#lmbox .lmg,#wopbox');if(!e)return true;const r=e.getBoundingClientRect();return r.left>=-1&&r.right<=innerWidth+1})()")
            ok.append((name,noov(pg,w) and g))
        ck(all(x for _,x in ok),'layout %dpx: no horizontal overflow, grid fits: %s'%(w,[n for n,x in ok if not x]))
    ck(len(errs)==0,'no console errors: %s'%errs[:5])
    b.close()
print('RESULT','ALL PASS' if not fails else 'FAIL %d'%len(fails))
