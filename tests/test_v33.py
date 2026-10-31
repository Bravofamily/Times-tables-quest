# v33 tests: save-lineage id in the sync payload; local-only supervised mode makes ZERO non-localhost requests.
# Usage: PWB=chromium|webkit python test_v33.py
import os,threading,http.server,functools,json
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.dirname(os.path.abspath(__file__)));BR=os.environ.get('PWB','chromium')
PORT=int(os.environ.get('NR_PORT') or (8895 if BR=='chromium' else 8896))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',PORT),functools.partial(Q,directory=D));threading.Thread(target=srv.serve_forever,daemon=True).start()
fails=[]
def ck(c,m,info=''):
    print(('PASS ' if c else 'FAIL ')+f'[{BR}] '+m+(f'  :: {info}' if info else ''))
    if not c: fails.append(m)
B=f'http://127.0.0.1:{PORT}/'
LINK=json.dumps({'token':'t'*40,'hero':'x','kid':'k','dev':'test'})
with sync_playwright() as p:
    br=getattr(p,BR).launch()
    # 1) lineage id in payload, stable across reloads, copied with the save
    ctx=br.new_context();pg=ctx.new_page()
    pg.route('**/*',lambda r: r.abort() if '127.0.0.1' not in r.request.url else r.continue_())
    pg.goto(B+'index.html');pg.wait_for_timeout(800)
    l1=pg.evaluate("()=>{const h=save.hero||Object.keys(save.profiles)[0];const p=NRP.payload(save,h);return p&&p.lin}")
    ck(bool(l1) and l1.startswith('lin-'),'payload carries lin',str(l1))
    pg.reload();pg.wait_for_timeout(800)
    l2=pg.evaluate("()=>{const h=save.hero||Object.keys(save.profiles)[0];return NRP.payload(save,h).lin}")
    ck(l1==l2,'lin stable across reload')
    l3=pg.evaluate("()=>{const c=JSON.parse(JSON.stringify(save));return NRP.payload(c,save.hero||Object.keys(save.profiles)[0]).lin}")
    ck(l3==l1,'backup copy keeps the same lin')
    ctx.close()
    # 2) local-only mode: no request leaves localhost, even with a linked device and a queued sync
    ctx=br.new_context();pg=ctx.new_page();ext=[]
    def h(r):
        if '127.0.0.1' not in r.request.url and not r.request.url.startswith(('data:','blob:')): ext.append(r.request.url); return r.abort()
        return r.continue_()
    pg.route('**/*',h)
    pg.goto(B+'index.html?localonly=1&parenttest=1');pg.wait_for_timeout(800)
    ck(pg.evaluate('window.NR_LOCALONLY')==True,'local-only flag on')
    pg.evaluate(f"()=>{{localStorage.setItem('nr-parent-link',{json.dumps(LINK)});}}")
    pg.goto(B+'index.html');pg.wait_for_timeout(800)
    ck(pg.evaluate('window.NR_LOCALONLY')==True,'local-only persists without the URL flag')
    pg.evaluate("async()=>{try{NRP.queue();}catch(e){} try{await NRP.flush();}catch(e){}}");pg.wait_for_timeout(4500)
    pg.goto(B+'gamenight.html');pg.wait_for_timeout(1000)
    ck(len(ext)==0,'zero non-localhost requests in local-only mode (index + gamenight load)',str(ext[:5]))
    pg.goto(B+'index.html?localonly=0');pg.wait_for_timeout(500)
    ck(pg.evaluate('window.NR_LOCALONLY')==False,'local-only can be turned off with ?localonly=0')
    ctx.close();br.close()
print(f'RESULT v33 [{BR}] fails={len(fails)}')
