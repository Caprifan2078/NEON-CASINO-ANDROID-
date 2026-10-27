'use strict';
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const source=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
function create(seed=null){const saves=seed?{'neon-casino-local-v1':seed}:{},nodes=new Map(),timers=[],intervals=[];const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',children:[],firstElementChild:null,style:{},dataset:{},addEventListener(){},appendChild(){},click(){},remove(){},setAttribute(){},classList:{remove(){},add(){},toggle(){}},getContext(){return new Proxy({},{get:()=>()=>{}})}});return nodes.get(id)};const context={console,Math,Number,Boolean,Date,JSON,Array,Object,Set,Map,String,Intl,Uint32Array,Blob,crypto:crypto.webcrypto,performance:{now:()=>0},requestAnimationFrame(f){f()},confirm(){return true},setTimeout(f,n){timers.push({f,n});return{}},clearTimeout(){},setInterval(f,n){intervals.push({f,n});return{}},clearInterval(){},localStorage:{getItem(k){return saves[k]||null},setItem(k,v){saves[k]=v}},window:{addEventListener(){}},document:{getElementById:node,createElement(){return node('tmp')},querySelector(){return null},body:{appendChild(){},addEventListener(){}}},URL:{createObjectURL(){return'test'},revokeObjectURL(){}}};vm.createContext(context);vm.runInContext(source,context);return{r:s=>vm.runInContext(s,context),saves}}
const t=create(),r=t.r;
assert.equal(r('GAMES.length'),44);assert.equal(r('new Set(GAMES.map(g=>g.id)).size'),44);
for(const id of ['caribbean','teenpatti','fantan','crown']){r(`navigate('${id}')`);assert.ok(r('gameHTML().length')>500);assert.ok(r(`typeof MORE_RULES['${id}']==='string'`));}
console.log('PASS 44 unique games, all 4 new screens and instructions');
// Fan Tan (4 equally probable results) all 16 bet definitions, payouts and pushes.
assert.equal(r('FAN_BETS.length'),16);
for(const bet of JSON.parse(JSON.stringify(r('FAN_BETS.map(x=>x[0])')))){let average=0;for(let result=1;result<=4;result++){const p=r(`fanPayment('${bet}',${result},10000)`);assert.ok(Number.isInteger(p)&&p>=0);average+=p/4;}assert.ok(average>=9600&&average<=9900,`unexpected RTP ${bet}: ${average}`)}
assert.equal(r('fanPayment("nim:1:2",2,100)'),100);assert.equal(r('fanPayment("fan:2",2,100)'),385);
console.log('PASS Fan Tan 16 wagers, all outcomes, 4 payout families & pushes');
// 3 dice and 6 symbols, exhaustive 6**3 == 216 combinations.
let ways=[0,0,0,0];for(let a=0;a<6;a++)for(let b=0;b<6;b++)for(let c=0;c<6;c++){const n=[a,b,c].filter(x=>x===0).length;ways[n]++;assert.equal(r(`crownPayment([${a},${b},${c}],0,100)`),n?100*(n+1):0)}
assert.equal(ways.join(','),'125,75,15,1');console.log('PASS Crown & Anchor 216 dice outcomes and all prize levels');
// Poker rankings: dealer qualifies Ace-King, not A-Q high.
const A=(rank,suit)=>({rank,suit});
const p1=[A('A','♠'),A('K','♥'),A('Q','♦'),A('9','♣'),A('2','♥')];
const p2=[A('A','♠'),A('Q','♥'),A('J','♦'),A('9','♣'),A('2','♥')];
assert.equal(r(`qualifiedCaribbean(${JSON.stringify(p1)})`),true);assert.equal(r(`qualifiedCaribbean(${JSON.stringify(p2)})`),false);
assert.equal(r(`caribbeanPayment(100,${JSON.stringify(p1)},${JSON.stringify(p2)}).payout`),400);
assert.equal(r(`caribbeanCallOdds(${JSON.stringify([A('A','♠'),A('K','♠'),A('Q','♠'),A('J','♠'),A('10','♠')])})`),100);
console.log('PASS Caribbean Stud dealer qualification, nonqualification push, royal-flush Call table');
const royal=[A('A','♠'),A('K','♠'),A('Q','♠')],straight=[A('5','♠'),A('4','♥'),A('3','♣')],flush=[A('K','♠'),A('8','♠'),A('2','♠')],lowStraight=[A('A','♦'),A('2','♣'),A('3','♥')],triple=[A('K','♠'),A('K','♣'),A('K','♥')];
assert.equal(r(`teenScore(${JSON.stringify(royal)})[0]`),7);
assert.equal(r(`teenScore(${JSON.stringify(triple)})[0]`),6);
assert.equal(r(`teenScore(${JSON.stringify(straight)})[0]`),4);
assert.equal(r(`teenScore(${JSON.stringify(flush)})[0]`),3);
assert.equal(r(`teenScore(${JSON.stringify(lowStraight)})[1]`),3);
assert.equal(r(`teenPairPlusProfit(teenScore(${JSON.stringify(royal)}))`),100);
const noQual=[A('J','♣'),A('8','♣'),A('5','♥')];
assert.equal(r(`teenPayment(100,${JSON.stringify(straight)},${JSON.stringify(noQual)},false).payout`),400); // Ante 200, Play 100, straight bonus 100
console.log('PASS Teen Patti rank order, low Ace straight, Pair Plus and Ante bonus');
// Full user click handlers, no double settlement on completed rounds.
const plays=[['fantan','fanPlay()'],['crown','crownPlay()']];
for(let i=0;i<400;i++){const [game,action]=plays[i%2];r(action);assert.equal(r('state.reserved'),0,game);assert.ok(r('Number.isSafeInteger(state.balance)&&state.balance>=0&&state.balance<=BALANCE_CAP'))}
for(const game of ['caribbean','teenpatti']){
 r(`navigate('${game}')`);r('state.stake=100');r(game==='caribbean'?'caribbeanStart()':'teenStart()');assert.equal(r('state.reserved'),100);
 r(game==='caribbean'?'caribbeanFinish(true)':'teenFinish(true)');const rounds=r('state.stats.rounds');
 r(game==='caribbean'?'caribbeanFinish(true)':'teenFinish(true)');assert.equal(r('state.stats.rounds'),rounds);assert.equal(r('state.reserved'),0);
}
console.log('PASS new games: 400 rounds, multi-stage Call/Play, no double settlements');
r('navigate("caribbean");caribbeanStart()');assert.equal(r('state.reserved'),100);
const reopened=create(t.saves['neon-casino-local-v1']);assert.equal(reopened.r('state.reserved'),0);assert.equal(reopened.r('state.balance'),t.r('state.balance')+100);assert.equal(reopened.r('state.gameStats.caribbean.rounds'),1);
console.log('PASS reload refunds interrupted stakes exactly once; per-game stats persist');
const day=create(),d=day.r;
d('switchMode("daily");state.game="teenpatti";state.stake=100;teenStart()');assert.equal(d('state.reserved'),100);
d('switchMode("free")');d('switchMode("daily")');assert.equal(d('state.balance'),1000);
d('finishDailyDay()');assert.equal(d('dailyProgress.day'),2);assert.equal(d('state.balance'),1000);
console.log('PASS daily mode remains isolated and cannot top-up from free wallet');
console.log('ALL NEON ROYALE v1.7 REGRESSION TESTS PASSED');
