'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const source=fs.readFileSync(process.env.NEON_TEST_JS||'patched/app.js','utf8');
function boot(seed={},options={}){
 const store={...seed},nodes=new Map();
 function el(id){if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',style:{},hidden:false,value:'',dataset:{},classList:{add(){},remove(){},toggle(){}},setAttribute(){},querySelectorAll(){return[]},addEventListener(){},appendChild(){},remove(){},getContext(){return new Proxy({}, {get(){return()=>{}}})}});return nodes.get(id)}
 const ctx={console,Math,JSON,Number,Date,Array,Set,Map,Object,String,Intl,crypto:crypto.webcrypto,requestAnimationFrame:fn=>fn(),performance:{now:()=>1},setTimeout(){return 1},setInterval(){return 1},clearInterval(){},clearTimeout(){},document:{getElementById:el,querySelector(){return null},querySelectorAll(){return []},createElement(){return el('new')},body:{addEventListener(){},appendChild(){},classList:{toggle(){}}}},window:{addEventListener(){},matchMedia(){return {matches:false}}},navigator:{},localStorage:{getItem:k=>store[k]??null,setItem(k,v){if(options.failPreset&&k==='neon-casino-roulette-presets-v1')throw Error('quota');store[k]=v},removeItem(k){delete store[k]}},confirm:()=>true};
 vm.createContext(ctx);vm.runInContext(source,ctx);return{store,run:e=>vm.runInContext(e,ctx),el};
}

// P0 import is a wallet + preference operation; failure must never report success.
const keys={wallet:'neon-casino-local-v1',favorite:'neon-casino-favorites-v1',recent:'neon-casino-recent-v1',view:'neon-casino-view-v1',presets:'neon-casino-roulette-presets-v1',checkpoint:'neon-casino-preimport-v1'};
const seeded={
 [keys.favorite]:JSON.stringify(['coin']),
 [keys.recent]:JSON.stringify(['coin']),
 [keys.view]:'hall',
 [keys.presets]:JSON.stringify([[{type:'number',value:'4',amount:50}],null,null])
};
function makeBackup(app){
 const b=JSON.parse(app.run('JSON.stringify(snapshot())'));
 b.mode='free';b.balance=42000;b.profiles.free.balance=42000;
 b.profiles.daily.balance=777;b.dailyProgress.day=3;
 b.preferences.favorites=['roulette'];b.preferences.recent=['roulette'];
 b.preferences.view='casual';
 b.preferences.roulettePresets=[[{type:'number',value:'17',amount:100}],null,null];
 return JSON.stringify(b);
}
function failures(failKey,afterCheckpoint=false){
 const app=boot(seeded);const data=makeBackup(app);
 const oldEntries=Object.fromEntries(Object.entries(seeded));
 app.run(`(()=>{const original=localStorage.setItem.bind(localStorage); let armed=${!afterCheckpoint};localStorage.setItem=(key,value)=>{
   if(key===PREIMPORT_KEY)armed=true;
   if(armed&&key===${JSON.stringify(failKey)})throw Error('injected storage failure');
   return original(key,value)
 };})()`);
 let error;
 try{app.run('loadBackup('+JSON.stringify(data)+')');throw Error('Expected import to abort')}
 catch(e){error=String(e);assert.match(error,/Не удалось/)}
 assert.equal(app.run('state.balance'),50000,`wallet in memory changed on ${failKey}`);
 assert.equal(app.run('profileSnapshots.daily.balance'),1000,`daily wallet changed on ${failKey}`);
 assert.equal(JSON.parse(app.store[keys.wallet]).profiles.free.balance,50000,`wallet persisted changed on ${failKey}`);
 for(const [k,v] of Object.entries(oldEntries))assert.equal(app.store[k],v,`preference ${k} changed after ${failKey} failure`);
 assert.equal(app.run('roulettePresets[0][0].value'),'4');
 assert.equal(app.run('casinoView'),'hall');
 assert.equal(app.run('favoriteGames.has("coin")'),true);
 assert.ok(app.store[keys.checkpoint],`checkpoint lost on ${failKey}`);
}
for(const k of [keys.favorite,keys.recent,keys.view,keys.presets])failures(k);
failures(keys.wallet,true);
{
 const app=boot(seeded),data=makeBackup(app);
 assert.equal(app.run('loadBackup('+JSON.stringify(data)+')'),true);
 assert.equal(app.run('state.balance'),42000);
 assert.equal(app.run('profileSnapshots.daily.balance'),777);
 assert.equal(app.run('dailyProgress.day'),3);
 assert.equal(app.run('roulettePresets[0][0].value'),'17');
 assert.equal(JSON.parse(app.store[keys.presets])[0][0].value,'17');
 delete app.store['neon-casino-active-instance-v1']; // simulate normal pagehide before cold boot
 const cold=boot(app.store);
 assert.equal(cold.run('state.balance'),42000,'wallet lost after restart');
 assert.equal(cold.run('profileSnapshots.daily.balance'),777,'daily wallet lost after restart');
 assert.equal(cold.run('roulettePresets[0][0].value'),'17','preset lost after restart');
 assert.equal(cold.run('favoriteGames.has("roulette")'),true);
 assert.equal(cold.run('casinoView'),'casual');
 assert.equal(cold.run('restorePreImportBackup()'),true);
 assert.equal(cold.run('state.balance'),50000);
 assert.equal(cold.run('roulettePresets[0][0].value'),'4');
 assert.equal(JSON.parse(cold.store[keys.presets])[0][0].value,'4');
 assert.equal(cold.run('favoriteGames.has("coin")'),true);
 delete cold.store['neon-casino-active-instance-v1'];
 const recold=boot(cold.store);
 assert.equal(recold.run('state.balance'),50000,'undo did not survive cold restart');
 assert.equal(recold.run('roulettePresets[0][0].value'),'4','undo preset did not survive cold restart');
}
console.log('PASS P0 import: 4 injected preference failures, wallet-write failure, v5 import, cold start and complete undo');
