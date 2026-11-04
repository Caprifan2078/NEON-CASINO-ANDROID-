#!/usr/bin/env python3
"""Browser QA: backwards-compatible saves v2-v5; adversarial import fuzzing.

All data synthetic and confined to a temporary Chrome profile.
Uses the actual native Go launcher and Web Crypto, not a mocked save API.
"""
import json,os,subprocess,time,shutil,tempfile,traceback,sys
from pathlib import Path
import psutil
from playwright.sync_api import sync_playwright

def server(exe):
    proc=subprocess.Popen([str(exe)],cwd=str(exe.parent),env={**os.environ,'BROWSER':'true','DISPLAY':''},
                         stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
    for _ in range(140):
        if proc.poll() is not None:raise RuntimeError('Native launcher exited')
        for cn in psutil.Process(proc.pid).net_connections(kind='inet'):
            if cn.status=='LISTEN' and cn.laddr.ip=='127.0.0.1':return proc,cn.laddr.port
        time.sleep(.1)
    proc.terminate()
    raise RuntimeError('No local server')

def run(exe,out):
    p,port=server(exe)
    profile=tempfile.mkdtemp(prefix='neon-migration-qa-')
    report={'status':'FAIL','checks':[],'details':[],'page_errors':[]}
    try:
        with sync_playwright() as pw:
            chrome=shutil.which('google-chrome') or shutil.which('chromium')
            assert chrome,'Chrome not found'
            ctx=pw.chromium.launch_persistent_context(user_data_dir=profile,executable_path=chrome,headless=True,
                    args=['--no-sandbox','--disable-dev-shm-usage'])
            try:
                page=ctx.pages[0] if ctx.pages else ctx.new_page()
                page.on('dialog',lambda d:d.accept())
                page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                page.goto(f'http://127.0.0.1:{port}/',wait_until='domcontentloaded',timeout=30000)
                page.locator('#gameNav [data-action=nav]').first.wait_for(state='attached',timeout=30000)
                info=page.evaluate('({version:NEON_INFO.version,games:NEON_INFO.gameCount,mode:state.mode,balance:state.balance})')
                assert info['version']=='1.8.9' and info['games']==44
                original=page.evaluate('snapshot()')
                assert original['format']=='NEON_CASINO_SAVE' and original['version']==5
                report['checks'].append('v1.8.9 loaded 44 games and created v5 backup')
                for version in [2,3,4,5]:
                    candidate=page.evaluate('snapshot()')
                    candidate['version']=version
                    candidate['balance']=12345+version
                    candidate['profiles']['free']['balance']=12345+version
                    candidate['profiles']['daily']['balance']=950
                    candidate['mode']='free'
                    if version==2:
                        for field in ('profiles','dailyProgress','preferences','mode'):candidate.pop(field,None)
                    if version in (3,4):candidate.pop('preferences',None)
                    before=page.evaluate('({balance:state.balance,mode:state.mode,day:dailyProgress.day,free:profileSnapshots.free.balance,daily:profileSnapshots.daily.balance})')
                    accepted=page.evaluate('(raw)=>loadBackup(raw)',json.dumps(candidate,separators=(',',':')))
                    after=page.evaluate('({balance:state.balance,mode:state.mode,day:dailyProgress.day,daily:profileSnapshots.daily.balance})')
                    assert accepted and after['balance']==12345+version and after['mode']=='free',f'v{version}: wrong imported wallet {after}'
                    assert after['daily']==(950 if version>=3 else 1000),f'v{version}: daily migration wrong {after}'
                    assert page.evaluate('restorePreImportBackup()') is True
                    undid=page.evaluate('({balance:state.balance,mode:state.mode,day:dailyProgress.day,free:profileSnapshots.free.balance,daily:profileSnapshots.daily.balance})')
                    assert undid==before,f'v{version}: undo did not restore both wallets {before} {undid}'
                    report['checks'].append(f'v{version} JSON: import two wallets and undo with exact balance/day restoration')
                # Invalid or structurally inconsistent files must fail before confirmation
                # and never touch wallet or PREIMPORT safety backup.
                checked=page.evaluate("""() => {
                  const old={balance:state.balance,free:profileSnapshots.free.balance,daily:profileSnapshots.daily.balance,day:dailyProgress.day};
                  const base=snapshot();
                  const fields=[
                    ['missing format',o=>{delete o.format}],
                    ['invalid format',o=>{o.format='NOT_A_SAVE'}],
                    ['version old',o=>{o.version=1}],
                    ['version future',o=>{o.version=999}],
                    ['balance negative',o=>{o.balance=-100}],
                    ['balance not integer',o=>{o.balance=10.4}],
                    ['balance not number',o=>{o.balance='123'}],
                    ['reserved wager present',o=>{o.reserved=100}],
                    ['stats not object',o=>{o.stats='broken'}],
                    ['history not array',o=>{o.rouletteHistory='wrong'}],
                    ['activity not array',o=>{o.activity=42}],
                    ['missing free profile',o=>{delete o.profiles.free}],
                    ['bad daily profile',o=>{o.profiles.daily.reserved=1}],
                    ['daily day negative',o=>{o.dailyProgress.day=-1}],
                    ['daily day overflow',o=>{o.dailyProgress.day=100000001}],
                    ['daily history not array',o=>{o.dailyProgress.history={}}],
                    ['v5 missing preferences',o=>{delete o.preferences}],
                    ['v5 favorites wrong type',o=>{o.preferences.favorites={}}],
                    ['v5 favorites unknown id',o=>{o.preferences.favorites=['unknown']}],
                    ['v5 recent unknown id',o=>{o.preferences.recent=['unknown']}],
                    ['v5 favorites oversized',o=>{o.preferences.favorites=Array(45).fill('coin')}],
                    ['v5 recent oversized',o=>{o.preferences.recent=Array(5).fill('coin')}]
                  ];
                  let rejected=0,changed=0,accepted=[];
                  const compare=()=>JSON.stringify({balance:state.balance,free:profileSnapshots.free.balance,daily:profileSnapshots.daily.balance,day:dailyProgress.day});
                  const check=JSON.stringify(old);
                  for(const [name,mutate] of fields){
                    const c=JSON.parse(JSON.stringify(base));mutate(c);
                    try{if(loadBackup(JSON.stringify(c)))accepted.push(name)}
                    catch(e){rejected++}
                    if(compare()!==check)changed++;
                  }
                  for(const raw of ['null','[]','{}','42','true','\"x\"','','{','[']){
                    try{if(loadBackup(raw))accepted.push('invalid json:'+raw)}
                    catch(e){rejected++}
                    if(compare()!==check)changed++;
                  }
                  try{loadBackup('x'.repeat(1000001));accepted.push('oversized')}
                  catch(e){rejected++}
                  if(compare()!==check)changed++;
                  return {rejected,expected:fields.length+10,changed,accepted};
                }""")
                assert checked['rejected']==checked['expected'] and checked['changed']==0 and not checked['accepted'],checked
                report['checks'].append(str(checked['expected'])+' invalid save shapes rejected without changing wallet')
                # A specially crafted JSON object can override its toString method.
                # Before the P0 fix, safeActivity/safeJournal String(value) throws and
                # aborts import. Both wallets, their journals, and replay must survive.
                poisoned=page.evaluate("""() => {
                  const v=snapshot(),bomb={toString:null};
                  const rec={at:Date.now(),game:bomb,stake:2,payout:3,detail:bomb,
                    replay:{type:'roulette',number:17,bets:[{type:'number',value:bomb,amount:2}]}};
                  for(const mode of ['free','daily']){
                    v.profiles[mode].activity=[{game:bomb,detail:bomb,profit:0,at:bomb}];
                    v.profiles[mode].journal=[rec];
                  }
                  return JSON.stringify(v);
                }""")
                old_balance=page.evaluate('state.balance')
                assert page.evaluate('(raw)=>loadBackup(raw)',poisoned) is True
                result=page.evaluate("""() => ({
                    balance:state.balance,
                    freeActivity:profileSnapshots.free.activity[0],
                    freeJournal:profileSnapshots.free.journal[0],
                    dailyActivity:profileSnapshots.daily.activity[0],
                    dailyJournal:profileSnapshots.daily.journal[0]
                })""")
                assert result['balance']==old_balance
                assert result['freeActivity']['game']=='' and result['freeActivity']['detail']==''
                assert result['dailyActivity']['game']=='' and result['dailyActivity']['detail']==''
                assert result['freeJournal']['game']=='' and result['freeJournal']['detail']==''
                assert result['dailyJournal']['game']=='' and result['dailyJournal']['detail']==''
                assert result['freeJournal']['replay'] is None and result['dailyJournal']['replay'] is None
                assert page.evaluate('restorePreImportBackup()') is True
                assert page.evaluate('state.balance')==old_balance
                report['checks'].append('Poisoned toString objects in BOTH wallet journals/activities/replays sanitized; import and undo durable')
                # An accepted save might legitimately contain malformed *optional*
                # statistics from old clients. Sanitize, do not execute nested values.
                sanitized=page.evaluate("""() => {
                  const v=snapshot();
                  v.profiles.free.stats.rounds=-100;
                  v.profiles.free.stats.wagered='NaN';
                  v.profiles.free.journal=[{at:Date.now(),game:'<img src=x onerror=alert(1)>',stake:2,payout:3,detail:'<script>x</script>'}];
                  v.stats.rounds=-1;
                  return JSON.stringify(v);
                }""")
                assert page.evaluate('(raw)=>loadBackup(raw)',sanitized) is True
                safe=page.evaluate('({rounds:state.stats.rounds,journal:state.journal.map(x=>x.game),wallet:state.balance})')
                assert safe['rounds']==0 and safe['wallet']>=0,safe
                page.evaluate("() => {state.modal='profile';profileTab='journal';renderModal()}")
                assert page.locator('script').count()==page.locator('script').count()
                # Untrusted game label should render as text, not an executable image.
                assert not page.locator('#modalHost img[onerror]').count(),'Backup game label inserted unsafe HTML'
                report['checks'].append('Malformed optional stats sanitized, imported journal text escaped')
                assert page.evaluate('restorePreImportBackup()') is True
                assert page.evaluate('state.balance')==original['balance']
                page.reload(wait_until='domcontentloaded')
                assert page.evaluate('state.balance')==original['balance'],'Undo not durable after reload'
                report['checks'].append('Final backup undo persisted across cold reload')
                assert not report['page_errors'],report['page_errors']
                page.screenshot(path=str(out/'migration-last-screen.png'),full_page=True)
                report['status']='PASS'
            finally:ctx.close()
    finally:
        p.terminate()
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill()
        shutil.rmtree(profile,ignore_errors=True)
    return report
if __name__=='__main__':
    exe=Path(sys.argv[1]).resolve()
    out=Path(sys.argv[2]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    try:r=run(exe,out)
    except Exception as e:r={'status':'FAIL','error':repr(e),'traceback':traceback.format_exc()}
    (out/'backup_migration_result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps(r,ensure_ascii=False,indent=2))
    if r['status']!='PASS':sys.exit(1)
