import json,threading,http.server,functools,time,sys
from playwright.sync_api import sync_playwright
D='/workspace/times-tables-quest'
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8771),functools.partial(http.server.SimpleHTTPRequestHandler,directory=D))
srv.RequestHandlerClass.log_message=lambda *a:None
threading.Thread(target=srv.serve_forever,daemon=True).start()
URL='http://127.0.0.1:8771/index.html'
SAVE={"muted":True,"narrator":False,"hero":"emi","profiles":{"emi":{"name":"Emi","stars":{"2":3},"hist":{},"rewards":["fcrown"],"eq":{},"prologue":True}}}
errs=[];fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m); 
    if not c: fails.append(m)
with sync_playwright() as p:
    b=p.chromium.launch()
    def ctx(remote):
        c=b.new_context(service_workers='block'); c.add_init_script("if(!localStorage.getItem('ttq-test-seeded')){localStorage.setItem('ttq-test-seeded','1');localStorage.setItem('ttq-save-v2',%s)}"%json.dumps(json.dumps(SAVE)))
        st={'v':remote,'hits':0}
        def h(route):
            st['hits']+=1
            if st['v']=='ABORT': route.abort(); return
            route.fulfill(status=200,content_type='application/json',body=json.dumps({"version":st['v']}))
        c.route('**/version.json*',h)
        pg=c.new_page(); navs=[]
        pg.on('framenavigated',lambda f: navs.append(f.url) if f==pg.main_frame else None)
        pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None)
        pg.on('pageerror',lambda e: errs.append(str(e)))
        return c,pg,navs,st
    # find real save key
    c,pg,navs,st=ctx('12'); pg.goto(URL); pg.wait_for_timeout(1500)
    skey=pg.evaluate("Object.keys(localStorage).filter(k=>k!=='ttq-test-seeded')"); print('keys',skey)
    ck(navs==[URL],'matching version: no reload (navs=%s)'%navs)
    ck(st['hits']>=1,'version.json fetched on launch')
    ck(pg.evaluate("TTQ_VERSION.app")=='12','APP_VERSION=12')
    # resume while matching -> no reload
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(800)
    ck(len(navs)==1,'matching version on resume: no reload')
    # mid-level resume with new version -> waits
    pg.evaluate("show('<div id=fake-level>level in progress</div>')"); st['v']='13'
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(1000)
    ck(len(navs)==1 and pg.evaluate("TTQ_VERSION.pending")=='13','mid-level: update deferred, pending=13')
    before=pg.evaluate("JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
    pg.evaluate("mapScreen()"); pg.wait_for_timeout(2000)
    ck(len(navs)==2 and navs[-1].endswith('/index.html?v=13'),'back on map: reloaded once to ?v=13 (%s)'%navs)
    after=pg.evaluate("JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
    import json as J
    bb=J.loads(before);aa=J.loads(after)
    for k in set(bb)|set(aa):
        if bb.get(k)!=aa.get(k): print('DIFF',k,'\n before:',bb.get(k)[:400] if bb.get(k) else None,'\n after:',aa.get(k)[:400] if aa.get(k) else None)
    ck(J.loads(bb['ttq-save-v2'])['profiles']['emi']==J.loads(aa['ttq-save-v2'])['profiles']['emi'] and J.loads(bb['ttq-save-v2'])['hero']==J.loads(aa['ttq-save-v2'])['hero'],'Emi save + selected hero identical across reload (other heroes only gain their normal empty default profiles)')
    pg.wait_for_timeout(2500); pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(1500)
    ck(len(navs)==2,'no reload loop after ?v=13 (still-stale HTML)')
    # subject-realm lesson in progress -> deferred; back on subject map -> reload
    pg.evaluate("openChapter('add',1)"); pg.wait_for_timeout(300); st['v']='14'
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(1000)
    n0=len(navs); ck(pg.evaluate("TTQ_VERSION.pending")=='14','subject lesson: update deferred, pending=14')
    pg.evaluate("smapScreen('add')"); pg.wait_for_timeout(2000)
    ck(len(navs)==n0+1 and navs[-1].endswith('?v=14'),'back on subject map: reloaded to ?v=14 (%s)'%navs)
    c.close()
    # launch with mismatch -> immediate single reload
    c,pg,navs,st=ctx('13'); pg.goto(URL); pg.wait_for_timeout(4000)
    ck(len(navs)==2 and navs[-1].endswith('?v=13'),'launch mismatch: one reload to ?v=13 (%s)'%navs)
    ck(pg.evaluate("document.querySelector('#app').innerHTML.length")>100,'game rendered after reload')
    ck(pg.evaluate("TTQ.save.profiles.emi.stars['2']")==3,'save (emi stars) preserved')
    c.close()
    # offline
    c,pg,navs,st=ctx('ABORT'); pg.goto(URL); pg.wait_for_timeout(1500)
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(800)
    ck(len(navs)==1,'offline: silent, no reload')
    c.close(); b.close()
real=[e for e in errs if 'net::ERR_FAILED' not in e]
print('console errors:',errs); ck(not real,'no console errors (excluding the deliberately aborted offline fetch)')
print('RESULT', 'FAIL' if fails else 'ALL PASS'); sys.exit(1 if fails else 0)
