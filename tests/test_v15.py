# v22 update of test_v15.py: same checks, adapted only for age groups, v22 version numbers and self-hosted fonts on file://
import os
import json,threading,http.server,functools,re,sys,os
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
# box-local GStreamer plugins so headless WebKit has an audio sink (otherwise AudioContext can never run here)
os.environ.setdefault('GST_PLUGIN_PATH','/workspace/wkdeps/root/usr/lib/x86_64-linux-gnu/gstreamer-1.0')
D=os.environ.get('NR_DIR',os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8795),functools.partial(http.server.SimpleHTTPRequestHandler,directory=D))
srv.RequestHandlerClass.log_message=lambda *a:None
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8795/index.html'
HTML=open(D+'/index.html',encoding='utf8').read()
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m)
    if not c: fails.append(m)
IDS=['sage','emi','blu','eshon','melrose','cayden','zea']
OLD={"muted":False,"narrator":True,"voiceName":"Fred","hero":"emi","profiles":{"emi":{"name":"Emi","stars":{"2":3,"5":2},"hist":{"2x3":[1,1]},"rewards":["fcrown"],"eq":{},"prologue":True,"about":{"age":7}}}}
# ---- static: spelling / US English ----
for w in ['practise','colour','favourite','Lighter skin','Brackets','behaviour','centre','harbour','cosy','defence','All six heroes']:
    ck(w.lower() not in HTML.lower(),'no "%s" in index.html'%w)
