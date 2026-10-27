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
const shared={};
const a=create(shared);assert.equal(a.r('canModify()'),true);
assert.equal(a.r('spend(250)'),true);
assert.equal(JSON.parse(shared[KEY]).profiles.free.reserved,250);
const b=create(shared);assert.equal(b.r('canModify()'),false);
assert.equal(b.r('spend(100)'),false,'second window can never debit wallet');
assert.equal(b.r('state.reserved'),0,'second window cannot reserve chips');
assert.equal(JSON.parse(shared[KEY]).profiles.free.reserved,250,'second window startup cannot refund still-active A wager');
b.r('addChips(100000)');assert.equal(JSON.parse(shared[KEY]).balance,49750,'second window cannot grant chips');
b.r('handleAction({dataset:{action:"reset-stats"}})');assert.equal(JSON.parse(shared[KEY]).stats.rounds,0);
a.r('settle("Монетка",250,500)');assert.equal(JSON.parse(shared[KEY]).balance,50250);
assert.equal(JSON.parse(shared[KEY]).profiles.free.reserved,0);
console.log('PASS two-tab protection: secondary cannot debit, grant, refund, overwrite, or reset active wallet');
assert.equal(typeof b.events.pagehide,'function');b.events.pagehide();assert.ok(shared[LEASE],'blocked second window cannot release owner lease');
a.events.pagehide();assert.equal(shared[LEASE],undefined);
const c=create(shared);assert.equal(c.r('state.balance'),50250);assert.equal(c.r('canModify()'),true);
assert.equal(c.r('spend(100)'),true);assert.equal(JSON.parse(shared[KEY]).balance,50150);
console.log('PASS owner close + fresh tab: saved funds preserved and wallet unlocks');
// If storage refuses writes mid-round, never debit in memory and never advertise a successful stake.
const storageFail={};const d=create(storageFail);const before=d.r('state.balance');
d.ctx.localStorage.setItem=(k,v)=>{if(k===KEY)throw Error('QuotaExceededError');storageFail[k]=v};
assert.equal(d.r('spend(250)'),false);assert.equal(d.r('state.balance'),before);assert.equal(d.r('state.reserved'),0);
console.log('PASS storage write exception rolls back a newly requested wager');
// If another process tampers with the lease, the old instance must stop writing.
const other={};const e=create(other);
other[LEASE]=JSON.stringify({token:'some-other-owner',at:Date.now()});
assert.equal(e.r('canModify()'),false);assert.equal(e.r('spend(100)'),false);
assert.equal(other[KEY],undefined);
console.log('PASS lost ownership prevents stale writes');
console.log('ALL 1.7.1 MULTI-WINDOW ACCOUNTING TESTS PASSED');
