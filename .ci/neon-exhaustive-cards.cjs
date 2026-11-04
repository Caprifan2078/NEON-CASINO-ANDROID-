#!/usr/bin/env node
'use strict';
/*
 * Exhaustive evaluator audit: all possible 5-card and 3-card hands
 * from the actual NEON source. Crosscheck independent combinatorial counts.
 */
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const sourcePath=process.argv[2];
if(!sourcePath)throw Error('Usage: node neon-exhaustive-cards.cjs path/to/web/app.js');
const js=fs.readFileSync(sourcePath,'utf8');
const ranksMatch=js.match(/RANKS=(\[[^\]]+\])/);
if(!ranksMatch)throw Error('Cannot find RANKS constant');
function pickFunction(name){
 const start=js.indexOf('function '+name+'(');
 if(start<0)throw Error('Missing function '+name);
 const next=js.indexOf('\nfunction ',start+10);
 if(next<0)throw Error('Cannot locate end of function '+name);
 return js.slice(start,next);
}
const isolated=[
 "'use strict';const RANKS="+ranksMatch[1]+";",
 pickFunction('pokerFiveScore'),
 pickFunction('teenScore'),
 "const suits=['♠','♥','♦','♣'];",
 "const deck=[];for(const rank of RANKS)for(const suit of suits)deck.push({rank,suit});",
 "const poker=Array(9).fill(0),teen=Array(8).fill(0);let pokerHands=0,teenHands=0;",
 "for(let a=0;a<48;a++)for(let b=a+1;b<49;b++)for(let c=b+1;c<50;c++)for(let d=c+1;d<51;d++)for(let e=d+1;e<52;e++){",
 "const score=pokerFiveScore([deck[a],deck[b],deck[c],deck[d],deck[e]]);poker[score[0]]++;pokerHands++;}",
 "for(let a=0;a<50;a++)for(let b=a+1;b<51;b++)for(let c=b+1;c<52;c++){",
 "const score=teenScore([deck[a],deck[b],deck[c]]);teen[score[0]]++;teenHands++;}",
 "({pokerHands,teenHands,poker,teen})"
].join('\n');
const result=vm.runInNewContext(isolated,Object.create(null),{timeout:60000});
const expectedPoker=[1302540,1098240,123552,54912,10200,5108,3744,624,40];
const expectedTeen=[0,16440,3744,1096,720,44,52,4];
const valid=(got,expected)=>Array.from(got).every((x,i)=>x===expected[i])&&got.length===expected.length;
const pass=result.pokerHands===2598960&&result.teenHands===22100&&valid(result.poker,expectedPoker)&&valid(result.teen,expectedTeen);
console.log(JSON.stringify({status:pass?'PASS':'FAIL',source:path.basename(sourcePath),pokerHands:result.pokerHands,poker:[...result.poker],teenHands:result.teenHands,teen:[...result.teen],expectedPoker,expectedTeen}));
if(!pass)process.exitCode=1;
