# v25: fluent narrator - voice ranking, chunked speech queue, speech-only normalizer, Settings picker.
# Usage: PWB=chromium|webkit python test_v25.py   (SHOTS=1 -> /workspace/v25shots)
import os,json,re,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))));BR=os.environ.get('PWB','chromium');SH=os.environ.get('SHOTS')=='1'
OUT='/workspace/v25shots';os.makedirs(OUT,exist_ok=True)
PORT=8862 if BR=='chromium' else 8863
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
BASE=f'http://localhost:{PORT}/index.html'
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c: fails.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
_av=re.search(r"const APP_VERSION='(\d+)'",html);ck(_av and int(_av.group(1))>=25 and int(json.load(open(os.path.join(D,'version.json')))['version'])>=25,'version >= 25')
ALL={str(i):3 for i in range(1,13)}
subj={s:{"stars":{str(i):3 for i in range(1,20)},"hist":{},"intro":True} for s in ['add','sub','mult','div','frac','mix']}
SAVE={"muted":True,"narrator":True,"lastHero":"emi","hero":"emi","profiles":{"emi":{"name":"Emi","stars":ALL,"hist":{},"rewards":[],"eq":{},"prologue":True,"age":"8-10","grade":"3","subj":subj}}}
# mocked speechSynthesis: records calls; voices load late; modes: ok | errfirst | nostart
MOCK=r"""(()=>{const V=[['Albert','en-US',1],['Bad News','en-US',1],['Zarvox','en-US',1],['Jester','en-US',1],['eSpeak English','en',1],['Google US English','en-US',0],
 ['Samantha','en-US',1],['Daniel','en-GB',1],['Ava (Enhanced)','en-US',1],['Microsoft Aria Online (Natural) - English (United States)','en-US',0],['Amélie','fr-CA',1]].map(([name,lang,l])=>({name,lang,localService:!!l,voiceURI:name,default:false}));
 const M={calls:[],mode:'ok',ready:false,speaking:false,pending:false,paused:false,cur:null,q:[],ls:{},
  getVoices(){return M.ready?V.slice():[]},addEventListener(t,f){(M.ls[t]=M.ls[t]||[]).push(f)},removeEventListener(){},
  speak(u){M.calls.push(['speak',u.text,Date.now(),u.voice&&u.voice.name,u.rate,u.pitch]);M.q.push(u);M.pending=true;setTimeout(M.run,5)},
  cancel(){M.calls.push(['cancel',Date.now()]);const c=M.cur;M.q=[];M.cur=null;M.speaking=false;M.pending=false;if(c&&c.onerror)setTimeout(()=>c.onerror({error:'interrupted'}),0)},
  pause(){M.paused=true;M.calls.push(['pause'])},resume(){M.paused=false;M.calls.push(['resume'])},
  run(){if(M.cur||!M.q.length)return;const u=M.cur=M.q.shift();M.pending=M.q.length>0;
   if(M.mode==='nostart'&&!u._seen){u._seen=1;M.cur=null;return;}
   if(M.mode==='errfirst'&&!M._erred){M._erred=1;M.cur=null;setTimeout(()=>u.onerror&&u.onerror({error:'synthesis-failed'}),5);return;}
   M.speaking=true;u.onstart&&u.onstart({});setTimeout(()=>{if(M.cur!==u)return;M.cur=null;M.speaking=false;u.onend&&u.onend({});M.run()},20)}};
 Object.defineProperty(window,'speechSynthesis',{value:M,configurable:true});
 window.SpeechSynthesisUtterance=function(t){this.text=t;this.voice=null;this.lang='';this.rate=1;this.pitch=1;this.volume=1};
 setTimeout(()=>{M.ready=true;(M.ls.voiceschanged||[]).forEach(f=>f({}))},400);})();"""
