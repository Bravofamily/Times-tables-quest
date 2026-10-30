# v32 tests: Delete my account (UI + mocked nr-delete-account), shared "this week" stars (UTC), UTC note,
# AI vs measured labels, preview-limit message. Supabase is fully mocked; nothing reaches the network.
# Usage: PWB=chromium|webkit python test_v32.py   (SHOTS=1 -> /workspace/v32shots)
import os,json,threading,http.server,functools,time,uuid
from urllib.parse import urlparse,parse_qs
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));BR=os.environ.get('PWB','chromium');SH=os.environ.get('SHOTS')=='1';OUT=os.environ.get('SHOTS_DIR','/workspace/v32shots')
PORT=int(os.environ.get('NR_PORT') or (8893 if BR=='chromium' else 8894))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
fails=[];errs=[]
def ck(c,m,info=''):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m+(f'  :: {info}' if info else ''))
    if not c: fails.append(m)
UID='22222222-2222-4222-8222-222222222222';KID='11111111-1111-4111-8111-111111111111'
NOW='2026-10-29T15:00:00-04:00'
class M: pass
def reset(del_mode='ok'):
    M.calls=[];M.fn=[];M.del_mode=del_mode;M.logout=[];M.reauthed=False;M.otp=0;M.upserts=[]
    M.t={'parents':[{'id':UID}],'parent_consent':[{'parent_id':UID,'consent_version':'test-1'}],
         'kids':[{'id':KID,'parent_id':UID,'nickname':'TestKid A1','age_range':'8-10','grade':'3','created_at':'2026-10-01T00:00:00Z'}],
         'progress':[{'kid_id':KID,'parent_id':UID,'realms':{'add':{'chapters':3,'total':10,'stars':30,'max':30}},'skills':{},'time_played_sec':3600,'updated_at':'2026-10-29T18:00:00Z'}],
         'progress_events':[{'kid_id':KID,'parent_id':UID,'day':'2026-10-20','stars_total':10,'answers_right':10,'answers_total':12,'minutes':10},
                            {'kid_id':KID,'parent_id':UID,'day':'2026-10-23','stars_total':20,'answers_right':20,'answers_total':24,'minutes':20},
                            {'kid_id':KID,'parent_id':UID,'day':'2026-10-27','stars_total':30,'answers_right':30,'answers_total':36,'minutes':30}]}
def user(): return {'id':UID,'email':'parent@example.test','aud':'authenticated','role':'authenticated','app_metadata':{},'user_metadata':{'nr_tour_done':True,'guardian_confirmed':True},'created_at':'2026-10-01T00:00:00Z'}
def handler(route):
    req=route.request;u=urlparse(req.url);path=u.path;qs=parse_qs(u.query);meth=req.method
    H={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'*','Content-Type':'application/json'}
    if meth=='OPTIONS': return route.fulfill(status=200,headers=H,body='')
    M.calls.append((meth,path+('?'+u.query if u.query else '')))
    body={}
    try: body=json.loads(req.post_data or '{}')
    except Exception: pass
    ok=lambda o,st=200: route.fulfill(status=st,headers=H,body=json.dumps(o))
    if path=='/functions/v1/nr-delete-account':
        M.fn.append({'body':body,'auth':req.headers.get('authorization')})
        if M.del_mode=='reauth' and not M.reauthed: return ok({'ok':False,'error':'reauth'},401)
        if M.del_mode=='unverified': return ok({'ok':True,'deleted':True})
        if M.del_mode in('ok','reauth'): return ok({'ok':True,'deleted':True,'verified':True})
        if M.del_mode=='partial': return ok({'ok':False,'error':'partial','step':'kids'},502)
        return route.abort()
    if path=='/functions/v1/nr-weekly':
        if body.get('action')=='preview': return ok({'ok':False,'error':'preview_limit'},429)
        if body.get('action')=='summary':
            ai=any(r.get('ai_summaries') for r in M.t.get('notify_prefs',[]))
            st={'minutes':95,'days_played':5,'stars':12,'answers':140,'accuracy':86,'strong':[{'n':'x2 facts','acc':97}],'weak':[{'n':'x7 facts','acc':58,'fam':'mult'}],'quests_done':1}
            if getattr(M,'ai_reason',None): return ok({'ok':True,'week':'2026-W44','source':'template','ai_reason':M.ai_reason,'text':'{{KID}} played 95 minutes this week.','stats':st})
            return ok({'ok':True,'week':'2026-W44','source':'ai' if ai else 'template','text':('{{KID}} had a strong week: 95 minutes on 5 days and 12 stars. x2 facts are rock solid at 97%. Try skip-counting by 7s on the stairs at home.' if ai else '{{KID}} played 95 minutes on 5 days this week and earned 12 stars.'),'stats':st})
        return ok({'code':'NOT_FOUND'},404)
    if path=='/auth/v1/otp': M.otp+=1;return ok({})
    if path=='/auth/v1/verify':
        if body.get('token')!='123456': return ok({'code':403,'error_code':'otp_expired','msg':'bad'},403)
        M.reauthed=M.otp>1
        return ok({'access_token':'test-access','token_type':'bearer','expires_in':3600,'expires_at':int(time.time())+3600,'refresh_token':'r','user':user()})
    if path=='/auth/v1/user': return ok(user())
    if path=='/auth/v1/logout': M.logout.append(qs.get('scope',[''])[0]);return route.fulfill(status=204,headers=H,body='')
    if path.startswith('/rest/v1/'):
        t=path.rsplit('/',1)[1]
        if meth=='GET':
            rows=M.t.get(t,[])
            if 'vnd.pgrst.object' in (req.headers.get('accept') or ''): return ok(rows[0]) if rows else ok({'code':'PGRST116'},406)
            return ok(rows)
        if meth=='POST' and t=='notify_prefs':
            M.upserts.append(body);M.t['notify_prefs']=[dict(body)]
        return route.fulfill(status=201 if meth=='POST' else 204,headers=H,body='')
    return ok({'message':'not mocked'},404)
