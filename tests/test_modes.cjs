'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
function harness(seed=null){
  let clock=0, tasks=[],intervals=[],listeners={},saves={};
  if(seed!==null)saves['neon-casino-local-v1']=seed;
  const nodes=new Map();
  const element=id=>{if(!nodes.has(id)){const o={id,innerHTML:'',textContent:'',value:'',className:'',disabled:false,style:{},classList:{add(){},remove(){},toggle(){}},dataset:{},clientWidth:420,setAttribute(){},appendChild(){},click(){},remove(){},addEventListener(t,cb){listeners[id+':'+t]=cb},getContext(){return new Proxy({}, {get(){return ()=>{}}})}};nodes.set(id,o)}return nodes.get(id)};
  const context={console,Math,JSON,Number,Date,Array,Set,Map,Object,String,Intl,crypto:crypto.webcrypto,Blob,
    performance:{now:()=>clock},requestAnimationFrame(f){f()},
    setTimeout(f,ms=0){const o={f,ms,active:true};tasks.push(o);return o},clearTimeout(o){if(o)o.active=false},
    setInterval(f,ms=0){const o={f,ms,active:true};intervals.push(o);return o},clearInterval(o){if(o)o.active=false},
    localStorage:{getItem(k){return saves[k]||null},setItem(k,v){saves[k]=v}},
    document:{getElementById:element,querySelector(){return null},createElement(){return element('generated'+Math.random())},body:{addEventListener(t,cb){listeners[t]=cb},appendChild(){}}},window:{addEventListener(){}},navigator:{},confirm(){return true},
    URL:{createObjectURL(){return 'blob:test'},revokeObjectURL(){}}
  };
  vm.createContext(context);vm.runInContext(source,context,{filename:'app.js'});
  const run=(code)=>vm.runInContext(code,context);
  const later=(min=0)=>{for(let n=0;n<50&&tasks.some(x=>x.active&&x.ms>=min);n++){const active=tasks.filter(x=>x.active&&x.ms>=min);tasks=tasks.filter(x=>!(x.active&&x.ms>=min));for(const task of active)task.f()}};
  const tick=(count=100,delta=80)=>{for(let i=0;i<count;i++){clock+=delta;for(const timer of intervals.slice())if(timer.active)timer.f()}};
  return {run, later,tick,element,saves,context,advance:(ms)=>{clock+=ms},listeners};
}

function ok(message){console.log('PASS',message)}
const t=harness();let run=t.run;
assert.equal(run('GAMES.length'),44);
assert.equal(run('state.mode'),'free');
assert.equal(run('state.balance'),50000);
assert.equal(run('dailyProgress.day'),1);
assert.ok(t.element('modeBar').innerHTML.includes('Игровые дни'));
ok('initial free wallet, day one and mode selector rendered');

run('switchMode("daily")');
assert.equal(run('state.mode'),'daily');assert.equal(run('state.balance'),1000);
assert.equal(run('state.stats.rounds'),0);
run('addChips(1000000)');assert.equal(run('state.balance'),1000);
run('handleAction({dataset:{action:"add-chips",value:"100000"}})');assert.equal(run('state.balance'),1000);
assert.ok(t.element('modalHost'));
ok('daily wallet fixed at 1000, all top-up entry points blocked');

run('state.stake=100;startMines()');assert.equal(run('state.balance'),900);assert.equal(run('state.reserved'),100);
run('switchMode("free")');assert.equal(run('state.balance'),50000);assert.equal(run('state.reserved'),0);
run('addChips(1500)');assert.equal(run('state.balance'),51500);
run('switchMode("daily")');assert.equal(run('state.balance'),1000);assert.equal(run('state.reserved'),0);
run('switchMode("free")');assert.equal(run('state.balance'),51500);
ok('switch cancels outstanding bets without moving chips between wallets');

