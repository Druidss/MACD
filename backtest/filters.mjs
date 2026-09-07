// All candidates are post-hoc exploration on previously inspected data, not fresh holdouts.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {run,daily,compact,periods,csv,dir} from './run.mjs';

function rma(values,n){
  let seed=[],last=NaN;
  return values.map(v=>{
    if(!Number.isFinite(v))return NaN;
    if(!Number.isFinite(last)){seed.push(v);if(seed.length===n)last=seed.reduce((a,b)=>a+b,0)/n;}
    else last=(last*(n-1)+v)/n;
    return last;
  });
}
function features(bars){
  const plus=[],minus=[],tr=[];
  for(let i=0;i<bars.length;i++){
    const b=bars[i],p=bars[i-1];
    const up=p?b.h-p.h:NaN,down=p?p.l-b.l:NaN;
    plus.push(p?(up>down&&up>0?up:0):NaN);
    minus.push(p?(down>up&&down>0?down:0):NaN);
    tr.push(p?Math.max(b.h-b.l,Math.abs(b.h-p.c),Math.abs(b.l-p.c)):NaN);
  }
  const atr=rma(tr,14),pr=rma(plus,14),mr=rma(minus,14);
  const dx=atr.map((a,i)=>{
    if(!Number.isFinite(a))return NaN;
    const sum=pr[i]+mr[i];return sum===0?0:100*Math.abs(pr[i]-mr[i])/sum;
  });
  const adx=rma(dx,14);
  return bars.map((b,i)=>{
    let distance=0;for(let j=Math.max(1,i-19);j<=i;j++)distance+=Math.abs(bars[j].c-bars[j-1].c);
    const er=i<20?NaN:distance?Math.abs(b.c-bars[i-20].c)/distance:0;
    return {adx:adx[i],er};
  });
}
const f=features(daily);
const byTime=new Map(daily.map((b,i)=>[b.t,f[i]]));
// Small, fixed grid declared before this experiment's first run; no best-value search afterwards.
const definitions=[
  {id:'none',label:'无过滤',kind:'none',threshold:0},
  ...[20,25].map(threshold=>({id:`adx${threshold}`,label:`ADX14 >= ${threshold}`,kind:'adx',threshold})),
  ...[.2,.3].map(threshold=>({id:`er${threshold}`,label:`ER20 >= ${threshold}`,kind:'er',threshold})),
  ...[.1,.2].map(threshold=>({id:`slope${threshold}`,label:`EMA52五日升幅/ATR14 >= ${threshold}`,kind:'slope',threshold})),
  ...[.25,.5].map(threshold=>({id:`gap${threshold}`,label:`(EMA25-EMA52)/ATR14 >= ${threshold}`,kind:'gap',threshold})),
  {id:'adx20_slope01',label:'ADX >= 20 且斜率 >= 0.1',kind:'combined',threshold:0},
  // Second round, after inspecting hard gates: reject only jointly flat AND inefficient price action.
  ...[.1,.2].map(threshold=>({id:`flat_veto${threshold}`,label:`排除ER20<0.2且EMA52绝对斜率<${threshold}`,kind:'flat_veto',threshold,round:2})),
];
function pass(d,{i,r,e52,efast}){
  const x=byTime.get(r.t),slope=(e52[i]-e52[i-5])/r.atr,gap=(efast[i]-e52[i])/r.atr;
  switch(d.kind){
    case 'none':return true;
    case 'adx':return x.adx>=d.threshold;
    case 'er':return x.er>=d.threshold;
    case 'slope':return slope>=d.threshold;
    case 'gap':return gap>=d.threshold;
    case 'combined':return x.adx>=20&&slope>=.1;
    case 'flat_veto':return Number.isFinite(x.er)&&Number.isFinite(slope)&&!(x.er<.2&&Math.abs(slope)<d.threshold);
    default:throw Error('Unknown filter');
  }
}
const results=[];
for(const rearm of [false,true]){
  const base={id:rearm?'rearm':'ema25',fast:25,exit:'cross',regime:'original',short:false,rearm};
  const baseline=run(base);
  for(const d of definitions){
    const v={...base,id:`${base.id}_${d.id}`,filter:c=>pass(d,c)},full=run(v);
    const entryDates=new Set(full.tradeLog.map(t=>t.entryDate));if(full.open)entryDates.add(full.open.entryDate);
    const absent=baseline.tradeLog.filter(t=>!entryDates.has(t.entryDate));
    // Same-date absence includes subsequent path changes; it does not prove direct filter rejection.
    const row={base:base.id,filter:d,full:compact(full),periods:Object.fromEntries(Object.entries(periods).map(([k,p])=>[k,compact(run(v,p))])),
      slippage10bps:compact(run(v,{slip:.001})),
      absentBaselineEntries:absent.map(t=>({entryDate:t.entryDate,net:t.net})),
      keyEntries:['2024-02-08','2024-10-12'].map(entryDate=>({entryDate,retained:entryDates.has(entryDate)}))};
    results.push(row);
    csv(`filter-${v.id}-trades.csv`,full.tradeLog);
    const prefix=run(v,{bars:daily.filter(b=>b.t<Date.parse('2025-01-01'))});
    assert.deepEqual(prefix.curve,full.curve.filter(b=>b.date<'2025-01-01'));
    const last=full.curve.at(-1).equity;
    assert(Math.abs(last-(10000+full.tradeLog.reduce((s,t)=>s+t.net,0)+(full.open?full.open.unrealized-10:0)))<1e-7);
    if(d.kind==='none')assert.deepEqual(full.curve,baseline.curve);
    for(const signal of full.signals.filter(s=>s.kind==='entry')){
      const trade=full.tradeLog.find(t=>Date.parse(t.entryDate)===signal.t+86400000);
      assert(trade||full.open&&Date.parse(full.open.entryDate)===signal.t+86400000||full.pending?.kind==='entry'&&full.pending.t===signal.t);
    }
  }
}
// Indicator calculations themselves must not see future bars.
assert.deepEqual(features(daily.slice(0,1000)),f.slice(0,1000));
const flat=features(Array.from({length:80},(_,i)=>({t:i,c:100,h:100,l:100})));
assert.equal(flat.at(-1).er,0);assert.equal(flat.at(-1).adx,0);
const rising=features(Array.from({length:80},(_,i)=>({t:i,c:100+i,h:101+i,l:99+i})));
assert.equal(rising.at(-1).er,1);assert.equal(rising.at(-1).adx,100);
const blocked=run({id:'blocked',fast:25,exit:'cross',regime:'original',short:false,filter:()=>false});
assert.equal(blocked.returnPct,0);assert.equal(blocked.trades,0);assert.equal(blocked.open,null);
const baseline=run({id:'diagnostic',fast:25,exit:'cross',regime:'original',short:false});
const signalDiagnostics=baseline.signals.filter(s=>s.kind==='entry').map(s=>{
  const idx=baseline.curve.findIndex(c=>c.date===new Date(s.t).toISOString().slice(0,10)),c=baseline.curve[idx];
  const bar=daily.find(b=>b.t===s.t),feat=byTime.get(s.t);
  return {signalDate:c.date,...feat,slope:(c.ema52-baseline.curve[idx-5]?.ema52)/bar.atr,gap:(c.emaFast-c.ema52)/bar.atr};
});
const table=results.map(r=>({base:r.base,filter:r.filter.id,return:r.full.returnPct,realized:r.full.realizedPct,dd:r.full.closeDD,trades:r.full.trades,pf:r.full.pf,exposure:r.full.exposurePct,y2024:r.periods.train.returnPct,y2025:r.periods.validation.returnPct,y2026:r.periods.test.returnPct,slip10:r.slippage10bps.returnPct,key:r.keyEntries.map(x=>x.retained)}));
fs.writeFileSync(path.join(dir,'filter-results.json'),JSON.stringify({status:'post-hoc exploratory; no fresh holdout',exit:'EMA52-300 cross; unchanged',signalDiagnostics,results},null,2));
csv('filter-summary.csv',table.map(({key,...r})=>r));
console.log(JSON.stringify({filterTable:table,checks:'baseline parity, all-filter prefix/accounting/next-open checks, flat/rising indicator fixtures passed'},null,2));
