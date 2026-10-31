# v33.1 NF-1 regression: Parent Area recorder (NRP.rec -> nr-parent-stats) counts every finished question exactly once,
# for keypad, tap/choice and mixed input, and matches the offline metrics export. Local server only; all other hosts aborted.
import os,threading,http.server,functools,json,sys
from playwright.sync_api import sync_playwright
D=os.environ.get('NF1_DIR','/workspace/v33-repo');PORT=int(os.environ.get('NF1_PORT','8881'));BR=os.environ.get('PWB','chromium')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
src=open('/workspace/v18tmp/audit_play.py').read();ns={};exec(compile(src.split('ENGS=')[0]+'\n'+src[src.index('def pad'):src.index('def practice')],'ap','exec'),ns)
SEED={"muted":True,"narrator":False,"hero":"emi","profiles":{"emi":{"name":"Emi","prologue":True,"age":8,"grade":3,"stars":{"2":3},"subj":{"add":{"stars":{"1":3,"2":3},"hist":{},"intro":True}}}}}
LINK={'token':'t'*40,'hero':'emi','kidId':'k','deviceName':'test'}
B=f'http://127.0.0.1:{PORT}/';fails=0;outside=[]
def ck(c,m,d=''):
    global fails
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m+('' if c else ' :: '+str(d)));fails+=0 if c else 1
def pstats(pg):
    st=pg.evaluate("JSON.parse(localStorage.getItem('nr-parent-stats')||'{}')")
    return sum(o.get('t',0) for h in st.get('h',{}).values() for o in h.get('s',{}).values()),sum(o.get('r',0) for h in st.get('h',{}).values() for o in h.get('s',{}).values())
def ctx_for(br,q=''):
    c=br.new_context(viewport={'width':1280,'height':860})
    c.add_init_script("if(!localStorage.getItem('ttq-save-v2'))localStorage.setItem('ttq-save-v2',%s);localStorage.setItem('nr-parent-link',%s)"%(json.dumps(json.dumps(SEED)),json.dumps(json.dumps(LINK))))
    def rt(r):
        if r.request.url.startswith(B): r.continue_()
        else: outside.append(r.request.url); r.abort()
    c.route('**/*',rt);pg=c.new_page();pg.goto(B+'index.html'+q);pg.wait_for_timeout(1200);return c,pg
with sync_playwright() as p:
    br=getattr(p,BR).launch()
    # 1 keypad (subject realm uses keypad sOK) + 2 forced tap/choice + 3 mixed: we force the input kind on the live question
    for name,kinds in (('keypad',['pad']*4),('tap/choice',['mc']*4),('mixed',['pad','mc','pad','mc','mc','pad'])):
        c,pg=ctx_for(br)
        pg.evaluate("openChapter('add',2)");ns['scene'](pg);ns['learn'](pg);pg.wait_for_selector('[data-stage=practice]')
        got=[];deltas=[];plan=[True,False,True,True,False,True]
        for k in kinds:
            pg.wait_for_function("TTQ_SUBJ.SS&&TTQ_SUBJ.SS.cur&&!TTQ_SUBJ.SS.locked",timeout=10000)
            if k=='mc':
                # turn the live question into a 3-option choice of the same answer and re-render (same as Qmc), so sPick is the input path
                pg.evaluate("""(()=>{const S=TTQ_SUBJ.SS,q=S.cur;if(q.input==='mc')return;const a=q.ans;const v=[a,a+1,a+2];q.input='mc';q.opts=v.map(x=>({h:String(x),v:x}));q.ans=0;q.check=i=>i===0;
                  const box=document.querySelector('#spad')?document.querySelector('#spad').parentNode:null;
                  const h=`<div class="opts sopts" id="sopts">${q.opts.map((o,i)=>`<button class="opt" data-i="${i}" onclick="sPick(${i},this)">${o.h}</button>`).join('')}</div>`;
                  const sp=document.querySelector('#spad');if(sp)sp.insertAdjacentHTML('beforebegin',h);})()""")
            inp=pg.evaluate("TTQ_SUBJ.SS.cur.input")
            if k=='pad' and inp=='mc':
                # turn a choice question into a keypad question with the same answer (keypad -> sOK path)
                pg.evaluate("""(()=>{const S=TTQ_SUBJ.SS,q=S.cur,o0=q.opts[q.ans],a=Number(o0&&o0.v!==undefined?o0.v:(o0&&o0.h!==undefined?o0.h:o0));if(!Number.isInteger(a)||a<0)return;q.input='pad';q.ans=a;q.check=v=>v===a;S.vals=[''];S.fi=0;
                  const o=document.querySelector('#sopts');o.insertAdjacentHTML('afterend','<div class="center"><div class="ansbox" id="sans">?</div></div>'+sPadHTML());o.remove();})()""")
                inp=pg.evaluate("TTQ_SUBJ.SS.cur.input")
            r=plan[len(got)%len(plan)];t0,_=pstats(pg);ns['answer'](pg,r);pg.wait_for_timeout(900);t1,_=pstats(pg);got.append((inp,r));deltas.append((inp,t1-t0))
            nx=pg.query_selector('#nextbtn:not(.hidden)') or pg.query_selector('#snext:not(.hidden)')
            if nx:
                try: nx.click()
                except Exception: pass
            pg.wait_for_timeout(400)
        ck(all(d==1 for _,d in deltas),f'{name}: every single answer adds exactly 1 attempt',deltas)
        if name=='keypad': ck(sum(1 for i,_ in got if i=='pad')>=3,f'{name}: at least 3 keypad answers',got)
        t,cc=pstats(pg);exp_t=len(got);exp_c=sum(1 for _,r in got if r)
        ck(t==exp_t and cc==exp_c,f'{name}: Parent Area counts each answer exactly once ({exp_t} answered, {exp_c} right)',f'got t={t} c={cc} inputs={got}')
        ck(set(i for i,_ in got)>=set(kinds),f'{name}: input paths exercised {sorted(set(i for i,_ in got))}',got)
        c.close()
    # 4 offline mode: parent stats vs metrics export
    outside.clear();c,pg=ctx_for(br,'?localonly=1')
    pg.evaluate("openChapter('add',2)");ns['scene'](pg);ns['learn'](pg);pg.wait_for_selector('[data-stage=practice]');got=[]
    for r in (True,False,True,True):
        pg.wait_for_function("TTQ_SUBJ.SS&&TTQ_SUBJ.SS.cur&&!TTQ_SUBJ.SS.locked",timeout=10000);got.append((pg.evaluate("TTQ_SUBJ.SS.cur.input"),r));ns['answer'](pg,r);pg.wait_for_timeout(900)
        nx=pg.query_selector('#nextbtn:not(.hidden)') or pg.query_selector('#snext:not(.hidden)')
        if nx:
            try: nx.click()
            except Exception: pass
        pg.wait_for_timeout(400)
    off_out=list(outside)
    raw=pg.evaluate("NRM._raw()");t,cc=pstats(pg);m=len(raw['ans']);mc=sum(1 for a in raw['ans'] if a['ok'])
    ck(m==4 and mc==3,'offline: metrics export has 4 answers / 3 right',(m,mc))
    ck(t==m and cc==mc,'offline: Parent Area totals match the metrics export',(t,cc,m,mc))
    c.close()
    ck(not off_out,'offline: no requests to any other host',off_out[:3])
    br.close()
print('RESULT fails=%d'%fails);sys.exit(1 if fails else 0)
