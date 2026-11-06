#!/usr/bin/env python3
"""Actual Chromium regression for multi-step rounds and wallet-mode transitions.

Uses the already-audited offline Go launcher and fresh throwaway browser profile.
No financial services, accounts, or real customer saves.
"""
import json,os,sys,shutil,subprocess,tempfile,time,traceback
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

def start(exe):
    env={**os.environ,'BROWSER':'true','DISPLAY':''}
    p=subprocess.Popen([str(exe)],cwd=str(exe.parent),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for _ in range(120):
        if p.poll() is not None:raise RuntimeError('Native launcher stopped unexpectedly')
        for c in psutil.Process(p.pid).net_connections(kind='inet'):
            if c.status=='LISTEN' and c.laddr.ip=='127.0.0.1':return p,c.laddr.port
        time.sleep(.1)
    p.terminate()
    raise RuntimeError('No local game server')

def check(executable,output):
    profile=tempfile.mkdtemp(prefix='neon-multistep-qa-')
    process,port=start(executable)
    result={'checks':[],'page_errors':[],'status':'FAIL'}
    try:
        browser_exe=shutil.which('google-chrome') or shutil.which('chromium')
        if not browser_exe:raise RuntimeError('No Chromium browser')
        with sync_playwright() as pw:
            context=pw.chromium.launch_persistent_context(
                user_data_dir=profile,executable_path=browser_exe,headless=True,
                args=['--no-sandbox','--disable-dev-shm-usage'],viewport={'width':390,'height':844})
            try:
                page=context.pages[0] if context.pages else context.new_page()
                page.on('pageerror',lambda e:result['page_errors'].append(str(e)))
                page.on('dialog',lambda d:d.accept())
                page.goto(f'http://127.0.0.1:{port}/',wait_until='domcontentloaded',timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=20000)
                assert page.evaluate('GAMES.length')==44
                assert page.evaluate('canModify()===true')
                before=page.evaluate("""() => {state.stake=10;navigate('letitride');letItRideStart();
                    return {mode:state.mode,active:rt.letitride?.active,balance:state.balance,reserved:state.reserved}
                }""")
                assert before=={'mode':'free','active':True,'balance':49970,'reserved':30},before
                page.evaluate("switchMode('daily')")
                checked=page.evaluate("""() => ({
                    mode:state.mode,free:profileSnapshots.free.balance,daily:state.balance,
                    reserved:state.reserved,stale:rt.letitride?.active===true,
                    writable:canModify()
                })""")
                assert checked=={'mode':'daily','free':50000,'daily':1000,'reserved':0,'stale':False,'writable':True},checked
                result['checks'].append('Cancelled 3-chip Let It Ride on mode switch, refunded all chips, no stale active game')
                actual=page.evaluate("""() => {
                    state.stake=10;navigate('letitride');letItRideStart();
                    if(!rt.letitride?.active)throw Error('Cannot start Let It Ride in new mode');
                    letItRideNext(true);letItRideNext(true);
                    return {active:rt.letitride.active,rounds:state.stats.rounds,
                            wagered:state.stats.wagered,reserved:state.reserved}
                }""")
                assert actual=={'active':False,'rounds':1,'wagered':10,'reserved':0},actual
                result['checks'].append('New Let It Ride round starts, two chips refunded, final round charged exactly one')
                page.evaluate("switchMode('free')")
                page.evaluate("state.stake=10;navigate('threecard');threeDeal()")
                assert page.evaluate("rt.threecard?.active===true && state.reserved===10")
                page.evaluate("switchMode('daily')")
                three=page.evaluate("""() => ({mode:state.mode,reserved:state.reserved,
                          free:profileSnapshots.free.balance,active:rt.threecard?.active===true})""")
                assert three['mode']=='daily' and three['reserved']==0 and three['free']==50000 and not three['active'],three
                page.evaluate("switchMode('free')")
                page.evaluate("state.stake=10;navigate('threecard');threeDeal();threeFinish(false)")
                assert page.evaluate("rt.threecard.active===false && state.reserved===0 && state.stats.rounds===1")
                result['checks'].append('Three Card Poker cancelled on mode change then new Fold settles normally')
                page.evaluate("state.stake=10;navigate('ladder');ladderStart()")
                assert page.evaluate("rt.ladder?.active===true && state.reserved===10")
                page.evaluate("switchMode('daily')")
                ladder=page.evaluate("""() => ({
                    mode:state.mode,reserved:state.reserved,
                    active:rt.ladder?.active===true,writable:canModify()
                })""")
                assert ladder=={'mode':'daily','reserved':0,'active':False,'writable':True},ladder
                result['checks'].append('Double Ladder active round fully reset after wallet switch')
                # Deterministic Blackjack payout paths: test actual finish and split/double
                # functions, not mocked settlement. The synthetic deck is explicit.
                bj=page.evaluate("""() => {
                    switchMode('free');
                    const out=[];
                    const C=(rank,suit='♠')=>({rank,suit});
                    const run=(label,action,stake,payout)=>{
                        if(state.reserved!==0)throw Error('Previous round leaked reserved chips');
                        resetRuntime();state.stake=100;navigate('blackjack');
                        const old={balance:state.balance,rounds:state.stats.rounds,
                                   wagered:state.stats.wagered,paid:state.stats.paid};
                        if(!spend(100))throw Error('Initial Blackjack stake failed');
                        action();
                        const added=state.stats.paid-old.paid;
                        if(rt.bj?.stage!=='done'||state.reserved!==0||state.stats.rounds!==old.rounds+1||
                           state.stats.wagered!==old.wagered+stake||added!==payout||
                           state.balance-old.balance!==payout-stake){
                            throw Error('Blackjack settlement mismatch in '+label+': '+JSON.stringify({
                                stake,payout,added,reserved:state.reserved,rounds:state.stats.rounds-old.rounds,
                                wagered:state.stats.wagered-old.wagered,balance:state.balance-old.balance
                            }));
                        }
                        out.push(label);
                    };
                    run('natural-21',()=>{
                        rt.bj={stage:'playing',dealer:[C('9'),C('8')],deck:[],
                            hands:[{cards:[C('A'),C('K')],stake:100,finished:false,fromSplit:false}],active:0};
                        finishBlackjack();
                    },100,250);
                    run('double-to-21',()=>{
                        rt.bj={stage:'playing',dealer:[C('9'),C('7')],deck:[C('4'),C('10')],
                            hands:[{cards:[C('5'),C('6')],stake:100,finished:false,fromSplit:false}],active:0};
                        bjAction('bj-double');
                    },200,400);
                    run('split-and-push',()=>{
                        rt.bj={stage:'playing',dealer:[C('9'),C('7')],deck:[C('2'),C('9'),C('10')],
                            hands:[{cards:[C('8'),C('8')],stake:100,finished:false,fromSplit:false}],active:0};
                        bjAction('bj-split');bjAction('bj-stand');bjAction('bj-stand');
                    },200,100);
                    return out;
                }""")
                assert bj==['natural-21','double-to-21','split-and-push'],bj
                result['checks'].append('Blackjack natural, double and split settle with exact stake and payouts')
                mine=page.evaluate("""() => {
                    const out=[];
                    const run=(name,action)=>{
                        resetRuntime();state.stake=10;state.minesSize=16;state.minesCount=1;navigate('mines');
                        const start={balance:state.balance,rounds:state.stats.rounds,wagered:state.stats.wagered,paid:state.stats.paid};
                        startMines();
                        if(!rt.mines?.active||state.reserved!==10)throw Error('Mines did not start');
                        action();
                        const stake=state.stats.wagered-start.wagered,payout=state.stats.paid-start.paid;
                        if(rt.mines.active||state.reserved!==0||state.stats.rounds!==start.rounds+1||
                           stake!==10||state.balance-start.balance!==payout-10)
                            throw Error(name+' gave inconsistent Mines settlement');
                        out.push({name,payout});
                    };
                    run('mine-hit',()=>openMine(rt.mines.mines[0]));
                    run('mine-cashout',()=>{
                        const safe=Array.from({length:16},(_,i)=>i).find(i=>!rt.mines.mines.includes(i));
                        openMine(safe);cashMines();
                    });
                    run('mine-full-board',()=>{
                        const bombs=new Set(rt.mines.mines);
                        for(let i=0;i<16;i++)if(!bombs.has(i))openMine(i);
                    });
                    return out;
                }""")
                assert len(mine)==3 and mine[0]['payout']==0 and mine[1]['payout']>0 and mine[2]['payout']>0,mine
                result['checks'].append('Mines loss, manual cashout and auto-completion settle exactly once')
                page.reload(wait_until='domcontentloaded')
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=20000)
                assert page.evaluate('state.reserved===0 && canModify()===true')
                assert not result['page_errors'],result['page_errors'][:3]
                page.screenshot(path=str(output/'multistep_390px.png'),full_page=True)
                result['checks'].append('Cold reload retains zero reserved chips and writable wallet')
                result['status']='PASS'
                return result
            finally:context.close()
    finally:
        process.terminate()
        try:process.wait(timeout=4)
        except subprocess.TimeoutExpired:process.kill()
        shutil.rmtree(profile,ignore_errors=True)

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Usage: neon-multistep-browser-qa.py EXECUTABLE EVIDENCE_DIR')
    output=Path(sys.argv[2]).resolve();output.mkdir(parents=True,exist_ok=True)
    try:report=check(Path(sys.argv[1]).resolve(),output)
    except Exception as e:report={'status':'FAIL','error':repr(e),'traceback':traceback.format_exc()}
    (output/'MULTISTEP_QA.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['status']!='PASS':sys.exit(1)
