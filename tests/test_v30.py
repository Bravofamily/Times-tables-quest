# v30: Parent Login for everyone, 18+ grown-up gate pop-up, guardian checkbox on parent sign-up.
# Usage: PWB=chromium|webkit python test_v30.py
import os,re,json,threading,http.server,functools
from playwright.sync_api import sync_playwright
D=os.environ.get('NR_DIR') or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BR=os.environ.get('PWB','chromium');P=8751 if BR=='chromium' else 8753
SHOTS=os.environ.get('NR_SHOTS','/tmp/v30shots');os.makedirs(SHOTS,exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
    def end_headers(self):self.send_header('Cache-Control','no-cache');super().end_headers()
s=http.server.ThreadingHTTPServer(('127.0.0.1',P),functools.partial(Q,directory=D));threading.Thread(target=s.serve_forever,daemon=True).start()
HOST=f'http://127.0.0.1:{P}';F=[];errs=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m)
    if not c:F.append(m)
html=open(os.path.join(D,'index.html'),encoding='utf-8').read()
av=re.search(r"const APP_VERSION='(\d+)'",html).group(1)
ck(int(av)>=30 and json.load(open(os.path.join(D,'version.json')))['version']==av,'APP_VERSION and version.json match and are >=30')
otp=[]
def sb(r):
    if '/auth/v1/otp' in r.request.url:otp.append(r.request.post_data or '');return r.fulfill(status=200,content_type='application/json',body='{}')
    r.abort()
def ctx(b,phone=False):
    c=b.new_context(viewport={'width':390,'height':844} if phone else {'width':1280,'height':800},service_workers='block',has_touch=phone,is_mobile=phone and BR=='chromium')
    c.route('**/*supabase.co/**',sb);return c
def home(pg,q=''):
    pg.goto(f'{HOST}/index.html{q}');pg.wait_for_timeout(1300)
    pg.evaluate("void(document.getElementById('nrSplash')&&document.getElementById('nrSplash').remove())")
def answer(pg):
    a,b,c=map(int,re.findall(r'\d+',pg.inner_text('#nrtQ')));return a*b+c
