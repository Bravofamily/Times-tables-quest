# v11: guide-lantern hints — limit enforced, never contains the answer, refill on retry / new chapter, usage saved + shown on Progress.
import json, os, re
from playwright.sync_api import sync_playwright
D=os.path.dirname(os.path.abspath(__file__)); URL='file://'+os.path.join(D,'index.html'); errs=[]; fails=[]
def ck(c,m):
    print(('PASS ' if c else 'FAIL ')+m); fails.append(m) if not c else None
SAVE={"muted":True,"narrator":False,"hero":"emi","profiles":{"emi":{"name":"Emi","stars":{"1":3},"hist":{},"rewards":[],"eq":{},"prologue":True,"age":6,"grade":"1",
  "subj":{"add":{"stars":{"1":3,"2":3},"hist":{},"intro":True},"sub":{"stars":{},"hist":{},"intro":True},"div":{"stars":{"1":3,"2":3,"3":3,"4":3,"5":3,"6":3,"7":3},"hist":{},"intro":True}}}}}
NUMS=lambda s: set(int(x) for x in re.findall(r'(?<![\d.])\d+(?![\d.])',s))
with sync_playwright() as p:
    b=p.chromium.launch(); c=b.new_context(viewport={'width':390,'height':844}); pg=c.new_page()
    pg.on('console',lambda m: errs.append(m.text) if m.type=='error' else None); pg.on('pageerror',lambda e: errs.append(str(e)))
    pg.goto(URL); pg.evaluate("s=>localStorage.setItem('ttq-save-v2',JSON.stringify(s))",SAVE); pg.reload(); pg.wait_for_timeout(500)
    ck(pg.evaluate("TTQ_V11.HINT_MAX.practice")==3 and pg.evaluate("TTQ_V11.HINT_MAX.boss")==1,'limits: 3 per chapter (practice+apply), 1 per boss')
    # ---- subject chapter: limit enforced
    pg.evaluate("openChapter('add',1)"); pg.wait_for_timeout(200); pg.evaluate("sPracticeStart()"); pg.wait_for_timeout(300)
    ck(pg.locator('#hintBtn').count()==1 and pg.is_enabled('#hintBtn'),'lantern button shown and enabled')
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==3,'3 lanterns at chapter start')
    ck('3 left' in pg.get_attribute('#hintBtn','aria-label'),'aria-label says 3 left')
    def answer_text(): return pg.evaluate("String(SS.cur.ans)")
    def qtext(): return pg.evaluate("document.querySelector('#hintbox').closest('.card').innerText.replace(document.querySelector('#hintbox').innerText,'')")
    used=0; nq=0; leaks=[]
    for qn in range(8):
        if pg.locator('#hintBtn').count()==0: break
        if not pg.is_enabled('#hintBtn'): break
        pg.click('#hintBtn'); pg.wait_for_timeout(120); used+=1
        t1=pg.inner_text('#hintbox'); tier1_only=pg.locator('#hintbox .vis').count()==0
        if qn==0: ck(tier1_only and 'think about it' in t1.lower(),'tier 1 = strategy reminder (no picture yet)')
        if pg.is_enabled('#hintBtn'):
            pg.click('#hintBtn'); pg.wait_for_timeout(120); used+=1
            if qn==0: ck(pg.locator('#hintbox .vis').count()==1 and 'answer is yours to find' in pg.inner_text('#hintbox'),'tier 2 = picture model + "answer is yours to find"')
            ck(not pg.is_enabled('#hintBtn'),'after both tiers the button is disabled for this question (q%d)'%qn)
        a=answer_text(); ht=pg.inner_text('#hintbox'); qn_nums=NUMS(pg.evaluate("SS.cur.text.replace(/<[^>]+>/g,' ')"))
        if a.isdigit() and int(a) in NUMS(ht) and int(a) not in qn_nums: leaks.append((a,ht[:120]))
        nq+=1
        # answer correctly to move on
        pg.evaluate("SS.onAnswer(true)"); pg.wait_for_timeout(1300)
    ck(used==3,'exactly 3 lanterns could be used in the chapter (used %d)'%used)
    ck(pg.locator('#hintBtn').count()==1 and not pg.is_enabled('#hintBtn') and 'No guide lanterns left' in pg.get_attribute('#hintBtn','aria-label'),'lanterns run out: button disabled + labelled')
    n0=pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())"); pg.evaluate("useHint()"); ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==0 and n0==0,'calling useHint() with 0 left does nothing')
    ck(not leaks,'answer never appears in the hint (%s)'%leaks)
    ck(pg.locator('.opt[disabled], .opt.gone, .opt.elim').count()==0,'no answer choices eliminated')
    sv=pg.evaluate("JSON.parse(localStorage.getItem('ttq-save-v2'))"); hl=sv['profiles']['emi'].get('hintLog',{})
    ck(hl.get('add',{}).get('used')==3 and sv['profiles']['emi'].get('hintTotal')==3,'usage saved under ttq-save-v2 (hintLog.add.used=3, hintTotal=3): %s'%hl)
    ck(hl.get('add',{}).get('ch',{}).get('1')==3,'usage saved per chapter')
    ck(hl.get('add',{}).get('ok',0)>=1 and hl['add'].get('qs')==2,'"questions helped"=2 and "solved after a clue" counted')
    # ---- boss: 1 lantern, both tiers at once
    pg.evaluate("SS.pi=SS.list.length-1;sPracticeDone()"); pg.wait_for_timeout(200); pg.evaluate("sBossStart()"); pg.wait_for_timeout(300)
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==1 and pg.locator('#qbox #hintBtn').count()==1,'boss: 1 lantern in the question box')
    pg.click('#hintBtn'); pg.wait_for_timeout(150)
    ck(pg.locator('#hintbox .vis').count()==1 and not pg.is_enabled('#hintBtn'),'boss lantern shows both clues then is spent')
    a=answer_text(); ck(not (a.isdigit() and int(a) in NUMS(pg.inner_text('#hintbox')) and int(a) not in NUMS(pg.evaluate("SS.cur.text.replace(/<[^>]+>/g,' ')"))),'boss hint has no answer')
    pg.evaluate("SS.onAnswer(true)"); pg.wait_for_timeout(1200)
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==0 and not pg.is_enabled('#hintBtn'),'boss lantern does not come back on the next boss question')
    # ---- refill on retry (boss lose -> new session)
    ck(pg.evaluate("SS.lanP")==0,'before retry: chapter lanterns are spent')
    pg.evaluate("sBossLose()"); pg.wait_for_timeout(300)
    for i in range(40):   # click through the lose scene + the new intro scene, as a kid would
        if not pg.evaluate("!!SC"): break
        pg.locator('#app button:visible').last.click(); pg.wait_for_timeout(250)
    ck(not pg.evaluate("!!SC") and pg.evaluate("SS.lanP")==None,'retry: a fresh session after "Try again"')
    pg.evaluate("sPracticeStart()"); pg.wait_for_timeout(300)
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==3,'retry refills to 3 lanterns')
    pg.evaluate("SS.cur=null;openChapter('add',2)"); pg.wait_for_timeout(200); pg.evaluate("sPracticeStart()"); pg.wait_for_timeout(300)
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==3,'new chapter refills to 3 lanterns')
    # ---- long division step hints
    pg.evaluate("SS.cur=null;openChapter('div',8)"); pg.wait_for_timeout(200); pg.evaluate("sPracticeStart()"); pg.wait_for_timeout(300)
    isld=pg.evaluate("SS.cur.input==='ld'")
    if isld:
        pg.click('#hintBtn'); pg.wait_for_timeout(120); pg.click('#hintBtn'); pg.wait_for_timeout(120)
        want=pg.evaluate("(()=>{const st=SS.ldseq[SS.ldStep],s=SS.cur.L.steps[st[0]];return String(st[1]==='D'?s.q:st[1]==='M'?s.m:st[1]==='S'?s.r:'')})()")
        ck(pg.locator('#hintbox').is_visible(),'long-division step hint shown')
    # ---- times tables (mult) path
    pg.evaluate("SS=null;mapScreen()"); pg.wait_for_timeout(200); pg.evaluate("S=makeSession(ORDER[0]);practiceStart()"); pg.wait_for_timeout(300)
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==3 and pg.locator('#hintBtn').count()==1,'times-table practice has 3 lanterns')
    pg.click('#hintBtn'); pg.wait_for_timeout(120); a=pg.evaluate("String(S.cur.ans)")
    ck(pg.is_visible('#hintbox') and not (a.isdigit() and int(a) in NUMS(pg.inner_text('#hintbox')) and int(a) not in NUMS(pg.evaluate("String(S.cur.text||'').replace(/<[^>]+>/g,' ')"))),'times-table hint has no answer')
    pg.evaluate("useHint()"); pg.wait_for_timeout(100); pg.evaluate("useHint()"); pg.evaluate("S.onAnswer&&0"); 
    pg.evaluate("S.lanP=0;S.cur=null;retryLevel()"); pg.wait_for_timeout(300); pg.evaluate("practiceStart()"); pg.wait_for_timeout(300)
    ck(pg.evaluate("TTQ_V11.lanLeft(TTQ_V11.hintCtx())")==3,'times-table retry refills to 3 lanterns')
    # ---- Progress shows usage
    pg.evaluate("S=null;progressScreen()"); pg.wait_for_timeout(300)
    ck(pg.locator('#lanStats').count()==1 and pg.inner_text('#hUsed').strip()==str(pg.evaluate("P().hintTotal")),'Progress shows lanterns used (%s)'%pg.inner_text('#hUsed'))
    ck('lanterns used' in pg.inner_text('.prow[data-psubj=add]'),'per-subject lantern count on Progress')
    pg.reload(); pg.wait_for_timeout(300); ck(pg.evaluate("P('emi').hintLog.add.used")>=4,'hint usage persists across reload')
    pg.screenshot(path='/tmp/v11-hints-final.png')
    ck(not errs,'no console errors (%s)'%errs[:3])
    b.close()
print('RESULT', 'ALL PASS' if not fails else 'FAILS: %d'%len(fails))
