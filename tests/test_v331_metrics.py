# v33.1 offline session metrics export: only in offline mode, grown-up gate behind a 1.5 s press on the offline badge,
# records real answers/hints, exports JSON on the device, 0 requests to any other host. Synthetic hero "Emi" only.
# Usage: PWB=chromium|webkit python test_v331_metrics.py   (screenshots -> SHOTS_DIR, default /workspace/v33shots/v33.1)
import os,sys,threading,http.server,functools,json,re
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));BR=os.environ.get('PWB','chromium')
PORT=int(os.environ.get('NR_PORT') or (8893 if BR=='chromium' else 8894))
SH=os.environ.get('SHOTS_DIR','/workspace/v33shots/v33.1');os.makedirs(SH,exist_ok=True)
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
src=open('/workspace/v18tmp/audit_play.py').read();ns={};exec(compile(src.split('ENGS=')[0]+'\n'+src[src.index('def pad'):src.index('def practice')],'ap','exec'),ns)
fails=[];B=f'http://127.0.0.1:{PORT}/'
def ck(c,m,info=''):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m+(f'  :: {info}' if info else ''))
    if not c: fails.append(m)
SEED={"muted":True,"narrator":False,"hero":"emi","profiles":{"emi":{"name":"Emi","prologue":True,"age":8,"grade":3,"stars":{"2":3},"subj":{"add":{"stars":{"1":3,"2":3},"hist":{},"intro":True}}}}}
with sync_playwright() as p:
    br=getattr(p,BR).launch()
    for vp,(w,h) in {'desktop':(1280,860),'phone':(390,844)}.items():
        ctx=br.new_context(viewport={'width':w,'height':h},is_mobile=(vp=='phone' and BR=='chromium'),has_touch=(vp=='phone'),accept_downloads=True)
        ctx.add_init_script("if(!localStorage.getItem('ttq-save-v2'))localStorage.setItem('ttq-save-v2',%s)"%json.dumps(json.dumps(SEED)))
        log=[];ctx.on('request',lambda r: log.append(r.url))
        ctx.route('**/*',lambda r: r.abort() if not r.request.url.startswith(B) and not r.request.url.startswith(('data:','blob:')) else r.continue_())
        pg=ctx.new_page();errs=[];pg.on('pageerror',lambda e: errs.append(str(e)))
        pg.goto(B+'index.html');pg.wait_for_timeout(1200)
        ck(pg.evaluate("NRM.on")==False and not pg.query_selector('#nrOfflineBadge'),f'{vp}: normal mode: no metrics recorder, no badge')
        log.clear();pg.goto(B+'index.html?localonly=1');pg.wait_for_timeout(1500)
        ck(pg.evaluate("NRM.on")==True,f'{vp}: offline mode: metrics recorder on')
        pg.evaluate("openChapter('add',2)");ns['scene'](pg);ns['learn'](pg);pg.wait_for_selector('[data-stage=practice]');pg.wait_for_function("TTQ_SUBJ.SS&&TTQ_SUBJ.SS.cur",timeout=10000)
        for right in (True,False,True):
            pg.wait_for_function("TTQ_SUBJ.SS&&TTQ_SUBJ.SS.cur&&!TTQ_SUBJ.SS.locked",timeout=10000);ns['answer'](pg,right);pg.wait_for_timeout(900)
            nx=pg.query_selector('#nextbtn:not(.hidden)') or pg.query_selector('#snext:not(.hidden)')
            if nx:
                try: nx.click()
                except Exception: pass
            pg.wait_for_timeout(500)
        raw=pg.evaluate("NRM._raw()");ck(len(raw['ans'])==3 and [a['ok'] for a in raw['ans']]==[True,False,True],f'{vp}: 3 real answers recorded (right, wrong, right)',str([a['ok'] for a in raw['ans']]))
        pg.evaluate("TTQ_HOME?TTQ_HOME():0") if pg.evaluate("typeof TTQ_HOME==='function'") else pg.goto(B+'index.html');pg.wait_for_timeout(1200)
        bb=pg.query_selector('#nrOfflineBadge').bounding_box();cx,cy=bb['x']+bb['width']/2,bb['y']+bb['height']/2
        pg.mouse.move(cx,cy);pg.mouse.down();pg.wait_for_timeout(400);pg.mouse.up();pg.wait_for_timeout(300)
        ck(not pg.query_selector('#nrmDlg'),f'{vp}: a short tap on the badge does nothing')
        pg.mouse.move(cx,cy);pg.mouse.down();pg.wait_for_timeout(1800);pg.mouse.up();pg.wait_for_timeout(300)
        ck(bool(pg.query_selector('#nrmDlg #nrmA')),f'{vp}: press-and-hold 1.5 s opens the grown-up check')
        lab=pg.inner_text('#nrmDlg label');a,b=map(int,re.findall(r'(\d+) × (\d+)',lab)[0])
        pg.fill('#nrmA','1');pg.click('#nrmGo');ck('Not quite' in pg.inner_text('#nrmErr') and not pg.query_selector('#nrmTxt'),f'{vp}: wrong grown-up answer keeps metrics closed')
        pg.fill('#nrmA',str(a*b+11));pg.click('#nrmGo');pg.wait_for_selector('#nrmTxt')
        txt=pg.inner_text('#nrmTxt');ck('Answers: 3, correct 2 (67%)' in txt and 'Hero: Emi' in txt,f'{vp}: panel shows the real numbers',txt.split('\n')[4] if len(txt.split('\n'))>4 else txt)
        ck(pg.inner_text('#nrmClose').strip()=='🏠 Back to NumiRealm',f'{vp}: panel has 🏠 Back to NumiRealm')
        pg.screenshot(path=f'{SH}/{BR}-{vp}-metrics-panel.png')
        with pg.expect_download() as dl: pg.click('#nrmDl')
        f=dl.value.path();J=json.load(open(f));ua=pg.evaluate('navigator.userAgent')
        ck(J['format']=='numirealm-session-metrics' and J['totals']['attempts']==3 and J['totals']['correct']==2 and J['heroes']==['Emi'],f'{vp}: exported JSON has real totals and only the hero nickname')
        ck(J['device']['user_agent']==ua and J['device']['viewport']==f'{w}x{h}',f'{vp}: device/browser filled from the browser itself, not invented',J['device']['viewport'])
        ck(len(J['tables_practiced'])>=1 and all(t['attempts']>0 for t in J['tables_practiced']) and J['totals']['median_sec_per_question']>=0,f'{vp}: per-skill attempts/accuracy/time present')
        ck(re.match(r'numirealm-session-\d{8}-\d{4}\.json$',dl.value.suggested_filename) is not None,f'{vp}: file name',dl.value.suggested_filename)
        ck(not re.search(r'@|token|parent|kid_id',json.dumps(J)),f'{vp}: no emails, tokens or account ids in the export')
        pg.click('#nrmClose');ck(not pg.query_selector('#nrmDlg'),f'{vp}: Back closes the panel')
        ext=[u for u in log if not u.startswith(B) and not u.startswith(('data:','blob:'))]
        ck(len(ext)==0,f'{vp}: 0 requests to any other host during the whole offline session',str(ext[:3]))
        ck(not errs,f'{vp}: no page errors',str(errs[:2]))
        pg.screenshot(path=f'{SH}/{BR}-{vp}-after-export.png');ctx.close()
    br.close()
print(f'RESULT metrics-{BR} {"FAIL" if fails else "OK"} fails={len(fails)}');sys.exit(1 if fails else 0)
