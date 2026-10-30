# v28 Family Game Night: gamenight.html with a mocked Supabase Realtime (Phoenix vsn 2.0.0) hub shared by
# several browser contexts (1 host + 3 phone players, plus late joiner / reconnect / full room / host-left checks).
# Usage: PWB=chromium|webkit NR_DIR=<repo> python test_gamenight.py   (SHOTS=1 GN_SHOTS_DIR=... for screenshots)
import os,json,re,threading,http.server,functools,time,struct
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)));BR=os.environ.get('PWB','chromium')
SH=os.environ.get('SHOTS')=='1';OUT=os.environ.get('GN_SHOTS_DIR','/tmp/numirealm-gn-shots')
os.makedirs(OUT,exist_ok=True) if SH else None
PORT=8891 if BR=='chromium' else 8892
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
HOST=f'http://localhost:{PORT}'
fails=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c: fails.append(m)

class Hub:
    """Tiny Phoenix/Realtime channel server: phx_join, presence track/untrack, binary user broadcasts, heartbeats."""
    def __init__(s): s.socks=[];s.pres={};s.n=0;s.log=[];s.blocked=False
    def handler(s,ws):
        if s.blocked: ws.close();return
        c={'ws':ws,'topics':{}};s.socks.append(c)
        ws.on_message(lambda m:s.msg(c,m));ws.on_close(lambda *a:s.gone(c))
    def out(s,c,arr):
        try: c['ws'].send(json.dumps(arr))
        except Exception: pass
    def peers(s,topic): return [c for c in s.socks if topic in c['topics']]
    def state(s,topic): return {k:{'metas':[v]} for k,v in s.pres.get(topic,{}).items()}
    def diff(s,topic,joins,leaves):
        for c in s.peers(topic): s.out(c,[None,None,topic,'presence_diff',{'joins':joins,'leaves':leaves}])
    def untrack(s,c,topic):
        key=c['topics'].get(topic,{}).get('key');P=s.pres.get(topic,{})
        if key in P and P[key].get('_sock')==id(c):
            m=P.pop(key);s.diff(topic,{},{key:{'metas':[m]}})
    def gone(s,c):
        if c in s.socks: s.socks.remove(c)
        for t in list(c['topics']): s.untrack(c,t)
        c['topics']={}
    def decode(s,b):
        b=bytes(b);kind=b[0]
        jl,rl,tl,el,ml,enc=b[1],b[2],b[3],b[4],b[5],b[6];i=7
        jr=b[i:i+jl].decode();i+=jl;ref=b[i:i+rl].decode();i+=rl;topic=b[i:i+tl].decode();i+=tl
        ev=b[i:i+el].decode();i+=el;i+=ml;payload=json.loads(b[i:].decode() or '{}')
        return jr,ref,topic,ev,payload
    def msg(s,c,m):
        if isinstance(m,(bytes,bytearray)):
            jr,ref,topic,ev,payload=s.decode(m);s.log.append(('bc',topic,ev,payload))
            for o in s.peers(topic):
                if o is not c: s.out(o,[None,None,topic,'broadcast',{'type':'broadcast','event':ev,'payload':payload}])
            if ref: s.out(c,[jr or None,ref,topic,'phx_reply',{'status':'ok','response':{}}])
            return
        jr,ref,topic,ev,p=json.loads(m)
        ok=lambda r={}:s.out(c,[jr,ref,topic,'phx_reply',{'status':'ok','response':r}])
        if ev=='heartbeat': ok();return
        if ev=='phx_join':
            key=(((p or {}).get('config') or {}).get('presence') or {}).get('key') or ''
            c['topics'][topic]={'key':key,'jr':jr};ok({'postgres_changes':[]})
            s.out(c,[jr,None,topic,'presence_state',s.state(topic)]);return
        if ev=='phx_leave': s.untrack(c,topic);c['topics'].pop(topic,None);ok();return
        if ev=='presence':
            key=c['topics'].get(topic,{}).get('key')
            if p.get('event')=='track':
                s.n+=1;meta=dict(p.get('payload') or {});meta['phx_ref']='r%d'%s.n;meta['_sock']=id(c)
                s.pres.setdefault(topic,{})[key]=meta;s.diff(topic,{key:{'metas':[meta]}},{})
            else: s.untrack(c,topic)
            ok();return
        if ev=='broadcast':  # JSON-encoded broadcast (older clients)
            for o in s.peers(topic):
                if o is not c: s.out(o,[None,None,topic,'broadcast',p])
            ok();return
        ok()

