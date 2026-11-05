#!/usr/bin/env python3
"""Import/export safety for NEON SAVE v2/v3/v4/v5, undo and failed writes.

Uses isolated Chromium and actual audited 1.8.9 game JS. Never touches real saves.
"""
import json,os,sys,shutil,subprocess,tempfile,time,traceback
from pathlib import Path
from playwright.sync_api import sync_playwright
import psutil

def launch(executable):
    env={**os.environ,'BROWSER':'true','DISPLAY':''}
    p=subprocess.Popen([str(executable)],cwd=executable.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for _ in range(100):
        if p.poll() is not None:raise RuntimeError('Native launcher exited')
        for conn in psutil.Process(p.pid).net_connections(kind='inet'):
            if conn.status=='LISTEN' and conn.laddr.ip=='127.0.0.1':return p,conn.laddr.port
        time.sleep(.1)
    p.terminate();raise RuntimeError('No local server')
def check(exe,out):
    profile=tempfile.mkdtemp(prefix='neon-migrations-')
    p,port=launch(exe)
    report={'checks':[],'javascript_errors':[],'status':'FAIL'}
    try:
        chrome=shutil.which('google-chrome') or shutil.which('chromium')
        if not chrome:raise RuntimeError('Chrome missing')
        with sync_playwright() as pw:
            ctx=pw.chromium.launch_persistent_context(user_data_dir=profile,executable_path=chrome,headless=True,
                args=['--no-sandbox','--disable-dev-shm-usage'],viewport={'width':390,'height':844})
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                page.on('dialog',lambda d:d.accept())
                page.on('pageerror',lambda e:report['javascript_errors'].append(str(e)))
                page.goto(f'http://127.0.0.1:{port}/',wait_until='domcontentloaded',timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=30000)
                assert page.evaluate('GAMES.length')==44
                assert page.evaluate('state.balance')==50000
                report['checks'].append('clean v1.8.9 game with 44 modes and free wallet')
                setup=page.evaluate("""() => {
                  addChips(5000);
                  switchMode('daily');state.stake=100;
                  if(!spend(100)||!settle('Монетка',100,200))throw Error('Daily wager failed');
                  switchMode('free');
                  return {free:state.balance,daily:profileSnapshots.daily.balance,
                          freeGranted:state.manualGranted,day:dailyProgress.day};
                }""")
                assert setup=={'free':55000,'daily':1100,'freeGranted':5000,'day':1},setup
                initial=page.evaluate("JSON.stringify(snapshot())")
                v5=json.loads(initial)
                assert v5['version']==5 and v5['profiles']['free']['balance']==55000
                assert v5['profiles']['daily']['balance']==1100
                assert v5['profiles']['free']['manualGranted']==5000
                report['checks'].append('v5 export includes both wallets and manual grants without treating grants as wins')
                page.evaluate("addChips(77)")
                assert page.evaluate('state.balance')==55077
                assert page.evaluate('(raw) => loadBackup(raw)',initial) is True
                assert page.evaluate('state.balance')==55000
                assert page.evaluate('profileSnapshots.daily.balance')==1100
                assert page.evaluate("Boolean(localStorage.getItem(PREIMPORT_KEY))")
                assert page.evaluate('restorePreImportBackup()') is True
                assert page.evaluate('state.balance')==55077
                assert page.evaluate('profileSnapshots.daily.balance')==1100
                report['checks'].append('v5 import backup, checkpoint and undo restore exact prior balances')
                for version in (4,3):
                    doc=json.loads(initial);doc['version']=version;doc.pop('preferences',None)
                    assert page.evaluate('(raw)=>loadBackup(raw)',json.dumps(doc,ensure_ascii=False)) is True
                    assert page.evaluate("state.balance===55000 && profileSnapshots.daily.balance===1100")
                    report['checks'].append(f'v{version} legacy import preserved free and daily wallets')
                old=json.loads(initial)
                old['version']=2
                old['balance']=22222
                old['stats']={'rounds':3,'wins':1,'wagered':300,'paid':190}
                old.pop('profiles',None);old.pop('dailyProgress',None);old.pop('preferences',None)
                assert page.evaluate('(raw)=>loadBackup(raw)',json.dumps(old,ensure_ascii=False)) is True
                result=page.evaluate("({mode:state.mode,free:state.balance,daily:profileSnapshots.daily.balance,rounds:state.stats.rounds})")
                assert result=={'mode':'free','free':22222,'daily':1000,'rounds':3},result
                report['checks'].append('v2 legacy import normalizes both modes without corrupting old stats')
                # Invalid saves must not prompt and must not write.
                before=page.evaluate('localStorage.getItem(STORAGE)')
                malformed=['{}','[]','not json',json.dumps({'format':'NEON_CASINO_SAVE','version':5,'balance':-10}), 'x'*1000001]
                for text in malformed:
                    rejected=page.evaluate("""raw => {
                        try{loadBackup(raw);return false}catch(e){return true}
                    }""",text)
                    assert rejected,'Malformed save was accepted'
                    assert page.evaluate('localStorage.getItem(STORAGE)')==before,'Bad save changed persistent wallet'
                report['checks'].append('five invalid/oversized backups rejected without writing storage')
                # If pre-import checkpoint cannot be created, abort before wallet mutation.
                testdoc=initial
                failure=page.evaluate("""raw => {
                    const original=Storage.prototype.setItem;
                    Storage.prototype.setItem=function(key,value){
                        if(key===PREIMPORT_KEY)throw new DOMException('quota','QuotaExceededError');
                        return original.call(this,key,value)
                    };
                    let rejected=false;
                    try{loadBackup(raw)}catch(e){rejected=true}
                    finally{Storage.prototype.setItem=original}
                    return {rejected,balance:state.balance,
                            saved:JSON.parse(localStorage.getItem(STORAGE)).balance};
                }""",testdoc)
                assert failure=={'rejected':True,'balance':22222,'saved':22222},failure
                report['checks'].append('failed pre-import checkpoint refuses import atomically')
                # If actual wallet commit fails after checkpoint, rollback state and persist original.
                bad_commit=page.evaluate("""raw => {
                    const original=Storage.prototype.setItem;
                    Storage.prototype.setItem=function(key,value){
                        if(key===STORAGE)throw new DOMException('quota','QuotaExceededError');
                        return original.call(this,key,value)
                    };
                    let rejected=false;
                    try{loadBackup(raw)}catch(e){rejected=true}
                    finally{Storage.prototype.setItem=original}
                    return {rejected,balance:state.balance,
                            saved:JSON.parse(localStorage.getItem(STORAGE)).balance};
                }""",testdoc)
                assert bad_commit=={'rejected':True,'balance':22222,'saved':22222},bad_commit
                page.reload(wait_until='domcontentloaded')
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=20000)
                assert page.evaluate('state.balance===22222 && profileSnapshots.daily.balance===1000')
                assert page.evaluate('canModify()===true'),'Own stale lease not released on failed write and reload'
                report['checks'].append('failed wallet commit rolls back, cold reload retains prior balance and releases lease')
                assert not report['javascript_errors'],str(report['javascript_errors'][:3])
                page.screenshot(path=str(out/'migration_result_mobile.png'),full_page=True)
                report['status']='PASS'
                return report
            finally:ctx.close()
    finally:
        p.terminate()
        try:p.wait(timeout=4)
        except subprocess.TimeoutExpired:p.kill()
        shutil.rmtree(profile,ignore_errors=True)
if __name__=='__main__':
    exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
    try:result=check(exe,out)
    except Exception as e:result={'status':'FAIL','error':repr(e),'traceback':traceback.format_exc()}
    (out/'migration_qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['status']!='PASS':sys.exit(1)
