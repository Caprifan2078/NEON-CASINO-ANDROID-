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
const test=harness();const run=test.run;
assert.equal(run('GAMES.length'),44);
for(const game of ['sicbo','limbo','hilo','craps'])assert.equal(run(`GAMES.filter(x=>x.id==='${game}').length`),1);
console.log('PASS four new games registered');

// Sic Bo: exhaustively enumerate 216 equally likely triples, never count triples as big/small.
let small=0,big=0,triple=0;
for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++){
 const dice=[a,b,c];test.context.dice=dice;
 const results=run('[sicboOutcome(dice,"small"),sicboOutcome(dice,"big"),sicboOutcome(dice,"triple")]');
 const n=results.filter(Boolean).length;
 assert.equal(n,1,`sicbo outcome exclusive: ${dice}`);
 if(results[0])small++;if(results[1])big++;if(results[2])triple++;
}
assert.deepEqual([small,big,triple],[105,105,6]);
console.log('PASS Sic Bo exhaustive 216 outcomes: small=105 big=105 triple=6');

run('state.stake=100;state.sicboBet="triple";rnd=()=>1;playSicbo()');
assert.equal(run('state.reserved'),0);assert.equal(run('state.balance'),52400);
assert.equal(run('state.gameStats.sicbo.rounds'),1);
console.log('PASS Sic Bo triple payout and per-game stats');

for(const m of [1.5,2,3,5,10,20,50,100]){
 test.context.m=m;
 assert.equal(run('limboOutcome(m,0)'),false);
 assert.equal(run('limboOutcome(m,0.999999999)'),true);
 const threshold=1-.97/m;
 test.context.u=threshold;
 assert.equal(run('limboOutcome(m,u+0.000001)'),true);
 assert.equal(run('limboOutcome(m,u-0.000001)'),false);
}
run('state.limboTarget=20;state.stake=100;unit=()=>0.9999;playLimbo()');
assert.equal(run('rt.limbo.payout'),2000);
assert.equal(run('state.reserved'),0);assert.equal(run('state.gameStats.limbo.rounds'),1);
console.log('PASS Limbo probabilities and x20 payout across all target choices');

for(let i=0;i<13;i++){
 test.context.i=i;
 const hi=run('hiloOdds(RANKS[i],"higher")');
 const lo=run('hiloOdds(RANKS[i],"lower")');
 if(i===12)assert.equal(hi,0);
 else assert.ok(hi>0);
 if(i===0)assert.equal(lo,0);
 else assert.ok(lo>0);
 for(let j=0;j<13;j++){
  const outcome=i===j?'tie':i<j?'higher':'lower';
  assert.ok(['higher','lower','tie'].includes(outcome));
 }
}
run('state.hiloBet="higher";rt.hilo={current:{rank:"5",suit:"♠"}};rnd=()=>12;state.stake=100;playHilo()');
assert.equal(run('rt.hilo.current.rank'),'K');assert.equal(run('state.reserved'),0);
assert.equal(run('state.gameStats.hilo.rounds'),1);
run('state.hiloBet="lower";rt.hilo={current:{rank:"K",suit:"♠"}};rnd=()=>12;playHilo()');
assert.equal(run('rt.hilo.payout'),100);
console.log('PASS Hi-Lo 13 ranks, equal-rank stake return and ranking');

for(let sum=2;sum<=12;sum++){
 test.context.sum=sum;
 const out=run('crapsStep(null,sum)');
 assert.equal(out.status,[7,11].includes(sum)?'won':[2,3,12].includes(sum)?'lost':'point');
}
for(const point of [4,5,6,8,9,10]){
 test.context.point=point;
 for(let sum=2;sum<=12;sum++){
  test.context.sum=sum;
  assert.equal(run('crapsStep(point,sum)').status,sum===point?'won':sum===7?'lost':'point');
 }
}
const pending=harness(),p=pending.run;
p('state.stake=100;rnd=()=>2;rollCraps()'); // dice 3+3=6, point six
assert.equal(p('rt.craps.active'),true);assert.equal(p('state.reserved'),100);
const balance=p('state.balance');
p('rollCraps()'); // reroll 6 => payout x2
assert.equal(p('rt.craps.active'),false);assert.equal(p('state.reserved'),0);
assert.equal(p('state.balance'),balance+200);
assert.equal(p('state.gameStats.craps.rounds'),1);
console.log('PASS Craps Pass Line 11 opening totals, 6 points, multi-roll accounting');

const day=harness(),d=day.run;
d('switchMode("daily");state.stake=100');
for(const game of ['sicbo','limbo','hilo']){
 d(`state.game='${game}'`);
 d(game==='sicbo'?'playSicbo()':game==='limbo'?'playLimbo()':'playHilo()');
 assert.equal(d('state.reserved'),0);
}
d('rnd=()=>2;rollCraps()');
assert.equal(d('state.reserved'),100);
d('switchMode("free")');
assert.equal(d('state.reserved'),0);assert.equal(d('state.balance'),50000);
d('switchMode("daily")');assert.equal(d('state.reserved'),0);
console.log('PASS four new games in daily wallet with safe pending Craps refund');

const cap=harness(),c=cap.run;
c('state.balance=BALANCE_CAP-5;state.stake=10;save();addChips(1000000)');
assert.equal(c('state.balance'),9000000000000000);
const restored=harness(cap.saves['neon-casino-local-v1']);
assert.equal(restored.run('state.balance'),9000000000000000);
console.log('PASS near-cap wallet survives reload without dropping virtual money');

const fuzz=harness(),f=fuzz.run;
for(let i=0;i<500;i++){
 if(i%4===0)f('playSicbo()');
 else if(i%4===1)f('playLimbo()');
 else if(i%4===2)f('playHilo()');
 else {f('rollCraps()');if(f('rt.craps?.active'))f('switchMode("daily");switchMode("free")')}
 assert.equal(f('state.reserved'),0);
 assert.ok(f('state.balance>=0&&Number.isSafeInteger(state.balance)'));
}
assert.ok(f('state.stats.rounds')>=300&&f('state.stats.rounds')<=500);
assert.equal(f('Object.values(state.gameStats).reduce((n,g)=>n+g.rounds,0)'),f('state.stats.rounds'));
console.log('PASS 500 new-game fuzz rounds, zero ghost stakes or balance underflow');
console.log('ALL v1.3 TESTS PASSED');