def ctx(b,mob):
    c=b.new_context(viewport={'width':390,'height':844} if mob else {'width':1280,'height':900},device_scale_factor=2 if mob else 1,is_mobile=mob and BR=='chromium',has_touch=mob,timezone_id='America/New_York')
    c.route('**/*supabase.co/**',handler);return c
def signin(pg):
    pg.clock.set_fixed_time(NOW)
    pg.goto(f'http://localhost:{PORT}/parent.html');pg.wait_for_selector('#email')
    pg.fill('#email','parent@example.test');pg.click('#sendBtn');pg.wait_for_selector('#otp');pg.fill('#otp','123456');pg.click('#verifyBtn')
    pg.wait_for_selector('[data-kid]',timeout=15000)
def shot(pg,name,full=True):
    if SH: os.makedirs(OUT,exist_ok=True);pg.screenshot(path=f'{OUT}/{BR}-{name}.png',full_page=full)
with sync_playwright() as pw:
    b=getattr(pw,BR).launch()
    for mob in (False,True):
        tag='phone' if mob else 'desktop'
        # ---- shared "this week" stars (UTC) ----
        reset();c=ctx(b,mob);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));signin(pg)
        r=pg.evaluate("()=>{const ev=S.events[S.kids[0].id],pr=S.progress[S.kids[0].id];return [weekStars(ev,pr),starsThisWeek(ev,pr),mondayKey()]}")
        ck(r[0]==r[1]==10,f'{tag}: family card and challenge use one "this week" stars value (10)',r)
        ck(r[2]=='2026-10-26',f'{tag}: week starts Monday (UTC date)',r[2])
        pill=pg.locator('.pill',has_text='this week').first
        ck('10 this week' in pill.inner_text() and 'UTC' in (pill.get_attribute('title') or ''),f'{tag}: family card shows 10 this week with a UTC hint',pill.inner_text())
        shot(pg,f'{tag}-dashboard-family')
        r=pg.evaluate("()=>{const t=new Date('2026-11-01T23:30:00-05:00');const R=Date;let k;try{window.Date=class extends R{constructor(...a){return a.length?new R(...a):new R(t)}static now(){return t.getTime()}};k=mondayKey()}finally{window.Date=R}return k}")
        ck(r=='2026-11-02',f'{tag}: Sunday 11:30 PM Eastern is already Monday in UTC (new week, as documented)',r)
        pg.click('[data-kid]');pg.wait_for_selector('#statsNote',timeout=15000)
        note=pg.inner_text('#statsNote');ck('UTC' in note and 'not written by AI' in note,f'{tag}: kid page states days/weeks are UTC and stats are measured',note)
        lab=pg.inner_text('#sumLabel');ck(('AI-written' in lab) or ('Smart summary' in lab),f'{tag}: summary carries a source label',lab)
        shot(pg,f'{tag}-dashboard-kid')
        M.ai_reason='bad_key';pg.click('#sumRefresh');pg.wait_for_selector('#aiWhy',timeout=15000)
        w=pg.inner_text('#aiWhy');ck('AI unavailable (bad_key)' in w and 'Test mode' in w,f'{tag}: v32 (f) test mode shows why AI fell back',w)
        pg.locator('#summaryCard').scroll_into_view_if_needed();shot(pg,f'{tag}-ai-unavailable')
        M.ai_reason=None;pg.click('#sumRefresh');pg.wait_for_timeout(800);ck(pg.locator('#aiWhy').count()==0,f'{tag}: no fallback note when AI is simply off')
        # ---- delete account ----
        pg.click('#bellBtn');pg.wait_for_selector('#deleteCard')
        pg.locator('#deleteCard').scroll_into_view_if_needed();shot(pg,f'{tag}-delete-1-card',False)
        pg.click('#delAccount');pg.wait_for_selector('#delNote')
        ck('Type DELETE' in pg.inner_text('#delNote') and not M.fn,f'{tag}: delete without typing DELETE does nothing',pg.inner_text('#delNote'))
        pg.fill('#delConfirm','delete');pg.click('#delAccount');pg.wait_for_timeout(200);ck(not M.fn,f'{tag}: lowercase "delete" is not accepted')
        pg.fill('#delConfirm','DELETE');pg.locator('#deleteCard').scroll_into_view_if_needed();shot(pg,f'{tag}-delete-2-typed',False)
        pg.click('#delAccount');pg.wait_for_selector('#loginCard',timeout=10000)
        ck(len(M.fn)==1 and M.fn[0]['body']=={'confirm':'DELETE'} and M.fn[0]['auth']=='Bearer test-access',f'{tag}: calls nr-delete-account once with the parent JWT and the confirmation',M.fn)
        ck('global' in M.logout,f'{tag}: signs out everywhere (global logout)',M.logout)
        ck('deleted' in pg.inner_text('#loginCard'),f'{tag}: lands on sign-in with "account deleted" message')
        ck(pg.evaluate("!Object.keys(localStorage).some(k=>k.startsWith('sb-'))"),f'{tag}: no Supabase session left in localStorage')
        ck(not any('service' in json.dumps(x).lower() for x in M.fn),f'{tag}: no service key in the browser request')
        shot(pg,f'{tag}-delete-3-done')
        c.close()
        # ---- partial failure + unreachable ----
        for mode,want in (('partial','not all of it'),('down','nothing was deleted')):
            reset(mode);c=ctx(b,mob);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));signin(pg)
            pg.click('#bellBtn');pg.wait_for_selector('#deleteCard');pg.fill('#delConfirm','DELETE');pg.click('#delAccount')
            pg.wait_for_function("(()=>{const n=document.getElementById('delNote');return n&&!/Deleting/.test(n.textContent)})()",timeout=15000)
            t=pg.inner_text('#delNote');ck(want in t and pg.locator('#deleteCard').count()==1 and not M.logout,f'{tag}: {mode} -> stays signed in with a clear message',t)
            if mode=='partial': pg.locator('#deleteCard').scroll_into_view_if_needed();shot(pg,f'{tag}-delete-4-partial',False)
            # preview limit message (4th preview)
            if mode=='partial':
                pg.click('#emailPreview');pg.wait_for_function("(()=>{const n=document.getElementById('mailNote');return n&&!/Building/.test(n.textContent)})()")
                ck('3 previews a day' in pg.inner_text('#mailNote'),f'{tag}: preview limit message shown',pg.inner_text('#mailNote'))
            c.close()
        # ---- v32 CR-01: fresh re-auth, and unverified end state never shows 'deleted' ----
        reset('reauth');c=ctx(b,mob);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));signin(pg)
        pg.click('#bellBtn');pg.wait_for_selector('#deleteCard')
        ck('Delete your NumiRealm Parent Center account' in pg.inner_text('#deleteCard') and 'encrypted backups' in pg.inner_text('#deleteCard'),f'{tag}: delete screen uses the draft deletion text')
        pg.fill('#delConfirm','DELETE');pg.click('#delAccount');pg.wait_for_selector('#delOtp',timeout=10000)
        ck('Nothing has been deleted yet' in pg.inner_text('#delNote') and M.otp==2 and not M.logout,f'{tag}: stale sign-in -> code emailed, nothing deleted',pg.inner_text('#delNote'))
        pg.locator('#deleteCard').scroll_into_view_if_needed();shot(pg,f'{tag}-delete-5-reauth',False)
        pg.fill('#delOtp','000000');pg.click('#delVerify');pg.wait_for_function("/did not work/.test((document.getElementById('delNote')||{}).textContent||'')")
        ck(len(M.fn)==1,f'{tag}: wrong code -> no second delete call')
        pg.fill('#delOtp','123456');pg.click('#delVerify');pg.wait_for_selector('#loginCard',timeout=10000)
        ck(len(M.fn)==2 and 'deleted' in pg.inner_text('#loginCard'),f'{tag}: after re-auth the delete completes')
        c.close()
        reset('unverified');c=ctx(b,mob);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));signin(pg)
        pg.click('#bellBtn');pg.wait_for_selector('#deleteCard');pg.fill('#delConfirm','DELETE');pg.click('#delAccount')
        pg.wait_for_function("(()=>{const n=document.getElementById('delNote');return n&&!/Deleting/.test(n.textContent)})()",timeout=15000)
        ck(not M.logout and pg.locator('#deleteCard').count()==1,f'{tag}: server reply without verified=true is NOT shown as deleted')
        c.close()
        # ---- AI summaries toggle (default OFF) + full report ----
        reset();c=ctx(b,mob);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)));signin(pg)
        ck(pg.evaluate('AI_DEFAULT===false&&PREF_DEF.ai_summaries===false'),f'{tag}: AI summaries default OFF (single constant)')
        pg.click('[data-kid]');pg.wait_for_selector('#sumLabel');ck('Smart summary' in pg.inner_text('#sumLabel'),f'{tag}: before opt-in the summary is the template')
        pg.click('#bellBtn');pg.wait_for_selector('#pfAI');ck(not pg.is_checked('#pfAI'),f'{tag}: toggle starts off')
        pg.locator('#aiPrefs').scroll_into_view_if_needed();shot(pg,f'{tag}-ai-toggle-off',False)
        pg.check('#pfAI');pg.click('#savePrefs');pg.wait_for_timeout(500)
        ck(any(u.get('ai_summaries') is True for u in M.upserts),f'{tag}: turning it on saves ai_summaries=true to notify_prefs',M.upserts[-1:] )
        pg.click('#bellBtn') if pg.locator('#pfAI').count()==0 else None
        pg.wait_for_selector('#pfAI');pg.locator('#aiPrefs').scroll_into_view_if_needed();shot(pg,f'{tag}-ai-toggle-on',False)
        pg.goto(f'http://localhost:{PORT}/parent.html');pg.wait_for_selector('[data-kid]',timeout=15000);pg.click('[data-kid]');pg.wait_for_selector('#sumLabel')
        pg.wait_for_function("/AI-written/.test(document.getElementById('sumLabel').textContent)",timeout=10000)
        ck('AI-written' in pg.inner_text('#sumLabel') and 'not written by AI' in pg.inner_text('#statsNote'),f'{tag}: report shows AI-written section and measured stats, labeled')
        shot(pg,f'{tag}-report-full-ai-on')
        c.close()
    gp=b.new_page();gp.goto(f'http://localhost:{PORT}/gamenight.html?parenttest=1');gp.wait_for_function('typeof GN==="object"&&typeof GN.newCode==="function"')
    r=gp.evaluate("(()=>{const o=Math.random;let used=0;Math.random=()=>{used++;return o()};const c=[...Array(200)].map(GN.newCode),u=GN.uid();Math.random=o;return {used,uniq:new Set(c).size,ok:c.every(x=>/^[A-Z0-9]{5}$/.test(x)),u}})()")
    ck(r['used']==0 and r['uniq']>=195 and r['ok'] and len(r['u'])==24,'Game Night: room codes and ids use crypto.getRandomValues (no Math.random)',r)
    gp.close()
    ck(not errs,'no page errors',errs[:3])
    b.close()
print(f'RESULT {BR} {"OK" if not fails else "FAIL"} {len(fails)}')
srv.shutdown()