ck("No sound? Check your phone's volume and silent switch." in HTML,'silent-switch note present')
ck("const APP_VERSION='22'" in HTML and json.load(open(D+'/version.json'))['version']=='22','APP_VERSION and version.json are 22')
with sync_playwright() as p:
    b=getattr(p,os.environ.get('PWB','chromium')).launch()
    c=b.new_context(viewport={'width':390,'height':844})
    c.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('ttq-save-v2',%s)}"%json.dumps(json.dumps(OLD)))
    c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"22"}'))
    pg=c.new_page(); pg.on('pageerror',lambda e:errs.append(str(e))); pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
    pg.goto(URL); pg.wait_for_timeout(1200)
    sv=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))")
    e=sv['profiles']['emi']
    ck(e['stars']=={"2":3,"5":2} and e['hist']=={"2x3":[1,1]} and e['rewards']==["fcrown"] and sv['hero']=='emi','old save migrated intact')
    ck(len(sv['profiles'])==7,'all 7 profiles present after migration')
    ck(sv.get('voiceName') in (None,),'novelty voice "Fred" saved choice reset to Automatic (got %r)'%sv.get('voiceName'))
    # hero pages uniform
    seqs={};texts={}
    for id in IDS:
        pg.evaluate("go('hero',%r)"%id); pg.wait_for_timeout(150)
        seq=pg.evaluate("""()=>{const c=document.querySelector('.hphero');const out=[];c.querySelectorAll('*').forEach(el=>{if(el.closest('svg')||el.closest('.hpport'))return;if(el.className&&typeof el.className==='string'&&/^(hp|chips|hloves|hpers|hpbtns)/.test(el.className.split(' ')[0]))out.push(el.className.split(' ')[0]+(el.className.startsWith('chips')?':'+el.children.length:''));});
          const secs=[...document.querySelectorAll('.hpage > .card h2')].map(h=>h.textContent.replace(/[^A-Za-z ]/g,'').trim().split(' ')[0]);return out.join(',')+'|'+secs.join(',');}""")
        seqs[id]=seq; t=pg.inner_text('.hpage'); texts[id]=t
        ck(not re.search(r'skin|👀|Real name|Player name',t),'%s page: no appearance/skin/real-name text'%id)
        ck('Loves' in t and 'Age' in t,'%s page: has age chip + Loves line'%id)
        ck(pg.evaluate("!!document.querySelector('.hpnick')&&document.querySelector('.hpnick').textContent.trim().length>5"),'%s page: has quote row'%id)
    base=seqs['emi']; print('layout:',base)
    for id in IDS: ck(seqs[id]==base,'%s page layout identical to Emi (%s)'%(id,seqs[id]))
    pers=[pg.evaluate("HERO12[%r].pers.length"%id) for id in IDS]; print('pers lengths',pers)
    ck(max(pers)<=1.6*min(pers),'personality lines similar length')
    lv=[pg.evaluate("HERO12[%r].loves.length"%id) for id in IDS]; ck(len(set(lv))==1,'same number of Loves items (%s)'%lv)
    # hall + pick tiles
    pg.evaluate("go('heroes')"); pg.wait_for_timeout(200)
    hs=pg.evaluate("[...document.querySelectorAll('.hallcard:not(.villain)')].map(b=>[...b.children].map(x=>x.tagName+'.'+x.className).join(','))")
    ck(len(hs)==7 and len(set(hs))==1,'Heroes Hall cards identical structure')
    pg.evaluate("heroPickScreen()"); pg.wait_for_timeout(200)
    ts=pg.evaluate("[...document.querySelectorAll('.herocard')].map(b=>[...b.children].map(x=>x.className).join(','))")
    ck(len(ts)==7 and len(set(ts))==1,'hero select tiles identical structure')
    # progress wording
    pg.evaluate("go('progress')"); pg.wait_for_timeout(200)
    pt=pg.inner_text('#app'); ck('practise' not in pt.lower(),'Progress uses US "practice"')
    # settings
    pg.evaluate("go('settings')"); pg.wait_for_timeout(300)
    st=pg.inner_text('#app'); ck("No sound? Check your phone's volume and silent switch." in st,'Settings shows silent-switch note')
    ck(pg.locator('#testVoice').count()==1,'Test voice button present')
    # toggles gate + persist (chromium, stubbed speech)
    pg.evaluate("""window.__sp=[];speechSynthesis.speak=u=>window.__sp.push({t:u.text,v:u.voice&&u.voice.name});window.__tones=0;{const o=AudioContext.prototype.createOscillator;AudioContext.prototype.createOscillator=function(){window.__tones++;return o.call(this);};};0""")
    pg.evaluate("save.narrator=true;speak('hello there','owl')"); n1=pg.evaluate("__sp.length")
    pg.evaluate("save.narrator=false;speak('hello again','owl')"); n2=pg.evaluate("__sp.length")
    ck(n1==1 and n2==1,'narrator toggle gates speak()')
    pg.click('#testVoice'); ck(pg.evaluate("__sp.length")>=2 and pg.evaluate("__sp[__sp.length-1].t").startswith('Hoo'),'Test voice speaks even with narrator off')
    pg.evaluate("save.muted=false"); t0=pg.evaluate("__tones"); pg.evaluate("SFX.tap()"); t1=pg.evaluate("__tones")
    pg.evaluate("save.muted=true"); pg.evaluate("SFX.tap()"); t2=pg.evaluate("__tones")
    ck(t1>t0 and t2==t1,'sound toggle gates SFX (%s,%s,%s)'%(t0,t1,t2))
    pg.evaluate("save.muted=false;save.narrator=true;persist()"); pg.click('#tg-sound'); pg.click('#tg-narrator'); pg.wait_for_timeout(100)
    sv=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))"); ck(sv['muted']==True and sv['narrator']==False,'toggles persist to save')
    pg.reload(); pg.wait_for_timeout(800); ck(pg.evaluate("save.muted===true&&save.narrator===false"),'toggles survive reload')
    # narrator reads question + lantern clue
    pg.evaluate("save.narrator=true;save.muted=true;window.__sp=[];speechSynthesis.speak=u=>window.__sp.push(u.text);0")
    pg.evaluate("openLevel(ORDER[0])"); pg.wait_for_timeout(1500)
    ck(pg.evaluate("__sp.length")>=1,'narrator speaks in a level (%s)'%pg.evaluate("__sp.slice(0,2)"))
    # voice labels
    lab=pg.evaluate("voiceLabel({name:'Samantha',lang:'en-US'})+'|'+voiceLabel({name:'Microsoft Aria Online (Natural) - English (United States)',lang:'en-US'})")
    print('labels',lab); ck(lab.startswith('Samantha (US)'),'friendly voice labels')
    ck(pg.evaluate("NOVELTY.test('Fred')&&NOVELTY.test('Zarvox')&&!NOVELTY.test('Samantha')"),'novelty voices filtered')
    b.close()
    # ---- WebKit iPhone emulation ----
    wk=p.webkit.launch()
    c=wk.new_context(**p.devices['iPhone 13'])
    c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"22"}'))
    c.add_init_script("""
      window.__spoken=[];
      const FV=[{name:'Fred',lang:'en-US',localService:true,default:false,voiceURI:'Fred'},{name:'Samantha',lang:'en-US',localService:true,default:true,voiceURI:'Samantha'},{name:'Daniel',lang:'en-GB',localService:true,default:false,voiceURI:'Daniel'},{name:'Thomas',lang:'fr-FR',localService:true,default:false,voiceURI:'Thomas'}];
      let ready=false;window.__voicesNow=()=>{ready=true;try{speechSynthesis.dispatchEvent(new Event('voiceschanged'))}catch(e){}};
      window.__played=[];{const pl=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){window.__played.push({src:this.src.slice(0,15),loop:this.loop});return pl.call(this);};}
      const ss=new EventTarget();ss.speaking=false;ss.pending=false;ss.paused=false;ss.getVoices=()=>ready?FV:[];ss.cancel=()=>{};ss.resume=()=>{};
      ss.speak=u=>window.__spoken.push({t:u.text,v:u.voice&&u.voice.name,vol:u.volume});
      Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
      window.SpeechSynthesisUtterance=function(t){this.text=t;this.volume=1;};
      localStorage.setItem('ttq-save-v2',JSON.stringify({muted:false,narrator:false,hero:'emi',profiles:{emi:{name:'Emi',stars:{},hist:{},rewards:[],eq:{},prologue:true}}}));
    """)
    pg=c.new_page(); pg.on('pageerror',lambda e:errs.append('webkit: '+str(e)))
    pg.goto(URL); pg.wait_for_timeout(300)
    pg.evaluate("go('settings')"); pg.wait_for_timeout(100)
    ck(pg.locator('#voiceLoading').count()==1 and 'Loading voices' in pg.inner_text('#app'),"WebKit: shows 'Loading voices…' while list empty")
    pg.evaluate("__voicesNow()"); pg.wait_for_timeout(600)
    opts=pg.evaluate("[...document.querySelectorAll('#voiceSel option')].map(o=>o.textContent)"); print('webkit options',opts)
    ck(pg.locator('#voiceSel').count()==1 and not any('Fred' in o or 'Thomas' in o for o in opts) and any(o.startswith('Samantha (US)') for o in opts),'WebKit: English non-novelty voices with friendly labels')
    print('VOICE',pg.evaluate("[VOICE&&VOICE.name,JSON.stringify(save.voiceName)]")); ck(pg.evaluate("VOICE&&VOICE.name")=='Samantha','WebKit: default voice is Samantha')
    st0=pg.evaluate("actx?actx.state:'none'")
    pg.tap('#testVoice'); pg.wait_for_timeout(400)
    st1=pg.evaluate("actx?actx.state:'none'"); print('actx before/after tap',st0,st1)
    ck(st1=='running','WebKit iPhone: AudioContext running after a tap')
    sp=pg.evaluate("__spoken"); print('spoken',sp)
    ck(any(s['t'].startswith('Hoo') and s['v']=='Samantha' for s in sp),'WebKit iPhone: Test voice calls speak() with chosen voice (narrator off)')
    ck(pg.evaluate("!!AUD.el&&AUD.el.loop&&AUD.el.src.startsWith('data:audio/wav')&&__played.length>=1&&__played[0].loop"),'WebKit: silent looping <audio> (data-URI WAV) played on first gesture')
    ck(pg.evaluate("AUD.warm===true"),'WebKit: speech warm-up utterance spoken inside the gesture')
    pg.select_option('#voiceSel','Daniel'); pg.wait_for_timeout(200)
    ck(pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2')).voiceName")=='Daniel' and pg.evaluate("__spoken[__spoken.length-1].v")=='Daniel','WebKit: voice choice persists and is used')
    pg.evaluate("actx.suspend()"); pg.wait_for_timeout(200); pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(400)
    ck(pg.evaluate("actx.state")=='running','WebKit: context resumed on visibilitychange')
    wk.close()
srv.shutdown()
errs=[e for e in errs if 'favicon' not in e]
ck(not errs,'no page errors (%s)'%errs[:3])
print('FAILS',len(fails)); sys.exit(1 if fails else 0)
