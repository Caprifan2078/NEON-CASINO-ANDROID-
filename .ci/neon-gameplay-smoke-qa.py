#!/usr/bin/env python3
"""Smoke a real on-screen play/start action in ALL 44 virtual-chip games.

Uses the same DOM event delegation as player clicks. It never forces random
results, rewrites balances, or skips a broken action. Only 3 selection setups
for games whose documented rules require 5/6 picked numbers.
"""
import sys,os,time,json,shutil,tempfile,subprocess
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

ACTION_MAP={
'roulette':['roulette-bet','roulette-spin'],
'blackjack':['bj-deal'],
'wheel':['wheel-spin'],
'crash':['crash-start'],
'slots':['slots-spin'],
'mines':['mines-start'],
'plinko':['plinko-drop'],
'dice':['dice-roll'],
'baccarat':['baccarat-play'],
'coin':['coin-flip'],
'keno':['keno-play'],
'poker':['poker-deal'],
'sicbo':['sicbo-roll'],
'limbo':['limbo-play'],
'hilo':['hilo-play'],
'craps':['craps-roll'],
'roulette-us':['vr-bet','vr-spin'],
'roulette-fr':['vr-bet','vr-spin'],
'threecard':['three-deal'],
'war':['war-deal'],
'dragontiger':['dragon-deal'],
'tower':['tower-start'],
'bingo':['bingo-play'],
'lotto':['lotto-play'],
'scratch':['scratch-start'],
'seven':['seven-roll'],
'dicepoker':['dicepoker-roll'],
'treasure':['treasure-start'],
'andar':['andar-play'],
'reddog':['reddog-play'],
'pick3':['pick3-play'],
'bingo90':['bingo90-play'],
'keno80':['keno80-play'],
'cardsuit':['cardsuit-play'],
'ladder':['ladder-start'],
'slots5':['slots5-spin'],
'holdem':['holdem-play'],
'letitride':['letitride-start'],
'rps':['rps-play'],
'colors':['colors-play'],
'caribbean':['caribbean-start'],
'teenpatti':['teen-start'],
'fantan':['fan-play'],
'crown':['crown-play'],
}
assert len(ACTION_MAP)==44

def main(exe,out):
    env=os.environ.copy();env.update({'BROWSER':'true','DISPLAY':''})
    p=subprocess.Popen([str(exe)],cwd=exe.parent,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    profile=tempfile.mkdtemp(prefix='neon-gameplay-smoke-')
    report={'status':'FAIL','gameCount':0,'failures':[],'started':[],'pageErrors':[]}
    try:
        port=None
        for i in range(120):
            if p.poll() is not None:raise RuntimeError('Launcher exited early')
            for n in psutil.Process(p.pid).net_connections(kind='inet'):
                if n.status=='LISTEN' and n.laddr.ip=='127.0.0.1':port=n.laddr.port;break
            if port:break
            time.sleep(.1)
        if not port:raise RuntimeError('No localhost server')
        chrome=shutil.which('google-chrome') or shutil.which('chromium')
        assert chrome
        with sync_playwright() as pw:
            ctx=pw.chromium.launch_persistent_context(user_data_dir=profile,executable_path=chrome,
                headless=True,args=['--no-sandbox','--disable-dev-shm-usage'],viewport={'width':390,'height':844})
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                page.on('pageerror',lambda err: report['pageErrors'].append(str(err)))
                page.goto(f'http://127.0.0.1:{port}/',wait_until='domcontentloaded',timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=30000)
                runtime=page.evaluate('GAMES.map(x=>x.id)')
                assert len(runtime)==44 and set(runtime)==set(ACTION_MAP), 'Game catalogue and test inventory disagree'
                report['gameCount']=len(runtime)
                for game in runtime:
                    actions=ACTION_MAP[game]
                    result=page.evaluate("""({game,actions}) => {
                      navigate(game);state.stake=10;render();
                      const before={balance:state.balance,reserved:state.reserved,rounds:state.stats.rounds};
                      const pick = (action,count) => {
                        for(let i=0;i<count;i++){
                          // Every click rerenders the board: never reuse detached DOM nodes.
                          const b=[...document.querySelectorAll('#gameArea [data-action="'+action+'"]')]
                            .find(x=>!x.disabled && x.getAttribute('aria-pressed')!=='true' && !x.classList.contains('selected'));
                          if(!b)throw Error('Could not select number '+(i+1)+' for '+action);
                          b.click();
                        }
                      };
                      if(game==='keno')pick('keno-pick',5);
                      if(game==='lotto')pick('lotto-pick',6);
                      if(game==='keno80')pick('keno80-pick',6);
                      const clicked=[];
                      for(const action of actions){
                        const buttons=[...document.querySelectorAll('[data-action="'+action+'"]')];
                        const b=buttons.find(x=>!x.disabled);
                        if(!b)return {ok:false,why:'Missing enabled action: '+action,clicked,before};
                        b.click();clicked.push(action);
                      }
                      const after={balance:state.balance,reserved:state.reserved,rounds:state.stats.rounds};
                      const altered = after.balance!==before.balance || after.reserved!==before.reserved || after.rounds!==before.rounds;
                      const valid = [after.balance,after.reserved,after.rounds].every(Number.isSafeInteger) && after.balance>=0 && after.reserved>=0;
                      return {ok:altered&&valid,game,clicked,before,after,altered,valid};
                    }""",{'game':game,'actions':actions})
                    if result.get('ok'): report['started'].append(game)
                    else:report['failures'].append(result)
                page.screenshot(path=str(out/'all_games_smoke_final.png'),full_page=True)
                assert not report['pageErrors'],f'JavaScript exceptions: {report["pageErrors"][:5]}'
                assert not report['failures'],f"Games without a valid on-screen play action: {report['failures'][:5]}"
                assert len(report['started'])==44
                report['status']='PASS'
                print('PASS: all 44 game modes accepted a real UI start/bet action; wallet values valid')
            finally:ctx.close()
    finally:
        p.terminate()
        try:p.wait(timeout=4)
        except subprocess.TimeoutExpired:p.kill();p.wait(timeout=4)
        shutil.rmtree(profile,ignore_errors=True)
    return report
if __name__=='__main__':
    exe=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
    try:result=main(exe,out)
    except Exception as e:result={'status':'FAIL','error':repr(e)}
    (out/'gameplay_smoke.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result['status']!='PASS':sys.exit(1)
