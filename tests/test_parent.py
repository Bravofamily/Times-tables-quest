# Parent Area PHASE 1 (test, v26 repo layout: pages next to index.html) - parent.html + patched game, Supabase endpoints mocked.
# Usage: PWB=chromium|webkit python test_parent.py   (SHOTS=1 -> /workspace/parent/shots)
import os,json,re,threading,http.server,functools,time,uuid,random,datetime
from urllib.parse import urlparse,parse_qs,unquote
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)));BR=os.environ.get('PWB','chromium');SH=os.environ.get('SHOTS')=='1';OUT=os.environ.get('SHOTS_DIR','/tmp/numirealm-parent-shots');HOUT=os.environ.get('HEADER_SHOTS_DIR','/tmp/numirealm-header-shots')
os.makedirs(OUT,exist_ok=True) if SH else None
PORT=8881 if BR=='chromium' else 8882
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
HOST=f'http://localhost:{PORT}'
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c: fails.append(m)
SB='https://uuigasrelqbwxopvqoib.supabase.co'
def now(): return datetime.datetime.now(datetime.timezone.utc)
# ---------- stateful mock of the Supabase REST/Auth API (mirrors setup.sql behavior) ----------
class Mock:
    def __init__(s): s.reset()
    def reset(s):
        s.uid=str(uuid.uuid4());s.parents=[];s.consent=[];s.kids=[];s.devices=[];s.codes={};s.progress={};s.events=[];s.calls=[];s.down=False;s.pushes=[]
    def user(s): return {'id':s.uid,'email':'parent@example.com','aud':'authenticated','role':'authenticated','app_metadata':{},'user_metadata':{},'created_at':now().isoformat()}
    def session(s): return {'access_token':'test-access','token_type':'bearer','expires_in':3600,'expires_at':int(time.time())+3600,'refresh_token':'test-refresh','user':s.user()}
    def table(s,t): return {'parents':s.parents,'parent_consent':s.consent,'kids':s.kids,'devices':s.devices,'progress':list(s.progress.values()),'progress_events':s.events}[t]
M=Mock()
def flt(rows,qs):
    out=rows
    for k,v in qs.items():
        if k in('select','order','limit','columns','offset'): continue
        v=v[0]
        if v.startswith('eq.'): out=[r for r in out if str(r.get(k))==v[3:]]
        elif v=='is.null': out=[r for r in out if r.get(k) is None]
    if 'limit' in qs: out=out[:int(qs['limit'][0])]
    return out
