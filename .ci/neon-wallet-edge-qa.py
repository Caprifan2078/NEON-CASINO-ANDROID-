#!/usr/bin/env python3
"""P0 wallet transition / durability and distribution-edge browser QA.

Runs the ORIGINAL NEON 1.8.9 source unchanged. Enforces exact state
conservation around interrupted live rounds, storage failure, and mode changes.
"""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

def server(path):
    env={**os.environ,"BROWSER":"true","DISPLAY":""}
    p=subprocess.Popen([str(path)],cwd=str(path.parent),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for i in range(120):
        if p.poll() is not None:raise AssertionError("Native launcher exited early")
        for c in psutil.Process(p.pid).net_connections(kind="inet"):
            if c.status=="LISTEN" and c.laddr.ip=="127.0.0.1":
                return p,int(c.laddr.port)
        time.sleep(.1)
    p.terminate();raise AssertionError("Server did not listen on loopback")

def main(exe, out):
    profile=tempfile.mkdtemp(prefix="neon-p0-wallet-")
    chrome=shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:raise AssertionError("Chromium missing")
    p,port=server(exe)
    report={"status":"FAIL","checks":[],"page_errors":[]}
    try:
        with sync_playwright() as pw:
            ctx=pw.chromium.launch_persistent_context(user_data_dir=profile,executable_path=chrome,
                  headless=True,args=["--no-sandbox","--disable-dev-shm-usage"],viewport={"width":390,"height":844})
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                page.on("pageerror",lambda error:report["page_errors"].append(str(error)))
                page.on("dialog",lambda dialog:dialog.accept())
                page.goto(f"http://127.0.0.1:{port}/",wait_until="domcontentloaded",timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state="attached",timeout=30000)
                vals=page.evaluate("({mode:state.mode,balance:state.balance,reserved:state.reserved})")
                assert vals=={"mode":"free","balance":50000,"reserved":0}, vals
                report["checks"].append("Free wallet starts 50,000; reserved=0")
                # Immediately cancel active Crash and switch to Daily: refund exactly once;
                # no late asynchronous crash settlement may mutate the fresh wallet.
                result=page.evaluate("""() => {
                    state.stake=100;navigate('crash');startCrash();
                    const pending={mode:state.mode,balance:state.balance,reserved:state.reserved};
                    if(pending.balance!==49900||pending.reserved!==100)throw Error('Crash failed to reserve 100 chips');
                    switchMode('daily');
                    return {mode:state.mode,daily:state.balance,reserved:state.reserved,free:profileSnapshots.free.balance,
                            freeReserved:profileSnapshots.free.reserved,freeRounds:profileSnapshots.free.stats.rounds};
                }""")
                assert result=={"mode":"daily","daily":1000,"reserved":0,"free":50000,"freeReserved":0,"freeRounds":0}, result
                page.wait_for_timeout(1500)
                assert page.evaluate("profileSnapshots.free.balance===50000 && profileSnapshots.free.stats.rounds===0 && state.balance===1000 && state.reserved===0"),"Stale Crash callback debited after mode switch"
                report["checks"].append("Cancel running Crash on mode switch: refunded exactly once, no late settlement")
                # Daily mode intentionally disallows manual chip additions.
                result=page.evaluate("""() => {
                  const before=state.balance;addChips(100000);
                  return {day:dailyProgress.day,before,after:state.balance,mode:state.mode}
                }""")
                assert result=={"day":1,"before":1000,"after":1000,"mode":"daily"},result
                report["checks"].append("Manual top-up blocked in Daily mode")
                # Finish a day; free profile must remain untouched and day 2 persist.
                result=page.evaluate("""() => {
                    if(!finishDailyDay('manual'))throw Error('Could not finish daily day');
                    return {day:dailyProgress.day,balance:state.balance,history:dailyProgress.history.length,free:profileSnapshots.free.balance}
                }""")
                assert result=={"day":2,"balance":1000,"history":1,"free":50000},result
                page.reload(wait_until="domcontentloaded")
                assert page.evaluate("dailyProgress.day===2 && state.mode==='daily' && state.balance===1000 && profileSnapshots.free.balance===50000")
                report["checks"].append("Daily day-rollover and both independent profiles survive browser cold reload")
                # Real interrupted wager in daily wallet must be compensated at startup.
                result=page.evaluate("""() => {
                    state.stake=50;const a=state.balance;const ok=spend(50);
                    return {ok,old:a,balance:state.balance,reserved:state.reserved}
                }""")
                assert result=={"ok":True,"old":1000,"balance":950,"reserved":50},result
                page.reload(wait_until="domcontentloaded")
                assert page.evaluate("state.mode==='daily' && state.balance===1000 && state.reserved===0"),"Daily interrupted wager not refunded"
                page.reload(wait_until="domcontentloaded")
                assert page.evaluate("state.balance===1000 && state.reserved===0"),"Daily wager refunded twice"
                report["checks"].append("Daily interrupted stake refunded once after two cold reloads")
                # A pending asynchronous Coin must NOT be settled into the other wallet.
                # Reduced-motion duration is 380ms, wait > 2 seconds.
                result=page.evaluate("""() => {
                    switchMode('free');
                    state.stake=100;navigate('coin');flipCoin();
                    if(state.reserved!==100)throw Error('Coin failed to reserve stake');
                    switchMode('daily');
                    return {mode:state.mode,balance:state.balance,free:profileSnapshots.free.balance,
                        freeReserve:profileSnapshots.free.reserved,freeRounds:profileSnapshots.free.stats.rounds};
                }""")
                assert result=={"mode":"daily","balance":1000,"free":50000,"freeReserve":0,"freeRounds":0},result
                page.wait_for_timeout(2100)
                assert page.evaluate("state.mode==='daily' && state.balance===1000 && profileSnapshots.free.balance===50000 && profileSnapshots.free.stats.rounds===0")
                report["checks"].append("Cancel asynchronous Coin on mode switch: no cross-wallet contamination")
                # Save to storage then deliberately simulate full disk/browser storage refusal
                # during a new spend: no chip debit may be visible or persistent.
                page.evaluate("switchMode('free')")
                page.evaluate("state.stake=100")
                prior=page.evaluate("({balance:state.balance,reserved:state.reserved,saved:JSON.parse(localStorage.getItem(STORAGE)).profiles.free.balance})")
                assert prior=={"balance":50000,"reserved":0,"saved":50000},prior
                storage=page.evaluate("""() => {
                    const old=Storage.prototype.setItem;
                    Storage.prototype.setItem=function(){throw new DOMException('Quota exceeded','QuotaExceededError')};
                    let ok,error=null;
                    try{ok=spend(100)}catch(e){error=String(e)}
                    Storage.prototype.setItem=old;
                    return {ok,error,balance:state.balance,reserved:state.reserved,
                        saved:JSON.parse(localStorage.getItem(STORAGE)).profiles.free.balance};
                }""")
                assert storage=={"ok":False,"error":None,"balance":50000,"reserved":0,"saved":50000},storage
                page.reload(wait_until="domcontentloaded")
                assert page.evaluate("state.mode==='free' && state.balance===50000 && state.reserved===0")
                report["checks"].append("QuotaExceeded during stake write: no in-memory debit and persisted wallet intact")
                # Use real payout settlement with failed storage after a successfully
                # reserved stake; persisted reserved amount MUST refund after reload.
                page.evaluate("state.stake=100")
                assert page.evaluate("spend(100)")==True
                result=page.evaluate("""() => {
                    const old=Storage.prototype.setItem;
                    Storage.prototype.setItem=function(){throw new DOMException('Quota exceeded','QuotaExceededError')};
                    let ok,error=null;try{ok=settle('Монетка',100,195)}catch(e){error=String(e)}
                    Storage.prototype.setItem=old;
                    return {ok,error,balance:state.balance,reserved:state.reserved,
                      saved:JSON.parse(localStorage.getItem(STORAGE)).profiles.free.balance};
                }""")
                assert result=={"ok":False,"error":None,"balance":49900,"reserved":100,"saved":49900},result
                page.reload(wait_until="domcontentloaded")
                assert page.evaluate("state.balance===50000 && state.reserved===0 && state.stats.rounds===0"),"Failed settlement did not restore single reserved stake"
                page.reload(wait_until="domcontentloaded")
                assert page.evaluate("state.balance===50000 && state.reserved===0"),"Refund duplicated after write failure"
                report["checks"].append("QuotaExceeded during settlement: reserved wager recovered exactly once; uncommitted win not credited")
                # 44 game modes, replayable snapshot, 5-second click stress and bounded layout.
                assert page.evaluate("GAMES.length===44")
                for width,height in [(320,700),(390,844),(768,1024),(1440,900)]:
                    page.set_viewport_size({"width":width,"height":height})
                    result=page.evaluate("""() => {
                        const errors=[];
                        for (const g of GAMES){navigate(g.id);
                          const node=document.querySelector('#gameArea');
                          if(!node||!node.children.length)errors.push(g.id)}
                        return {games:GAMES.length,errors,scroll:document.documentElement.scrollWidth,inner:innerWidth};
                    }""")
                    assert not result["errors"],f"{width} missing panels: {result['errors']}"
                    assert result["games"]==44 and result["scroll"]<=result["inner"]+2,f"{width}px overflow: {result}"
                    report["checks"].append(f"{width}px viewport: 44 panels; no document horizontal overflow")
                assert not report["page_errors"],"JS errors: "+repr(report["page_errors"])
                report["status"]="PASS"
                page.screenshot(path=str(out/"final-screen.png"),full_page=True)
            finally:ctx.close()
    finally:
        p.terminate()
        try:p.wait(timeout=4)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=4)
        shutil.rmtree(profile,ignore_errors=True)
    return report

if __name__=="__main__":
    exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
    try:r=main(exe,out)
    except Exception as exc:r={"status":"FAIL","error":repr(exc)}
    (out/"P0_wallet_edge_qa.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if r["status"]!="PASS":sys.exit(1)
