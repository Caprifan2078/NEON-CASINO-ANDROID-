#!/usr/bin/env python3
"""Long simulated virtual-chip stress: memory, bounded journals, reload durability.

This tests 5000 committed game rounds and 4400 actual UI game transitions
in a real Chromium. It does not pretend to test hours of physical device use.
"""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

def launch(exe):
    env={**os.environ,"BROWSER":"true","DISPLAY":""}
    process=subprocess.Popen([str(exe)],cwd=str(exe.parent),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for _ in range(150):
        if process.poll() is not None:raise AssertionError("Native launcher exited")
        for conn in psutil.Process(process.pid).net_connections(kind="inet"):
            if conn.status=="LISTEN" and conn.laddr.ip=="127.0.0.1":
                return process, conn.laddr.port
        time.sleep(.1)
    process.terminate()
    raise AssertionError("Native launcher did not bind localhost")

def run(exe,out):
    profile=tempfile.mkdtemp(prefix="neon-long-stress-")
    process,port=launch(exe)
    report={"status":"FAIL","rounds":0,"navigation_events":0,"checks":[],"errors":[]}
    try:
        chrome=shutil.which("google-chrome") or shutil.which("chromium")
        if not chrome:raise AssertionError("Real Chrome/Chromium missing")
        with sync_playwright() as pw:
            browser=pw.chromium.launch_persistent_context(
                user_data_dir=profile,executable_path=chrome,headless=True,
                args=["--no-sandbox","--disable-dev-shm-usage","--enable-precise-memory-info",
                      "--js-flags=--expose-gc"],viewport={"width":390,"height":844})
            try:
                page=browser.pages[0] if browser.pages else browser.new_page()
                page.on("pageerror",lambda err:report["errors"].append(str(err)))
                url=f"http://127.0.0.1:{port}/"
                page.goto(url,wait_until="domcontentloaded",timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state="attached",timeout=20000)
                assert page.evaluate("GAMES.length")==44
                starting=page.evaluate("({balance:state.balance,rounds:state.stats.rounds,wins:state.stats.wins,paid:state.stats.paid,wagered:state.stats.wagered})")
                page.evaluate("typeof gc==='function'&&gc()")
                baseline_heap=page.evaluate("performance.memory?.usedJSHeapSize||0")
                report["initial_heap_bytes"]=baseline_heap
                rounds=5000
                for batch in range(20):
                    completed=page.evaluate("""({batch}) => {
                        const start=batch*250, end=start+250;
                        for(let i=start;i<end;i++){
                            if(!spend(10))throw Error('Spend failed on round '+i);
                            if(!settle('Монетка',10,(i%2)*20,'long-run QA'))
                                throw Error('Settlement failed on round '+i);
                            if(state.reserved!==0||!Number.isSafeInteger(state.balance))
                                throw Error('Nonzero reserved or unsafe balance at '+i);
                        }
                        return end;
                    }""",{"batch":batch})
                    assert completed==(batch+1)*250
                    report["rounds"]=completed
                result=page.evaluate("""() => ({
                    balance:state.balance,rounds:state.stats.rounds,wins:state.stats.wins,
                    paid:state.stats.paid,wagered:state.stats.wagered,
                    reserved:state.reserved,journal:state.journal.length,
                    recent:state.activity.length,days:state.dayBuckets.length,
                    savedBytes:(localStorage.getItem(STORAGE)||'').length
                })""")
                assert result["balance"]==starting["balance"],"Coin-flip loop changed balanced wallet"
                assert result["rounds"]==starting["rounds"]+rounds
                assert result["wins"]==starting["wins"]+rounds//2
                assert result["wagered"]==starting["wagered"]+rounds*10
                assert result["paid"]==starting["paid"]+rounds*10
                assert result["reserved"]==0
                assert result["journal"]<=240 and result["recent"]<=20 and result["days"]<=120
                assert 0<result["savedBytes"]<1_000_000
                report["after_rounds"]=result
                report["checks"].append("5000 committed virtual-chip rounds, balances/stats exact; bounded journals")
                for width,height in ((320,700),(390,844),(768,1024),(1440,900)):
                    page.set_viewport_size({"width":width,"height":height})
                    t0=time.monotonic()
                    loops=25
                    ui=page.evaluate("""({loops}) => {
                        let visits=0;
                        for(let pass=0;pass<loops;pass++){
                            for(const game of GAMES){
                                navigate(game.id);
                                if(!document.querySelector('#gameArea')?.children.length)
                                    throw Error('Unrendered game: '+game.id);
                                visits++;
                            }
                        }
                        return {visits,width:innerWidth,scroll:document.documentElement.scrollWidth,
                            balance:state.balance,rounds:state.stats.rounds};
                    }""",{"loops":loops})
                    assert ui["visits"]==44*loops
                    assert ui["balance"]==starting["balance"]
                    assert ui["rounds"]==starting["rounds"]+rounds
                    assert ui["scroll"]<=ui["width"]+2,f"Horizontal layout overflow at {width}px"
                    report["navigation_events"]+=ui["visits"]
                    report["checks"].append(f"{width}px: 1100 game renders in {time.monotonic()-t0:.2f}s, no overflow")
                page.evaluate("typeof gc==='function'&&gc()")
                after_heap=page.evaluate("performance.memory?.usedJSHeapSize||0")
                report["final_heap_bytes"]=after_heap
                report["heap_delta_bytes"]=after_heap-baseline_heap
                if baseline_heap and after_heap:
                    # Leak alarm only: generous envelope to avoid GC/flaky false positives.
                    assert after_heap<100_000_000, "Heap >100MB after repeated navigation"
                    assert after_heap-baseline_heap<65_000_000, "Heap grew >65MB after GC"
                report["checks"].append("Bounded JS heap after 4400 UI renders (generous regression threshold)")
                page.reload(wait_until="domcontentloaded")
                page.locator('#gameNav [data-action=nav]').first.wait_for(state="attached",timeout=20000)
                after=page.evaluate("""() => ({
                    balance:state.balance,rounds:state.stats.rounds,
                    wins:state.stats.wins,paid:state.stats.paid,
                    wagered:state.stats.wagered,reserved:state.reserved,
                    journal:state.journal.length
                })""")
                for k in ("balance","rounds","wins","paid","wagered","reserved","journal"):
                    assert after[k]==result[k],f"Reload changed {k}: {after[k]} vs {result[k]}"
                report["checks"].append("After cold document reload, all 5000 rounds and exact counters persisted")
                assert not report["errors"],f"Page errors: {report['errors'][:3]}"
                page.screenshot(path=str(out/"final_390_and_stress.png"),full_page=True)
                report["status"]="PASS"
                print("PASS: 5000 committed rounds, 4400 game renders, guarded heap and cold reload")
            finally:browser.close()
    finally:
        process.terminate()
        try:process.wait(timeout=4)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=4)
        shutil.rmtree(profile,ignore_errors=True)
    return report

if __name__=="__main__":
    exe=Path(sys.argv[1]).resolve()
    out=Path(sys.argv[2]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    try:result=run(exe,out)
    except Exception as exc:
        import traceback
        result={"status":"FAIL","error":repr(exc),"traceback":traceback.format_exc()}
    (out/"LONG_STRESS_RESULT.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result["status"]!="PASS":sys.exit(1)
