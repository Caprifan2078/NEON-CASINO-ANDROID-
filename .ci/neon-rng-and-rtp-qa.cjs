#!/usr/bin/env node
'use strict';
/* Independent exact RTP and secure RNG sanity tests against the application's real JS. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const js=fs.readFileSync(process.argv[2]||'','utf8');
function constant(name){const m=js.match(new RegExp('const '+name+'=(\\[[^;]*\\]|\\{[^;]*\\});'));assert(m,'Missing '+name);return vm.runInNewContext('('+m[1]+')')}
const wheel=constant('WIN_SECTORS'),plinko=constant('PLINKO_PAY'),slots=constant('SLOT_MULT'),keno=constant('KENO_PAY'),keno80=constant('KENO80_PAY');
function near(actual,expected,name,tol=1e-10){assert(Math.abs(actual-expected)<=tol,name+': '+actual+' != '+expected)}
let checks=0;
function check(ok,name){assert(ok,name);checks++}
const result={status:'FAIL',checks:0,random_draws:0,expected_returns:{}};
check(wheel.length===24&&wheel.every(x=>typeof x==='number'&&x>=0&&x<=10),'24 wheel sectors');
const wheelRTP=wheel.reduce((a,b)=>a+b,0)/24;near(wheelRTP,23/24,'Wheel expected gross payout');checks++;result.expected_returns.wheel=wheelRTP;
function choose(n,k){if(k<0||k>n)return 0;let x=1;for(let i=1;i<=k;i++)x=x*(n-i+1)/i;return x}
check(plinko.length===9,'9 Plinko buckets');
const plinkoRTP=plinko.reduce((s,m,i)=>s+choose(8,i)*m/256,0);near(plinkoRTP,0.9765625,'Plinko RTP');checks++;result.expected_returns.plinko=plinkoRTP;
const symbols=Object.values(slots);
check(symbols.length===6,'Six standard slots symbols');
const slotRTP=symbols.reduce((a,b)=>a+b,0)/6/36;near(slotRTP,205/216,'Standard slots RTP');checks++;result.expected_returns.slots=slotRTP;
function rtp(N,picks,drawn,pays){
 let pTotal=0,pay=0;
 for(let k=0;k<=picks;k++){
  const p=choose(picks,k)*choose(N-picks,drawn-k)/choose(N,drawn);
  pTotal+=p;pay+=p*pays[k]
 }
 near(pTotal,1,'Keno exact hypergeometric distribution');checks++;
 return pay;
}
const kenoRTP=rtp(40,5,10,keno),keno80RTP=rtp(80,6,20,keno80);
near(kenoRTP,0.9451252872305504,'Keno40 theoretical RTP');checks++;
near(keno80RTP,0.9265196828487968,'Keno80 theoretical RTP');checks++;
result.expected_returns.keno40=kenoRTP;result.expected_returns.keno80=keno80RTP;
for(const target of [1.5,2,3,5,10,20,50,100]){
 const probability=.97/target;
 check(probability>0&&probability<1&&Math.abs(probability*target-.97)<1e-12,'Limbo odds/payout '+target);
}
for(let chance=5;chance<=95;chance+=5){
 const probability=chance/100,multiplier=.97/probability;
 check(Math.abs(probability*multiplier-.97)<1e-12,'Dice probability '+chance);
}
const a=js.indexOf('function rnd('),b=js.indexOf('\nfunction ',a+9);
assert(a>=0&&b>a,'Cannot extract actual RNG function');
const source=js.slice(a,b),rnd=vm.runInNewContext(source+'\nrnd',{crypto:crypto.webcrypto,Uint32Array},{timeout:10000});
for(const bound of [2,6,24,37,80]){
 const n=100000,counts=new Uint32Array(bound);
 for(let i=0;i<n;i++){const v=rnd(bound);assert(Number.isInteger(v)&&v>=0&&v<bound);counts[v]++}
 const expected=n/bound,chisq=Array.from(counts).reduce((sum,v)=>sum+(v-expected)**2/expected,0);
 const upper=(bound-1)+8*Math.sqrt(2*(bound-1))+10;
 check(chisq<upper,'RNG statistical anomaly bound='+bound+' chi2='+chisq);
 result.random_draws+=n;
}
for(const bound of [3,6,37,80,1000000000]){
 const limit=Math.floor(4294967296/bound)*bound;
 let calls=0;
 const fake={getRandomValues(a){a[0]=calls++===0?4294967295:limit-1;return a}};
 const actual=vm.runInNewContext(source+'\nrnd('+bound+')',{crypto:fake,Uint32Array});
 check(actual===(limit-1)%bound,'RNG unbiased tail rejection '+bound);
 check(calls===(limit===4294967296?1:2),'RNG tail rejection count '+bound);
}
result.status='PASS';result.checks=checks;console.log(JSON.stringify(result,null,2));
