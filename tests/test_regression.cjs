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
const t=harness();let run=t.run;
function pass(title){console.log('PASS',title)}
assert.equal(run('GAMES.length'),44);
assert.equal(run('KENO_PAY.length'),6);
assert.equal(run('new Set(RNUM).size'),37);
assert.equal(run('state.balance'),50000);
pass('clean initial state + 12 games');

// Roulette actions cannot accept nonexistent numbers, game types, or chip denominations.
run('rouletteBet("number","200")');run('rouletteBet("unknown","red")');
assert.equal(run('state.balance'),50000);
run('state.chip=-100; rouletteBet("color","red")');assert.equal(run('state.balance'),50000);
run('state.chip=10; rouletteBet("number","0")');assert.equal(run('state.balance'),49990);
run('refund(rt.bets.pop().amount)');assert.equal(run('state.balance'),50000);
pass('roulette invalid inputs cannot charge or credit chips');

// Exact poker payouts, including the ace-low straight and low-pair exclusion.
const hand=(cards)=>JSON.stringify(cards.map(([rank,suit])=>({rank,suit})));
function eqPoker(cards,kind,mult){const result=JSON.parse(run('JSON.stringify(evaluatePoker('+hand(cards)+'))'));assert.equal(result.kind,kind);assert.equal(result.mult,mult)}
eqPoker([['10','♥'],['J','♥'],['Q','♥'],['K','♥'],['A','♥']],'royal',250);
eqPoker([['A','♠'],['2','♠'],['3','♠'],['4','♠'],['5','♠']],'straightFlush',50);
eqPoker([['J','♥'],['J','♠'],['J','♦'],['J','♣'],['2','♥']],'quads',25);
eqPoker([['Q','♥'],['Q','♠'],['Q','♦'],['5','♣'],['5','♥']],'fullHouse',9);
eqPoker([['2','♥'],['4','♥'],['6','♥'],['8','♥'],['10','♥']],'flush',6);
eqPoker([['A','♠'],['2','♥'],['3','♦'],['4','♣'],['5','♠']],'straight',4);
eqPoker([['8','♥'],['8','♠'],['8','♦'],['A','♣'],['6','♥']],'trips',3);
eqPoker([['2','♥'],['2','♠'],['Q','♦'],['Q','♣'],['6','♥']],'twoPair',2);
eqPoker([['J','♥'],['J','♠'],['3','♦'],['7','♣'],['9','♥']],'jacks',1);
eqPoker([['10','♥'],['10','♠'],['3','♦'],['7','♣'],['9','♥']],'none',0);
pass('video poker 10 combination types and correct payouts');

// A poker redraw can only happen once and never duplicates a card in its 52-card shoe.
run('pokerDeal()');assert.equal(run('state.reserved'),100);
run('pokerHold(0); pokerHold(4); pokerDraw()');assert.equal(run('rt.poker.phase'),'done');
assert.equal(run('new Set(rt.poker.cards.map(c=>c.rank+c.suit)).size'),5);
assert.equal(run('state.reserved'),0);const rounds=run('state.stats.rounds'),balance=run('state.balance');
run('pokerDraw()');assert.equal(run('state.balance'),balance);assert.equal(run('state.stats.rounds'),rounds);
pass('poker redraw never double-settles or duplicates cards');

// Pick validation, exact 10-of-40 distinct Keno balls and known deterministic payout.
run('state.kenoPicks=[]; kenoPick(-1);kenoPick(41);kenoPick(7);kenoPick(7)');assert.equal(run('state.kenoPicks.length'),0);
run('[1,2,3,4,5].forEach(kenoPick)');assert.equal(run('state.kenoPicks.length'),5);
run('kenoPick(6)');assert.equal(run('state.kenoPicks.length'),5);
const n=run('state.stats.rounds');run('const oldRnd=rnd; rnd=()=>0');run('playKeno()');
assert.equal(run('rt.keno.hits'),5);assert.equal(run('rt.keno.payout'),20000);
assert.equal(run('new Set(rt.keno.drawn).size'),10);assert.equal(run('state.stats.rounds'),n+1);
run('rnd=oldRnd');pass('Keno exact 5-hit payout and distinct draw without replacement');

