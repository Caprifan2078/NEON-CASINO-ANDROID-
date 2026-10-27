'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
const KEY='neon-casino-local-v1',LEASE='neon-casino-active-instance-v1';
function create(store,options={}){
 const elem=new Map(),events={};
 const node=id=>{if(!elem.has(id))elem.set(id,{innerHTML:'',textContent:'',value:'',style:{},dataset:{},children:[],addEventListener(){},appendChild(){},remove(){},setAttribute(){},classList:{toggle(){},add(){},remove(){},contains(){return false}},getContext(){return new Proxy({},{get:()=>()=>{}})}});return elem.get(id)};
 const webstore={getItem:k=>store[k]??null,setItem(k,v){if(options.rejectSaves&&k===KEY)throw Error('QuotaExceededError');store[k]=v},removeItem:k=>delete store[k]};
 const ctx={console,Math,Number,Date,JSON,Array,Object,Set,Map,String,Intl,Uint32Array,Blob,crypto:crypto.webcrypto,localStorage:webstore,performance:{now:()=>0},requestAnimationFrame:f=>f(),setTimeout(){},setInterval(){},clearTimeout(){},clearInterval(){},confirm:()=>true,document:{getElementById:node,createElement:()=>node('el'),querySelector:()=>null,querySelectorAll:()=>[],body:{appendChild(){},addEventListener(){}}},window:{addEventListener(e,fn){events[e]=fn}},URL:{createObjectURL:()=>'',revokeObjectURL(){}}};
 vm.createContext(ctx);vm.runInContext(src,ctx);return {r:s=>vm.runInContext(s,ctx),events,ctx};
}

function rejectSaves(game){const real=game.ctx.localStorage.setItem;game.ctx.localStorage.setItem=(k,v)=>{if(k===KEY)throw Error('QuotaExceededError');return real(k,v)}}
function getWallet(game){return JSON.stringify({balance:game.r('state.balance'),reserved:game.r('state.reserved'),mode:game.r('state.mode'),rounds:game.r('state.stats.rounds'),day:game.r('dailyProgress.day')})}
// A resolved game may never show a cash award if persistence has failed.
{
 const storage={},g=create(storage);assert.equal(g.r('spend(200)'),true);
 const before=getWallet(g),persisted=storage[KEY];rejectSaves(g);
 assert.equal(g.r('settle("Монетка",200,400)'),false);
 assert.equal(getWallet(g),before);
 assert.equal(storage[KEY],persisted);
 console.log('PASS failed settlement rolls back balance, reservation, game stats and persistent wallet');
}
// Same rule for refund of a placed bet and the UI bet list.
{
 const storage={},g=create(storage);
 g.r('rouletteBet("color","red")');assert.equal(g.r('rt.bets.length'),1);
 const before=getWallet(g),persisted=storage[KEY];rejectSaves(g);
 g.r('handleAction({dataset:{action:"roulette-undo"}})');
 assert.equal(g.r('rt.bets.length'),1);
 assert.equal(getWallet(g),before);
 assert.equal(storage[KEY],persisted);
 console.log('PASS failed undo preserves chips and unrefunded roulette selection');
}
// A storage failure cannot grant imaginary chips, including during import/reset.
for(const action of ['topup','reset','import']){
 const storage={},g=create(storage),before=getWallet(g);
 const backup=g.r('JSON.stringify(snapshot())'),altered=JSON.parse(backup);
 altered.profiles.free.balance=54321;
 const persisted=storage[KEY];rejectSaves(g);
 if(action==='topup')g.r('addChips(5000)');
 if(action==='reset')g.r('resetAll()');
 if(action==='import')assert.throws(()=>g.r(`loadBackup(${JSON.stringify(JSON.stringify(altered))})`),/Не удалось записать импорт/);
 assert.equal(getWallet(g),before,action+' in-memory rollback');
 assert.equal(storage[KEY],persisted,action+' persisted wallet unchanged');
 console.log('PASS failed',action,'does not replace previous save');
}
// Switching modes must be one persisted transaction; not two half-commits.
{
 const storage={},g=create(storage);g.r('spend(100)');
 const before=getWallet(g),persisted=storage[KEY];rejectSaves(g);
 g.r('switchMode("daily")');assert.equal(getWallet(g),before);assert.equal(storage[KEY],persisted);
 console.log('PASS failed switch preserves active wallet and reserved stake');
}
// A new daily credit must not be granted when it cannot be persisted.
{
 const storage={},g=create(storage);g.r('switchMode("daily")');
 const before=getWallet(g),persisted=storage[KEY];rejectSaves(g);
 assert.equal(g.r('finishDailyDay("manual")'),false);
 assert.equal(getWallet(g),before);assert.equal(storage[KEY],persisted);
 console.log('PASS failed daily rollover retains day number and wallet');
}
// Multi-step game: refund failure must not advance the round.
{
 const storage={},g=create(storage);g.r('letItRideStart()');
 assert.equal(g.r('rt.letitride.bets'),3);
 const before=getWallet(g);rejectSaves(g);
 g.r('letItRideNext(true)');
 assert.equal(g.r('rt.letitride.bets'),3);
 assert.equal(g.r('rt.letitride.phase'),1);
 assert.equal(getWallet(g),before);
 console.log('PASS failed Let It Ride pull cannot advance or lose pending stake');
}
console.log('ALL 1.7.2 PERSISTENCE FAILURE TESTS PASSED');