with sync_playwright() as p:
    br=getattr(p,BR).launch()
    for phone in (False,True):
        tag='phone' if phone else 'desktop'
        c=ctx(br,phone);pg=c.new_page();pg.on('pageerror',lambda e:errs.append(str(e)))
        home(pg)
        ck(pg.locator('#nrhTop').is_visible(),f'{tag}: no flag, top-bar 🔑 Parent Login visible')
        ck(pg.locator('#nrhLogin').count()==1 and 'Parent Login' in pg.inner_text('#nrhLogin'),f'{tag}: no flag, Home "Parent Login" entry shown')
        ck(pg.locator('#nrhWhat').count()==1,f'{tag}: no flag, "What\'s included?" link shown')
        ck(pg.locator('#nrhGN').count()==0 and pg.locator('#nrQuest').count()==0,f'{tag}: no flag, Game Night and Quest stay hidden')
        pg.screenshot(path=f'{SHOTS}/{BR}-{tag}-home-noflag.png')
        url0=pg.url
        pg.click('#nrhTop');pg.wait_for_timeout(300)
        g=pg.locator('#nrhTopGate')
        ck(g.is_visible() and '18+' in g.inner_text() and 'parents and guardians' in g.inner_text(),f'{tag}: gate pop-up says parents and guardians only (18+)')
        box=pg.locator('#nrhTopGate .nrhdlg').bounding_box();vw=pg.viewport_size['width']
        ck(box and box['x']>=0 and box['x']+box['width']<=vw+1,f'{tag}: gate fits the screen')
        pg.screenshot(path=f'{SHOTS}/{BR}-{tag}-gate.png')
        pg.click('#nrtCancel');pg.wait_for_timeout(300)
        ck(pg.locator('#nrhTopGate').count()==0 and pg.url==url0,f'{tag}: Cancel closes the gate and stays in the game')
        pg.click('#nrhTop');pg.wait_for_timeout(200);ans=answer(pg)
        pg.fill('#nrtGate',str(ans+1));pg.click('#nrtGo');pg.wait_for_timeout(400)
        ck(pg.locator('#nrtErr').is_visible() and pg.url==url0,f'{tag}: wrong answer blocks and shows an error')
        pg.keyboard.press('Escape');pg.wait_for_timeout(200)
        pg.click('#nrhLogin');pg.wait_for_timeout(200)
        ck(pg.locator('#nrhTopGate').is_visible(),f'{tag}: Home Parent Login opens the same gate pop-up')
        pg.fill('#nrtGate',str(answer(pg)));pg.click('#nrtGo');pg.wait_for_load_state();pg.wait_for_timeout(900)
        ck('parent.html' in pg.url and '#login' in pg.url and 'parenttest' not in pg.url,f'{tag}: right answer continues to parent.html#login ({pg.url})')
        # sign-up checkbox
        pg.goto(f'{HOST}/parent.html#signup');pg.wait_for_timeout(1200)
        chk=pg.locator('#guardChk')
        ck(chk.count()==1 and not chk.is_checked(),f'{tag}: sign-up checkbox present and unchecked')
        lt=pg.inner_text('#loginCard')
        ck("I'm a parent or legal guardian, 18 or older, and I agree to the Terms and Privacy Policy." in lt,f'{tag}: checkbox wording')
        ck(pg.get_attribute('#termsLink','href')=='parent-about.html#safeT',f'{tag}: Terms/Privacy link points to existing grown-up privacy content')
        ck(pg.get_attribute('#sendBtn','aria-disabled')=='true',f'{tag}: Create account disabled until ticked')
        pg.fill('#email','parent@example.com');n=len(otp);pg.click('#sendBtn',force=True);pg.wait_for_timeout(500)
        ck(len(otp)==n and pg.locator('#err').is_visible() and 'tick' in pg.inner_text('#err'),f'{tag}: unticked sign-up blocked with a clear error')
        pg.locator('#guardChk').check();pg.wait_for_timeout(200)
        ck(pg.get_attribute('#sendBtn','aria-disabled') is None,f'{tag}: ticking enables Create account')
        pg.screenshot(path=f'{SHOTS}/{BR}-{tag}-signup-checkbox.png',full_page=False)
        pg.fill('#email','parent@example.com');pg.click('#sendBtn');pg.wait_for_timeout(1200)
        body=otp[-1] if len(otp)>n else ''
        ck('"guardian_confirmed":true' in body.replace(' ','') and 'guardian_confirmed_at' in body and '"create_user":true' in body.replace(' ',''),f'{tag}: sign-up sends guardian_confirmed metadata')
        ck(pg.locator('#otp').count()==1,f'{tag}: email code step still follows')
        pg.goto(f'{HOST}/parent.html#login');pg.wait_for_timeout(1000)
        ck(pg.locator('#guardChk').count()==0,f'{tag}: plain Parent Login has no checkbox')
        n=len(otp);pg.fill('#email','parent@example.com');pg.click('#sendBtn');pg.wait_for_timeout(1200)
        ck(len(otp)>n and '"create_user":false' in otp[-1].replace(' ',''),f'{tag}: Parent Login does not create new accounts')
        c.close()
    # tester flag still unlocks extras
    c=ctx(br);pg=c.new_page();home(pg,'?parenttest=1')
    ck(pg.locator('#nrhGN').count()==1,'?parenttest=1: Game Night button shown for testers')
    home(pg,'?parenttest=0');ck(pg.locator('#nrhGN').count()==0 and pg.locator('#nrhTop').is_visible(),'?parenttest=0: extras off, Parent Login still shown')
    c.close();br.close()
ck(not errs,'no page errors '+str(errs[:2]))
print('RESULT',BR,'OK' if not F else 'FAIL',len(F))
