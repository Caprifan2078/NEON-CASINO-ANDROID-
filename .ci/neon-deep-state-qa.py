#!/usr/bin/env python3
"""Deep virtual-wallet and UI regression in real Chromium. No gambling or money."""
import sys,os,time,json,shutil,tempfile,subprocess
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

def server(exe):
    env=os.environ.copy();env.update({"BROWSER":"true","DISPLAY":""})
    p=subprocess.Popen([str(exe)],cwd=exe.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for _ in range(120):
        if p.poll() is not None:raise RuntimeError("Launcher stopped during startup")
        for conn in psutil.Process(p.pid).net_connections(kind="inet"):
            if conn.status=="LISTEN" and conn.laddr.ip=="127.0.0.1":
                return p,conn.laddr.port
        time.sleep(.1)
    p.terminate()
    raise RuntimeError("Launcher did not bind loopback")
def shutdown(p):
    p.terminate()
    try:p.wait(timeout=4)
    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=4)

def test(exe,output):
    chrome=shutil.which("google-chrome") or shutil.which("chromium")
    if not chrome:raise RuntimeError("Chromium not available")
    profile=tempfile.mkdtemp(prefix="neon-wallet-deep-")
    p,port=server(exe)
    report={"checks":[],"errors":[]}
    def passed(v):report["checks"].append(v);print("PASS",v)
    try:
        with sync_playwright() as pw:
            ctx=pw.chromium.launch_persistent_context(user_data_dir=profile,executable_path=chrome,headless=True,
                        args=["--no-sandbox","--disable-dev-shm-usage"],viewport={"width":390,"height":844})
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                page.on("pageerror",lambda exc:report["errors"].append(str(exc)))
                page.on("dialog",lambda dialog:dialog.accept())
                page.goto(f"http://127.0.0.1:{port}/",wait_until="domcontentloaded",timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=30000)
                assert page.locator('#gameNav [data-action=nav]').count()==44
                assert page.evaluate("canModify()===true"),"First tab did not own wallet"
                balance=page.evaluate("state.balance")
                assert isinstance(balance,int) and balance>0
                assert page.evaluate("state.reserved") == 0
                passed("initial 44 modes; wallet owned and integer balance")
                # Never spend actual money: this is isolated browser virtual credits.
                snapshot=page.evaluate("JSON.stringify(snapshot())")
                obj=json.loads(snapshot)
                assert obj["format"]=="NEON_CASINO_SAVE" and obj["version"]==5
                assert obj["profiles"]["free"]["reserved"]==0 and obj["profiles"]["daily"]["reserved"]==0
                page.evaluate("addChips(777)")
                assert page.evaluate("state.balance")==balance+777
                assert page.evaluate("(src) => loadBackup(src)",snapshot) is True
                assert page.evaluate("state.balance")==balance
                assert page.evaluate("typeof localStorage.getItem('neon-casino-preimport-v1')==='string'")
                assert page.evaluate("restorePreImportBackup()") is True
                assert page.evaluate("state.balance")==balance+777
                passed("JSON backup export/import/undo: both profiles and wallet preserved")
                bad_sources=['{}','[]','{"format":"NEON_CASINO_SAVE","version":5,"balance":-10}','a'*1000001]
                for source in bad_sources:
                    try:page.evaluate("(raw) => loadBackup(raw)",source)
                    except Exception:pass
                    else:raise AssertionError("Invalid backup accepted")
                    assert page.evaluate("state.balance")==balance+777,"Invalid import modified wallet"
                passed("4 malformed/oversized backups rejected without wallet mutation")
                # Reserved chips are refunded exactly once after a renderer reload.
                before=page.evaluate("state.balance")
                assert page.evaluate("spend(80)") is True
                assert page.evaluate("state.reserved")==80
                assert page.evaluate("state.balance")==before-80
                page.reload(wait_until="domcontentloaded")
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=30000)
                assert page.evaluate("state.balance")==before,"Interrupted bet was not refunded"
                assert page.evaluate("state.reserved")==0,"Refund left reserved virtual chips"
                page.reload(wait_until="domcontentloaded")
                assert page.evaluate("state.balance")==before,"Interrupted bet refunded twice"
                passed("interrupted bet refunded once, not twice")
                # Two tabs may not write to the same wallet.
                second=ctx.new_page()
                second.goto(f"http://127.0.0.1:{port}/",wait_until="domcontentloaded")
                second.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=30000)
                assert second.evaluate("canModify()===false"),"Second tab claimed live wallet"
                second.evaluate("addChips(500)")
                assert second.evaluate("state.balance")==before
                assert page.evaluate("state.balance")==before
                passed("second tab cannot change first tab's wallet")
                page.close()
                second.reload(wait_until="domcontentloaded")
                second.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=30000)
                assert second.evaluate("canModify()===true"),"Wallet not reclaimed after owner closed"
                second.evaluate("addChips(123)")
                assert second.evaluate("state.balance")==before+123
                second.reload(wait_until="domcontentloaded")
                assert second.evaluate("state.balance")==before+123
                passed("closing first tab releases wallet; new owner saves normally")
                # Fast visual setting preferences persist and do not touch wallet.
                second.locator("#compactToggle").click()
                compact=second.evaluate("localStorage.getItem('neon-casino-compact-v1')")
                assert compact in ('0','1')
                second.reload(wait_until="domcontentloaded")
                assert second.evaluate("localStorage.getItem('neon-casino-compact-v1')")==compact
                assert second.evaluate("state.balance")==before+123
                passed("compact UI preference persists without changing wallet")
                # All modes render in both compact/mobile and desktop viewports.
                for width,height in [(390,844),(768,1024),(1440,900)]:
                    second.set_viewport_size({"width":width,"height":height})
                    t0=time.monotonic()
                    game_panels=second.evaluate("""() => Array.from(document.querySelectorAll('#gameNav [data-action=nav]')).map(n => {
                        n.click();
                        return Boolean(document.querySelector('#gameArea')?.children.length)
                    })""")
                    assert len(game_panels)==44 and all(game_panels),f"{width}px: incomplete render"
                    assert second.evaluate("state.balance")==before+123
                    elapsed=time.monotonic()-t0
                    metrics=second.evaluate("({width:innerWidth, scroll:document.documentElement.scrollWidth})")
                    report["checks"].append(f"{width}px: 44 modes rendered in {elapsed:.2f}s; scrollWidth={metrics['scroll']}")
                    second.screenshot(path=str(output/f"qa_{width}.png"),full_page=True)
                assert not report["errors"],"Unhandled page JS errors: "+str(report["errors"][:5])
                passed("mobile/tablet/desktop panels and no unhandled JavaScript errors")
            finally:ctx.close()
    finally:
        shutdown(p);shutil.rmtree(profile,ignore_errors=True)
    return report

if __name__=="__main__":
    exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(exist_ok=True)
    try:r=test(exe,out);r["status"]="PASS"
    except Exception as exc:r={"status":"FAIL","error":repr(exc)}
    (out/"deep_qa_result.json").write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if r["status"]!="PASS":sys.exit(1)
