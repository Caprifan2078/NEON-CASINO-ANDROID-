#!/usr/bin/env python3
"""RED/GREEN: canceled virtual-chip rounds may never outlive a wallet mode switch.
Run on isolated real Chromium with actual P0-patched S5 Go application.
"""
import json,os,shutil,subprocess,sys,tempfile,time,traceback
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

def run(executable,out):
    env={**os.environ,"BROWSER":"true","DISPLAY":""}
    p=subprocess.Popen([str(executable)],cwd=executable.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    port=None
    for _ in range(110):
        if p.poll() is not None:raise AssertionError("Native launcher stopped before startup")
        for conn in psutil.Process(p.pid).net_connections(kind='inet'):
            if conn.status=='LISTEN' and conn.laddr.ip=='127.0.0.1':
                port=conn.laddr.port;break
        if port:break
        time.sleep(.1)
    assert port, "Native launcher did not bind loopback"
    profile=tempfile.mkdtemp(prefix='neon-stale-round-')
    record={"checks":[],"page_errors":[],"status":"FAIL"}
    try:
        with sync_playwright() as pw:
            chrome=shutil.which('google-chrome') or shutil.which('chromium')
            assert chrome
            ctx=pw.chromium.launch_persistent_context(user_data_dir=profile,executable_path=chrome,headless=True,
                   args=['--no-sandbox','--disable-dev-shm-usage'],viewport={'width':390,'height':844})
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                page.on('dialog',lambda d:d.accept())
                page.on('pageerror',lambda e:record["page_errors"].append(str(e)))
                page.goto(f'http://127.0.0.1:{port}/',wait_until='domcontentloaded',timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=22000)
                assert page.evaluate("GAMES.length") == 44
                # First assertion is expected RED on original S5: Scratch stays
                # active after switchMode refunded its wager, making the old
                # scratch settlement throw on an already-refunded bet.
                for game,start,slot in [
                    ('scratch','scratchStart()','scratch'),
                    ('tower','towerStart()','tower'),
                    ('threecard','threeDeal()','threecard'),
                    ('caribbean','caribbeanStart()','caribbean'),
                    ('teenpatti','teenStart()','teenpatti'),
                    ('treasure','treasureStart()','treasure'),
                    ('roulette-us',"vrBet('red')",'us'),
                    ('roulette-fr',"vrBet('red')",'fr')
                ]:
                    result=page.evaluate("""({game,start,slot}) => {
                        if(state.mode==='daily')switchMode('free');
                        state.stake=100;
                        state.chip=10;
                        navigate(game);
                        // These are the SAME public game actions called by the UI.
                        switch(game){
                          case 'scratch': scratchStart(); break;
                          case 'tower': towerStart(); break;
                          case 'threecard': threeDeal(); break;
                          case 'caribbean': caribbeanStart(); break;
                          case 'teenpatti': teenStart(); break;
                          case 'treasure': treasureStart(); break;
                          case 'roulette-us': case 'roulette-fr': vrBet('red'); break;
                          default: throw Error('Missing game '+game);
                        }
                        if(state.reserved<=0)throw Error('Round did not reserve chips: '+game);
                        switchMode('daily');
                        return {
                          game,mode:state.mode,balance:state.balance,reserved:state.reserved,
                          freeBalance:profileSnapshots.free.balance,
                          oldRuntimeStillPresent:!!rt[slot],
                          active:!!rt[slot]?.active,
                          oldBets:rt[slot]?.bets?.length||0
                        };
                    }""",{"game":game,"start":start,"slot":slot})
                    assert result['mode']=='daily' and result['balance']==1000 and result['reserved']==0 and result['freeBalance']==50000,result
                    assert not result['oldRuntimeStillPresent'],f"STALE ROUND: {result}"
                    record['checks'].append("Cancelled "+game+" on wallet switch; old runtime cleared; exact refund")
                # Verify genuine completed rounds use one settlement and ignore duplicate UI actions.
                tasks=[
                    ("scratch","scratchStart();for(let i=0;i<9;i++)scratchOpen(i);scratchOpen(8);"),
                    ("tower","towerStart();for(let row=0;row<5;row++){const c=[0,1,2].find(x=>!rt.tower.traps[row].includes(x));towerPick(row,c)};towerPick(4,0);"),
                    ("mines","startMines();const r=rt.mines;openMine([...Array(r.size).keys()].find(x=>!r.mines.includes(x)));cashMines();cashMines();"),
                    ("treasure","treasureStart();treasureOpen(0);treasureOpen(0);"),
                    ("threecard","threeDeal();threeFinish(true);threeFinish(true);"),
                    ("caribbean","caribbeanStart();caribbeanFinish(false);caribbeanFinish(true);"),
                    ("teenpatti","teenStart();teenFinish(false);teenFinish(true);")
                ]
                for game,action in tasks:
                    result=page.evaluate("""({game,action}) => {
                        if(state.mode!=='daily')switchMode('daily');
                        state.stake=100;
                        navigate(game);
                        const before=state.stats.rounds;
                        switch(game){
                          case 'scratch': scratchStart(); for(let i=0;i<9;i++)scratchOpen(i);scratchOpen(8); break;
                          case 'tower': towerStart();for(let row=0;row<5;row++){
                            const c=[0,1,2].find(x=>!rt.tower.traps[row].includes(x));towerPick(row,c);
                          }towerPick(4,0);break;
                          case 'mines': startMines();{
                            const r=rt.mines;
                            openMine([...Array(r.size).keys()].find(x=>!r.mines.includes(x)));
                            cashMines();cashMines();
                          }break;
                          case 'treasure':treasureStart();treasureOpen(0);treasureOpen(0);break;
                          case 'threecard':threeDeal();threeFinish(true);threeFinish(true);break;
                          case 'caribbean':caribbeanStart();caribbeanFinish(false);caribbeanFinish(true);break;
                          case 'teenpatti':teenStart();teenFinish(false);teenFinish(true);break;
                          default:throw Error('Missing finish scenario '+game);
                        }
                        return {game,settlements:state.stats.rounds-before,reserved:state.reserved,balance:state.balance};
                    }""",{"game":game,"action":action})
                    assert result["settlements"]==1 and result["reserved"]==0,f"Bad finalization: {result}"
                    record["checks"].append("Finished "+game+" exactly once; no reserved stake or double payout")
                # Reload must not restore an active canceled round or change persistent wallet.
                balances=page.evaluate("({mode:state.mode,balance:state.balance,rounds:state.stats.rounds})")
                page.reload(wait_until='domcontentloaded')
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=20000)
                assert page.evaluate("({mode:state.mode,balance:state.balance,rounds:state.stats.rounds})")==balances
                assert page.evaluate("state.reserved===0 && canModify()")
                assert not record["page_errors"],record["page_errors"][:3]
                record["checks"].append("Cold restart preserves exact wallet and statistics")
                record["status"]="PASS"
                page.screenshot(path=str(out/'completed_rounds_mobile.png'),full_page=True)
            finally:ctx.close()
    finally:
        p.terminate()
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
        shutil.rmtree(profile,ignore_errors=True)
    return record

if __name__=="__main__":
    exe=Path(sys.argv[1]).resolve()
    out=Path(sys.argv[2]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    try:r=run(exe,out)
    except Exception as e:r={"status":"FAIL","error":repr(e),"traceback":traceback.format_exc()}
    (out/'round_completion_result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if r['status']!='PASS':sys.exit(1)
