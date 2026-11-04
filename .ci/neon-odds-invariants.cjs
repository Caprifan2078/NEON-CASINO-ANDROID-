#!/usr/bin/env node
'use strict';
// Compare real NEON function outputs against independent exhaustive outcomes.
const fs=require('fs'),vm=require('vm'),assert=require('assert').strict;
const source=fs.readFileSync(process.argv[2],'utf8');
function read(name){
 const a=source.indexOf('function '+name+'('),b=source.indexOf('\nfunction ',a+9);
 assert(a>=0&&b>a,'Missing function '+name);return source.slice(a,b);
}
const names=['outcomeColor','rouletteWin','rouletteVariantWin','sicboOutcome','sicboMultiplier','sevenOutcome','permutationCount','pick3Payout','extraPayout'];
const ids=['small','big','triple'];
for(let i=4;i<=17;i++)ids.push('sum-'+i);
for(const k of ['exact','pair','single'])for(let i=1;i<=6;i++)ids.push(k+'-'+i);
const red=[1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
const sums={4:51,5:19,6:15,7:13,8:9,9:7,10:7,11:7,12:7,13:9,14:13,15:15,16:19,17:51};
const defs='const REDS=new Set('+JSON.stringify(red)+');const SICBO_SUM_PAY='+JSON.stringify(sums)+
 ';const SICBO_IDS=new Set('+JSON.stringify(ids)+');const ROULETTE_COMBO_ODDS={2:17,3:11,4:8,6:5};const BALANCE_CAP=9000000000000000;';
const act=vm.runInNewContext(defs+names.map(read).join('\n')+'\n({'+names.join(',')+'})',Object.create(null),{timeout:15000});
let checks=0;
function eq(got,want,reason){assert.equal(got,want,reason);checks++;}
for(let n=0;n<=36;n++){
 for(let t=0;t<=36;t++)eq(act.rouletteWin({type:'number',value:String(t)},n),n===t?35:0,'straight');
 for(const color of ['red','black'])eq(act.rouletteWin({type:'color',value:color},n),n===0?0:(red.includes(n)===(color==='red')?1:0),'color');
 for(const k of ['low','high','even','odd'])eq(act.rouletteWin({type:k,value:k},n),
  n===0?0:(k==='low'?n<=18:k==='high'?n>=19:k==='even'?n%2===0:n%2===1)?1:0,'even money');
 for(let d=1;d<=3;d++)eq(act.rouletteWin({type:'dozen',value:String(d)},n),n&&Math.ceil(n/12)===d?2:0,'dozen');
}
for(const variant of ['fr','us']){
 const nums=Array.from({length:37},(_,i)=>String(i));if(variant==='us')nums.push('00');
 for(const n of nums)for(const k of ['red','black','even','odd','low','high','d1','d2','d3','n:17']){
  const v=Number(n),zero=n==='0'||n==='00';
  const yes=k==='red'?red.includes(v):k==='black'?!red.includes(v):k==='even'?v%2===0:
    k==='odd'?v%2===1:k==='low'?v<=18:k==='high'?v>=19:
    k==='d1'?v<=12:k==='d2'?v>=13&&v<=24:v>=25;
  const expected=k==='n:17'?(n==='17'?3600:0):zero?(variant==='fr'&&!k.startsWith('d')?50:0):yes?(k.startsWith('d')?300:200):0;
  eq(act.rouletteVariantWin(k,n,variant,100),expected,variant+' '+k+' '+n);
 }
}
for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(let c=1;c<=6;c++){
 const d=[a,b,c],sum=a+b+c,triple=a===b&&b===c;
 for(const k of ['small','big','triple']){
  const win=k==='triple'?triple:!triple&&(k==='small'?sum<=10:sum>=11);
  eq(act.sicboOutcome(d,k),win,'sicbo outcome');
  eq(act.sicboMultiplier(d,k),win?(k==='triple'?25:2):0,'sicbo multiplier');
 }
 for(let x=4;x<=17;x++)eq(act.sicboMultiplier(d,'sum-'+x),sum===x?sums[x]:0,'sicbo sum');
 for(let x=1;x<=6;x++){const count=d.filter(z=>z===x).length;
  eq(act.sicboMultiplier(d,'exact-'+x),count===3?181:0,'sicbo triple');
  eq(act.sicboMultiplier(d,'pair-'+x),count>=2?12:0,'sicbo pair');
  eq(act.sicboMultiplier(d,'single-'+x),[0,2,3,4][count]||0,'sicbo single');
 }
}
for(let a=1;a<=6;a++)for(let b=1;b<=6;b++)for(const k of ['under','over','seven','double','even']){
 const sum=a+b;eq(act.sevenOutcome([a,b],k),k==='under'?sum<7:k==='over'?sum>7:k==='seven'?sum===7:k==='double'?a===b:sum%2===0,'seven');
}
for(const picks of [[1,2,3],[1,1,2],[1,1,1]])for(let a=0;a<=9;a++)for(let b=0;b<=9;b++)for(let c=0;c<=9;c++){
 const target=[a,b,c],exact=picks.every((x,i)=>x===target[i]);
 const box=[...picks].sort().join('')===[...target].sort().join('');
 eq(act.pick3Payout(picks,target,'exact',1000),exact?act.extraPayout(1000,900):0,'pick3 straight');
 eq(act.pick3Payout(picks,target,'box',1000),box?act.extraPayout(1000,900/act.permutationCount(picks)):0,'pick3 box');
}
console.log(JSON.stringify({status:'PASS',checks,roulette:37,sicbo:216,pick3:1000}));