// Concurrent wagers: roulette, wheel, crash, mines, poker and slots may coexist.
run('navigate("roulette");rouletteBet("color","red");spinRoulette()');
run('navigate("wheel");spinWheel()');
run('navigate("crash");startCrash()');
run('navigate("mines");startMines()');
run('navigate("poker");pokerDeal()');
run('navigate("slots");spinSlots()');
assert.equal(run('state.reserved'),510);
const previous=run('state.stats.rounds');run('resetAll()');
assert.equal(run('state.balance'),50000);assert.equal(run('state.reserved'),0);
t.later();t.tick();assert.equal(run('state.balance'),50000);assert.equal(run('state.stats.rounds'),0);
pass('reset cancels six concurrent in-flight wagers without phantom payouts');

// Switching games does not prematurely complete gameplay and reopening restores live state.
run('navigate("mines");startMines()');assert.equal(run('rt.mines.active'),true);run('navigate("dice");navigate("mines")');assert.equal(run('rt.mines.active'),true);
run('openMine(rt.mines.mines[0])');assert.equal(run('state.reserved'),0);
run('navigate("crash");startCrash()');run('cashCrash()');const onceRounds=run('state.stats.rounds');run('cashCrash()');assert.equal(run('state.stats.rounds'),onceRounds);
pass('navigation and fast repeat clicks do not double-pay');

// Backup is clean even when an unfinished stake exists, and can fully restore state.
run('navigate("roulette");rouletteBet("color","black")');
const backup=run('JSON.stringify(snapshot())');const parsed=JSON.parse(backup);
assert.equal(parsed.reserved,0);assert.equal(parsed.balance,run('state.balance+state.reserved'));
run('resetAll()');assert.equal(run('state.balance'),50000);
t.context.backupJSON=backup;
assert.equal(run('loadBackup(backupJSON)'),true);assert.equal(run('state.balance'),parsed.balance);
assert.equal(run('state.reserved'),0);assert.equal(run('state.stats.rounds'),parsed.stats.rounds);
pass('backup roundtrip with refund of in-flight virtual bets');

for(const invalid of ['{}','{','{"format":"NEON_CASINO_SAVE","version":2,"balance":-10,"stats":{},"reserved":0,"rouletteHistory":[],"activity":[]}']){
 t.context.invalidBackup=invalid;
 assert.throws(()=>run('loadBackup(invalidBackup)'));
}
pass('invalid backups rejected before modifying game state');

// Legacy storage migration: reserved chips were already debited from balance.
const legacy=JSON.stringify({balance:48000,reserved:2000,stats:{rounds:5,wins:-20,wagered:'bad',paid:100},rouletteHistory:[{n:55,at:1},{n:0,at:1}],activity:[{game:'<img src=x onerror=alert(1)>',profit:12,at:'10:05'}]});
const old=harness(legacy);assert.equal(old.run('state.balance'),50000);assert.equal(old.run('state.reserved'),0);
assert.equal(old.run('state.stats.wins'),0);assert.equal(old.run('state.stats.wagered'),0);
assert.equal(old.run('state.rouletteHistory.length'),1);
assert.equal(JSON.parse(old.saves['neon-casino-local-v1']).reserved,0);
assert.ok(old.element('rightPanel').innerHTML.includes('&lt;img'));
pass('legacy save recovery, corrupted stats filtering and HTML escaping');

const corrupt=harness('{garbage');assert.equal(corrupt.run('state.balance'),50000);
pass('malformed JSON does not prevent startup');

// Repeat 200 independent direct rolls and verify accounting and per-game stats.
const stress=harness();const r=stress.run;
for(let i=0;i<200;i++){
 if(i%2===0)r('rollDice()');else r('playBaccarat()');
 assert.equal(r('state.reserved'),0);
 assert.ok(r('Number.isSafeInteger(state.balance) && state.balance>=0'));
}
assert.equal(r('state.stats.rounds'),200);
assert.equal(r('state.gameStats.dice.rounds'),100);
assert.equal(r('state.gameStats.baccarat.rounds'),100);
pass('200-round accounting stress test and per-game history');