def page(b,w=1280,h=900,mob=False,save=SAVE):
    kw=dict(viewport={'width':w,'height':h},service_workers='block')
    if mob: kw.update(has_touch=True,**({'is_mobile':True,'device_scale_factor':2} if BR=='chromium' else {}))
    c=b.new_context(**kw);c.add_init_script(MOCK)
    c.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('ttq-save-v2',%s);}"%json.dumps(json.dumps(save)))
    pg=c.new_page();pg.on('console',lambda x: errs.append(x.text) if x.type=='error' else None);pg.on('pageerror',lambda e: errs.append('PAGEERR '+str(e)))
    pg.goto(BASE);pg.wait_for_timeout(1300);return c,pg
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    c,pg=page(b)
    # ---- 1. normalizer: expected phrasings ----
    CASES=[('7 × ? = 14','7 times what number equals 14'),('? × 7 = 56','what number times 7 equals 56'),('48 ÷ 6 = ?','48 divided by 6 equals what number'),
     ('12 − 5 = ?','12 minus 5 equals what number'),('40 - 15 = __','40 minus 15 equals what number'),('3 + ? = 10','3 plus what number equals 10'),
     ('What is <span class="fr"><span class="fn">3</span><span class="fd">4</span></span> of 8?','What is three fourths of 8?'),('1/2','one half'),('2/3 + 1/6','two thirds plus one sixth'),
     ('1 1/2','1 and one half'),('25 ÷ 4 = 6 R 1','25 divided by 4 equals 6 remainder 1'),('Ages 4–5','Ages 4 to 5'),('Ch.9 · ×7','Chapter 9, the 7 times table'),
     ('Blú, Khílo, Eshon, Zea and Emi','Bloo, Kee-lo, Eh-shawn, Zee-uh and Em-ee'),('Welcome to NumiRealm! ⭐✨🎉','Welcome to Noomy Realm!'),('1,250 + 3.5','1250 plus 3 point 5'),
     ('You came in 2nd!','You came in second!'),('Tom &amp; Sage &lt;b&gt;win&lt;/b&gt;','Tom and Sage win'),('Is 3/8 bigger than 1/2?','Is three eighths bigger than one half?'),('5 × 3 = 15 ✓ → next','5 times 3 equals 15 next'),
     ('Cayden and Melrose','Kay-den and Melrose'),('Times Table Castle • Division Docks','Times Table Castle, Division Docks')]
    got=pg.evaluate("c=>c.map(x=>narrNorm(x[0]))",CASES)
    bad=[(a,e,g) for (a,e),g in zip(CASES,got) if g!=e]
    ck(not bad,'normalizer gives the expected phrasings (%d cases): %s'%(len(CASES),bad[:6]))
    ck(pg.evaluate("typeof SAY_AS==='object'&&SAY_AS['Blú']==='Bloo'&&SAY_AS['Khílo']==='Kee-lo'&&SAY_AS['Eshon']==='Eh-shawn'&&SAY_AS['Zea']==='Zee-uh'&&SAY_AS['Emi']==='Em-ee'&&SAY_AS.NumiRealm==='Noomy Realm'"),'one pronunciation table holds the hero respellings')
    ck(pg.evaluate("(()=>{const q=makeQ('fill',7,3,CTX[0]);return q.text})()").find('×')>=0,'displayed text is unchanged (still shows ×)')
    # ---- 2. big sample: every generated question type + examples + narrated strings ----
    r=pg.evaluate(r"""(()=>{const L=[];const add=s=>{if(typeof s==='string'&&/[A-Za-z0-9]/.test(s))L.push(s)};
     const chs=[];SUBJ.forEach(sb=>sb.ch.forEach((ch,i)=>ch&&chs.push([sb.id,i+1,ch,sb])));MLX.forEach((ch,i)=>chs.push(['mult',ORDER.length+1+i,ch,SUBJ_BY.mult]));
     for(const [sid,c,ch,sb] of chs){if(ch.tip)add('Easy trick! '+stripH(ch.tip));for(let i=0;i<12;i++){SS={sid,c,ch,sb,attempt:1,team:SIBS.emi[0],inBoss:i%3==0};const q=ch.gen(['p','a','b'][i%3]);SS.cur=q;add(stripH(q.text));add(q.text);if(q.explain)add(stripH(q.explain));
      if(q.lead)add(q.lead);EX.last=[];try{const ex=exMake();if(ex)add('Example. '+exPlain(ex.q.text)+'. '+ex.st.map(exPlain).join(' '));}catch(e){}}}
     SS=null;for(const n0 of ORDER)for(const ty of ['fill','mc','missing','story','array'])for(let k=1;k<=12;k+=3){const q=makeQ(ty,n0,k,CTX[k%CTX.length]);add(stripH(q.text));if(q.lead)add(q.lead);try{add(stripH(explain(q)))}catch(e){}try{add(stripH(hintHTML(q,true)))}catch(e){}
      S={n:n0,inBoss:false,cur:q};EX.last=[];try{const ex=exMake();if(ex)add('Example. '+exPlain(ex.q.text)+'. '+ex.st.map(exPlain).join(' '));}catch(e){}}S=null;
     const walk=(o,d)=>{if(d>5||o==null)return;if(typeof o==='string'){if(!/^#|^<svg|^\s*<|url\(|^[a-z-]+$/.test(o)&&/\s/.test(o))add(o);return;}if(Array.isArray(o))o.forEach(x=>walk(x,d+1));else if(typeof o==='object')Object.values(o).forEach(x=>walk(x,d+1));};
     ['SIDE','BRAVE','VICTORY','SIB_PROUD','LOSE_SIB','LOSE_HERO','RETRY_OWL','RETRY_HERO','TAUNTS','SIB_INTRO','HERO_INTRO','OWL_WIN','ENC','SAGE_LINES','HERO_TEAM','ESHON_LINES','HTAUNTS','REALM_OWL','REALM_LINE','REPLY','STAUNTS','SFINAL','MUDDLE','CHEERS','BOSSES','HSUB','TEAM_SUB','PLACES','HPLACES','HBOSS'].forEach(n=>{try{walk(eval(n),0)}catch(e){}});
     Object.keys(HEROES).forEach(id=>{try{add(heroBio(id))}catch(e){}});try{Object.keys(HERO12||{}).forEach(id=>{try{add(heroBio(id))}catch(e){}})}catch(e){}
     const out=L.map(s=>[s,narrNorm(s)]);return {n:out.length,out}})()""")
    BADRE=re.compile(r'[×÷=/<>&\\{}\[\]_]|undefined|NaN|&\w+;|[\u2190-\u21FF\u2600-\u27BF\u2B50\u2B55]|[\U0001F000-\U0001FAFF]|\ufe0f')
    QRE=re.compile(r'(^|[\s(=+\-])\?|\?\s*(equals|plus|minus|times)')
    badS=[(a[:60],o[:80]) for a,o in r['out'] if BADRE.search(o) or QRE.search(o)]
    ck(r['n']>=2500 and not badS,'normalizer sample: no raw × ÷ = / ? emoji, tags, entities, undefined or NaN (%d strings): %s'%(r['n'],badS[:6]))
    mq=[(a,o) for a,o in r['out'] if re.search(r'\d\s*×\s*\?\s*=',a)][:50]
    ck(mq and all('times what number equals' in o for a,o in mq),'missing-number questions read "times what number equals" (%d checked)'%len(mq))
    fr=[(a,o) for a,o in r['out'] if 'class="fn"' in a][:80]
    ck(all(not re.search(r'\d\s*/\s*\d',o) for a,o in fr),'fractions read as words (%d checked)'%len(fr))
    nm=[o for a,o in r['out'] if 'Blú' in a]
    ck(nm and all('Bloo' in o and 'Blú' not in o for o in nm),'Blú read as Bloo everywhere (%d lines)'%len(nm))
    # ---- 3. chunking ----
    ch=pg.evaluate(r"""(()=>{const out=[];const base=[...new Set(window.__S||[])];const T=[];for(let i=0;i<60;i++){let t='';const n=1+i%9;for(let j=0;j<n;j++)t+=['Hoo-hoo, welcome back to the meadow, where every flower is waiting for you to count it',
      'First, split 39 into 30 and 9, then multiply each part by 4, and finally add the parts together to get 156','Great job','This is a very long sentence without any commas at all that just keeps going and going so that it has to be broken at word boundaries somewhere sensible'][ (i+j)%4]+(j%3==2?'!':'.')+' ';T.push(t.trim());}
      for(const t of T){const c=narrChunks(t,160);out.push([t,c])}return out})()""")
    okc=all(all(len(x)<=160 for x in cs) and ' '.join(cs).split()==t.split() for t,cs in ch)
    ck(okc,'chunks stay under 160 characters, nothing lost, order kept (%d texts)'%len(ch))
    ck(all(len(cs)==1 for t,cs in ch if len(t)<=160),'short lines stay in one piece')
    # ---- 4. voice ranking (mocked list; voices arrive late) ----
    v=pg.evaluate("[VOICE&&VOICE.name,niceVoices().map(v=>v.name)]")
    ck(v[0]=='Ava (Enhanced)','best voice after late load is Ava (Enhanced): %s'%v[0])
    nov=[n for n in v[1] if re.match(r'(Albert|Bad News|Zarvox|Jester|eSpeak)',n)]
    ck(not nov and 'Amélie' not in v[1],'novelty, eSpeak and non-English voices left out of the list: %s'%v[1])
    ck(v[1].index('Samantha')<v[1].index('Google US English') and v[1].index('Samantha')<v[1].index('Daniel'),'local en-US Samantha ranks above remote and en-GB voices')
    ck(pg.evaluate("rankVoices([{name:'Bells',lang:'en-US',localService:true},{name:'eSpeak',lang:'en',localService:true}])[0].name")=='eSpeak','with only poor voices, eSpeak beats novelty')
    # ---- 5. speaking: chunk queue, params, cancel/delay, retry ----
    pg.evaluate("speechSynthesis.calls=[];speakNow('Hello there. '+'This sentence is long, so it gets its own chunk, and it has commas, many commas, to split on. '.repeat(4)+'7 × ? = 14','owl')");pg.wait_for_timeout(900)
    calls=pg.evaluate("speechSynthesis.calls");sp=[x for x in calls if x[0]=='speak']
    ck(len(sp)>=3 and all(len(x[1])<=160 for x in sp) and sp[-1][1].endswith('7 times what number equals 14'),'long line plays as a queue of chunks, in order (%d)'%len(sp))
    ck(all(x[3]=='Ava (Enhanced)' and abs(x[4]-0.92)<1e-6 and abs(x[5]-1.05)<1e-6 for x in sp),'chunks use the chosen voice, rate 0.92 and pitch 1.05')
    pg.evaluate("speechSynthesis.calls=[];speakNow('One. Two. Three. Four. Five. '.repeat(8),'owl')");pg.wait_for_timeout(30)
    pg.evaluate("speakNow('Brand new line.','owl')");pg.wait_for_timeout(400)
    calls=pg.evaluate("speechSynthesis.calls");ci=[i for i,x in enumerate(calls) if x[0]=='cancel']
    after=[x for x in calls[ci[-1]+1:] if x[0]=='speak'] if ci else []
    ck(ci and after and after[0][1]=='Brand new line.' and after[0][2]-calls[ci[-1]][1]>=60 and len(after)==1,'a new line cancels the old one, then speaks after a short delay with no overlap')
    pg.evaluate("speechSynthesis.calls=[];speakNow('One. Two. Three. Four. Five. '.repeat(8),'owl')");pg.wait_for_timeout(40);pg.evaluate("mapScreen()");pg.wait_for_timeout(500)
    calls=pg.evaluate("speechSynthesis.calls");ci=[i for i,x in enumerate(calls) if x[0]=='cancel']
    ck(ci and not [x for x in calls[ci[-1]+1:] if x[0]=='speak'],'moving to a new screen cancels speech and nothing more is spoken')
    pg.evaluate("speechSynthesis.calls=[];speakNow('Hello.','owl');practiceStart&&0");pg.wait_for_timeout(200)
    pg.evaluate("speechSynthesis.calls=[];speechSynthesis.mode='errfirst';speechSynthesis._erred=0;speakNow('Retry me. Then me.','owl')");pg.wait_for_timeout(800)
    sp=[x[1] for x in pg.evaluate("speechSynthesis.calls") if x[0]=='speak']
    ck(sp[:3]==['Retry me. Then me.']*2 or sp[:2]==['Retry me. Then me.','Retry me. Then me.'],'an utterance that errors is retried once: %s'%sp)
    pg.evaluate("speechSynthesis.calls=[];speechSynthesis.mode='nostart';speakNow('Silent start.','owl')");pg.wait_for_timeout(3600)
    sp=[x[1] for x in pg.evaluate("speechSynthesis.calls") if x[0]=='speak']
    ck(sp.count('Silent start.')==2,'an utterance that never starts is retried once: %s'%sp)
    pg.evaluate("speechSynthesis.mode='ok'")
    pg.evaluate("save.narrator=false;speechSynthesis.calls=[];speak('Should stay quiet.','owl');save.narrator=true");pg.wait_for_timeout(100)
    ck(not [x for x in pg.evaluate("speechSynthesis.calls") if x[0]=='speak'],'narrator off: nothing spoken')
    # question screen narrates the normalized question
    pg.evaluate("mapScreen();S=makeSession(7,null);practiceStart()");pg.wait_for_timeout(400)
    pg.evaluate("speechSynthesis.calls=[];speak(stripH(S.cur.text),'owl')");pg.wait_for_timeout(300)
    sp=[x[1] for x in pg.evaluate("speechSynthesis.calls") if x[0]=='speak']
    ck(sp and not any(re.search(r'[×÷=]',x) for x in sp),'question line is spoken without symbols: %s'%sp[:2])
    c.close()
    # ---- 6. Settings picker, Test voice, tip, remembered voice; layout + screenshots ----
    for w,h,tag,mob in ((1280,900,'desktop',False),(390,844,'phone',True)):
        c,pg=page(b,w,h,mob)
        pg.evaluate("settingsScreen()");pg.wait_for_timeout(700)
        if not pg.locator('#voiceSel').count(): pg.evaluate("settingsScreen()");pg.wait_for_timeout(300)
        o=pg.evaluate("(()=>{const s=document.getElementById('voiceSel');return s?[s.options[0].textContent,[...s.options].map(o=>o.value)]:null})()")
        ck(o and o[0]=='Best voice (recommended)' and o[1][0]=='' and 'Zarvox' not in o[1],f'{tag}: picker defaults to "Best voice (recommended)" and has no novelty voices ({o and o[0]})')
        lab=pg.evaluate("[document.querySelector('label[for=voiceSel]').firstChild.textContent.trim(),[...document.querySelectorAll('.setrow .sl')].map(e=>e.firstChild.textContent.trim())]")
        ck(lab[0]=='Which voice' and lab[1].count('Narrator voice')==1,f'{tag}: picker label "Which voice", switch stays "Narrator voice" ({lab})')
        fit=pg.evaluate("(()=>{const s=$('voiceSel'),c=document.createElement('canvas').getContext('2d'),cs=getComputedStyle(s);c.font=cs.fontWeight+' '+cs.fontSize+' '+cs.fontFamily;const w=c.measureText(s.options[s.selectedIndex].text).width;return [Math.round(w),s.clientWidth]})()")
        ck(fit[0]+40<=fit[1],f'{tag}: selected picker text fits fully ({fit})')
        ck(pg.locator('#voiceTip').count()==1 and 'Accessibility › Spoken Content › Voices' in pg.inner_text('#voiceTip'),f'{tag}: grown-up tip about iPhone voices')
        tb=pg.evaluate("document.getElementById('testVoice').getBoundingClientRect().height")
        ck(tb>=44,f'{tag}: Test voice button at least 44px ({tb})')
        sx=pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
        ck(sx,f'{tag}: no sideways scroll on Settings')
        pg.evaluate("speechSynthesis.calls=[]");pg.click('#testVoice');pg.wait_for_timeout(600)
        sp=[x for x in pg.evaluate("speechSynthesis.calls") if x[0]=='speak']
        ck(sp and 'what number' in ' '.join(x[1] for x in sp) and 'Noomy Realm' in ' '.join(x[1] for x in sp),f'{tag}: Test voice speaks a normalized sample')
        if SH:
            pg.locator('#voiceSel').scroll_into_view_if_needed();pg.evaluate("document.getElementById('voiceSel').closest('.card').scrollIntoView({block:'start'})");pg.wait_for_timeout(200)
            pg.locator('#voiceSel').evaluate("e=>e.closest('.card')").screenshot if False else None
            pg.evaluate("document.getElementById('voiceSel').closest('.card').id='narrCard'")
            pg.locator('#narrCard').screenshot(path=f'{OUT}/{BR}-{tag}-settings-narrator.png');pg.screenshot(path=f'{OUT}/{BR}-{tag}-settings-screen.png')
        pg.select_option('#voiceSel','Samantha');pg.wait_for_timeout(300)
        ck(pg.evaluate("save.voiceName==='Samantha'&&VOICE.name==='Samantha'"),f'{tag}: choosing a voice applies it')
        pg.reload();pg.wait_for_timeout(1300)
        ck(pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2')).voiceName==='Samantha'&&VOICE&&VOICE.name==='Samantha'"),f'{tag}: chosen voice remembered after reload')
        pg.evaluate("settingsScreen()");pg.wait_for_timeout(300);pg.select_option('#voiceSel','');pg.wait_for_timeout(200)
        ck(pg.evaluate("save.voiceName===null&&VOICE.name==='Ava (Enhanced)'"),f'{tag}: back to Best voice picks the top voice')
        c.close()
    b.close()
ck(errs==[],'no console errors (%s)'%errs[:5])
print('RESULT',BR,'FAILS',len(fails));raise SystemExit(1 if fails else 0)
