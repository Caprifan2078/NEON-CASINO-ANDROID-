'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const src=fs.readFileSync(require('node:path').join(__dirname,'../web/app.js'),'utf8');
const elements=new Map(),tasks=[],intervals=[],stored={};let clock=0;
function el(id){if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',value:'',className:'',style:{},classList:{add(){},remove(){},toggle(){}},appendChild(){},remove(){},parentElement:null,clientWidth:500,setAttribute(){},addEventListener(){},getContext(){return new Proxy({}, {get(){return ()=>{}}})}});return elements.get(id)}
const ctx={console,Math,JSON,Number,Date,Array,Set,Map,Object,String,Intl,crypto:crypto.webcrypto,performance:{now:()=>clock},requestAnimationFrame(fn){fn()},setTimeout(fn,delay){tasks.push({fn,delay});return tasks.length},clearTimeout(){},setInterval(fn,delay){const a={fn,delay,active:true};intervals.push(a);return a},clearInterval(a){if(a)a.active=false},document:{getElementById:el,querySelector(){return null},createElement(){return el('temp'+Math.random())},body:{addEventListener(){},appendChild(){}}},window:{addEventListener(){}},navigator:{},localStorage:{getItem(k){return stored[k]||null},setItem(k,v){stored[k]=v},removeItem(k){delete stored[k]}},confirm(){return true}};
vm.createContext(ctx);vm.runInContext(src,ctx,{filename:'app.js'});
function run(js){return vm.runInContext(js,ctx)}
function flushTimers(min=0){let i=0;while(i<tasks.length){let t=tasks.splice(i,1)[0];if(t.delay>=min)t.fn()} }
function tickIntervals(times=25,step=100){for(let i=0;i<times;i++){clock+=step;for(let v of intervals.slice())if(v.active)v.fn()}}
function stat(){return run('({...state.stats})')}
function finishCheck(label,roundStart){assert.equal(run('state.reserved'),0,`${label}: reserved chips must clear`);assert.ok(stat().rounds>=roundStart+1,`${label}: round counted`);console.log('PASS',label,'balance=',run('state.balance'))}
assert.equal(run('GAMES.length'),44);
assert.equal(run('RNUM.length'),37);
assert.equal(run('new Set(RNUM).size'),37);
assert.equal(run('rouletteWin({type:"number",value:"17"},17)'),35);
assert.equal(run('rouletteWin({type:"number",value:"17"},16)'),0);
assert.equal(run('rouletteWin({type:"even",value:"even"},0)'),0);
assert.equal(run('rouletteWin({type:"column",value:"2"},2)'),2);
assert.equal(run('rouletteWin({type:"column",value:"2"},1)'),0);
run('rouletteBet("number","17")');assert.equal(run('state.reserved'),100);assert.equal(run('rt.bets.length'),1);
run('refund(rt.bets.pop().amount)');assert.equal(run('state.reserved'),0);assert.equal(run('state.balance'),50000);
run('rouletteBet("color","red")');let n=stat().rounds;run('spinRoulette()');flushTimers(4000);finishCheck('roulette',n);assert.equal(run('state.rouletteHistory.length'),1);
run('navigate("blackjack")');n=stat().rounds;run('dealBlackjack()');for(let i=0;i<4&&run('rt.bj.stage')==='playing';i++)run('bjAction("bj-stand")');finishCheck('blackjack',n);assert.equal(run('rt.bj.stage'),'done');
run('navigate("wheel")');n=stat().rounds;run('spinWheel()');flushTimers(4000);finishCheck('wheel',n);
run('navigate("crash")');n=stat().rounds;run('startCrash()');clock+=60;run('cashCrash()');finishCheck('crash',n);
run('navigate("slots")');n=stat().rounds;run('spinSlots()');tickIntervals(19,100);finishCheck('slots',n);
run('navigate("mines")');n=stat().rounds;run('startMines()');run('openMine(Array.from({length:25},(_,i)=>i).find(i=>!rt.mines.mines.includes(i)))');run('cashMines()');finishCheck('mines',n);
run('navigate("plinko")');n=stat().rounds;run('dropPlinko()');tickIntervals(25,100);finishCheck('plinko',n);
run('navigate("dice")');n=stat().rounds;run('rollDice()');finishCheck('dice',n);
run('navigate("baccarat")');n=stat().rounds;run('playBaccarat()');finishCheck('baccarat',n);
run('navigate("coin")');n=stat().rounds;run('flipCoin()');flushTimers(1000);finishCheck('coin',n);
run('navigate("keno")');n=stat().rounds;run('[3,9,17,26,34].forEach(kenoPick)');run('playKeno()');finishCheck('keno',n);
run('navigate("poker")');n=stat().rounds;run('pokerDeal()');run('pokerHold(0)');run('pokerDraw()');finishCheck('poker',n);
for(const g of ['roulette','blackjack','wheel','crash','slots','mines','plinko','dice','baccarat','coin','keno','poker']){run(`navigate('${g}')`);assert.ok(el('gameArea').innerHTML.length>300,`${g} has render`)}
console.log('ALL 12 GAME LOGIC TESTS PASSED; played',stat().rounds,'rounds.');
// Check that an in-flight roulette spin cannot write an old payout after reset.
run('navigate("roulette")');run('rouletteBet("number","5")');run('spinRoulette()');run('resetAll()');flushTimers(4000);
assert.equal(run('state.balance'),50000);assert.equal(run('state.reserved'),0);
assert.equal(run('state.rouletteHistory.length'),0);assert.equal(run('state.stats.rounds'),0);
console.log('PASS interrupted-round reset: no ghost credit or old history');