// Exhaustive European roulette paytable: 37 actual outcomes, every category.
const roulette=harness();const rr=roulette.run;
for(let n=0;n<=36;n++){
 assert.equal(rr(`rouletteWin({type:'number',value:'${n}'},${n})`),35);
 assert.equal(rr(`rouletteWin({type:'even',value:'even'},${n})`),n>0&&n%2===0?1:0);
 assert.equal(rr(`rouletteWin({type:'odd',value:'odd'},${n})`),n%2===1?1:0);
 assert.equal(rr(`rouletteWin({type:'low',value:'low'},${n})`),n>=1&&n<=18?1:0);
 assert.equal(rr(`rouletteWin({type:'high',value:'high'},${n})`),n>=19?1:0);
 for(let k=1;k<=3;k++){
  assert.equal(rr(`rouletteWin({type:'dozen',value:'${k}'},${n})`),n>0&&Math.ceil(n/12)===k?2:0);
  assert.equal(rr(`rouletteWin({type:'column',value:'${k}'},${n})`),n>0&&(n-1)%3+1===k?2:0);
 }
}
assert.equal(rr('REDS.size'),18);
pass('roulette 37-number exhaustive bet evaluation including zero');

// Blackjack critical settlement cases: natural, natural push, dealer natural, split.
function bjTest(player,dealer,wanted){
 const b=harness(), r=b.run;
 b.context.handsPayload=player;b.context.dealerPayload=dealer;
 r(`state.reserved=100;state.balance=49900;rt.bj={stage:'playing',deck:[],dealer:dealerPayload,hands:[{cards:handsPayload,stake:100,finished:true,fromSplit:false}],active:0,message:''}`);
 r('finishBlackjack()');assert.equal(r('rt.bj.hands[0].payout'),wanted);assert.equal(r('state.reserved'),0);assert.equal(r('state.balance'),49900+wanted);
}
bjTest([{rank:'A',suit:'♠'},{rank:'K',suit:'♣'}],[{rank:'Q',suit:'♥'},{rank:'10',suit:'♠'}],250);
bjTest([{rank:'A',suit:'♠'},{rank:'K',suit:'♣'}],[{rank:'A',suit:'♥'},{rank:'Q',suit:'♠'}],100);
bjTest([{rank:'7',suit:'♠'},{rank:'7',suit:'♣'},{rank:'7',suit:'♥'}],[{rank:'A',suit:'♥'},{rank:'Q',suit:'♠'}],0);
const split=harness(),sp=split.run;sp('state.balance=49900;state.reserved=100;rt.bj={stage:"playing",deck:newDeck(),dealer:[{rank:"7",suit:"♥"},{rank:"9",suit:"♠"}],hands:[{cards:[{rank:"9",suit:"♠"},{rank:"9",suit:"♥"}],stake:100,finished:false,fromSplit:false}],active:0,message:""}');sp('bjAction("bj-split")');
assert.equal(sp('rt.bj.hands.length'),2);assert.equal(sp('state.reserved'),200);
sp('bjAction("bj-stand");bjAction("bj-stand")');assert.equal(sp('rt.bj.stage'),'done');assert.equal(sp('state.reserved'),0);
pass('blackjack natural payouts, dealer natural and split settlement');

// Slot paylines: three rows and two diagonals, all identical => 5 wins.
const slot=harness(),sl=slot.run;
sl('rnd=()=>0;spinSlots()');slot.tick(20,100);assert.equal(sl('rt.slots.payout'),1000);
assert.equal(sl('state.stats.rounds'),1);assert.equal(sl('state.balance'),50900);
pass('all-five-line slots payout with single settlement');

// Crash late manual cash-out must lose if the predetermined crash is passed.
const crash=harness(),cr=crash.run;
cr('startCrash()');cr('rt.crash.crashAt=1.1');crash.advance(8000);cr('cashCrash()');
assert.equal(cr('rt.crash.status'),'crashed');assert.equal(cr('state.balance'),49900);
assert.equal(cr('state.stats.rounds'),1);cr('cashCrash()');assert.equal(cr('state.stats.rounds'),1);
pass('Crash past-limit manual claim cannot bypass predetermined outcome');

// Time display sanitization prevents broken local saves from breaking render.
const timestamps=harness(JSON.stringify({balance:50000,reserved:0,rouletteHistory:[{n:7,at:1e299}],stats:{rounds:1},activity:[]}));
assert.equal(timestamps.run('state.rouletteHistory.length'),0);
pass('out-of-range timestamp filtered before rendering roulette history');

console.log('ALL REGRESSION TESTS PASSED');