run('switchMode("daily")');
run('state.stake=100; state.diceChance=5;state.diceSide="under";');
run('const savedRnd=rnd; rnd=()=>99;rollDice();rnd=savedRnd;');
assert.equal(run('state.balance'),900);assert.equal(run('dailyProgress.rounds'),1);
assert.equal(run('dailyProgress.wagered'),100);
run('finishDailyDay("manual")');
assert.equal(run('state.balance'),1000);assert.equal(run('dailyProgress.day'),2);
assert.equal(run('dailyProgress.history[0].leftover'),900);
assert.equal(run('dailyProgress.history[0].reason'),'manual');
ok('manual day end forfeits remainder and records accurate completed-day totals');

run('state.balance=10;state.stake=10;save()');
run('rnd=()=>99;rollDice()');
assert.equal(run('dailyProgress.day'),3);
assert.equal(run('dailyProgress.history[0].reason'),'empty');
assert.equal(run('dailyProgress.history[0].leftover'),0);
assert.equal(run('state.balance'),1000);assert.equal(run('state.reserved'),0);
ok('automatic next day after final losing wager; exactly one new allowance');

run('state.balance=500;save();rouletteBet("color","red")');
assert.equal(run('state.reserved'),100);
assert.equal(run('finishDailyDay("manual")'),false);
assert.equal(run('dailyProgress.day'),3);
run('refund(rt.bets.pop().amount)');
assert.equal(run('finishDailyDay("manual")'),true);
assert.equal(run('dailyProgress.day'),4);
ok('pending wagers block manual day transition; canceling bet does not duplicate chips');

// Two-mode portable export / restore and 1.1 save migration.
run('switchMode("free");state.balance=67891;save();switchMode("daily");state.balance=345;save()');
const backup=run('JSON.stringify(snapshot())');
assert.equal(JSON.parse(backup).version,3);
run('resetAll()');assert.equal(run('state.balance'),1000);
t.context.backup=backup;
assert.equal(run('loadBackup(backup)'),true);
assert.equal(run('state.balance'),345);assert.equal(run('dailyProgress.day'),4);
run('switchMode("free")');assert.equal(run('state.balance'),67891);
ok('v3 backup exports/restores both wallets and historical days');

const invalid=JSON.parse(backup);invalid.profiles.daily.balance=-50;
t.context.bad=JSON.stringify(invalid);
assert.throws(()=>run('loadBackup(bad)'));
assert.equal(run('state.balance'),67891);
ok('corrupt v3 daily profile rejected atomically');

const v2=JSON.stringify({format:'NEON_CASINO_SAVE',version:2,balance:8888,reserved:0,stats:{rounds:2,wins:0,wagered:100,paid:0},rouletteHistory:[],activity:[]});
t.context.oldSave=v2;
assert.equal(run('loadBackup(oldSave)'),true);
assert.equal(run('state.mode'),'free');assert.equal(run('state.balance'),8888);
run('switchMode("daily")');assert.equal(run('dailyProgress.day'),1);assert.equal(run('state.balance'),1000);
ok('v2 standalone backups import as Free Play with new day-one wallet');

// Page reload must recover both virtual ledgers and day progress.
run('finishDailyDay("manual")');
const reload=harness(t.saves['neon-casino-local-v1']);
assert.equal(reload.run('state.mode'),'daily');assert.equal(reload.run('dailyProgress.day'),2);
reload.run('switchMode("free")');assert.equal(reload.run('state.balance'),8888);
ok('persistent separate profiles survive a simulated app restart');

// Fuzz repeated switches and completions for unauthorized cross-wallet transfer.
const stress=harness();
for(let i=0;i<120;i++){
 stress.run('switchMode("daily");state.balance=10;state.stake=10;state.diceChance=5;state.diceSide="under";rnd=()=>99;rollDice()');
 assert.equal(stress.run('state.balance'),1000);
 stress.run('switchMode("free")');
 assert.equal(stress.run('state.balance'),50000);
}
assert.equal(stress.run('dailyProgress.day'),121);
assert.equal(stress.run('dailyProgress.history.length'),100);
ok('120-day accounting stress test: history bounded, no leaked payouts or funds');

console.log('ALL v1.2 MODES TESTS PASSED');
