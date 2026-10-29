# v24: free "Example" button next to the guide lanterns on every question screen.
# Usage: PWB=chromium|webkit python test_v24.py   (SHOTS=1 -> /workspace/v24shots)
import os,json,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))));BR=os.environ.get('PWB','chromium');SH=os.environ.get('SHOTS')=='1'
OUT='/workspace/v24shots';os.makedirs(OUT,exist_ok=True)
PORT=8852 if BR=='chromium' else 8853
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
BASE=f'http://localhost:{PORT}/index.html'
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c: fails.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
ck("const APP_VERSION='24'" in html and json.load(open(os.path.join(D,'version.json')))['version']=='24','version 24')
ALL={str(i):3 for i in range(1,13)}
def prof():
    subj={s:{"stars":{str(i):3 for i in range(1,20)},"hist":{},"intro":True} for s in ['add','sub','mult','div','frac','mix']}
    return {"name":"Emi","stars":ALL,"hist":{},"rewards":["fcrown"],"eq":{},"prologue":True,"age":"8-10","grade":"3","subj":subj}
SAVE={"muted":True,"narrator":False,"lastHero":"emi","hero":"emi","profiles":{"emi":prof()}}
STATE="JSON.stringify({s:localStorage.getItem('ttq-save-v2')})"
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    def page(w=1280,h=900,mob=False):
        kw=dict(viewport={'width':w,'height':h},service_workers='block')
        if mob: kw.update(has_touch=True,**({'is_mobile':True,'device_scale_factor':2} if BR=='chromium' else {}))
        c=b.new_context(**kw);c.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('ttq-save-v2',%s);}"%json.dumps(json.dumps(SAVE)))
        pg=c.new_page();pg.on('console',lambda x: errs.append(x.text) if x.type=='error' else None);pg.on('pageerror',lambda e: errs.append('PAGEERR '+str(e)))
        pg.goto(BASE);pg.wait_for_timeout(1300);return c,pg
    # ---- 1. generator check over every chapter / stage, plus times tables ----
    c,pg=page()
    r=pg.evaluate("""(()=>{const bad=[],seen={},rec=[];let n=0;const R=(q,ex,src)=>rec.push([src,exPlain(q.text),String(exAnsKey(q)),exPlain(ex.q.text),String(exAnsKey(ex.q)),exFmt(q),exFmt(ex.q),q.type||'',(q.m&&q.m.op)||'',(q.m&&q.m.pos!=null)?1:0,(ex.q.m&&ex.q.m.op)||'',ex.q.n||0,q.n||0]);const chs=[];SUBJ.forEach(sb=>sb.ch.forEach((ch,i)=>ch&&chs.push([sb.id,i+1,ch,sb])));MLX.forEach((ch,i)=>chs.push(['mult',ORDER.length+1+i,ch,SUBJ_BY.mult]));
     const neg=t=>/(^|[\\s(=])-\\d/.test(t.replace(/<[^>]*>/g,' '));
     for(const [sid,c,ch,sb] of chs)for(let i=0;i<15;i++){SS={sid,c,ch,sb,attempt:1,team:SIBS.emi[0],inBoss:i%3==0};const q=ch.gen(i%3==0?'b':'p');SS.cur=q;EX.last=[];const ex=exMake();n++;seen[(q.m&&q.m.op)||q.input]=1;
      if(!ex){bad.push('null '+sid+c+' '+q.text.slice(0,40));continue;}const t=ex.st.join(' ')+' '+ex.q.text+' '+(ex.q.explain||'');
      R(q,ex,sid+c);if(exSig(ex.q)===exSig(q)||exAnsKey(ex.q)===exAnsKey(q)||exFmt(ex.q)!==exFmt(q)||exNums(exSig(ex.q))===exNums(exSig(q))||/NaN|undefined|Infinity/.test(t)||neg(t))bad.push(sid+c+': '+q.text.slice(0,30)+' => '+ex.q.text.slice(0,30));}
     SS=null;for(const n0 of ORDER)for(const ty of ['fill','mc','missing','story','array'])for(let k=1;k<=12;k++){S={n:n0,inBoss:k%2==0};S.cur=makeQ(ty,n0,k,CTX[0]);EX.last=[];const ex=exMake();n++;if(ex)R(S.cur,ex,'tt'+n0+ty+k);
      if(!ex||ex.q.type!==ty||ex.q.n!==n0&&false||ex.q.text===S.cur.text||exAnsKey(ex.q)===exAnsKey(S.cur)||/NaN|undefined/.test(ex.st.join(' ')))bad.push('tt '+n0+ty+k);}
     S=null;return {rec,n,bad:bad.slice(0,10),nb:bad.length,ops:Object.keys(seen).length}})()""")
    ck(r['nb']==0,'example is a different problem of the same type/format with a different answer, no NaN/negatives (%d samples, %d ops): %s'%(r['n'],r['ops'],r['bad']))

    import re
    from fractions import Fraction
    def nums(t): return [float(x) for x in re.findall(r'\d+(?:\.\d+)?',t)]
    def fracs(t): return [Fraction(int(a),int(b)) for a,b in re.findall(r'(\d+)\s*/\s*(\d+)',t) if int(b)]
    def aval(k,txt,op):
        n=re.findall(r'\d+(?:\.\d+)?',k)
        if len(n)==1: return ('one',float(n[0]))
        if len(n)==2 and ('fr' in op or '/' in txt) and int(float(n[1])): return ('fr',Fraction(int(float(n[0])),int(float(n[1]))))
        return ('key',k)
    leak=[];fmtbad=[];offtable=0
    for src,qt,qa,et,ea,fq,fe,ty,op,pos,eop,en,qn in r['rec']:
        why=''
        A=aval(qa,qt,op);B=aval(ea,et,eop)
        cur=set(nums(qt))|set(float(x) for x in fracs(qt))
        if A[0]!='key': cur.add(float(A[1]))
        if len(nums(qt))>1 and sorted(nums(qt))==sorted(nums(et)): why='same operands'
        elif fracs(qt) and sorted(fracs(qt))==sorted(fracs(et)): why='same fraction values'
        elif A==B or (A[0]=='key' and B[0]=='key' and sorted(nums(A[1]))==sorted(nums(B[1]))): why='same answer'
        elif B[0]!='key' and float(B[1]) in cur: why='example answer is a number from the current problem'
        miss=ty=='missing' or 'miss' in op or pos or ('?' in qt and '=' in qt and not re.search(r'=\s*\?\s*\.?$',qt))
        if not why and miss and A[0]=='one' and A[1] in nums(et): why='current answer appears as an operand'
        if not why and miss and A[0]=='fr' and A[1] in fracs(et): why='current answer appears as an operand'
        if why: leak.append(f'{src}: {qt[:30]} [{qa}] => {et[:30]} [{ea}] ({why})')
        emiss='?' in et and '=' in et and not re.search(r'=\s*\?\s*\.?$',et)
        if fq!=fe or (src.startswith('tt') and ty=='missing' and not emiss): fmtbad.append(f'{src}: {qt[:30]} => {et[:30]}')
        if src.startswith('tt') and en!=qn: offtable+=1
    ck(not leak,'(a) no example gives the current answer away (%d samples): %s'%(len(r['rec']),leak[:8]))
    ck(not fmtbad,'(b) every example keeps the format; missing-number gets missing-number: %s'%fmtbad[:8])
    print('INFO times-table examples that left the chapter table:',offtable)
    # ---- 2. button on real question screens in every realm/mode ----
    SCREENS=[('tt-practice',"S=makeSession(7,null);practiceStart()"),('tt-boss',"S=makeSession(4,null);bossStart()")]
    for sid,cs in (('add',[1,4,9]),('sub',[2,6]),('div',[3,7,9]),('frac',[1,5,10]),('mix',[2,4,6]),('mult',[13,14,16])):
        for ch in cs: SCREENS.append((f'{sid}{ch}-practice',f"makeSS('{sid}',{ch});sPracticeStart()"))
    SCREENS+=[('frac3-boss',"makeSS('frac',3);sBossStart()"),('mix5-boss',"makeSS('mix',5);sBossStart()"),('mult14-boss',"makeSS('mult',14);sBossStart()"),
              ('drill-div',"drillStart([{sid:'div',c:4}],false)"),('drill-mix',"drillStart([{sid:'add',c:3},{sid:'frac',c:6}],true)")]
    for tag,js in SCREENS:
        pg.evaluate("mapScreen()");pg.wait_for_timeout(100)
        try: pg.evaluate(js);pg.wait_for_selector('#exBtn',timeout=8000);ok=True
        except Exception as e: ok=False;print('  err',tag,str(e)[:150])
        if not ok: ck(False,f'{tag}: Example button present');continue
        info=pg.evaluate("""(()=>{const e=document.getElementById('exBtn'),l=document.getElementById('hintBtn'),a=e.getBoundingClientRect(),b=l.getBoundingClientRect();return {nx:e.parentNode===l.parentNode,gap:b.left-a.right,h:a.height,w:a.width,same:Math.abs((a.top+a.bottom)/2-(b.top+b.bottom)/2)<4}})()""")
        ck(info['nx'] and 0<=info['gap']<=20 and info['same'] and info['h']>=44 and info['w']>=44,f'{tag}: Example button right next to the lanterns, ≥44px ({info})')
        q0=pg.evaluate("(()=>{const o=(typeof SS!=='undefined'&&SS&&SS.cur)?SS:S;return exSig(o.cur)+'|'+exAnsKey(o.cur)+'|'+exFmt(o.cur)})()")
        before=pg.evaluate(STATE);lan0=pg.evaluate("document.getElementById('hintBtn').getAttribute('aria-label')")
        pg.click('#exBtn');pg.wait_for_selector('#exv #exvSteps li')
        ex=pg.evaluate("[document.getElementById('exvQ').innerText,document.getElementById('exvQ').dataset.ans,document.getElementById('exvQ').dataset.fmt,document.getElementById('exvSteps').innerText]")
        sig0,ans0,fmt0=q0.split('|',2)
        ck(ex[1]!=ans0 and ex[2]==fmt0 and 'NaN' not in ex[3] and 'undefined' not in ex[3],f'{tag}: example has the same format, a different answer ({ans0} vs {ex[1]})')
        pg.click('#exAgain');pg.wait_for_timeout(100);ex2=pg.evaluate("document.getElementById('exvQ').innerHTML")
        ck(ex2!=pg.evaluate("''")and pg.evaluate("EX.last.length")>=2,f'{tag}: another tap gives a new example')
        pg.click('#exBack');pg.wait_for_timeout(100)
        q1=pg.evaluate("(()=>{const o=(typeof SS!=='undefined'&&SS&&SS.cur)?SS:S;return exSig(o.cur)+'|'+exAnsKey(o.cur)+'|'+exFmt(o.cur)})()")
        ck(pg.locator('#exv').count()==0 and q1==q0 and pg.evaluate(STATE)==before and pg.evaluate("document.getElementById('hintBtn').getAttribute('aria-label')")==lan0,f'{tag}: closed back to the same problem; save and lanterns unchanged')
    # ---- 3. input preserved, timer paused (drill), Escape closes, many taps all different ----
    pg.evaluate("mapScreen()");pg.evaluate("makeSS('add',4);sPracticeStart()");pg.wait_for_selector('#exBtn')
    pg.evaluate("(()=>{const o=SS;})()")
    hasPad=pg.locator('#pad button').count()>0
    if hasPad: pg.locator('#pad button',has_text='4').first.click();pg.locator('#pad button',has_text='2').first.click()
    a0=pg.evaluate("(document.getElementById('ans')||{}).textContent")
    sigs=set()
    pg.click('#exBtn')
    for i in range(6):
        sigs.add(pg.evaluate("document.getElementById('exvQ').innerHTML"));pg.click('#exAgain');pg.wait_for_timeout(50)
    ck(len(sigs)==6,'6 taps of "Another example" give 6 different examples')
    pg.keyboard.press('Escape');pg.wait_for_timeout(100)
    ck(pg.locator('#exv').count()==0 and pg.evaluate("(document.getElementById('ans')||{}).textContent")==a0,'Escape closes; typed input preserved (%s)'%a0)
    pg.evaluate("mapScreen()");pg.evaluate("drillStart([{sid:'mult',c:13}],false)");pg.wait_for_selector('#exBtn');pg.wait_for_timeout(600)
    t0=pg.evaluate("drLeft()");pg.click('#exBtn');pg.wait_for_timeout(2600);tm=pg.evaluate("document.getElementById('drTime').textContent");pg.click('#exBack');t1=pg.evaluate("drLeft()")
    ck(abs(t1-t0)<=1,'drill timer paused while the example is open (%s -> %s, shown %s)'%(t0,t1,tm))
    # ---- 4. wrong-answer worked example still works; times-table wrong answer now gets one too ----
    pg.evaluate("mapScreen()");pg.evaluate("makeSS('sub',3);sPracticeStart()");pg.wait_for_selector('#exBtn');pg.evaluate("SS.onAnswer(false,0)");pg.wait_for_timeout(300)
    ck(pg.locator('#wex li').count()>=2,'subject wrong answer still shows the worked example')
    pg.evaluate("mapScreen()");pg.evaluate("S=makeSession(6,null);practiceStart()");pg.wait_for_selector('#exBtn');pg.evaluate("S.onAnswer(false)");pg.wait_for_timeout(300)
    ck(pg.locator('#wex li').count()==3 and ('Skip count' in pg.inner_text('#wex') or 'rows' in pg.inner_text('#wex')),'times-table wrong answer shows a worked example with skip counting')
    pg.click('#exBtn');pg.wait_for_selector('#exv');ck(pg.locator('#exv .gridwrap').count()>=1,'times-table example shows groups/array picture');pg.click('#exBack')
    c.close()
    # ---- 5. layout at 390 and 1280 + screenshots ----
    for w,h,tag,mob in ((1280,900,'desktop',False),(390,844,'phone',True)):
        c,pg=page(w,h,mob)
        for name,js in (('tt',"S=makeSession(7,null);practiceStart()"),('lm',"makeSS('mult',14);sPracticeStart()"),('miss',"makeSS('mix',4);sPracticeStart()"),('frac',"makeSS('frac',6);sPracticeStart()"),('boss',"makeSS('div',5);sBossStart()")):
            pg.evaluate("mapScreen()");pg.evaluate(js);pg.wait_for_selector('#exBtn');pg.wait_for_timeout(300)
            lay=pg.evaluate("""(()=>{const r=id=>document.getElementById(id).getBoundingClientRect();const e=r('exBtn'),l=r('hintBtn');const ov=!(e.right<=l.left||l.right<=e.left||e.bottom<=l.top||l.bottom<=e.top);const p=document.querySelector('#pad,#opts,.sin,input');let ov2=false;if(p){const q=p.getBoundingClientRect();ov2=!(e.bottom<=q.top||q.bottom<=e.top||e.right<=q.left||q.right<=e.left);}return {ov,ov2,sx:document.documentElement.scrollWidth<=innerWidth+1,inview:e.left>=0&&e.right<=innerWidth}})()""")
            ck(not lay['ov'] and not lay['ov2'] and lay['sx'] and lay['inview'],f'{tag}/{name}: no overlap, no sideways scroll ({lay})')
            if SH and name in('tt','lm') : pg.locator('#qbox,.card').first.screenshot(path=f'{OUT}/{BR}-{tag}-{name}-question-button.png')
            pos0=pg.evaluate("JSON.stringify([document.getElementById('hintBtn').getBoundingClientRect().top,(document.querySelector('#pad,#opts')||{getBoundingClientRect:()=>({top:0})}).getBoundingClientRect().top])")
            pg.click('#exBtn');pg.wait_for_selector('#exv');pg.wait_for_timeout(200)
            ck(pg.evaluate("document.querySelector('.exvc').getBoundingClientRect().right<=innerWidth+1"),f'{tag}/{name}: example screen fits')
            if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-{name}-example.png')
            pg.click('#exBack');pg.wait_for_timeout(100)
            ck(pg.evaluate("JSON.stringify([document.getElementById('hintBtn').getBoundingClientRect().top,(document.querySelector('#pad,#opts')||{getBoundingClientRect:()=>({top:0})}).getBoundingClientRect().top])")==pos0,f'{tag}/{name}: no layout shift after closing')
        if SH: pg.evaluate("mapScreen()");pg.evaluate("S=makeSession(7,null);practiceStart()");pg.wait_for_selector('#exBtn');pg.screenshot(path=f'{OUT}/{BR}-{tag}-tt-question-screen.png')
        c.close()
    b.close()
ck(errs==[],'no console errors (%s)'%errs[:5])
print('RESULT',BR,'FAILS',len(fails));raise SystemExit(1 if fails else 0)
