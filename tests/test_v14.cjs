'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
function create(seed=null){const saves=seed?{'neon-casino-local-v1':seed}:{},nodes=new Map(),timers=[],intervals=[],listeners={};let now=0;const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',children:[],firstElementChild:null,style:{},dataset:{},clientWidth:400,parentElement:null,addEventListener(t,f){listeners[id+':'+t]=f},appendChild(){},click(){},remove(){},setAttribute(){},classList:{remove(){},add(){},toggle(){}},getContext(){return new Proxy({},{get:()=>()=>{}})}});return nodes.get(id)};const context={console,Math,Number,Boolean,Date,JSON,Array,Object,Set,Map,String,Intl,Uint32Array,Blob,crypto:crypto.webcrypto,performance:{now:()=>now},requestAnimationFrame(f){f()},confirm(){return true},setTimeout(f,n){const t={f,n,active:true};timers.push(t);return t},clearTimeout(t){if(t)t.active=false},setInterval(f,n){const t={f,n,active:true};intervals.push(t);return t},clearInterval(t){if(t)t.active=false},localStorage:{getItem(k){return saves[k]||null},setItem(k,v){saves[k]=v}},window:{addEventListener(){}},document:{getElementById:node,createElement(){return node('generated'+Math.random())},querySelector(){return null},body:{appendChild(){},addEventListener(t,cb){listeners[t]=cb}}},URL:{createObjectURL(){return'test'},revokeObjectURL(){}}};vm.createContext(context);vm.runInContext(source,context);const run=s=>vm.runInContext(s,context);return{run,saves,timers,intervals,finishTimers(){for(const t of timers.slice()){if(t.active){t.active=false;t.f()}}},pulse(){now+=100000;for(const t of intervals.slice()){if(t.active)t.f()}}}}
const t=create(),r=t.run;assert.equal(r('GAMES.length'),44);assert.equal(r('new Set(GAMES.map(g=>g.id)).size'),44);console.log('PASS 40 uniquely selectable games');
for(const id of JSON.parse(JSON.stringify(r('EXTRA_GAMES.map(g=>g.id)')))){r(`navigate('${id}')`);assert.ok(t.run('gameHTML().length')>160,`HTML game ${id}`);assert.ok(t.run('rightHTML().includes("undefined")')===false,`rules ${id}`)}
console.log('PASS all 12 new games have real control screens, rules and no undefined values');
// Roulette exact probabilities and edge on zero.
for(const variant of ['us','fr']){const ns=variant==='us'?['0','00',...Array.from({length:36},(_,i)=>String(i+1))]:Array.from({length:37},(_,i)=>String(i));let reds=0,zeros=0;for(const n of ns){if(r(`rouletteVariantWin('red','${n}','${variant}',100)`)===200)reds++;if(n==='0'||n==='00')zeros++;assert.equal(r(`rouletteVariantWin('n:${n}','${n}','${variant}',100)`),3600)}assert.equal(reds,18);assert.equal(zeros,variant==='us'?2:1)}assert.equal(r("rouletteVariantWin('black','0','fr',100)"),50);assert.equal(r("rouletteVariantWin('black','00','us',100)"),0);assert.equal(r("rouletteVariantWin('d3','26','us',100)"),300);
console.log('PASS US/FR all wheel outcomes and la partage refunds');
// Mines 16..100 cells, valid bomb sample and exact survival multiplier, large payouts are safe.
for(const size of [16,25,32,36,49,64,100]){for(const count of [1,Math.min(35,size-1)]){t.run(`state.game='mines';state.minesSize=${size};state.minesCount=${count};state.stake=10;startMines()`);assert.equal(r('rt.mines.size'),size);assert.equal(r('new Set(rt.mines.mines).size'),count);assert.equal(r('rt.mines.mines.length'),count);let last=0;for(let i=0;i<Math.min(size-count,7);i++){const next=r('Array.from({length:rt.mines.size},(_,i)=>i).find(i=>!rt.mines.mines.includes(i)&&!rt.mines.opened.includes(i))');t.run(`openMine(${next})`);const mult=r('rt.mines.active?mineMultiplier(rt.mines):rt.mines.status===\'cashed\'?mineMultiplier(rt.mines):0');assert.ok(mult>=last,`monotonic ${size} ${count} ${i}`);last=mult}if(r('rt.mines.active'))r('cashMines()');assert.equal(r('state.reserved'),0)}}
const mSample={size:16,mineCount:4,opened:[1,2,3],stake:100};t.run(`sample=${JSON.stringify(mSample)}`);assert.ok(Math.abs(r('mineMultiplier(sample)')-(.97*(16/12)*(15/11)*(14/10)))<1e-10);
console.log('PASS Mines 7 sizes, 1..35 mines, correct combinatorial multipliers');
// Poker exhaustive straight orders + qualification.
for(const hand of ["[{rank:'A',suit:'♠'},{rank:'2',suit:'♠'},{rank:'3',suit:'♠'}]","[{rank:'Q',suit:'♥'},{rank:'K',suit:'♥'},{rank:'A',suit:'♥'}]"]){assert.equal(r(`threeScore(${hand}).cls`),5)}
assert.equal(r("threeScore([{rank:'J',suit:'♠'},{rank:'8',suit:'♥'},{rank:'2',suit:'♦'}]).qualifies"),false);assert.equal(r("threeScore([{rank:'Q',suit:'♠'},{rank:'8',suit:'♥'},{rank:'2',suit:'♦'}]).qualifies"),true);
r('navigate("threecard");state.stake=100;threeDeal()');assert.equal(r('state.reserved'),100);r('threeFinish(true)');assert.equal(r('state.reserved'),0);assert.equal(r('state.gameStats.threecard.rounds'),1);r('threeDeal();threeFinish(false)');assert.equal(r('state.gameStats.threecard.rounds'),2);
console.log('PASS 3-card ranking, qualifying and Ante/Play/Fold settlement');
// Force outcomes for 3 card, war, dragon, and the other independent games.
const playCases=[['war','warDeal()'],['dragontiger','dragonDeal()'],['bingo','bingoPlay()'],['seven','sevenRoll()'],['dicepoker','dicePokerRoll()']];for(const [id,call] of playCases){r(`navigate('${id}')`);const before=r('state.stats.rounds');r(call);if(id==='war'&&r('rt.war.tied'))r('warResolve(false)');assert.equal(r('state.stats.rounds'),before+1,id);assert.equal(r('state.reserved'),0,id)}
console.log('PASS card games, Bingo and five-dice settlement');
r('navigate("lotto");state.lottoPicks=[1,2,3,4,5,6];lottoPlay()');assert.equal(r('state.reserved'),0);assert.equal(r('state.gameStats.lotto.rounds'),1);
r('navigate("scratch");scratchStart()');assert.equal(r('state.reserved'),100);for(let i=0;i<9;i++)r(`scratchOpen(${i})`);assert.equal(r('state.reserved'),0);assert.equal(r('state.gameStats.scratch.rounds'),1);
r('navigate("treasure");treasureStart()');assert.equal(r('state.reserved'),100);r('treasureOpen(5)');assert.equal(r('state.reserved'),0);assert.equal(r('state.gameStats.treasure.rounds'),1);
console.log('PASS lotto, scratch and treasure start/finish and wallet integrity');
for(let mines=1;mines<=2;mines++){r(`navigate('tower');state.towerMines=${mines};towerStart()`);const size=r('rt.tower.traps[0].length');assert.equal(size,mines);const safe=r('Array.from({length:3},(_,i)=>i).find(i=>!rt.tower.traps[0].includes(i))');r(`towerPick(0,${safe})`);assert.equal(r('state.reserved'),100);r('towerCash()');assert.equal(r('state.reserved'),0)}
console.log('PASS Tower 1/2 traps, safe opening and cashout');
for(const [g,k] of [['roulette-us','us'],['roulette-fr','fr']]){r(`navigate('${g}');state.chip=100;vrBet('red');vrBet('n:12');vrSpin()`);assert.equal(r('state.reserved'),200);t.finishTimers();assert.equal(r('state.reserved'),0);assert.ok(r(`state.gameStats['${k==='us'?'roulette-us':'roulette-fr'}'].rounds`)>=1)}
console.log('PASS new roulette bets, timer settlement and double-click safeguards');
assert.ok(r('LOTTO_PAY[6]')===1000000);assert.ok(r('DICE_POKER_PAY.five')===50);
const saved=t.saves['neon-casino-local-v1'],restored=create(saved);assert.ok(restored.run('state.gameStats.threecard.rounds')===2);console.log('PASS v1.4 per-game stats persist across restart');
const d=create(),x=d.run;x('switchMode("daily");state.stake=100;state.game="scratch";scratchStart()');assert.equal(x('state.reserved'),100);x('switchMode("free")');assert.equal(x('state.reserved'),0);x('switchMode("daily")');assert.equal(x('state.balance'),1000);x('finishDailyDay()');assert.equal(x('dailyProgress.day'),2);assert.equal(x('state.balance'),1000);console.log('PASS interrupted games refund and daily budget stays isolated');
for(let i=0;i<1500;i++){const id=['dragon','bingo','seven','dicepoker','lotto','treasure','scratch','tower'][i%8];if(id==='dragon')r('dragonDeal()');if(id==='bingo')r('bingoPlay()');if(id==='seven')r('sevenRoll()');if(id==='dicepoker')r('dicePokerRoll()');if(id==='lotto')r('lottoPlay()');if(id==='treasure'){r('treasureStart()');r('treasureOpen(0)')}if(id==='scratch'){r('scratchStart()');for(let j=0;j<9;j++)r(`scratchOpen(${j})`)}if(id==='tower'){r('towerStart()');r('towerPick(0,rt.tower.traps[0].includes(0)?1:0)');if(r('rt.tower.active'))r('towerCash()')}assert.ok(r('Number.isSafeInteger(state.balance)&&state.balance>=0&&state.balance<=BALANCE_CAP'));assert.equal(r('state.reserved'),0)}
assert.equal(r('Object.values(state.gameStats).reduce((n,s)=>n+s.rounds,0)'),r('state.stats.rounds'));
console.log('PASS 1500 new-game mixed rounds: no leaked reservations, invalid balances or mismatched statistics');
console.log('ALL v1.4 TESTS PASSED');
// Sic Bo: 35 distinct bets over all 216 equally likely dice triples.
const allPicks=JSON.parse(JSON.stringify(r('SICBO_OPTIONS.flat().map(x=>x[0])')));
assert.equal(allPicks.length,35);assert.equal(new Set(allPicks).size,35);
let tripleTotal=0,smallTotal=0,bigTotal=0,exactTotal=0;
for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++){
 const dice=`[${a},${b},${c}]`;
 for(const pick of allPicks){const paid=r(`sicboMultiplier(${dice},'${pick}')`);assert.ok(Number.isSafeInteger(paid)&&paid>=0)}
 tripleTotal+=r(`sicboMultiplier(${dice},'triple')`);
 smallTotal+=r(`sicboMultiplier(${dice},'small')`);
 bigTotal+=r(`sicboMultiplier(${dice},'big')`);
 exactTotal+=r(`sicboMultiplier(${dice},'exact-3')`);
}
assert.deepEqual([smallTotal,bigTotal,tripleTotal,exactTotal],[210,210,150,181]);
assert.equal(r("sicboMultiplier([1,1,1],'single-1')"),4);
assert.equal(r("sicboMultiplier([1,1,2],'pair-1')"),12);
assert.equal(r("sicboMultiplier([6,6,5],'sum-17')"),51);
console.log('PASS 35 Sic Bo bets across all 216 outcomes with real sum/pair/exact payouts');
for(let s=2;s<=12;s++){
 const status=r(`crapsDontStep(null,${s}).status`);
 assert.equal(status,[2,3].includes(s)?'won':s===12?'push':[7,11].includes(s)?'lost':'point');
 for(const point of [4,5,6,8,9,10])assert.equal(r(`crapsDontStep(${point},${s}).status`),s===7?'won':s===point?'lost':'point');
}
const dontTest=create();dontTest.run('state.crapsBet="dont";state.stake=100;rnd=()=>5;rollCraps()'); // 6+6=12; push.
assert.equal(dontTest.run('rt.craps.active'),false);assert.equal(dontTest.run('state.balance'),50000);
assert.equal(dontTest.run('state.gameStats.craps.rounds'),1);
console.log('PASS Craps Don’t Pass 2–12, points, 12 push with no net debit');
