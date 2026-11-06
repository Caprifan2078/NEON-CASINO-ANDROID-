#!/usr/bin/env node
'use strict';
// Characterization regression against the ACTUAL resetRuntime() function.
// Expected RED on unpatched v1.8.9; expected GREEN after minimal P0 fix.
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
if(process.argv.length!==3)throw Error('Usage: neon-reset-runtime-test.cjs web/app.js');
const source=fs.readFileSync(process.argv[2],'utf8');
const match=source.match(/^function resetRuntime\(\)\{[^\n]+\}$/m);
assert.ok(match,'Cannot locate actual NEON 1.8.9 resetRuntime function');
const extraNames=[
 'threecard','war','dragontiger','tower','bingo','lotto','scratch','seven',
 'dicepoker','treasure','andar','reddog','pick3','bingo90','keno80',
 'cardsuit','ladder','slots5','holdem','letitride','rps','colors',
 'caribbean','teenpatti','fantan','crown'
];
const rt=Object.fromEntries(extraNames.map(k=>[k,{active:true,stake:100}]));
rt.crash={interval:13,active:true};rt.plinko={timer:14,active:true};
rt.bets=[{amount:100}];
const ctx={rt,roundEpoch:8,lastRouletteBets:[{amount:100}],cleared:[],clearInterval:null};
ctx.clearInterval=n=>ctx.cleared.push(n);
vm.runInNewContext(match[0]+'\nresetRuntime();',ctx,{timeout:2000});
assert.equal(ctx.roundEpoch,9,'Round epoch must invalidate delayed callbacks');
assert.equal(ctx.lastRouletteBets.length,0,'Roulette ticket remains after reset');
assert.equal(ctx.rt.bets.length,0,'Roulette table bet remains after reset');
assert.deepEqual(ctx.cleared.sort(),[13,14],'Crash/Plinko timers must be cancelled');
for(const key of extraNames){
 assert.ok(ctx.rt[key]==null, 'STALE ROUND: '+key+' remains active after switching wallet modes');
}
console.log(JSON.stringify({status:'PASS',extraStatesCleared:extraNames.length,cancelledTimers:ctx.cleared.length,epoch:ctx.roundEpoch}));