def handler(route):
    req=route.request;u=urlparse(req.url);path=u.path;qs=parse_qs(u.query);meth=req.method
    if meth=='OPTIONS': return route.fulfill(status=200,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*'})
    M.calls.append((meth,path))
    if M.down: return route.abort()
    body={}
    try: body=json.loads(req.post_data or '{}')
    except Exception: pass
    H={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'}
    def ok(o,st=200): return route.fulfill(status=st,headers=H,body=json.dumps(o))
    if path=='/auth/v1/otp': return ok({})
    if path=='/auth/v1/verify': return ok(M.session()) if body.get('token')=='123456' else ok({'code':403,'error_code':'otp_expired','msg':'Token has expired or is invalid'},403)
    if path=='/auth/v1/user': return ok(M.user())
    if path=='/auth/v1/logout': return route.fulfill(status=204,headers=H,body='')
    if path.startswith('/rest/v1/rpc/'):
        fn=path.rsplit('/',1)[1]
        if fn=='create_link_code':
            c=''.join(random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
            M.codes[c]={'kid':body['p_kid_id'],'exp':now()+datetime.timedelta(minutes=10),'used':False}
            return ok([{'code':c,'expires_at':M.codes[c]['exp'].isoformat()}])
        if fn=='redeem_link_code':
            c=re.sub('[^A-Z0-9]','',(body.get('p_code') or '').upper());x=M.codes.get(c)
            if not x or x['used'] or x['exp']<now(): return ok({'ok':False,'error':'invalid_or_expired'})
            x['used']=True;tok=uuid.uuid4().hex*3;d={'id':str(uuid.uuid4()),'parent_id':M.uid,'kid_id':x['kid'],'device_name':body.get('p_device_name'),'token':tok,'created_at':now().isoformat(),'last_seen_at':None,'revoked_at':None}
            M.devices.append(d);k=[k for k in M.kids if k['id']==x['kid']][0]
            return ok({'ok':True,'device_token':tok,'device_id':d['id'],'kid_id':x['kid'],'nickname':k['nickname']})
        if fn=='push_progress':
            d=[d for d in M.devices if d['token']==body.get('p_device_token')]
            if not d or d[0]['revoked_at']: return ok({'ok':False,'error':'unlinked'})
            d=d[0];p=body['p_payload'];M.pushes.append(p);d['last_seen_at']=now().isoformat()
            M.progress[d['kid_id']]={'kid_id':d['kid_id'],'parent_id':M.uid,'hero':p.get('hero'),'realms':p['realms'],'skills':p['skills'],'time_played_sec':p['time_played_sec'],'lanterns_used':p['lanterns_used'],'examples_opened':p['examples_opened'],'updated_at':now().isoformat()}
            return ok({'ok':True})
        if fn=='unlink_device':
            for d in M.devices:
                if d['id']==body['p_device_id']: d['revoked_at']=now().isoformat();return ok({'ok':True})
            return ok({'ok':False,'error':'not_found'})
        if fn=='unlink_this_device':
            for d in M.devices:
                if d['token']==body.get('p_device_token'): d['revoked_at']=now().isoformat()
            return ok({'ok':True})
        return ok({'message':'unknown rpc'},404)
    if path.startswith('/rest/v1/'):
        t=path.rsplit('/',1)[1]
        if meth=='GET':
            rows=flt(M.table(t),qs)
            if 'kids'==t: rows=[dict(r) for r in rows]
            if 'devices'==t: rows=[{k:v for k,v in r.items() if k!='token'} for r in rows]
            if 'vnd.pgrst.object' in (req.headers.get('accept') or ''):
                return ok(rows[0]) if rows else ok({'code':'PGRST116','message':'0 rows'},406)
            return ok(rows)
        if meth=='POST':
            rows=body if isinstance(body,list) else [body]
            for r in rows:
                if t=='kids':
                    if len(M.kids)>=2: return ok({'code':'P0001','message':'kid_limit: a parent account can have at most 2 kids'},400)
                    if not M.consent: return ok({'code':'42501','message':'new row violates row-level security policy'},403)
                    r=dict(r,id=str(uuid.uuid4()),created_at=now().isoformat());M.kids.append(r)
                elif t=='parents': M.parents.append(r)
                elif t=='parent_consent': M.consent.append(dict(r,agreed_at=now().isoformat()))
            return route.fulfill(status=201,headers=H,body='')
    return ok({'message':'not mocked'},404)
def noscroll(pg,m): ck(pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),m+': no sideways scroll')
def small_btns(pg): return pg.evaluate("[...document.querySelectorAll('button')].filter(b=>b.offsetParent&&(b.getBoundingClientRect().height<44||b.getBoundingClientRect().width<44)).map(b=>b.id||b.textContent.trim().slice(0,20))")
SAVE={"muted":True,"narrator":False,"lastHero":"emi","hero":"emi","profiles":{"emi":{"name":"Emi","stars":{"2":3,"10":2,"5":1},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":"6-7","grade":"1",
  "subj":{"add":{"stars":{"1":3,"2":3,"3":1},"hist":{},"intro":True},"frac":{"stars":{"1":2,"2":0},"hist":{},"intro":True}}},
  "sage":{"name":"Sage","stars":{},"hist":{},"rewards":[],"eq":{},"prologue":True,"subj":{"sub":{"stars":{"1":3},"hist":{},"intro":True}}}}}
def backck(pg,m,href='./'):
    # v27: 'Back to NumiRealm' pill top-left in the header, visible without scrolling, >=44px, links to the game Home
    r=pg.evaluate("(()=>{const a=document.getElementById('nrBack');if(!a)return null;const b=a.getBoundingClientRect(),cs=getComputedStyle(a);return {top:b.top+scrollY,left:b.left+scrollX,w:b.width,h:b.height,vw:innerWidth,vh:innerHeight,vis:cs.display!=='none'&&cs.visibility!=='hidden'&&b.width>0,inHeader:!!a.closest('header'),href:a.getAttribute('href'),txt:a.textContent}})()")
    ck(bool(r) and r['vis'] and r['inHeader'] and r['top']>=0 and r['top']+r['h']<=r['vh'] and r['left']<r['vw']/2 and r['h']>=44 and r['w']>=44 and 'Back to NumiRealm' in r['txt'] and r['href']==href,f'{m}: Back to NumiRealm button top-left, >=44px, href {href} ({r})')
def hdrshot(pg,name):
    if not SH: return
    os.makedirs(HOUT,exist_ok=True);pg.evaluate("scrollTo(0,0)");bb=pg.locator('header').bounding_box()
    pg.screenshot(path=f'{HOUT}/{name}.png',clip={'x':0,'y':0,'width':pg.viewport_size['width'],'height':min(pg.viewport_size['height'],bb['y']+bb['height']+40)})
def ctx(b,w,h,mob):
    kw=dict(viewport={'width':w,'height':h},service_workers='block')
    if mob: kw.update(has_touch=True,**({'is_mobile':True,'device_scale_factor':2} if BR=='chromium' else {}))
    c=b.new_context(**kw);c.route(SB+'/**',handler);return c
def watch(pg): pg.on('console',lambda x: errs.append(x.text) if x.type=='error' and 'favicon' not in x.text and 'Failed to load resource' not in x.text else None);pg.on('pageerror',lambda e: errs.append('PAGEERR '+str(e)))
def game(c,q=''):
    c.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('ttq-save-v2',%s);}"%json.dumps(json.dumps(SAVE)))
    pg=c.new_page();watch(pg);pg.goto(f'{HOST}/index.html{q}');pg.wait_for_timeout(1300);return pg
with sync_playwright() as p:
    b=getattr(p,BR).launch()
    for tag,w,h,mob in [('desktop',1280,900,False),('phone',390,844,True)]:
        M.reset()
        # ---------------- parent: login ----------------
        c=ctx(b,w,h,mob);pg=c.new_page();watch(pg);pg.goto(f'{HOST}/parent.html');pg.wait_for_selector('#email')
        ck(pg.locator('#testBanner').is_visible() and 'TEST VERSION' in pg.inner_text('#testBanner'),f'{tag}: Test version banner shown')
        ck(pg.evaluate("typeof supabase!=='undefined'&&!!document.querySelector('script[src=\"vendor/supabase.js\"]')&&![...document.scripts].some(s=>s.src&&new URL(s.src).origin!==location.origin)"),f'{tag}: supabase-js is vendored, no CDN scripts')
        noscroll(pg,f'{tag} login');backck(pg,f'{tag} login');hdrshot(pg,f'{BR}-{tag}-login-header')
        ck(pg.inner_text('#loginH')=='Parent Login' and pg.get_attribute('#whatLink','href')=='parent-about.html' and pg.get_attribute('#navAbout','href')=='parent-about.html',f'{tag}: login screen has What\'s included? link + header nav')
        ck(pg.locator('#welcomeBtn').is_hidden(),f'{tag}: account guide hidden before sign-in')
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-1-login.png')
        pg.click('#goSignup');pg.wait_for_timeout(400)
        ck(pg.inner_text('#loginH')=='Create your parent account' and pg.locator('#signupSteps li').count()==4,f'{tag}: sign-up path on the login page');backck(pg,f'{tag} signup steps')
        pg.click('#goLogin');pg.wait_for_timeout(300);ck(pg.inner_text('#loginH')=='Parent Login',f'{tag}: back to login')
        # ---------------- benefits page (no sign-in) ----------------
        ab=c.new_page();watch(ab);ab.goto(f'{HOST}/parent-about.html');ab.wait_for_selector('#benefits')
        at=ab.inner_text('main')
        ck(ab.locator('#benefits li').count()==6 and ab.locator('#soon li').count()==2 and at.count('Coming soon')==2 and 'Weekly email reports' in at and 'Premium area' in at,f'{tag}: benefits page: 6 benefits, 2 Coming soon')
        ck(all(x in at for x in ['6 realms','Needs practice','Trend graphs','Up to 2 kids','offline','Nickname only','No ads, no tracking','Delete any time']),f'{tag}: benefits + kid-safety text')
        ck('stays free' in ab.inner_text('#freeNote') and not re.search(r'[$€£]|\bprice|/mo\b|per month',ab.inner_text('body'),re.I),f'{tag}: game-stays-free, no prices')
        ck(ab.evaluate("![...document.scripts].some(s=>s.src)&&![...document.querySelectorAll('link[href^=http],img[src^=http]')].length"),f'{tag}: benefits page loads nothing external, needs no sign-in')
        noscroll(ab,f'{tag} benefits page');backck(ab,f'{tag} benefits page');hdrshot(ab,f'{BR}-{tag}-whats-included-header')
        if SH: ab.screenshot(path=f'{OUT}/{BR}-{tag}-10-benefits-page.png',full_page=True)
        ab.click('#ctaLogin');ab.wait_for_selector('#loginH');ck(ab.url.endswith('/parent.html#login') and ab.inner_text('#loginH')=='Parent Login',f'{tag}: benefits CTA opens Parent Login');ab.close()
        pg.fill('#email','bad');pg.click('#sendBtn');ck(pg.locator('#err').count()==1,f'{tag}: invalid email rejected')
        pg.fill('#email','parent@example.com');pg.click('#sendBtn');pg.wait_for_selector('#otp');backck(pg,f'{tag} email code')
        ck(('POST','/auth/v1/otp') in M.calls,f'{tag}: email code requested')
        pg.fill('#otp','000000');pg.click('#verifyBtn');pg.wait_for_selector('#err');ck(True,f'{tag}: wrong code shows error')
        pg.fill('#otp','123456');pg.click('#verifyBtn');pg.wait_for_selector('#consentChk')
        ck(len(M.parents)==1 and M.parents[0]['id']==M.uid,f'{tag}: parent profile row created')
        noscroll(pg,f'{tag} consent');backck(pg,f'{tag} consent')
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-2-consent.png',full_page=True)
        pg.click('#consentBtn');ck(pg.locator('#err').count()==1 and not M.consent,f'{tag}: consent needs the checkbox')
        pg.check('#consentChk');pg.click('#consentBtn');pg.wait_for_selector('#noKids')
        ck(pg.locator('#welcomeCard').is_visible() and pg.locator('#welcomeList li').count()==6 and all(x in pg.inner_text('#welcomeCard') for x in ['up to 2 kids','with a code','realm progress','Needs practice','Trend graphs','remove devices and data']),f'{tag}: welcome checklist shown right after consent')
        noscroll(pg,f'{tag} welcome');backck(pg,f'{tag} welcome checklist')
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-12-welcome.png',full_page=True)
        pg.click('#welcomeClose');ck(pg.locator('#welcomeCard').count()==0 and pg.locator('#welcomeBtn').is_visible(),f'{tag}: welcome dismissible')
        pg.click('#welcomeBtn');ck(pg.locator('#welcomeCard').is_visible(),f'{tag}: welcome re-opens from Account guide');pg.click('#welcomeClose')
        ck(len(M.consent)==1 and M.consent[0]['consent_version']=='test-1' and len(M.consent[0]['consent_text'])>50,f'{tag}: consent row saved with version and text')
        # ---------------- add kids ----------------
        for nick,age,gr in [('Mia','6-7','1'),('Leo','8-10','3')]:
            pg.click('#addKidBtn');pg.fill('#kNick',nick);pg.select_option('#kAge',age);pg.select_option('#kGrade',gr);pg.click('#saveKid');pg.wait_for_selector('#msg')
        ck([k['nickname'] for k in M.kids]==['Mia','Leo'] and M.kids[1]['age_range']=='8-10',f'{tag}: two kids added')
        ck(pg.locator('#addKidBtn').count()==0 and 'up to 2 kids' in pg.inner_text('#familyCard'),f'{tag}: Add kid hidden at 2 kids')
        ck(not small_btns(pg),f'{tag}: parent buttons >= 44px {small_btns(pg)}')
        mia=M.kids[0]['id']
        pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#noProgress')
        pg.click('#makeCode');pg.wait_for_selector('#linkCode')
        code=pg.inner_text('#linkCode').strip()
        ck(re.fullmatch(r'[A-HJ-NP-Z2-9]{6}',code) is not None,f'{tag}: link code shown ({code})')
        ck(re.fullmatch(r'(9|10):\d\d',pg.inner_text('#countdown')) is not None,f'{tag}: 10-minute countdown ({pg.inner_text("#countdown")})')
        ck(pg.locator('#qr svg').count()==1,f'{tag}: QR code drawn')
        noscroll(pg,f'{tag} link code')
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-5-link-code.png',full_page=True)
        # ---------------- game without the flag: hidden ----------------
        gc=ctx(b,w,h,mob);g0=game(gc,'');n0=len(M.calls);g0.evaluate("settingsScreen()");g0.wait_for_timeout(500)
        ck(g0.locator('#parentLink').count()==0 and g0.locator('#voiceSel').count()+g0.locator('#progressCard').count()>0,f'{tag}: parent link hidden without ?parenttest=1')
        ck(len(M.calls)==n0,f'{tag}: game makes no Supabase calls without the flag')
        ck(g0.evaluate("titleScreen(),!document.getElementById('nrParentHome')"),f'{tag}: Home parent card hidden without ?parenttest=1')
        g0.close()
        # ---------------- Home-screen Parent Login card (flag) ----------------
        gh=game(gc,'?parenttest=1');gh.evaluate("titleScreen()");gh.wait_for_timeout(500)
        ck(gh.evaluate("(e=>e&&e.nextElementSibling&&e.nextElementSibling.id==='nrApp')(document.getElementById('nrParentHome'))"),f'{tag}: Home card sits right above Get the NumiRealm app')
        ht=gh.inner_text('#nrParentHome')
        ck(gh.inner_text('#nrParentHome h3').strip().endswith('Parent Login') and gh.locator('#nrParentHome button.btn').count()==1 and gh.locator('#nrhWhat').is_visible() and 'Create' not in ht and not re.search(r'[$€£]|price',ht,re.I),f'{tag}: Home card: title, one Parent Login button, What\'s included? link')
        noscroll(gh,f'{tag} home card');ck(not [x for x in small_btns(gh) if x.startswith('nrh')],f'{tag}: home card buttons >= 44px')
        if SH: gh.locator('#nrParentHome').scroll_into_view_if_needed();gh.screenshot(path=f'{OUT}/{BR}-{tag}-8-home-parent-card.png')
        gh.evaluate("void(NRH.leave=u=>{window._left=u})")
        gh.click('#nrhLogin');ck(gh.locator('#nrhGate').count()==1 and gh.locator('#nrhLogin').count()==0,f'{tag}: grown-up gate before leaving the game')
        noscroll(gh,f'{tag} home gate')
        if SH: gh.locator('#nrParentHome').scroll_into_view_if_needed();gh.screenshot(path=f'{OUT}/{BR}-{tag}-9-home-gate.png')
        gh.fill('#nrhGate','3');gh.click('#nrhGo');ck(gh.locator('#nrhErr').count()==1 and not gh.evaluate("window._left"),f'{tag}: wrong gate answer stays in the game')
        gh.click('#nrhCancel');ck(gh.locator('#nrhLogin').count()==1,f'{tag}: gate cancel')
        def solve(): a,bb,cc=map(int,re.findall(r'\d+',gh.inner_text('#nrhQ'))[:3]);gh.fill('#nrhGate',str(a*bb+cc));gh.press('#nrhGate','Enter')
        gh.click('#nrhWhat');ck(gh.locator('#nrhGate').count()==1,f'{tag}: What\'s included? is gated too');solve();ck(gh.evaluate("window._left")=='parent-about.html?parenttest=1',f'{tag}: What\'s included? goes to benefits page')
        gh.evaluate("void(NRH.leave=u=>{location.href=u})");gh.click('#nrhLogin');solve();gh.wait_for_selector('#loginH',timeout=8000)
        ck(gh.url.endswith('/parent.html?parenttest=1#login') and gh.inner_text('#loginH')=='Parent Login',f'{tag}: Parent Login opens parent.html login')
        backck(gh,f'{tag} login from test game',href='./?parenttest=1')
        gh.goto(f'{HOST}/parent-about.html');gh.wait_for_selector('#benefits');backck(gh,f'{tag} benefits from test game',href='./?parenttest=1')
        gh.click('#nrBack');gh.wait_for_selector('#nrParentHome',timeout=8000)
        ck(gh.url==f'{HOST}/?parenttest=1',f'{tag}: Back to NumiRealm opens the test game Home with the flag kept ({gh.url})')
        gh.close()
        # ---------------- game with flag: gate, link ----------------
        g=game(gc,f'?parenttest=1&link={code}');g.wait_for_timeout(300)
        if not g.locator('#parentLink').count(): g.evaluate("settingsScreen()");g.wait_for_timeout(400)
        ck(g.locator('#plOpen').count()==1 and 'Link to a parent account (test)' in g.inner_text('#plOpen'),f'{tag}: "Link to a parent account (test)" shown with flag')
        g.click('#plOpen');ck(g.locator('#plGate').count()==1 and g.locator('#plCode').count()==0,f'{tag}: grown-up gate before the code form')
        g.fill('#plGate','1');g.click('#plGateGo');ck(g.locator('#plErr').count()==1 and g.locator('#plCode').count()==0,f'{tag}: wrong gate answer blocked')
        a,bb,cc=map(int,re.findall(r'\d+',g.inner_text('#plGateQ'))[:3]);g.fill('#plGate',str(a*bb+cc));g.click('#plGateGo')
        ck(g.input_value('#plCode')==code,f'{tag}: code prefilled from QR link')
        g.select_option('#plHero','emi');g.fill('#plDev','Mia\'s tablet')
        noscroll(g,f'{tag} kid link form');ck(not [x for x in small_btns(g) if x.startswith('pl')],f'{tag}: kid-side link buttons >= 44px')
        if SH: g.locator('#parentLink').scroll_into_view_if_needed();g.screenshot(path=f'{OUT}/{BR}-{tag}-6-kid-link-form.png')
        g.click('#plLink');g.wait_for_selector('#plStatus');g.wait_for_timeout(600)
        L=g.evaluate("JSON.parse(localStorage.getItem('nr-parent-link'))")
        ck(L and len(L['token'])==96 and L['hero']=='emi' and L['nickname']=='Mia',f'{tag}: device token stored with hero')
        ck(M.pushes and M.pushes[-1]['realms']['add']['stars']==7,f'{tag}: first progress summary pushed after linking')
        if SH: g.locator('#parentLink').screenshot(path=f'{OUT}/{BR}-{tag}-7-kid-linked.png')
        # ---------------- payload normalization from the real save format ----------------
        P=g.evaluate("NRP.payload(save,'emi',{h:{emi:{s:{'mult:x7':{n:'×7 facts',r:6,t:10,l:3}},sec:125.4,lan:3,ex:2}}})")
        exp=g.evaluate("Object.fromEntries(SUBJ.map(x=>[x.id,[sStars(x.id,save.profiles.emi),sCount(x.id)]]))")
        ck(all(P['realms'][k]['stars']==exp[k][0] and P['realms'][k]['total']==exp[k][1] and P['realms'][k]['max']==exp[k][1]*3 for k in exp),f'{tag}: realm stars/totals match the game ({P["realms"]})')
        ck(P['realms']['add']['chapters']==3 and P['realms']['mult']['chapters']==3 and P['realms']['frac']['chapters']==1 and P['realms']['sub']['chapters']==0,f'{tag}: chapters counted (0-star chapters ignored, other heroes ignored)')
        ck(P['skills']=={'mult:x7':{'n':'×7 facts','r':6,'t':10,'l':3}} and P['time_played_sec']==125 and P['lanterns_used']==3 and P['examples_opened']==2 and P['hero']=='emi',f'{tag}: skills/time/lanterns/examples normalized')
        ck(set(P.keys())=={'v','hero','realms','skills','time_played_sec','lanterns_used','examples_opened','client_at'} and 'name' not in json.dumps(P['realms']),f'{tag}: payload has only the minimal fields')
        g.evaluate("NRP.stats&&localStorage.removeItem('nr-parent-stats');SS={sid:'frac',c:3,ch:{skill:'halves, thirds and fourths'},cur:{}};NRP.rec('ans',true);NRP.rec('ans',false);NRP.rec('lan');NRP.rec('ex');SS=null")
        st=g.evaluate("JSON.parse(localStorage.getItem('nr-parent-stats')).h.emi")
        ck(st['s']['frac:c3']=={'n':'halves, thirds and fourths','r':1,'t':2,'l':1} and st['lan']==1 and st['ex']==1,f'{tag}: answers/lanterns/examples recorded per skill while linked')
        # ---------------- offline queue ----------------
        npush=len(M.pushes);gc.set_offline(True);M.down=True
        g.evaluate("save.profiles.emi.subj.add.stars['4']=3;persist()");g.wait_for_timeout(3600)
        ck(g.evaluate("!!localStorage.getItem('nr-parent-queue')") and len(M.pushes)==npush,f'{tag}: offline change is queued, not lost')
        g.evaluate("settingsScreen()");g.wait_for_timeout(300);ck(g.locator('#plPending').count()==1,f'{tag}: settings shows 1 update waiting')
        gc.set_offline(False);g.reload();g.wait_for_timeout(1200)  # page reload needs the local server; Supabase stays down
        ck(g.evaluate("!!localStorage.getItem('nr-parent-queue')"),f'{tag}: queue survives a reload while offline')
        qat=g.evaluate("JSON.parse(localStorage.getItem('nr-parent-queue')).at");gc.set_offline(False);M.down=False;g.evaluate("dispatchEvent(new Event('online'))");g.wait_for_timeout(2500)
        ck(len(M.pushes)>npush and M.pushes[-1]['realms']['add']['stars']==10 and g.evaluate("(q=>!q||JSON.parse(q).at>%d)(localStorage.getItem('nr-parent-queue'))"%qat),f'{tag}: queue sent when back online')
        # resume push
        n2=len(M.pushes);g.evaluate("document.dispatchEvent(new Event('visibilitychange'))");g.wait_for_timeout(3600);ck(len(M.pushes)>n2,f'{tag}: progress pushed on resume')
        # ---------------- parent dashboard ----------------
        today=datetime.date.today()
        M.events[:]=[{'kid_id':mia,'parent_id':M.uid,'day':(today-datetime.timedelta(days=6-i)).isoformat(),'stars_total':6+i*2,'answers_right':10+i*6,'answers_total':20+i*7,'minutes':5+i*4} for i in range(7)]
        M.progress[mia]['skills']={'mult:x7':{'n':'×7 facts','r':6,'t':14,'l':4},'add:c2':{'n':'adding within 20','r':19,'t':20,'l':0},'frac:c3':{'n':'halves, thirds and fourths','r':3,'t':6,'l':1}}
        M.progress[mia]['time_played_sec']=2460;M.progress[mia]['lanterns_used']=5;M.progress[mia]['examples_opened']=3
        pg.reload();pg.wait_for_selector('#familyCard')
        ft=pg.inner_text('#familyCard')
        ck('Mia' in ft and 'Needs practice: ×7 facts' in ft and '41 min' in ft,f'{tag}: family overview card shows realm, minutes, needs-practice skill')
        ck("Mia's tablet" in pg.inner_text('#allDevices'),f'{tag}: device listed')
        noscroll(pg,f'{tag} family');backck(pg,f'{tag} family')
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-3-family.png',full_page=True)
        pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#realms')
        kt=pg.inner_text('#kidCard')
        ck('3/11' in pg.inner_text('#realms') or re.search(r'4/\d+ ch',pg.inner_text('#realms')) is not None,f'{tag}: realm progress rows')
        ck(pg.inner_text('#struggles').index('×7 facts')<pg.inner_text('#struggles').index('halves') and 'adding within 20' not in pg.inner_text('#struggles'),f'{tag}: struggle skills sorted, strong skills excluded')
        ck(pg.locator('#trendSvg polyline').count()==1 and pg.locator('#trendSvg circle').count()==7 and pg.locator('#trendSvg rect').count()==7,f'{tag}: inline SVG trend chart')
        noscroll(pg,f'{tag} kid detail');backck(pg,f'{tag} kid detail')
        ck(not small_btns(pg),f'{tag} kid detail: all buttons >=44px')
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-4-kid-detail.png',full_page=True)
        # ---------------- v27: back to the game keeps the parent signed in ----------------
        np=c.new_page();watch(np);np.goto(f'{HOST}/parent.html');np.wait_for_selector('#allDevices',timeout=8000);backck(np,f'{tag} signed-in family (new tab, no flag)')
        np.click('#nrBack');np.wait_for_function("typeof settingsScreen==='function'",timeout=8000)
        ck(np.url==f'{HOST}/' and np.locator('#nrParentHome').count()==0,f'{tag}: Back to NumiRealm opens the normal game Home ({np.url})')
        np.goto(f'{HOST}/parent.html');np.wait_for_selector('#allDevices',timeout=8000)
        ck(np.locator('#email').count()==0 and np.locator('#signOut').is_visible(),f'{tag}: parent still signed in after going back to the game');np.close()
        # ---------------- unlink from dashboard -> device learns it ----------------
        dev=[d for d in M.devices if not d['revoked_at']][0]['id']
        pg.once('dialog',lambda d: d.accept());pg.click(f'button[data-unlink="{dev}"]');pg.wait_for_selector('#msg')
        ck([d for d in M.devices if d['id']==dev][0]['revoked_at'] is not None and 'No devices' in pg.inner_text('#kidDevices'),f'{tag}: parent removes device')
        g.evaluate("NRP.syncNow()");g.wait_for_timeout(800)
        ck(not g.evaluate("localStorage.getItem('nr-parent-link')"),f'{tag}: device clears its token after being removed')
        # ---------------- relink + unlink from the device ----------------
        pg.click('#makeCode');pg.wait_for_selector('#linkCode');code2=pg.inner_text('#linkCode').strip()
        g.goto(f'{HOST}/index.html?parenttest=1');g.wait_for_timeout(1200);g.evaluate("settingsScreen()");g.wait_for_timeout(300)
        g.click('#plOpen');a,bb,cc=map(int,re.findall(r'\d+',g.inner_text('#plGateQ'))[:3]);g.fill('#plGate',str(a*bb+cc));g.click('#plGateGo')
        g.fill('#plCode','zzzzzz');g.click('#plLink');g.wait_for_selector('#plErr');ck('expired' in g.inner_text('#plErr'),f'{tag}: wrong code explained to the grown-up')
        g.fill('#plCode',code2.lower());g.click('#plLink');g.wait_for_selector('#plStatus')
        g.click('#plUnlink');g.click('#plUnlinkYes');g.wait_for_timeout(500)
        ck(not g.evaluate("localStorage.getItem('nr-parent-link')") and ('POST','/rest/v1/rpc/unlink_this_device') in M.calls and g.locator('#plOpen').count()==1,f'{tag}: "Unlink this device" works')
        ck(g.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2')).profiles.emi.subj.add.stars['4']")==3,f'{tag}: local progress kept after unlink')
        c.close();gc.close()
    b.close()
real=[e for e in errs if 'net::ERR_INTERNET_DISCONNECTED' not in e and 'Failed to fetch' not in e and 'Load failed' not in e and 'NetworkError' not in e]
ck(not real,f'no console errors {real[:5]}')
print(f'RESULT {BR} FAILS {len(fails)}')
