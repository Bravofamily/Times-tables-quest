# v20: one realm list drives every count/name; hardened saves (validate, backup, recovery, no-storage fallback); progress code copy/load; honest labels
import json,os,re,sys,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));PORT=8822;URL=f'http://127.0.0.1:{PORT}/index.html'
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(http.server.SimpleHTTPRequestHandler,directory=D));srv.RequestHandlerClass.log_message=lambda *a:None
threading.Thread(target=srv.serve_forever,daemon=True).start()
FAILS=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m);(None if c else FAILS.append(m))
HTML=open(D+'/index.html',encoding='utf-8').read()
V19={"muted":True,"narrator":False,"lastHero":"emi","chv":13,"voiceName":"","calm":False,"profiles":{
 "emi":{"name":"Emi","stars":{"2":3,"3":3,"4":2,"10":3},"hist":{},"rewards":["r1","r2"],"eq":{"hat":"crown"},"prologue":True,"age":6,"grade":"1","ss":{"add":{"1":3,"2":2}},"v18":{"run":2,"bestRun":7,"noLan":1}},
 "sage":{"name":"Sage","stars":{"2":3},"hist":{},"rewards":[],"eq":{},"prologue":True,"ss":{"sub":{"1":1}}}}}
NUMW=['zero','one','two','three','four','five','six','seven','eight','nine','ten']
def newctx(b,w=1280,save=None,init=None,rm=False):
    c=b.new_context(viewport={'width':w,'height':844 if w<500 else 800})
    c.route('**/version.json*',lambda r:r.fulfill(status=200,content_type='application/json',body='{"version":"20"}'))
    if save is not None:
        c.add_init_script("if(!sessionStorage.getItem('seeded')){localStorage.clear();%s;sessionStorage.setItem('seeded','1')}"%''.join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k,v in save.items()))
    if init:c.add_init_script(init)
    pg=c.new_page();errs=[];pg.on('pageerror',lambda e:errs.append(str(e)));pg.on('console',lambda m:(m.type=='error' and 'NumiRealm' in m.text) and errs.append(m.text))
    pg.goto(URL);pg.wait_for_timeout(1500);return c,pg,errs
