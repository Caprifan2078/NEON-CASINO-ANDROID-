#!/usr/bin/env python3
"""Real Chromium QA for the existing Go desktop launcher. Isolated browser profile."""
import json, os, sys, shutil, time, tempfile, subprocess
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

def start(exe):
    env=os.environ.copy()
    env.update({"BROWSER":"true","DISPLAY":""})
    p=subprocess.Popen([str(exe)],cwd=str(exe.parent),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for _ in range(100):
        if p.poll() is not None:
            raise AssertionError("Desktop launcher exited before binding")
        for c in psutil.Process(p.pid).net_connections(kind="inet"):
            if c.status=="LISTEN" and c.laddr.ip=="127.0.0.1":
                return p,c.laddr.port
        time.sleep(0.1)
    p.terminate()
    raise AssertionError("Launcher did not bind to localhost")

def stop(p):
    p.terminate()
    try:p.wait(timeout=4)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(timeout=4)

def check(exe, output):
    profile=Path(tempfile.mkdtemp(prefix="neon-browser-qa-"))
    chrome=shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("google-chrome-stable")
    if not chrome:raise AssertionError("System Chromium/Chrome not found")
    report={"status":"FAIL","steps":[]}
    p=None
    try:
        p,port=start(exe)
        report["port_before"]=port
        with sync_playwright() as pw:
            ctx=pw.chromium.launch_persistent_context(user_data_dir=str(profile),executable_path=chrome,
                    headless=True,args=["--no-sandbox","--disable-dev-shm-usage"],viewport={"width":390,"height":844})
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                resp=page.goto(f"http://127.0.0.1:{port}/",wait_until="domcontentloaded",timeout=30000)
                assert resp and resp.status==200,"Desktop page unavailable"
                page.wait_for_function("document.querySelectorAll('#gameNav [data-action=nav]').length === 44",timeout=25000)
                balance=page.evaluate("String(state.balance)")
                checks=page.evaluate("""() => Array.from(document.querySelectorAll('#gameNav [data-action=nav]')).map((n,i)=>{
                    const id=n.dataset.game;n.click();
                    return {i,id,ok:state.game===id && Boolean(document.querySelector('#gameArea')?.children.length)}
                })""")
                failed=[x for x in checks if not x["ok"]]
                assert not failed,f"Unrendered game panels: {failed[:4]}"
                assert page.evaluate("String(state.balance)")==balance,"Navigation changed wallet"
                page.evaluate("() => {save();localStorage.setItem('__neon_browser_CI_20261104','persisted')}")
                assert page.evaluate("Boolean(localStorage.getItem('neon-casino-local-v1'))"),"Wallet save missing"
                page.screenshot(path=str(output/"mobile.png"),full_page=True)
                report["steps"].append("44 rendered mobile game panels; wallet unchanged")
            finally:ctx.close()
        stop(p);p=None
        p,new_port=start(exe)
        report["port_after_restart"]=new_port
        assert new_port==port,"Browser-origin port changed across application restart"
        with sync_playwright() as pw:
            ctx=pw.chromium.launch_persistent_context(user_data_dir=str(profile),executable_path=chrome,
                    headless=True,args=["--no-sandbox","--disable-dev-shm-usage"],viewport={"width":1440,"height":900})
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                page.goto(f"http://127.0.0.1:{new_port}/",wait_until="domcontentloaded",timeout=30000)
                page.wait_for_function("document.querySelectorAll('#gameNav [data-action=nav]').length === 44",timeout=25000)
                assert page.evaluate("localStorage.getItem('__neon_browser_CI_20261104')")=="persisted","Checkpoint lost on restart"
                assert page.evaluate("String(state.balance)")==balance,"Wallet changed on restart"
                page.screenshot(path=str(output/"desktop.png"),full_page=True)
                report["steps"].append("Cold launcher restart preserved origin, checkpoint and wallet")
            finally:ctx.close()
        report["status"]="PASS"
    finally:
        if p is not None:stop(p)
        shutil.rmtree(profile,ignore_errors=True)
    return report

if __name__=="__main__":
    exe=Path(sys.argv[1]).resolve()
    out=Path(sys.argv[2]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    try:r=check(exe,out)
    except Exception as exc:r={"status":"FAIL","error":repr(exc)}
    (out/"report.json").write_text(json.dumps(r,indent=2,ensure_ascii=False))
    print(json.dumps(r,indent=2,ensure_ascii=False))
    if r["status"]!="PASS":sys.exit(1)
