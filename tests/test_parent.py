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
        s.fn=None;s.fnmail='html';s.fncalls=[];s.p4=True;s.quests=[];s.plans=[];s.rewards=[];s.chal=[];s.prefs=[];s.meta={'nr_tour_done':True}
    def user(s): return {'id':s.uid,'email':'parent@example.com','aud':'authenticated','role':'authenticated','app_metadata':{},'user_metadata':dict(s.meta),'created_at':now().isoformat()}
    def session(s): return {'access_token':'test-access','token_type':'bearer','expires_in':3600,'expires_at':int(time.time())+3600,'refresh_token':'test-refresh','user':s.user()}
    def table(s,t): return {'parents':s.parents,'parent_consent':s.consent,'kids':s.kids,'devices':s.devices,'progress':list(s.progress.values()),'progress_events':s.events,'quests':s.quests,'fixit_plans':s.plans,'rewards':s.rewards,'challenge_done':s.chal,'notify_prefs':s.prefs}[t]
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
PCT={'quests','fixit_plans','rewards','challenge_done','notify_prefs'}
def pcrow(t,r):
    r=dict(r)
    if t=='quests': r={'id':str(uuid.uuid4()),'message':'','goal':10,'source':'parent','plan_id':None,'status':'active','right_count':0,'total_count':0,'created_at':now().isoformat(),'done_at':None,**r}
    elif t=='fixit_plans': r={'id':str(uuid.uuid4()),'day_done':0,'before_acc':None,'after_acc':None,'status':'active','created_at':now().isoformat(),'updated_at':now().isoformat(),**r}
    elif t=='rewards': r={'id':str(uuid.uuid4()),'start_value':0,'status':'active','created_at':now().isoformat(),'earned_at':None,**r}
    elif t=='challenge_done': r={'done_at':now().isoformat(),**r}
    return r
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
    if path=='/functions/v1/nr-weekly':
        M.fncalls.append(body)
        if not M.fn: return ok({'code':'NOT_FOUND','message':'Requested function was not found'},404)
        if body.get('action')=='summary':
            t='{{KID}} had a great week: 95 minutes on 5 days and 12 stars. ×2 facts are rock solid. Try skip-counting by 7s on the stairs at home.' if M.fn=='ai' else '{{KID}} played 95 minutes on 5 days this week and earned 12 stars. About 86% of 100 answers were right, which is excellent. Worth practicing: x7 facts. Skip-count out loud together (7, 14, 21...) for two minutes a day.'
            return ok({'ok':True,'week':'2026-W44','source':M.fn,'text':t,'stats':{}})
        if body.get('action')=='preview':
            if M.fnmail=='sent': return ok({'ok':True,'sent':True,'to':'parent@example.com'})
            h=open('/tmp/nr-email-preview.html',encoding='utf-8').read() if os.path.exists('/tmp/nr-email-preview.html') else '<h1>Preview</h1>'
            return ok({'ok':False,'error':'email_not_configured','html':h})
        return ok({'ok':False,'error':'action'},400)
    if path=='/auth/v1/otp': return ok({})
    if path=='/auth/v1/verify': return ok(M.session()) if body.get('token')=='123456' else ok({'code':403,'error_code':'otp_expired','msg':'Token has expired or is invalid'},403)
    if path=='/auth/v1/user':
        if meth=='PUT' and isinstance(body.get('data'),dict): M.meta.update(body['data'])
        return ok(M.user())
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
            M.progress[d['kid_id']]={'kid_id':d['kid_id'],'parent_id':M.uid,'hero':p.get('hero'),'realms':p['realms'],'skills':p['skills'],'time_played_sec':p['time_played_sec'],'lanterns_used':p['lanterns_used'],'examples_opened':p['examples_opened'],'play':p.get('play'),'updated_at':now().isoformat()}
            return ok({'ok':True})
        if fn in('get_home','quest_progress'):
            if not M.p4: return ok({'code':'PGRST202','message':'Could not find the function'},404)
            d=[d for d in M.devices if d['token']==body.get('p_device_token')]
            if not d or d[0]['revoked_at']: return ok({'ok':False,'error':'unlinked'})
            kid=d[0]['kid_id']
            if fn=='quest_progress':
                q=[q for q in M.quests if q['id']==body.get('p_quest_id') and q['kid_id']==kid]
                if not q: return ok({'ok':False,'error':'not_found'})
                q=q[0]
                if q['status']!='active': return ok({'ok':True,'status':q['status']})
                tot=max(q['total_count'],body.get('p_total') or 0);q['total_count']=min(q['goal'],tot);q['right_count']=min(q['total_count'],max(q['right_count'],body.get('p_right') or 0))
                if tot>=q['goal']: q['status']='done';q['done_at']=now().isoformat()
                return ok({'ok':True,'status':q['status']})
            pr=M.progress.get(kid) or {};st=sum((v or {}).get('stars',0) for v in (pr.get('realms') or {}).values());mn=(pr.get('time_played_sec') or 0)//60
            qs=[{'id':q['id'],'skill':q['skill'],'title':q['title'],'message':q['message'],'goal':q['goal'],'right':q['right_count'],'total':q['total_count'],'status':q['status']} for q in M.quests if q['kid_id']==kid and q['status'] in('active','done')]
            def have(r):
                if r['goal_type']=='stars': return max(0,st-r['start_value'])
                if r['goal_type']=='minutes': return max(0,mn-r['start_value'])
                return len([q for q in M.quests if q['kid_id']==kid and q['status']=='done' and q['done_at']>=r['created_at']])
            rw=[{'id':r['id'],'title':r['title'],'goal_type':r['goal_type'],'goal':r['goal'],'have':have(r),'status':r['status']} for r in M.rewards if r['kid_id']==kid and r['status'] in('active','earned')]
            return ok({'ok':True,'quests':qs,'rewards':rw,'badges':len([c for c in M.chal if c['kid_id']==kid])})
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
        if t in PCT:
            if not M.p4: return ok({'code':'PGRST205','message':f"Could not find the table 'public.{t}' in the schema cache"},404)
            rows=M.table(t)
            if meth=='GET': return ok(flt(rows,qs))
            if meth=='POST':
                new=body if isinstance(body,list) else [body];out=[]
                for r in new:
                    if r.get('parent_id')!=M.uid: return ok({'code':'42501','message':'new row violates row-level security policy'},403)
                    if t=='quests' and len([q for q in rows if q['kid_id']==r['kid_id'] and q['status']=='active'])>=5: return ok({'code':'P0001','message':'quest_limit: at most 5 active quests per kid'},400)
                    if t=='notify_prefs':
                        ex=[x for x in rows if x['parent_id']==r['parent_id']]
                        if ex: ex[0].update(r);out.append(ex[0]);continue
                    if t=='challenge_done' and [x for x in rows if x['kid_id']==r['kid_id'] and x['week']==r['week']]: return ok({'code':'23505','message':'duplicate key value violates unique constraint'},409)
                    r=pcrow(t,r);rows.append(r);out.append(r)
                return ok(out,201) if 'return=representation' in (req.headers.get('prefer') or '') else route.fulfill(status=201,headers=H,body='')
            if meth=='PATCH':
                for r in flt(rows,qs): r.update(body)
                return route.fulfill(status=204,headers=H,body='')
            if meth=='DELETE':
                for r in flt(rows,qs): rows.remove(r)
                return route.fulfill(status=204,headers=H,body='')
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
        ck(ab.locator('#benefits li').count()==7 and ab.locator('#soon li').count()==1 and at.count('Coming soon')==1 and 'Weekly summary and email' in at and 'Premium area' in at,f'{tag}: benefits page: 7 benefits, 1 Coming soon')
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
        pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#noProgress');pg.wait_for_selector('#sumText')
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
        ck(gh.inner_text('#nrParentHome h3').strip().endswith('Parent Login') and gh.locator('#nrParentHome button.btn:not(#nrhGN)').count()==1 and gh.locator('#nrhGN').count()==1 and gh.locator('#nrhWhat').is_visible() and 'Create' not in ht and not re.search(r'[$€£]|price',ht,re.I),f'{tag}: Home card: title, one Parent Login button, What\'s included? link')
        noscroll(gh,f'{tag} home card');ck(not [x for x in small_btns(gh) if x.startswith('nrh')],f'{tag}: home card buttons >= 44px')
        if SH: gh.locator('#nrParentHome').scroll_into_view_if_needed();gh.screenshot(path=f'{OUT}/{BR}-{tag}-8-home-parent-card.png')
        gh.evaluate("void(NRH.leave=u=>{window._left=u})")
        gh.click('#nrhLogin');ck(gh.locator('#nrhTopGate #nrtGate').count()==1,f'{tag}: grown-up gate before leaving the game')
        noscroll(gh,f'{tag} home gate')
        if SH: gh.locator('#nrParentHome').scroll_into_view_if_needed();gh.screenshot(path=f'{OUT}/{BR}-{tag}-9-home-gate.png')
        gh.fill('#nrtGate','3');gh.click('#nrtGo');ck(gh.locator('#nrtErr').count()==1 and not gh.evaluate("window._left"),f'{tag}: wrong gate answer stays in the game')
        gh.click('#nrtCancel');ck(gh.locator('#nrhTopGate').count()==0 and gh.locator('#nrhLogin').count()==1,f'{tag}: gate cancel')
        def solve(): a,bb,cc=map(int,re.findall(r'\d+',gh.inner_text('#nrtQ'))[:3]);gh.fill('#nrtGate',str(a*bb+cc));gh.press('#nrtGate','Enter')
        gh.click('#nrhWhat');ck(gh.locator('#nrtGate').count()==1,f'{tag}: What\'s included? is gated too');solve();ck(gh.evaluate("window._left")=='parent-about.html?parenttest=1',f'{tag}: What\'s included? goes to benefits page')
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
        ck(set(P.keys())=={'v','hero','realms','skills','time_played_sec','lanterns_used','examples_opened','play','client_at'} and 'name' not in json.dumps(P['realms']),f'{tag}: payload has only the minimal fields')
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
        pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#engTabs');pg.wait_for_selector('#sumText');pg.click('[data-etab="realms"]');pg.wait_for_selector('#realms')
        kt=pg.inner_text('#kidCard')
        ck('3/11' in pg.inner_text('#realms') or re.search(r'4/\d+ ch',pg.inner_text('#realms')) is not None,f'{tag}: realm progress rows')
        ck(pg.inner_text('#struggles').index('×7 facts')<pg.inner_text('#struggles').index('halves') and 'adding within 20' not in pg.inner_text('#struggles'),f'{tag}: struggle skills sorted, strong skills excluded')
        pg.click('[data-etab="acc"]');pg.wait_for_selector('#trendSvg')
        ck(pg.locator('#trendSvg polyline').count()==1 and pg.locator('#trendSvg circle').count()==7 and pg.locator('#trendSvg rect').count()==7,f'{tag}: inline SVG trend chart')
        noscroll(pg,f'{tag} kid detail');backck(pg,f'{tag} kid detail')
        ck(not small_btns(pg),f'{tag} kid detail: all buttons >=44px')
        if SH: pg.screenshot(path=f'{OUT}/{BR}-{tag}-4-kid-detail.png',full_page=True)
        pg.click('[data-etab="time"]');pg.wait_for_selector('#playBox')
        # ---------------- v28: Time played (day / week / month / year) ----------------
        POUT=os.environ.get('PLAY_SHOTS_DIR','/tmp/numirealm-v28-shots')
        if SH: os.makedirs(POUT,exist_ok=True)
        def ptshot(name):
            pg.evaluate("void(document.getElementById('engTabs').scrollIntoView({block:'start'}))");pg.evaluate("void(window.scrollBy(0,-12))");pg.wait_for_timeout(150)
            if SH: pg.screenshot(path=f'{POUT}/{BR}-{tag}-{name}.png')
        ck(pg.locator('#playBox [role=tab]').count()==4 and pg.locator('#playBox [aria-selected=true]').inner_text()=='Week',f'{tag}: Time played has Day/Week/Month/Year tabs, Week first')
        pg.click('[data-etab="acc"]');ck(pg.locator('#trendSvg').count()==1 and pg.locator('h3:text("Accuracy trend")').count()==1,f'{tag}: accuracy trend kept, now in the Accuracy tab');pg.click('[data-etab="time"]')
        saved_ev=list(M.events);saved_play=M.progress[mia].get('play')
        # older device / server without the play log: estimate from daily snapshots (cumulative minutes 5,9,...,29)
        M.progress[mia]['play']=None;pg.reload();pg.wait_for_selector('#familyCard');pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#playBox');pg.wait_for_selector('#sumText')
        ck(pg.locator('#playEst').count()==1 and '29 min in the last 12 weeks' in pg.inner_text('#playTotal'),f'{tag}: no play log -> estimate from daily totals ({pg.inner_text("#playTotal")})')
        # empty state
        M.events[:]=[];pg.reload();pg.wait_for_selector('#familyCard');pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#playBox');pg.wait_for_selector('#sumText')
        ck(pg.locator('#playEmpty').is_visible() and 'No play time yet' in pg.inner_text('#playEmpty') and pg.locator('#playSvg').count()==0,f'{tag}: friendly empty state with no data')
        for k in ['day','month','year']:
            pg.click(f'[data-ptab="{k}"]');ck(pg.locator('#playEmpty').count()==1,f'{tag}: empty state on {k} tab too')
        pg.click('[data-ptab="week"]');noscroll(pg,f'{tag} play empty');ptshot('empty')
        # varied play log for Mia (as stored by setup-part4): 400 days ending today + older rolled-up months
        today=datetime.date.today();days=[0 if i%7==3 or i%11==5 else 5+(i*37)%52 for i in range(400)]
        first=today-datetime.timedelta(days=399);months={}
        for j in range(1,25):
            y,m=first.year,first.month-j
            while m<1: m+=12;y-=1
            months[f'{y:04d}-{m:02d}']=200+(j*53)%500
        dmap={(today-datetime.timedelta(days=399-i)).isoformat():v for i,v in enumerate(days) if v}
        def fm(m):
            m=round(m);return f'{m} min' if m<60 else f'{m//60} h'+(f' {m%60} min' if m%60 else '')
        def msum(y,m):
            pre=f'{y:04d}-{m:02d}';return months.get(pre,0)+sum(v for k,v in dmap.items() if k[:7]==pre)
        exp={}
        bq=[dmap.get((today-datetime.timedelta(days=13-i)).isoformat(),0) for i in range(14)];exp['day']=(bq,'Today')
        mon=today-datetime.timedelta(days=today.weekday())
        bq=[sum(dmap.get((mon-datetime.timedelta(days=7*w)+datetime.timedelta(days=i)).isoformat(),0) for i in range(7)) for w in range(11,-1,-1)];exp['week']=(bq,'This week')
        bq=[]
        for i in range(11,-1,-1):
            y,m=today.year,today.month-i
            while m<1: m+=12;y-=1
            bq.append(msum(y,m))
        exp['month']=(bq,'This month')
        ys=sorted({int(k[:4]) for k in list(dmap)+list(months)}|{today.year});lo=max(ys[0],today.year-5)
        exp['year']=([sum(msum(y,m) for m in range(1,13)) for y in range(lo,today.year+1)],'This year')
        M.events[:]=saved_ev;M.progress[mia]['play']={'v':1,'end':today.isoformat(),'days':days,'months':months}
        pg.reload();pg.wait_for_selector('#familyCard');pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#playSvg');pg.wait_for_selector('#sumText')
        ck(pg.locator('#playEst').count()==0,f'{tag}: exact log used when the server stores it')
        for k in ['day','week','month','year']:
            pg.click(f'[data-ptab="{k}"]');pg.wait_for_timeout(80)
            bars=[int(x) for x in pg.eval_on_selector_all('#playSvg .ptbar','e=>e.map(r=>r.dataset.min)')]
            bq,lab=exp[k];tt=pg.inner_text('#playTotal')
            ck(bars==bq,f'{tag}: {k} tab bars match the log ({len(bars)} bars)')
            ck(tt.startswith(f'{lab}: {fm(bq[-1])}') and f'{fm(sum(bq))} in ' in tt and 'in the all' not in tt,f'{tag}: {k} total line "{tt}"')
            ck(pg.locator(f'[data-ptab="{k}"]').get_attribute('aria-selected')=='true' and pg.locator('#playBox [aria-selected=true]').count()==1,f'{tag}: {k} tab selected')
            sw=pg.evaluate("document.getElementById('playSvg').getBoundingClientRect().width");cw=pg.evaluate("document.getElementById('kidCard').clientWidth")
            ck(0<sw<=cw,f'{tag}: {k} graph fits the card ({sw:.0f}/{cw}px)')
            noscroll(pg,f'{tag} play {k}');ck(not small_btns(pg),f'{tag} play {k}: all buttons >=44px')
            ptshot(f'play-{k}')
        if saved_play is not None: M.progress[mia]['play']=saved_play
        # ---------------- v27: back to the game keeps the parent signed in ----------------
        np=c.new_page();watch(np);np.goto(f'{HOST}/parent.html');np.wait_for_selector('#allDevices',timeout=8000);backck(np,f'{tag} signed-in family (new tab, no flag)')
        np.click('#nrBack');np.wait_for_function("typeof settingsScreen==='function'",timeout=8000)
        ck(np.url==f'{HOST}/' and np.locator('#nrParentHome').count()==1 and np.locator('#nrhGN').count()==0,f'{tag}: v30: Back to NumiRealm opens the normal game Home (public Parent card, no test extras) ({np.url})')
        np.goto(f'{HOST}/parent.html');np.wait_for_selector('#allDevices',timeout=8000)
        ck(np.locator('#email').count()==0 and np.locator('#signOut').is_visible(),f'{tag}: parent still signed in after going back to the game');np.close()
        # ---------------- v28 Parent Center ----------------
        COUT=os.environ.get('PC_SHOTS_DIR','/tmp/numirealm-v28-pc-shots')
        if SH: os.makedirs(COUT,exist_ok=True)
        def cshot(name,sel=None,full=False):
            if not SH: return
            if sel: pg.wait_for_timeout(100);pg.locator(sel).scroll_into_view_if_needed();pg.evaluate(f"void(document.querySelector('{sel}').scrollIntoView({{block:'start'}}),window.scrollBy(0,-10))");pg.wait_for_timeout(150)
            pg.screenshot(path=f'{COUT}/{BR}-{tag}-{name}.png',full_page=full)
        def kidview():
            pg.reload();pg.wait_for_selector('#familyCard');pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#engTabs');pg.wait_for_selector('#sumText')
        M.events[:]=saved_ev;M.progress[mia]['play']=saved_play
        def seed(): M.progress[mia]['skills']={'mult:x7':{'n':'×7 facts','r':6,'t':14,'l':4},'add:c2':{'n':'adding within 20','r':19,'t':20,'l':0},'frac:c3':{'n':'halves, thirds and fourths','r':3,'t':6,'l':1}}
        seed()
        pg.evaluate("localStorage.removeItem('nr-pc-seen');localStorage.removeItem('nr-pc-local')")
        kidview()
        ck(pg.locator('#engTabs [role=tab]').count()==4 and pg.locator('#engTabs [aria-selected=true]').inner_text().endswith('Time'),f'{tag} PC: 4 engagement tabs, Time first')
        ck(all(b['h']>=44 for b in pg.eval_on_selector_all('#engTabs button','e=>e.map(b=>({h:b.getBoundingClientRect().height}))')),f'{tag} PC: engagement tabs >= 44px')
        pg.click('[data-etab="acc"]');pg.wait_for_selector('#accBox')
        ck(pg.locator('#accBox [data-atab]').count()==4 and pg.locator('#trendSvg').count()==1,f'{tag} PC: Accuracy tab with Day/Week/Month/Year + trend')
        pg.click('[data-atab="day"]');ps=pg.eval_on_selector_all('#accSvg .acbar','e=>e.map(x=>+x.dataset.p)')
        expp=[round(100*6/7)]*6
        ck(ps==expp,f'{tag} PC: daily accuracy bars from snapshots ({ps})')
        noscroll(pg,f'{tag} acc');cshot('01-tab-accuracy','#engTabs')
        pg.click('[data-atab="week"]');ck(pg.locator('#accSvg .acbar').count()>=1 and '%' in pg.inner_text('#accTotal'),f'{tag} PC: weekly accuracy')
        pg.click('[data-etab="realms"]');ck(pg.locator('#realms').count()==1 and re.search(r'\d+/\d+',pg.inner_text('#realms')) is not None,f'{tag} PC: Realms tab');cshot('02-tab-realms','#engTabs')
        pg.click('[data-etab="skills"]');cls=pg.evaluate("Object.fromEntries([...document.querySelectorAll('#skillMap .smt')].map(e=>[e.dataset.skill,e.className]))")
        ck('sm-help' in cls.get('mult:x7','') and 'sm-star' in cls.get('add:c2','') and 'sm-new' in cls.get('mult:x3',''),f'{tag} PC: skill map tile states ({cls.get("mult:x7")},{cls.get("add:c2")})')
        noscroll(pg,f'{tag} skill map');cshot('03-tab-skillmap','#engTabs')
        pg.click('[data-etab="time"]');ck(pg.locator('#playBox').count()==1,f'{tag} PC: back to Time tab');cshot('00-tab-time','#engTabs')
        # tips
        tt=pg.inner_text('#tipsCard')
        ck('Mia gets ×7 facts right 6 of 14 times' in tt and '5, 6, 7, 8' in tt and 'adding within 20' not in tt,f'{tag} PC: tip tied to the real weak spot')
        cshot('04-tips','#tipsCard')
        pg.click('#tipsCard [data-lesson="m78"]');pg.wait_for_selector('#lessonDetail')
        ck('7s and 8s' in pg.inner_text('#lessonDetail') and pg.locator('#lessonDetail svg').count()>=1,f'{tag} PC: tip opens its lesson');noscroll(pg,f'{tag} lesson');cshot('05-lesson-detail',full=False)
        pg.click('#lessonClose');n_all=pg.locator('#lessonsCard .lcard').count();pg.click('[data-lrealm="frac"]');n_fr=pg.locator('#lessonsCard .lcard').count()
        ck(n_all==10 and 1<=n_fr<n_all,f'{tag} PC: lessons library with realm filter ({n_all}/{n_fr})');pg.click('[data-lrealm="all"]') if pg.locator('[data-lrealm="all"]').count() else None
        ck(not small_btns(pg),f'{tag} PC lessons: buttons >= 44px');cshot('06-lessons-library','#lessonsCard')
        pg.click('#toFamily');pg.wait_for_selector('#familyCard')
        ck(pg.locator('#soonCard li').count()==7 and pg.locator('#soonCard button, #soonCard a, #soonCard input').count()==0 and pg.inner_text('#soonCard').count('Coming soon')>=7,f'{tag} PC: 7 Coming soon items, none clickable')
        cshot('07-coming-soon','#soonCard')
        # quest from home
        pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#engTabs');pg.wait_for_selector('#sumText')
        ck(pg.locator('#questEmpty').count()==1 and pg.locator('#fixitEmpty').count()==1 and pg.locator('#rewardsEmpty').count()==1,f'{tag} PC: empty quest/fix-it/reward states');cshot('08-quest-empty','#questCard')
        pg.click('#tipsCard [data-qpick="mult:x7"]');pg.wait_for_selector('#questForm')
        ck(pg.input_value('#qSkill')=='mult:x7' and 'Practice ×7 facts' in pg.inner_text('#questPreview'),f'{tag} PC: tip pre-fills the quest form')
        pg.fill('#qMsg','Go Mia! Beat the dragon 🐉');ck('Go Mia! Beat the dragon' in pg.inner_text('#qpM'),f'{tag} PC: live scroll preview')
        noscroll(pg,f'{tag} quest form');ck(not small_btns(pg),f'{tag} quest form: buttons >= 44px');cshot('09-quest-form','#questForm')
        pg.click('#qSend');pg.wait_for_selector('#questList')
        q=M.quests[-1] if M.quests else {}
        ck(q.get('skill')=='mult:x7' and q.get('goal')==10 and q.get('message')=='Go Mia! Beat the dragon 🐉' and q.get('source')=='suggested' and q.get('kid_id')==mia and q.get('parent_id')==M.uid,f'{tag} PC: quest saved ({q})')
        # in-game scroll
        g.evaluate("save.hero='emi';titleScreen()");g.evaluate("NRQ.refresh()");g.wait_for_selector('#nrQuest',timeout=8000)
        qt=g.inner_text('#nrQuest')
        ck('Practice ×7 facts' in qt and 'Go Mia! Beat the dragon' in qt,f'{tag} PC game: scroll from home with message')
        ck(g.evaluate("(()=>{const a=document.getElementById('nrQuest'),b=document.getElementById('nrParentHome');return !!a&&(!b||!!(a.compareDocumentPosition(b)&4))})()"),f'{tag} PC game: scroll sits above the parent card')
        ck(not [x for x in small_btns(g) if 'nrq' in x.lower()],f'{tag} PC game: scroll buttons >= 44px');noscroll(g,f'{tag} game scroll')
        if SH: g.locator('#nrQuest').scroll_into_view_if_needed();g.screenshot(path=f'{COUT}/{BR}-{tag}-10-game-scroll.png')
        g.evaluate("save.hero='leo';NRQ.onAns('mult:x7',true);save.hero='emi'");ck(json.loads(g.evaluate("localStorage.getItem('nr-parent-home')"))['quests'][0]['total']==0,f'{tag} PC game: other heroes do not count toward the quest')
        g.evaluate("for(let i=0;i<10;i++)NRQ.onAns('mult:x7',i<8);NRQ.onAns('add:c2',true)");g.evaluate("NRQ.refresh()");g.wait_for_timeout(1200)
        ck(q.get('status')=='done' and q.get('right_count')==8 and q.get('total_count')==10,f'{tag} PC game: quest progress syncs back ({q.get("right_count")}/{q.get("total_count")} {q.get("status")})')
        ck('quest_progress' in ' '.join(p for _,p in M.calls),f'{tag} PC game: progress sent by quest_progress RPC')
        ck('NRQ.onAns(c.k,ok)' in open(os.path.join(D,'index.html'),encoding='utf-8').read(),f'{tag} PC game: answer hook wired into NRP.rec')
        if SH: g.wait_for_selector('#nrQuest');g.locator('#nrQuest').scroll_into_view_if_needed();g.screenshot(path=f'{COUT}/{BR}-{tag}-11-game-scroll-done.png')
        seed();kidview();ck('✅' in pg.inner_text('#questList') and '8 of 10' in pg.inner_text('#questList'),f'{tag} PC: finished quest shows in portal ({pg.inner_text("#questList")[:80]})')
        # fix-it plan
        _b=pg.locator('#tipsCard [data-plan="m78"]');_b.wait_for(state='visible',timeout=20000);_b.scroll_into_view_if_needed();_b.click(timeout=60000);pg.wait_for_selector('#fixitCard .plan',timeout=30000)
        pl=M.plans[-1] if M.plans else {}
        fq=[x for x in M.quests if x.get('plan_id')==pl.get('id')]
        ck(pl.get('plan_key')=='m78' and pl.get('before_acc')==43 and len(fq)==1 and fq[0]['source']=='fixit',f'{tag} PC: fix-it plan started with before accuracy and Day 1 quest ({pl.get("before_acc")})')
        noscroll(pg,f'{tag} fixit');cshot('12-fixit-plan','#fixitCard')
        M.progress[mia]['skills']['mult:x8']={'n':'×8 facts','r':9,'t':10,'l':0}
        fq[0].update(status='done',right_count=9,total_count=10)
        for i in range(5):
            pg.click(f'[data-planday="{pl.get("id")}"]');pg.wait_for_timeout(250)
        ck(pl.get('status')=='done' and pl.get('day_done')==5 and pl.get('after_acc')==90,f'{tag} PC: 5 days done, after accuracy saved ({pl.get("after_acc")})')
        ck('43%' in pg.inner_text('#fixitCard') and '90%' in pg.inner_text('#fixitCard'),f'{tag} PC: before/after shown');cshot('13-fixit-done','#fixitCard')
        # rewards
        pg.click('#rNew');pg.wait_for_selector('#rewardForm');pg.fill('#rTitle','Trip to the park');pg.select_option('#rType','stars');pg.fill('#rGoal','3')
        ck(not small_btns(pg),f'{tag} reward form: buttons >= 44px');cshot('14-reward-form','#rewardsCard')
        pg.click('#rSave');pg.wait_for_selector('#rewardsCard .qrow')
        rw=M.rewards[-1] if M.rewards else {};st0=sum(v.get('stars',0) for v in M.progress[mia]['realms'].values())
        ck(rw.get('title')=='Trip to the park' and rw.get('goal')==3 and rw.get('start_value')==st0 and rw.get('status')=='active',f'{tag} PC: reward saved, counted from today')
        M.progress[mia]['realms']['add']['stars']+=3;kidview()
        ck(rw.get('status')=='earned' and pg.locator(f'[data-rwgive="{rw.get("id")}"]').count()==1,f'{tag} PC: reward auto-earned at the goal');cshot('15-reward-earned','#rewardsCard')
        g.evaluate("NRQ.refresh()");g.wait_for_timeout(900);ck('Trip to the park' in g.inner_text('body'),f'{tag} PC game: reward goal shown in game')
        pg.click(f'[data-rwgive="{rw.get("id")}"]');pg.wait_for_timeout(400);ck(rw.get('status')=='given',f'{tag} PC: reward marked as given')
        # milestones + challenge
        ck(pg.locator('#milestoneCard .ms.big').count()==1,f'{tag} PC: milestone celebration card');pg.click('#celebrate');ck(pg.locator('.confetti').count()>=1,f'{tag} PC: confetti on celebrate')
        pg.wait_for_timeout(2300);cshot('16-milestones','#milestoneCard')
        ck(pg.locator('#chalBtn').count()==1 and pg.locator('#chalProg').count()==1,f'{tag} PC: weekly family challenge');cshot('17-challenge','#challengeCard')
        pg.click('#chalBtn');pg.wait_for_selector('#chalDone')
        ck(len(M.chal)==1 and re.match(r'^\d{4}-W\d\d$',M.chal[0]['week']),f'{tag} PC: challenge saved for this ISO week');pg.wait_for_timeout(2300);cshot('18-challenge-done','#challengeCard')
        noscroll(pg,f'{tag} PC kid');ck(not small_btns(pg),f'{tag} PC kid: all buttons >= 44px')
        cshot('19-kid-full',full=True)
        # alerts + preferences
        seed();M.prefs[:]=[{'parent_id':M.uid,'events':{},'quiet_start':0,'quiet_end':0,'idle_days':3,'daily_goal':30}]
        pg.evaluate("localStorage.removeItem('nr-pc-seen')");pg.reload();pg.wait_for_selector('#familyCard')
        ck(pg.locator('#alertToast').count()==1 and pg.locator('#bellCount').count()==1,f'{tag} PC: alert banner + bell count outside quiet hours');cshot('20-alert-toast')
        pg.click('#bellBtn');pg.wait_for_selector('#alertsCard')
        ev=pg.eval_on_selector_all('#alertList li','e=>e.map(x=>x.dataset.ev)')
        ck('quest' in ev and 'fixit' in ev and 'weak' in ev and 'milestone' in ev,f'{tag} PC: alerts list ({ev})')
        noscroll(pg,f'{tag} alerts');ck(not small_btns(pg),f'{tag} alerts: buttons >= 44px');cshot('21-alerts',full=True)
        pg.click('#markRead');ck(pg.locator('#alertList li.unread').count()==0 and pg.locator('#bellCount').count()==0,f'{tag} PC: mark all as read')
        h=datetime.datetime.now().hour
        pg.uncheck('#pf_weak');pg.select_option('#pfQs',str(h));pg.select_option('#pfQe',str((h+1)%24));pg.click('#savePrefs');pg.wait_for_timeout(500)
        pr0=M.prefs[0]
        ck(pr0['events'].get('weak') is False and pr0['quiet_start']==h and pr0['events'].get('quest') is True,f'{tag} PC: preferences saved')
        pg.evaluate("localStorage.removeItem('nr-pc-seen')");pg.reload();pg.wait_for_selector('#familyCard')
        ck(pg.locator('#alertToast').count()==0,f'{tag} PC: no banner during quiet hours')
        pg.click('#bellBtn');pg.wait_for_selector('#alertsCard');ck('weak' not in pg.eval_on_selector_all('#alertList li','e=>e.map(x=>x.dataset.ev)'),f'{tag} PC: turned-off alert type hidden')
        cshot('22-prefs','#prefsCard')
        M.prefs[:]=[]
        # setup-part4 not run -> friendly notes, no errors
        seed();M.p4=False;errs0=len(errs);kidview()
        ck(pg.locator('#questCard [data-setup]').count()==1 and pg.locator('#qNew').count()==0 and pg.locator('#tipsCard .tip').count()>=1 and pg.locator('#chalBtn, #chalDone').count()==1,f'{tag} PC: graceful note without setup-part4')
        ck(len(errs)==errs0,f'{tag} PC: no page errors without setup-part4');cshot('23-setup-note','#questCard')
        M.p4=True
        # weekly summary (nr-weekly Edge Function): not deployed -> on-device smart summary
        M.fn=None;errs0=len(errs);kidview();pg.wait_for_selector('#sumText')
        ck(pg.inner_text('#sumLabel').endswith('Smart summary') and 'Mia' in pg.inner_text('#sumText') and '{{KID}}' not in pg.inner_text('#sumText') and 'No AI used' in pg.inner_text('#sumNote') and 'EDGE_SETUP' in pg.inner_text('#sumNote'),f'{tag} PC: summary falls back on device when the function is not deployed')
        ck(len(errs)==errs0 and pg.locator('#sumRefresh').count()==0,f'{tag} PC: no page errors without the Edge Function');cshot('26-summary-fallback','#summaryCard')
        M.fn='template';kidview();pg.wait_for_selector('#sumText')
        ck(pg.inner_text('#sumLabel').endswith('Smart summary') and 'Mia played 95 minutes' in pg.inner_text('#sumText') and 'No AI used' in pg.inner_text('#sumNote'),f'{tag} PC: server template summary labeled Smart summary')
        M.fn='ai';pg.click('#sumRefresh');pg.wait_for_selector('#sumLabel.aipill')
        ck('AI-written' in pg.inner_text('#sumLabel') and pg.inner_text('#sumText').startswith('Mia had a great week') and 'never sees names' in pg.inner_text('#sumNote') and M.fncalls[-1].get('refresh') is True,f'{tag} PC: AI summary clearly labeled AI-written')
        ck(not [x for x in small_btns(pg) if 'sum' in x.lower() or 'openalerts3' in x.lower()],f'{tag} PC: summary buttons >= 44px');noscroll(pg,f'{tag} summary');cshot('27-summary-ai','#summaryCard')
        # weekly email preferences + preview
        pg.click('#openAlerts3');pg.wait_for_selector('#emailPrefs')
        ck(not pg.is_checked('#pfEmail') and pg.locator('#pfEmailDay option').count()==7 and 'unsubscribe' in pg.inner_text('#emailPrefs') and 'parent@example.com' in pg.inner_text('#emailPrefs'),f'{tag} PC: weekly email is off by default, day picker, unsubscribe note')
        pg.check('#pfEmail');pg.select_option('#pfEmailDay','5');pg.click('#savePrefs');pg.wait_for_timeout(500)
        ck(M.prefs and M.prefs[0].get('email_weekly') is True and M.prefs[0].get('email_day')==5 and 'unsub_token' not in M.prefs[0],f'{tag} PC: weekly email opt-in + day saved')
        pg.click('#emailPreview');pg.wait_for_selector('#emailPreviewFrame')
        fr=pg.frame_locator('#emailPreviewFrame')
        ck('not set up yet' in pg.inner_text('#mailNote') and fr.locator('text=Unsubscribe').count()>=1,f'{tag} PC: preview shown on screen when sending is not set up')
        ck(not small_btns(pg),f'{tag} email prefs: buttons >= 44px');noscroll(pg,f'{tag} email prefs');cshot('28-email-prefs','#emailPrefs')
        M.fnmail='sent';pg.click('#emailPreview');pg.wait_for_function("document.getElementById('mailNote')&&/Preview sent/.test(document.getElementById('mailNote').textContent)")
        ck('parent@example.com' in pg.inner_text('#mailNote') and {'action':'preview'} in M.fncalls,f'{tag} PC: "Send me a preview now" sends')
        M.fn=None;pg.click('#emailPreview');pg.wait_for_function("/not switched on/.test(document.getElementById('mailNote').textContent)");ck(True,f'{tag} PC: preview degrades gracefully when the function is missing')
        M.fn=None;M.fnmail='html';M.prefs[:]=[]
        if SH and os.path.exists('/tmp/nr-email-preview.html'):
            ep=c.new_page();ep.goto('file:///tmp/nr-email-preview.html');ep.screenshot(path=f'{COUT}/{BR}-{tag}-29-email.png',full_page=True);ep.close()
        # empty kid
        leo_added=len(M.kids)<2
        if leo_added: M.kids.append({'id':str(uuid.uuid4()),'parent_id':M.uid,'nickname':'Leo','avatar':M.kids[0].get('avatar'),'created_at':now().isoformat()})
        leo=[k for k in M.kids if k['id']!=mia][0]['id']
        pg.reload();pg.wait_for_selector('#familyCard');pg.click(f'button[data-kid="{leo}"]');pg.wait_for_selector('#engTabs');pg.wait_for_selector('#sumText')
        ck(pg.locator('#tipsEmpty').count()==1 and pg.locator('#msEmpty').count()==1 and pg.locator('#questEmpty').count()==1,f'{tag} PC: empty kid states');cshot('24-empty-kid',full=True)
        pg.click('[data-etab="acc"]');ck(pg.locator('#accEmpty').count()==1,f'{tag} PC: accuracy empty');pg.click('[data-etab="skills"]');ck(pg.locator('#skillEmpty').count()==1,f'{tag} PC: skill map empty');cshot('25-empty-skillmap','#engTabs')
        M.kids[:]=[k for k in M.kids if k['id']!=leo] if leo_added else M.kids;pg.click('#toFamily');pg.wait_for_selector('#familyCard');pg.click(f'button[data-kid="{mia}"]');pg.wait_for_selector('#kidDevices');pg.wait_for_selector('#sumText')
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
    # ---------------- v28: first-visit guided tour, sample data, Help/FAQ ----------------
    TOUT='/workspace/v28shots-full/tour';os.makedirs(TOUT,exist_ok=True)
    for tag,w,h,mob in [('desktop',1280,900,False),('phone',390,844,True)]:
        M.reset();M.meta={}
        c=ctx(b,w,h,mob);pg=c.new_page();watch(pg);pg.goto(f'{HOST}/parent.html');pg.wait_for_selector('#email')
        pg.fill('#email','parent@example.com');pg.click('#sendBtn');pg.wait_for_selector('#otp');pg.fill('#otp','123456');pg.click('#verifyBtn');pg.wait_for_selector('#consentChk')
        pg.check('#consentChk');pg.click('#consentBtn');pg.wait_for_selector('#tourPop',timeout=8000)
        n=pg.evaluate('TOUR.STEPS.length');ck(n>=15 and '1 / ' in pg.inner_text('#tourStep'),f'{tag} tour: starts automatically on first visit ({n} steps)')
        ck(pg.locator('#tourBack').count()==0 and pg.locator('#tourNext').is_visible() and pg.locator('#tourSkip').is_visible(),f'{tag} tour: Next and Skip on step 1, no Back')
        seen=[];shots={1:'01-linking',3:'02-accuracy-tab',6:'03-summary',13:'04-gamenight'}
        for k in range(n):
            r=pg.evaluate("""(()=>{const st=TOUR.STEPS[TOUR.i],t=document.querySelector(st.sel),p=document.getElementById('tourPop').getBoundingClientRect();if(!t)return {sel:st.sel,miss:1};const r=t.getBoundingClientRect();
              return {sel:st.sel,top:r.top,vis:r.top<innerHeight-p.height&&r.bottom>0,ex:!!document.getElementById('sampleBar'),bs:[...document.querySelectorAll('#tourPop button')].every(b=>b.getBoundingClientRect().height>=44&&b.getBoundingClientRect().width>=44)}})()""")
            seen.append(r['sel']);ck(not r.get('miss') and r['vis'] and r['bs'],f'{tag} tour step {k+1} {r["sel"]}: target present, scrolled into view above the popup, buttons >=44px {r}')
            if 0<k<11: ck(r['ex'],f'{tag} tour step {k+1}: example-data banner shown while no kid is linked')
            if k in shots: pg.wait_for_timeout(350);pg.screenshot(path=f'{TOUT}/{BR}-{tag}-{shots[k]}.png')
            if k==2: pg.click('#tourBack');pg.wait_for_timeout(150);ck(pg.inner_text('#tourStep').startswith('2 /'),f'{tag} tour: Back works');pg.click('#tourNext');pg.wait_for_timeout(150)
            if k<n-1: pg.click('#tourNext');pg.wait_for_timeout(200)
        for sel in ['#familyCard','#kidDevices','#engWrap','#summaryCard','#tipsCard','#fixitCard','#questCard','#rewardsCard','#prefsCard','#emailPrefs','#openGameNight','#openLessons','#helpCard']: ck(sel in seen,f'{tag} tour covers {sel}')
        ck(pg.evaluate("TOUR.STEPS.filter(s=>s.sel=='#engWrap').length")==4,f'{tag} tour: each engagement tab gets a step')
        pg.click('#tourDone');pg.wait_for_timeout(400)
        ck(pg.locator('#tourPop').count()==0 and pg.locator('#sampleBar').count()==0 and pg.locator('#noKids').count()==1,f'{tag} tour: Got it closes and removes the example data')
        ck(M.meta.get('nr_tour_done') is True and ('PUT','/auth/v1/user') in M.calls or M.meta.get('nr_tour_done') is True,f'{tag} tour: completion saved on the account')
        ck(pg.evaluate("localStorage.getItem('nr-tour-done:'+S.user.id)")=='1',f'{tag} tour: completion remembered on this device too')
        pg.evaluate("localStorage.removeItem('nr-tour-done:'+S.user.id)");pg.reload();pg.wait_for_selector('#noKids');pg.wait_for_timeout(800)
        ck(pg.locator('#tourPop').count()==0,f'{tag} tour: not shown again for the same account (even with a cleared browser)')
        ck(pg.locator('#tourBtn').is_visible() and 'How it works' in pg.inner_text('#tourBtn'),f'{tag}: "How it works" button in the header')
        pg.click('#tourBtn');pg.wait_for_selector('#tourPop');ck('1 / ' in pg.inner_text('#tourStep'),f'{tag}: How it works replays the tour')
        pg.keyboard.press('Escape');pg.wait_for_timeout(300);ck(pg.locator('#tourPop').count()==0,f'{tag}: Escape / Skip closes the tour')
        hc=pg.locator('#helpCard');ck(hc.count()==1 and pg.locator('#helpCard details').count()>=9,f'{tag}: Help & FAQ has a short explainer per feature')
        hc.scroll_into_view_if_needed();pg.click('#helpCard details[data-help="0"] summary');pg.click('#helpCard details[data-help="7"] summary');pg.wait_for_timeout(200)
        ck(pg.locator('#helpCard details[data-help="0"] p').is_visible(),f'{tag}: Help answer opens on tap')
        pg.screenshot(path=f'{TOUT}/{BR}-{tag}-05-help.png',full_page=False) if hc.bounding_box() else None
        hc.screenshot(path=f'{TOUT}/{BR}-{tag}-05-help-card.png')
        pg.click('#sampleBtn');pg.wait_for_selector('#sampleBar')
        ck('EXAMPLE DATA' in pg.inner_text('#sampleBar') and 'Sample Kid' in pg.inner_text('#familyCard'),f'{tag}: Try it with sample data shows a clearly labeled example kid')
        pg.click('button.kid[data-kid="sample-kid"]');pg.wait_for_selector('#engWrap');pg.wait_for_timeout(300)
        ck(pg.locator('#sampleBar').is_visible() and pg.locator('#summaryCard').count()==1,f'{tag}: example kid page works with the banner on top')
        pg.screenshot(path=f'{TOUT}/{BR}-{tag}-06-sample-kid.png')
        AX='''(()=>{const out=[];document.querySelectorAll('#engWrap svg').forEach(sv=>{const b=sv.getBoundingClientRect();sv.querySelectorAll('text').forEach(t=>{const r=t.getBoundingClientRect();if(r.width&&(r.left<b.left-0.5||r.right>b.right+0.5))out.push(t.textContent)})});return out})()'''
        for et in ['time','acc','realms','skills']:
            pg.click(f'[data-etab="{et}"]');pg.wait_for_timeout(200)
            per=pg.locator('#engWrap [data-ptab],#engWrap [data-atab]');np_=per.count() or 1
            for j in range(np_):
                if per.count(): per.nth(j).click();pg.wait_for_timeout(150)
                cl=pg.evaluate(AX);ck(not cl,f'{tag} {et} tab view {j}: axis labels not clipped {cl}')
        pg.click('[data-etab="acc"]');pg.wait_for_timeout(200);ck(pg.evaluate("[...document.querySelectorAll('#engWrap svg text')].some(t=>t.textContent=='100%')"),f'{tag}: accuracy axis shows 100%')
        before=len(M.calls);pg.locator('#makeCode').click();pg.wait_for_timeout(300)
        ck(len(M.calls)==before and 'turned off' in pg.inner_text('#sampleMsg'),f'{tag}: write buttons are disabled in the example (nothing sent)')
        pg.click('#sampleExit');pg.wait_for_timeout(300);ck(pg.locator('#sampleBar').count()==0 and pg.locator('#noKids').count()==1 and not M.kids,f'{tag}: Exit example returns to the real (empty) family')
        noscroll(pg,f'{tag} after tour');c.close()
    b.close()
real=[e for e in errs if 'net::ERR_INTERNET_DISCONNECTED' not in e and 'Failed to fetch' not in e and 'Load failed' not in e and 'NetworkError' not in e and "Blocked script execution in 'about:srcdoc'" not in e]
ck(not real,f'no console errors {real[:5]}')
print(f'RESULT {BR} FAILS {len(fails)}')