hub=Hub()
IPHONE=dict(viewport={'width':390,'height':844},device_scale_factor=2,has_touch=True,is_mobile=BR=='chromium')
# v32 CR-02: GN_SEC=1 sends seat claims to a local nr-gn (throwaway key); otherwise nr-gn "not deployed" (legacy mode)
GN_SEC=os.environ.get('GN_SEC')=='1';GN_URL=os.environ.get('GN_URL','http://127.0.0.1:8899')
def gn_route(r):
    if not GN_SEC: return r.fulfill(status=503,headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'},body='{"ok":false,"error":"not_configured"}')
    if r.request.method=='OPTIONS': return r.fulfill(status=200,headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'},body='ok')
    import urllib.request
    q=urllib.request.Request(GN_URL,data=r.request.post_data.encode(),headers={'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(q,timeout=10) as x: b=x.read();st=x.status
    except urllib.error.HTTPError as e: b=e.read();st=e.code
    r.fulfill(status=st,headers={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'},body=b)
def shot(pg,name,full=False):
    if SH: pg.wait_for_timeout(150);pg.screenshot(path=f'{OUT}/{name}.png',full_page=full)
def ctx(b,phone=True,flag=True):
    c=b.new_context(**(IPHONE if phone else dict(viewport={'width':1280,'height':900})))
    c.route_web_socket(re.compile(r'.*/realtime/v1/websocket.*'),hub.handler)
    c.route('**/functions/v1/nr-gn',gn_route)
    pg=c.new_page();pg.on('console',lambda m:errs.append(m.text) if m.type=='error' else None);pg.on('pageerror',lambda e:errs.append(str(e)))
    return c,pg
def solve(q):
    t=q.replace('−','-').replace('×','*').replace('÷','/').replace(' = ?','').strip()
    m=re.match(r'(\d+)/(\d+) of (\d+)',t)
    if m: return int(m.group(3))//int(m.group(2))*int(m.group(1))
    return int(eval(t))
def gate(pg):
    t=pg.inner_text('#gateQ');a,b,c=map(int,re.findall(r'\d+',t));pg.fill('#gateIn',str(a*b+c));pg.click('#gateGo')

with sync_playwright() as p:
    b=getattr(p,BR).launch()
    # ---- normal game unchanged; visibility rules ----
    c0,pg=ctx(b,phone=False)
    pg.goto(HOST+'/gamenight.html');ck(pg.is_visible('#gnOff') and pg.is_hidden('#joinBtn'),'gamenight hidden (Coming soon) without flag/link/portal')
    pg.goto(HOST+'/index.html');pg.wait_for_timeout(600);ck(pg.locator('#nrhGN,#nrGameNight').count()==0,'normal game: no Game Night entry')
    pg.goto(HOST+'/index.html?parenttest=1');pg.wait_for_selector('#nrhGN',timeout=8000);ck(pg.is_visible('#nrhGN'),'game (?parenttest=1): Game Night button on the home card')
    bb=pg.locator('#nrhGN').bounding_box();ck(bb and bb['height']>=44,'Game Night button >=44px')
    pg.click('#nrhGN');pg.wait_for_url(re.compile(r'gamenight\.html\?parenttest=1'));ck(pg.is_visible('#gnHome') and pg.is_visible('#testBanner'),'game button opens Game Night home (test banner)')
    # v29: the test flag is remembered per device, so forget it before checking a linked device without the flag
    pg.evaluate("localStorage.removeItem('nr-parenttest')");pg.evaluate("localStorage.setItem('nr-parent-link',JSON.stringify({nickname:'Mia',hero:'emi',deviceName:'iPad',code:'X'}))")
    pg.goto(HOST+'/index.html');pg.wait_for_timeout(800)
    ck(pg.locator('#nrParentHome #nrhGN').count()==1,'v30: linked device (no flag): Game Night button in the public Parent card')
    pg.goto(HOST+'/gamenight.html');ck(pg.is_visible('#gnHome') and pg.is_hidden('#testBanner'),'linked device can open Game Night')
    pg.evaluate("localStorage.clear()");c0.close()
    # ---- host: gate + setup ----
    ch,host=ctx(b,phone=False)
    host.goto(HOST+'/gamenight.html?parenttest=1');host.click('#hostBtn')
    host.fill('#gateIn','1');host.click('#gateGo');ck(host.is_visible('#gateErr'),'host gate: wrong answer rejected')
    gate(host);host.wait_for_selector('#gnSetup');shot(host,'gn-01-host-setup',True)
    for el in host.query_selector_all('#gnSetup .btn,#gnSetup .chip,#gnSetup select'):
        bx=el.bounding_box()
        if bx and bx['height']<44: ck(False,'setup control <44px');break
    else: ck(True,'setup controls >=44px')
    host.uncheck('input[value=mult]');host.click('#createRoom');ck('at least one topic' in host.inner_text('#setupErr'),'setup needs a topic')
    host.check('input[value=mult]');host.check('input[value=add]');host.select_option('#rounds','3');host.select_option('#secs','20')
    host.uncheck('#voice');host.click('#createRoom');host.wait_for_selector('#roomCode')
    host.wait_for_function("!document.getElementById('hostConn')",timeout=8000)
    code=host.inner_text('#roomCode').strip();ck(re.fullmatch(r'[A-Z2-9]{5}',code) is not None,f'room code {code}')
    bk=host.evaluate("(()=>{const a=document.getElementById('backLink'),r=a.getBoundingClientRect(),cs=getComputedStyle(a);return {t:a.textContent.trim(),h:a.getAttribute('href'),ht:r.height,top:r.top,left:r.left,vw:innerWidth,pill:cs.borderRadius,bg:cs.backgroundImage}})()")
    ck(bk['t']=='🏠 Back to NumiRealm' and bk['h']=='./?parenttest=1' and bk['ht']>=44 and bk['left']<bk['vw']/2 and 'gradient' in bk['bg'],f'Back to NumiRealm pill like the parent pages, keeps ?parenttest=1 {bk}')
    ck(host.locator('#qr svg').count()==1,'QR code shown');ck(host.is_disabled('#startGame'),'start disabled with no players')
    # ---- 3 players join on phones ----
    names=[('Mia','emi','b'),('Leo','blu','a'),('Dad','sage','g')];pl=[]
    for i,(n,h,lv) in enumerate(names):
        c,pg=ctx(b)
        if i==0:
            pg.goto(HOST+f'/gamenight.html?parenttest=1&join={code}');pg.wait_for_selector('#gnJoin')
            ck(pg.input_value('#joinCode')==code,'QR link pre-fills the code')
        else:
            pg.goto(HOST+'/gamenight.html?parenttest=1');pg.click('#joinBtn');pg.fill('#joinCode',code.lower())
        pg.click(f'[data-hero={h}]')
        ck(pg.input_value('#joinName')==dict(emi='Emi',blu='Blú',sage='Sage')[h],'hero pick fills nickname')
        pg.fill('#joinName',n+('<>' if i==2 else ''));pg.select_option('#joinLevel',lv)
        if i==0: shot(pg,'gn-02-join-phone',True)
        pg.click('#joinGo');pg.wait_for_selector('#waitMsg',timeout=8000);pl.append((c,pg))
    host.wait_for_function("document.querySelectorAll('#plist li:not(.off)').length===3",timeout=8000)
    ck('Dad' in host.inner_text('#plist') and 'Dadb' not in host.inner_text('#plist') and '<' not in host.inner_text('#plist'),'nickname cleaned (no HTML)')
    ck(not host.is_disabled('#startGame'),'start enabled');shot(host,'gn-03-host-lobby',True)
    # bad code
    cx,px=ctx(b);px.goto(HOST+'/gamenight.html?parenttest=1');px.click('#joinBtn');px.fill('#joinCode','AB');px.click('[data-hero=eshon]');px.click('#joinGo')
    ck('5-letter' in px.inner_text('#joinErr'),'short code rejected')
    # ---- round 1: fair play, different levels ----
    host.click('#startGame')
    for c,pg in pl: pg.wait_for_selector('#qText',timeout=8000)
    qt=[pg.inner_text('#qText') for c,pg in pl];ck(all('= ?' in q for q in qt),f'all 3 phones show a question {qt}')
    ck(pl[0][1].locator('.choice').count()==4,'multiple choice: 4 answers')
    bx=pl[0][1].locator('.choice').first.bounding_box();ck(bx['height']>=44,'answer buttons >=44px')
    shot(pl[0][1],'gn-04-question-phone');shot(host,'gn-05-host-question',True)
    a0=solve(qt[0]);pl[0][1].click(f'.choice[data-v="{a0}"]');ck('locked in' in pl[0][1].inner_text('#locked'),'answer locked in')
    pl[1][1].wait_for_timeout(500);a1=solve(qt[1]);wrong=[v for v in pl[1][1].eval_on_selector_all('.choice','e=>e.map(x=>x.dataset.v)') if int(v)!=a1][0]
    pl[1][1].click(f'.choice[data-v="{wrong}"]')
    pl[2][1].wait_for_timeout(300);pl[2][1].click(f'.choice[data-v="{solve(qt[2])}"]')
    host.wait_for_selector('#gnHostReveal',timeout=8000)
    for c,pg in pl: pg.wait_for_selector('#gnReveal',timeout=8000)
    sc={l.get_attribute('data-pid'):int(l.inner_text().split()[-1]) for l in host.query_selector_all('#board li')}
    vals=sorted(sc.values(),reverse=True);ck(vals[0]>vals[1]>vals[2]==0,f'speed bonus orders scores {vals}')
    ck(all(100<=v<=150 for v in vals[:2]),'correct = 100 + up to 50 speed bonus')
    ck('Correct' in pl[0][1].inner_text('#myResult') and 'Almost' in pl[1][1].inner_text('#myResult'),'reveal: right/wrong per player')
    ck(str(a1) in pl[1][1].inner_text('#rightAns'),'reveal shows the right answer')
    ck(pl[0][1].locator('#board li.me').count()==1,'leaderboard highlights me')
    shot(pl[0][1],'gn-06-reveal-phone',True);shot(host,'gn-07-host-leaderboard',True)
    # ---- reconnect: player 2 reloads ----
    pl[1][1].reload();pl[1][1].wait_for_selector('#gnReveal,#gnWait',timeout=8000)
    ck('Leo' in pl[1][1].inner_text('#app'),'reload reconnects with the same nickname')
    host.wait_for_function("document.querySelectorAll('#board li').length===3",timeout=8000)
    ck(host.locator('#board li').count()==3,'reconnect does not create a duplicate player')
    # ---- late joiner ----
    cl,late=ctx(b);late.goto(HOST+f'/gamenight.html?parenttest=1&join={code}');late.click('[data-hero=eshon]');late.click('#joinGo')
    late.wait_for_selector('#gnReveal,#gnWait',timeout=8000)
    host.wait_for_function("document.querySelectorAll('#board li').length===4",timeout=8000);ck(True,'late joiner added to the leaderboard')
    # ---- round 2 (all answer; typed timeout path covered later) ----
    host.click('#nextQ')
    for c,pg in pl+[(cl,late)]: pg.wait_for_selector('#qText',timeout=8000)
    ck(late.is_visible('#qText'),'late joiner plays the next round')
    for c,pg in pl+[(cl,late)]: pg.click(f'.choice[data-v="{solve(pg.inner_text("#qText"))}"]')
    host.wait_for_selector('#nextQ',timeout=8000)
    # ---- round 3 = last: one player times out? use Show answers now ----
    host.click('#nextQ');pl[0][1].wait_for_selector('#qText',timeout=8000)
    pl[0][1].click(f'.choice[data-v="{solve(pl[0][1].inner_text("#qText"))}"]');host.wait_for_timeout(300);host.click('#skipQ')
    pl[2][1].wait_for_selector('#gnReveal',timeout=8000);ck('Time ran out' in pl[2][1].inner_text('#myResult'),'no answer -> time ran out, 0 points')
    host.wait_for_selector('#gnPodium',timeout=12000);pl[0][1].wait_for_selector('#gnPodium',timeout=8000)
    ck(host.locator('.pod.p1 .nm').count()==1 and host.is_visible('#owlLine'),'podium + owl narrator on host')
    ck('Mia' in host.inner_text('.pod.p1'),'fastest correct player wins');ck('You won' in pl[0][1].inner_text('#myPlace'),'winner sees You won')
    shot(host,'gn-08-podium-host',True);shot(pl[0][1],'gn-09-podium-phone',True)
    # ---- play again then type mode ----
    host.click('#again');host.wait_for_selector('#gnLobby');pl[0][1].wait_for_selector('#waitMsg',timeout=8000);ck(True,'play again returns everyone to the lobby')
    # ---- room full (8) ----
    extra=[]
    for i in range(4):
        c,pg=ctx(b);pg.goto(HOST+f'/gamenight.html?parenttest=1&join={code}');pg.fill('#joinName',f'Kid{i}');pg.click('#joinGo');pg.wait_for_selector('#waitMsg',timeout=8000);extra.append(c)
    c9,p9=ctx(b);p9.goto(HOST+f'/gamenight.html?parenttest=1&join={code}');p9.fill('#joinName','Nine');p9.click('#joinGo')
    p9.wait_for_selector('#joinErr',timeout=8000);ck('full' in p9.inner_text('#joinErr'),'9th player: room is full')
    host.wait_for_timeout(300);ck(host.locator('#plist li').count()==8,'cap of 8 players')
    # ---- host leaves ----
    host.close()
    for c in list(hub.socks):  # server notices the closed tab (mock does not always get a close event)
        if any(t['key'].startswith('host-') for t in c['topics'].values()): hub.gone(c)
    pl[0][1].wait_for_selector('#gnEnded',timeout=15000)
    ck('host left' in pl[0][1].inner_text('#endMsg') or 'closed' in pl[0][1].inner_text('#endMsg'),'host leaving ends the game for players')
    # host connection lost without goodbye -> 10 s grace
    ch2,h2=ctx(b,phone=False);h2.goto(HOST+'/gamenight.html?parenttest=1');h2.click('#hostBtn');gate(h2);h2.select_option('#mode','type');h2.click('#createRoom')
    h2.wait_for_selector('#roomCode');h2.wait_for_function("!document.getElementById('hostConn')",timeout=8000);code2=h2.inner_text('#roomCode').strip()
    cp,pp=ctx(b);pp.goto(HOST+f'/gamenight.html?parenttest=1&join={code2}');pp.fill('#joinName','Mia');pp.click('#joinGo');pp.wait_for_selector('#waitMsg',timeout=8000)
    h2.click('#startGame');pp.wait_for_selector('#typeAns',timeout=8000);ck(pp.locator('.choice').count()==0,'typed-number mode')
    pp.fill('#typeAns',str(solve(pp.inner_text('#qText'))));pp.click('#typeGo');pp.wait_for_selector('#gnReveal',timeout=8000)
    ck('Correct' in pp.inner_text('#myResult'),'typed answer scored correct')
    # simulate the host dropping (no 'end' message): close its socket from the hub side
    for c in list(hub.socks):
        if any(t['key'].startswith('host-') for t in c['topics'].values()): hub.gone(c)
    pp.wait_for_selector('#hostAway',timeout=4000);ck(True,'player sees host-lost warning')
    pp.wait_for_selector('#gnEnded',timeout=14000);ck('host left' in pp.inner_text('#endMsg'),'after grace the game ends (host left)')
    # offline: hub refuses -> friendly error
    co,po=ctx(b);co.route('**/vendor/supabase.js',lambda r:r.abort());po.goto(HOST+'/gamenight.html?parenttest=1&join=ABCDE');po.fill('#joinName','Mia');po.click('#joinGo')
    po.wait_for_selector('#connErr,#joinErr',timeout=16000);ck(po.locator('#connErr').count()==1,'no realtime client (offline) -> friendly message')
    # broadcasts never carried answers before reveal
    def body(e):
        pl=e[3] or {}
        return json.loads(pl['st']) if isinstance(pl.get('st'),str) else pl
    if GN_SEC:
        sts=[e for e in hub.log if e[2]=='state'];ans=[e for e in hub.log if e[2]=='answer']
        ck(sts and all(isinstance(e[3].get('st'),str) and e[3].get('s') for e in sts),f'CR-02: all {len(sts)} host states are signed')
        ck(ans and all(e[3].get('s') for e in ans),f'CR-02: all {len(ans)} answers are signed')
        cx,px=ctx(b);px.goto(HOST+'/gamenight.html?parenttest=1');px.wait_for_selector('#gnHome')
        r=px.evaluate('''async()=>{const G=GN,o={};const a=await G.gnClaim('QWERT','player'),bb=await G.gnClaim('QWERT','player'),h=await G.gnClaim('QWERT','host');
          o.claims=!!(a&&bb&&h)&&a.pid!==bb.pid;const ca=await G.gnCheck(h,a.claim,a.sig,'QWERT','player');o.valid=!!ca&&ca.pid===a.pid;
          const msg=JSON.stringify(['QWERT',a.pid,1,'42']);o.ownSig=await G.gnVerify(ca.key,msg,await G.gnSign(a,msg));
          o.impersonate=await G.gnVerify(ca.key,msg,await G.gnSign(bb,msg));
          const forged=a.claim.replace(a.pid,bb.pid);o.forgedClaim=await G.gnCheck(h,forged,a.sig,'QWERT','player');
          o.wrongRoom=await G.gnCheck(h,a.claim,a.sig,'ZZZZZ','player');o.playerAsHost=await G.gnCheck(h,a.claim,a.sig,'QWERT','host');return o;}''')
        ck(r['claims'] and r['valid'] and r['ownSig'],'CR-02: server-signed seats issued and verified')
        ck(r['impersonate'] is False,'CR-02: player B cannot sign an answer as player A')
        ck(r['forgedClaim'] is None,'CR-02: edited claim (stolen id) rejected')
        ck(r['wrongRoom'] is None and r['playerAsHost'] is None,'CR-02: claim for another room or a player posing as host rejected')
        cx.close()
    leak=[e for e in hub.log if e[2]=='state' and body(e).get('phase')=='question' and 'ans' in json.dumps(body(e).get('q'))]
    ck(not leak,'question broadcasts carry no answers')
real=[e for e in errs if 'WebSocket' not in e and 'websocket' not in e and 'Failed to load resource' not in e and 'supabase.js' not in e]
ck(not real,f'no console errors {real[:5]}')
print(f'RESULT {BR} FAILS {len(fails)}',flush=True)
os._exit(0)  # skip slow teardown of many routed websockets
