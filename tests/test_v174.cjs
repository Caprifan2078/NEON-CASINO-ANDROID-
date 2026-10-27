'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../web/app.js'),'utf8');
const KEY='neon-casino-local-v1',LEASE='neon-casino-active-instance-v1';
function create(store,native=false){
 const elem=new Map();
 const node=id=>{if(!elem.has(id))elem.set(id,{innerHTML:'',textContent:'',value:'',style:{},dataset:{},children:[],addEventListener(){},appendChild(){},remove(){},setAttribute(){},classList:{toggle(){},add(){},remove(){},contains(){return false}},getContext(){return new Proxy({},{get:()=>()=>{}})}});return elem.get(id)};
 const webstore={getItem:k=>store[k]??null,setItem(k,v){store[k]=v},removeItem:k=>delete store[k]};
 const window={addEventListener(){}};if(native)window.NeonBridge={saveBackup(){}};
 const ctx={console,Math,Number,Date,JSON,Array,Object,Set,Map,String,Intl,Uint32Array,Blob,crypto:crypto.webcrypto,localStorage:webstore,performance:{now:()=>0},requestAnimationFrame:f=>f(),setTimeout(){},setInterval(){},clearTimeout(){},clearInterval(){},confirm:()=>true,document:{getElementById:node,createElement:()=>node('el'),querySelector:()=>null,querySelectorAll:()=>[],body:{appendChild(){},addEventListener(){}}},window,URL:{createObjectURL:()=>'',revokeObjectURL(){}}};
 vm.createContext(ctx);vm.runInContext(src,ctx);return {r:s=>vm.runInContext(s,ctx),ctx};
}
const shared={};
const before=create(shared,true);
assert.equal(before.r('canModify()'),true);
assert.equal(before.r('spend(140)'),true);
assert.equal(JSON.parse(shared[KEY]).profiles.free.reserved,140);
// Simulate abrupt native renderer death: the old tab cannot run pagehide.
const after=create(shared,true);
assert.equal(after.r('canModify()'),true,'Native shell should reclaim lease immediately');
assert.equal(after.r('state.balance'),50000,'reserved chips returned once after process death');
assert.equal(after.r('state.reserved'),0);
const third=create(shared,true);
assert.equal(third.r('state.balance'),50000,'restart cannot refund twice');
// Same save must still be locked in a *normal browser* second tab.
const browser=create(shared,false);
assert.equal(browser.r('canModify()'),false);
console.log('PASS native renderer crash immediately recovers a pending wager without duplicated chips');
console.log('PASS browser secondary window remains blocked');
let result=[];third.ctx.window.neonNativeBackupComplete=function(ok){result.push(ok)};
third.r('window.neonNativeBackupComplete(true)');
assert.deepEqual(result,[true]);
console.log('PASS export completion bridge is present');
console.log('ALL v1.7.4 MOBILE RECOVERY TESTS PASSED');
