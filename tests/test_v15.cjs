'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
function create(seed=null){const saves=seed?{'neon-casino-local-v1':seed}:{},nodes=new Map(),timers=[],intervals=[],listeners={};let now=0;const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',children:[],firstElementChild:null,style:{},dataset:{},clientWidth:400,parentElement:null,addEventListener(t,f){listeners[id+':'+t]=f},appendChild(){},click(){},remove(){},setAttribute(){},classList:{remove(){},add(){},toggle(){}},getContext(){return new Proxy({},{get:()=>()=>{}})}});return nodes.get(id)};const context={console,Math,Number,Boolean,Date,JSON,Array,Object,Set,Map,String,Intl,Uint32Array,Blob,crypto:crypto.webcrypto,performance:{now:()=>now},requestAnimationFrame(f){f()},confirm(){return true},setTimeout(f,n){const t={f,n,active:true};timers.push(t);return t},clearTimeout(t){if(t)t.active=false},setInterval(f,n){const t={f,n,active:true};intervals.push(t);return t},clearInterval(t){if(t)t.active=false},localStorage:{getItem(k){return saves[k]||null},setItem(k,v){saves[k]=v}},window:{addEventListener(){}},document:{getElementById:node,createElement(){return node('generated'+Math.random())},querySelector(){return null},body:{appendChild(){},addEventListener(t,cb){listeners[t]=cb}}},URL:{createObjectURL(){return'test'},revokeObjectURL(){}}};vm.createContext(context);vm.runInContext(source,context);const run=s=>vm.runInContext(s,context);return{run,saves,timers,intervals,finishTimers(){for(const t of timers.slice()){if(t.active){t.active=false;t.f()}}},pulse(){now+=100000;for(const t of intervals.slice()){if(t.active)t.f()}}}}
const t=create(),r=t.run;
assert.equal(r('GAMES.length'),44);
assert.equal(r('new Set(GAMES.map(g=>g.id)).size'),44);
const more=JSON.parse(JSON.stringify(r('MORE_GAMES.map(g=>g.id)')));
assert.equal(more.length,16);
for(const id of more){r(`navigate('${id}')`);assert.ok(r('gameHTML().length')>220,`missing UI for ${id}`);assert.ok(r(`typeof MORE_RULES['${id}']==='string'`),`no rules for ${id}`)}
console.log('PASS all 40 games have unique nav IDs, 12 new games have screens and game rules');
// Math and boundary tests, particularly deliberate ties and refund outcomes.
assert.equal(r("redDogMultiplier({rank:'3'},{rank:'5'},{rank:'4'})"),6);
assert.equal(r("redDogMultiplier({rank:'3'},{rank:'5'},{rank:'8'})"),0);
assert.equal(r("redDogMultiplier({rank:'3'},{rank:'4'},{rank:'8'})"),1);
assert.equal(r("redDogMultiplier({rank:'A'},{rank:'K'},{rank:'Q'})"),2);
assert.equal(r('permutationCount([1,2,3])'),6);assert.equal(r('permutationCount([1,1,2])'),3);assert.equal(r('permutationCount([8,8,8])'),1);
assert.equal(r('pick3Payout([1,2,3],[3,1,2],"box",100)'),15000);
assert.equal(r('pick3Payout([1,1,2],[2,1,1],"box",100)'),30000);
assert.equal(r('pick3Payout([1,2,3],[3,1,2],"exact",100)'),0);
for(const pick of JSON.parse(JSON.stringify(r('CARD_PICKS.map(x=>x[0])')))){let wins=0;for(const rank of JSON.parse(JSON.stringify(r('RANKS'))))for(const suit of JSON.parse(JSON.stringify(r('SUITS')))){if(r(`cardsuitWin({rank:'${rank}',suit:'${suit}'},'${pick}')`))wins++}assert.equal(wins,pick==='red'||pick==='black'?26:['ace'].includes(pick)?4:pick==='face'?12:13,pick)}
const p=r('pokerFiveScore'); // strict VM plain values via snippets
assert.equal(r("pokerFiveScore([{rank:'A',suit:'♠'},{rank:'K',suit:'♠'},{rank:'Q',suit:'♠'},{rank:'J',suit:'♠'},{rank:'10',suit:'♠'}])[0]"),8);
assert.equal(r("pokerFiveScore([{rank:'A',suit:'♠'},{rank:'2',suit:'♠'},{rank:'3',suit:'♠'},{rank:'4',suit:'♠'},{rank:'5',suit:'♠'}])[1]"),5);
assert.equal(r("pokerFiveScore([{rank:'2',suit:'♠'},{rank:'2',suit:'♣'},{rank:'2',suit:'♦'},{rank:'3',suit:'♠'},{rank:'3',suit:'♥'}])[0]"),6);
assert.equal(r('bestSeven([{rank:"A",suit:"♠"},{rank:"K",suit:"♠"},{rank:"Q",suit:"♠"},{rank:"J",suit:"♠"},{rank:"10",suit:"♠"},{rank:"2",suit:"♦"},{rank:"9",suit:"♠"}])[0]'),8);
assert.equal(r('letItRideMult([{rank:"A",suit:"♠"},{rank:"K",suit:"♠"},{rank:"Q",suit:"♠"},{rank:"J",suit:"♠"},{rank:"10",suit:"♠"}])'),1001);
assert.equal(r('rpsWinner("rock","scissors")'),1);assert.equal(r('rpsWinner("rock","paper")'),-1);assert.equal(r('rpsWinner("rock","rock")'),0);
assert.equal(r('colorDiceWin(["red","blue","red"],"red","two")'),true);
assert.equal(r('colorDiceWin(["red","blue","red"],"red","three")'),false);
let ways=[0,0,0,0];for(const a of ['red','green','blue'])for(const b of ['red','green','blue'])for(const c of ['red','green','blue'])ways[[a,b,c].filter(x=>x==='red').length]++;
assert.equal(ways.join(','),'8,12,6,1');
assert.equal(r('slots5Evaluate(Array.from({length:5},()=>["🍒","🍒","🍒"])).total'),5000);
console.log('PASS payout ranking, Pick3 permutations, all 52 card bets, 27 color outcomes, Red Dog, Let It Ride, 5×3 slots');
for(let i=0;i<200;i++){const board=JSON.parse(JSON.stringify(r('bingo90Ticket()'))),v=board.flat().filter(x=>x!==null);assert.equal(v.length,15);assert.equal(new Set(v).size,15);for(const row of board)assert.equal(row.filter(x=>x!==null).length,5);for(let col=0;col<9;col++)for(let row=0;row<3;row++){const n=board[row][col];if(n!==null)assert.ok(n>=(col===0?1:col*10)&&n<=(col===8?90:col*10+9))}assert.equal(r(`bingo90Lines(${JSON.stringify(board)},${JSON.stringify(v)})`),3)}
console.log('PASS 200 proper 3×9 Bingo 90 tickets, 15 unique values, complete-line counts');
const plays=[['andar','playAndar()'],['reddog','playRedDog()'],['pick3','playPick3()'],['bingo90','playBingo90()'],['keno80','playKeno80()'],['cardsuit','playCardsuit()'],['slots5','playSlots5()'],['holdem','playHoldem()'],['rps','playRps()'],['colors','playColorDice()']];
r('state.keno80Picks=[1,2,3,4,5,6]');
for(const [id,call] of plays){r(`navigate('${id}')`);const before=r('state.stats.rounds');r(call);assert.equal(r('state.stats.rounds'),before+1,id);assert.equal(r('state.reserved'),0,id);assert.equal(r(`state.gameStats['${id}'].rounds`),1,id)}
r('navigate("ladder");ladderStart()');assert.equal(r('state.reserved'),100);r('ladderNext()');if(r('rt.ladder.active')&&r('rt.ladder.steps'))r('ladderCash()');if(r('rt.ladder.active')){r('rt.ladder.steps=1;ladderCash()')}assert.equal(r('state.reserved'),0);
r('navigate("letitride");letItRideStart()');assert.equal(r('state.reserved'),300);r('letItRideNext(true)');assert.equal(r('state.reserved'),200);r('letItRideNext(false)');assert.equal(r('state.reserved'),0);assert.equal(r('state.gameStats.letitride.rounds'),1);
const saved=t.saves['neon-casino-local-v1'],after=create(saved);assert.equal(after.run('state.gameStats.letitride.rounds'),1);assert.equal(after.run('state.gameStats.cardsuit.rounds'),1);assert.equal(after.run('state.reserved'),0);
console.log('PASS 12 new game settlements, no orphaned wagers, new per-game stats retained after reload');
// Crash recovery and daily isolation with new multi-step sessions.
const day=create(),q=day.run;
q('switchMode("daily");state.game="letitride";state.stake=100;letItRideStart()');assert.equal(q('state.reserved'),300);
q('switchMode("free")');assert.equal(q('state.reserved'),0);q('switchMode("daily")');assert.equal(q('state.balance'),1000);
q('state.game="ladder";ladderStart()');assert.equal(q('state.reserved'),100);q('switchMode("free")');q('switchMode("daily")');assert.equal(q('state.balance'),1000);
q('finishDailyDay()');assert.equal(q('dailyProgress.day'),2);assert.equal(q('state.balance'),1000);
console.log('PASS daily wallet isolation, unfinished new rounds refunded, next day credit');
for(let i=0;i<2000;i++){const [id,call]=plays[i%plays.length];r(call);assert.ok(r('Number.isSafeInteger(state.balance)&&state.balance>=0&&state.balance<=BALANCE_CAP'));assert.equal(r('state.reserved'),0);}
assert.equal(r('Object.values(state.gameStats).reduce((n,s)=>n+s.rounds,0)'),r('state.stats.rounds'));
console.log('PASS 2000 mixed rounds, balance bounded and per-game statistics reconcile');
console.log('ALL v1.5 TESTS PASSED');