with sync_playwright() as p:
    b=p.chromium.launch()
    # ---------- 1. realm list is the single source ----------
    c,pg,errs=newctx(b,save={'ttq-save-v2':json.dumps(V19)})
    R=pg.evaluate("REALM_DEFS.map(r=>({id:r.id,name:r.name,realm:r.realm,e:r.e}))")
    ck(len(R)==6 and [r['id'] for r in R]==['add','sub','mult','div','frac','mix'] and R[-1]['realm']=='Muddle Tower','six realms in REALM_DEFS: '+', '.join(r['realm'] for r in R))
    ck(pg.evaluate("SUBJ.map(s=>s.id+s.realm+s.e+s.name).join()===REALM_DEFS.map(r=>r.id+r.realm+r.e+r.name).join()"),'SUBJ (all game data) follows REALM_DEFS names/emoji/order')
    ck(pg.evaluate("Object.keys(QCOL).join()===REALM_IDS.join()&&REALM_DEFS.every(r=>QCOL[r.id]===r.accent)"),'realm colors come from REALM_DEFS')
    ck(pg.evaluate("realmCountWord()")==NUMW[len(R)],'count word derived from list length')
    ck(not re.search(r'\b(five|seven) realms\b',HTML,re.I),'no stale realm counts in the HTML')
    ck(pg.evaluate("(()=>{const s=REALM_DEFS;return realmListText().split(/, | and /).length===s.length})()"),'story intro lists every realm from the list')
    names=[r['realm'] for r in R]
    VAR=re.compile(r'\b(Addition|Subtraction|Times ?Table|Multiplication|Division|Fractions?|Muddle|Mixed Math) (Meadows?|Caves?|Castle|Docks?|Bakery|Tower|Kingdom|Land|Realm)\b')
    for scr,args,need in [('home',[],True),('realms',[],True),('progress',[],False),('guide',[],False),('trophies',[],False),('subjectScreen',[],True)]:
        pg.evaluate(f"(()=>{{try{{go({json.dumps(scr)})}}catch(e){{if(typeof {scr}==='function'){scr}()}}}})()");pg.wait_for_timeout(450)
        t=pg.inner_text('#app')
        cnt=[m.group(1).lower() for m in re.finditer(r'(?<!in )\b(\w+) realms\b',t,re.I) if m.group(1).lower() in NUMW or m.group(1).isdigit()]
        ck(all(x in ('six','6') for x in cnt),f'{scr}: realm counts say six {cnt}')
        bad=[m.group(0) for m in VAR.finditer(t) if m.group(0) not in names and m.group(0)!='Multiplication Wing']
        ck(not bad,f'{scr}: only canonical realm names {bad}')
        if need:
            pos=[t.find(n) for n in names]
            ck(all(x>=0 for x in pos) and pos==sorted(pos),f'{scr}: all six realms shown in list order {pos}')
    pg.evaluate("go('guide')");pg.wait_for_timeout(400)
    ck('save all six realms' in pg.inner_text('#app'),'guide: "save all six realms"')
    ck(pg.evaluate("(()=>{const b=badgesOf('emi').find(x=>x.k==='finisher');return !!b&&/one realm/.test(b.how)})()"),'Realm Finisher badge reads realms from the list')
    # ---------- 2. v19 save migration ----------
    sv=json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))
    e=sv['profiles']['emi'];o=V19['profiles']['emi']
    ck(all(e[k]==o[k] for k in o),'v19 save: every Emi field kept exactly (stars, subjects, rewards, eq, v18 stats)')
    ck(sv['profiles']['sage']['ss']==V19['profiles']['sage']['ss'] and sv['muted'] is True and sv['lastHero']=='emi','v19 save: other heroes and settings kept')
    ck(pg.evaluate("localStorage.getItem('ttq-save-v2-backup')")==pg.evaluate("localStorage.getItem('ttq-save-v2')"),'backup copy written on save')
    ck(pg.locator('#nrNote').count()==0 and not errs,f'no notice and no errors for a healthy save {errs}')
    c.close()
    # ---------- 3. schema defaults ----------
    c,pg,errs=newctx(b,save={'ttq-save-v2':json.dumps({"muted":"yes","hero":"nobody","profiles":{"emi":{"name":7,"stars":{"2":3,"3":"x"},"rewards":"bad","eq":[]},"zea":"oops"}})})
    s=pg.evaluate("save")
    ck(s['muted'] is False and s['hero'] is None and s['profiles']['emi']['name']=='Emi' and s['profiles']['emi']['stars']=={'2':3} and s['profiles']['emi']['rewards']==[] and s['profiles']['emi']['eq']=={} and s['profiles']['zea']['stars']=={},'bad field types get safe defaults, good data kept')
    c.close()
    # ---------- 4. corrupt save -> backup recovery ----------
    good=json.dumps(V19)
    c,pg,errs=newctx(b,save={'ttq-save-v2':'{"profiles":{"emi":{"sta','ttq-save-v2-backup':good})
    ck(pg.evaluate("save.profiles.emi.stars['2']")==3 and pg.evaluate("NRStore.source")=='backup','corrupt main save: progress recovered from backup')
    ck(pg.is_visible('#nrNote[data-kind=recovered]') and 'backup' in pg.inner_text('#nrNote'),'gentle recovery notice shown')
    ck(pg.evaluate("localStorage.getItem('ttq-save-v2-corrupt')")=='{"profiles":{"emi":{"sta','damaged copy kept (never wiped silently)')
    ck(json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))['profiles']['emi']['stars']['2']==3,'main save repaired from backup')
    pg.click('#nrNoteOk');ck(pg.locator('#nrNote').count()==0,'notice can be dismissed')
    ck(not errs,f'no errors {errs}');c.close()
    c,pg,errs=newctx(b,save={'ttq-save-v2':'garbage{'})
    ck(pg.is_visible('#nrNote[data-kind=unreadable]') and pg.evaluate("localStorage.getItem('ttq-save-v2-corrupt')")=='garbage{','unreadable save, no backup: fresh game, notice, damaged copy kept')
    c.close()
    # ---------- 5. localStorage throws (private mode / quota) ----------
    THROW="(()=>{const E=()=>{throw new DOMException('denied','SecurityError')};Storage.prototype.getItem=E;Storage.prototype.setItem=E;Storage.prototype.removeItem=E;})()"
    for w in [390,1280]:
        c,pg,errs=newctx(b,w=w,init=THROW)
        ck(pg.is_visible('#nrNote[data-kind=storage]') and 'private browsing' in pg.inner_text('#nrNote'),f'{w}: storage-blocked notice shown')
        pg.click('#nrNoteOk')
        pg.evaluate("pickHero('emi')");pg.wait_for_timeout(500)
        pg.evaluate("save.profiles.emi.stars['5']=2;persist()")
        ck(pg.evaluate("save.hero")=='emi' and json.loads(pg.evaluate("NRStore.mem['ttq-save-v2']"))['profiles']['emi']['stars']['5']==2,f'{w}: game playable, progress held in memory')
        pg.evaluate("openChapter('add',1)");pg.wait_for_timeout(800)
        ck(len(pg.inner_text('#app'))>20 and not errs,f'{w}: chapter opens with storage blocked, no errors {errs}')
        c.close()
    # ---------- 6. export / import round trip ----------
    c,pg,errs=newctx(b,save={'ttq-save-v2':good})
    rt=pg.evaluate("""(async()=>{const c=await pcMake();const r=await pcRead(c);const out={code:c,same:JSON.stringify(r.save.profiles)===JSON.stringify(NRStore.validate(save).profiles)};
     const bad=async x=>{try{await pcRead(x);return 'accepted'}catch(e){return e.message}};const p=c.split('.');
     out.flip=await bad(p[0]+'.'+p[1]+'.'+p[2]+'.'+(p[3][0]==='a'?'b':'a')+p[3].slice(1));
     out.cut=await bad(c.slice(0,Math.floor(c.length*.6))+'.'+p[3]);out.junk=await bad('hello world');out.wrongver=await bad('NR9'+c.slice(3));
     const j=JSON.stringify({v:1,app:'20',save:{nope:1}});const {crc32:_}={};out.schema=await bad(['NR1','j',b64u.enc(new TextEncoder().encode(j)),crc32(j)].join('.'));
     out.ws=(await pcRead(c.replace(/(.{40})/g,'$1\\n  '))).save.profiles.emi.stars['2'];return out})()""")
    ck(rt['code'].startswith('NR1.') and rt['same'],f'export/import round trip keeps all progress (code {len(rt["code"])} chars)')
    ck(rt['flip']=='checksum','changed checksum rejected')
    ck(rt['cut'] in ('damaged','checksum','format'),f'cut-off code rejected ({rt["cut"]})')
    ck(rt['junk']=='format' and rt['wrongver']=='format','junk / unknown version rejected')
    ck(rt['schema']=='schema','valid checksum but bad save shape rejected')
    ck(rt['ws']==3,'pasted code with line breaks/spaces still loads')
    code=rt['code'];c.close()
    # UI flow on a fresh device
    for w in [390,1280]:
        c,pg,errs=newctx(b,w=w)
        pg.evaluate("go('settings')");pg.wait_for_timeout(400)
        t=pg.inner_text('#progressCard')
        ck('For grown-ups' in t and 'only on this device' in t and 'no accounts' in t,f'{w}: card labeled For grown-ups + stored only on this device')
        ck(pg.locator('#pcCopy').is_visible() and pg.locator('#pcDl').is_visible(),f'{w}: copy + download buttons')
        pg.fill('#pcIn',code[:-3]+'zzz');pg.click('#pcCheck');pg.wait_for_timeout(300)
        ck(pg.is_visible('#pcErr') and pg.locator('#pcConfirm').count()==0,f'{w}: bad code shows a clear error, nothing replaced')
        pg.fill('#pcIn',code);pg.click('#pcCheck');pg.wait_for_timeout(400)
        pv=pg.inner_text('#pcPrev')
        ck(pg.is_visible('#pcConfirm') and 'Emi' in pv and '⭐ ' in pv and pg.is_visible('#pcBackupFirst'),f'{w}: preview shows heroes and stars, offers a backup first')
        ck(pg.evaluate("localStorage.getItem('ttq-save-v2')") is None or json.loads(pg.evaluate("localStorage.getItem('ttq-save-v2')"))['profiles']['emi']['stars']=={},f'{w}: nothing changes before confirming')
        with pg.expect_download() as dl:pg.click('#pcBackupFirst')
        ck(dl.value.suggested_filename.startswith('numirealm-progress-'),f'{w}: backup download offered ({dl.value.suggested_filename})')
        pg.click('#pcNo');pg.wait_for_timeout(200);ck(pg.locator('#pcConfirm').count()==0,f'{w}: cancel closes the preview')
        pg.click('#pcCheck');pg.wait_for_timeout(400);pg.click('#pcYes');pg.wait_for_timeout(1800)
        ck(pg.evaluate("save.profiles.emi.stars['2']")==3 and pg.evaluate("save.profiles.emi.ss.add['1']")==3,f'{w}: confirmed load replaces progress')
        ck(pg.is_visible('#nrNote') and 'Progress loaded' in pg.inner_text('#nrNote'),f'{w}: loaded notice after reload')
        lay=pg.evaluate("(()=>{go('settings');const c=document.getElementById('progressCard');const bs=[...c.querySelectorAll('button')].filter(b=>b.offsetParent);return {ov:document.documentElement.scrollWidth<=innerWidth,min:Math.min(...bs.map(b=>b.getBoundingClientRect().height)),order:[...document.querySelectorAll('#app .card')].map(x=>x.id||x.querySelector('h2')?.textContent.slice(0,12)).join('|')}})()")
        ck(lay['ov'] and lay['min']>=44,f'{w}: no overflow, buttons >= 44px {lay}')
        if w==390:o390=lay['order']
        else:ck(lay['order']==o390,'settings card order identical on phone and desktop')
        ck(not errs,f'{w}: no errors {errs}');c.close()
    b.close()
# ---------- 7. honest labels ----------
txt=re.sub(r'<style[\s\S]*?</style>','',HTML)
txt=txt.replace('There are no accounts and no cloud copy','')
bad=re.findall(r'.{30}\b(?:sign[ -]?in|log[ -]?in|sign up|your account|accounts|cloud|sync(?:ed|ing)?|subscri\w+|payments?|premium|purchase|parent dashboard|upgrade to)\b.{30}',txt,re.I)
bad=[x for x in bad if not re.search(r'apple-mobile|crossorigin|async|Cloud Pup|every sign in|EVERY sign in|Enhanced|enhanced\|premium',x)]
ck(not bad,f'no accounts / sync / payment claims in the game {bad[:5]}')
for w in ['practise','colour','favourite','centre','harbour','cosy','defence','behaviour','Brackets','Lighter skin','All six heroes','backed-up','licence','analyse']:
    ck(w not in HTML,'US spelling: no '+w)
print('RESULT','PASS' if not FAILS else 'FAIL',len(FAILS));sys.exit(1 if FAILS else 0)
