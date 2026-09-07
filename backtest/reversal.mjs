import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {run,daily,compact,periods,csv,dir} from './run.mjs';
const variants=[];
for(const exit of ['cross','atr_level'])for(const mode of ['long_only','flat_both','reverse_both'])variants.push({id:`${exit}_${mode}`,fast:25,exit,regime:'original',short:mode!=='long_only',shortFirst:true,reverse:mode==='reverse_both'});
const results=[];
for(const v of variants){
  const full=run(v),reversals=full.tradeLog.filter(t=>t.reason.startsWith('Reverse'));
  assert.deepEqual(run(v,{bars:daily.filter(b=>b.t<Date.parse('2025-01-01'))}).curve,full.curve.filter(b=>b.date<'2025-01-01'));
  assert(Math.abs(full.curve.at(-1).equity-(10000+full.tradeLog.reduce((s,t)=>s+t.net,0)+(full.open?full.open.unrealized-10:0)))<1e-7);
  const check=r=>{for(const t of r.tradeLog.filter(t=>t.reason.startsWith('Reverse'))){
    const next=r.tradeLog.find(n=>n.entryDate===t.exitDate&&n.side===-t.side)||r.open;
    assert(next&&next.entryDate===t.exitDate&&next.side===-t.side);assert.equal(t.exit,next.entry);
    assert(r.signals.some(s=>s.kind==='reverse'&&s.side===-t.side&&s.t===Date.parse(t.exitDate)-86400000));
  }};
  check(full);check(run(v,{slip:.001}));
  let fees=0;for(const t of full.tradeLog)fees+=10+10000/t.entry*t.exit*.001;if(full.open)fees+=10;
  assert(Math.abs(fees-full.fees)<1e-7);
  results.push({config:v,full:compact(full),reversals:reversals.length,toLong:reversals.filter(t=>t.side===-1).length,toShort:reversals.filter(t=>t.side===1).length,periods:Object.fromEntries(Object.entries(periods).map(([k,p])=>[k,compact(run(v,p))])),slip10:compact(run(v,{slip:.001}))});
  csv(`reversal-${v.id}-trades.csv`,full.tradeLog);csv(`reversal-${v.id}-equity.csv`,full.curve);
}
// The refactor must leave the prior strategy and ATR experiments unchanged.
const prior=JSON.parse(fs.readFileSync(path.join(dir,'atr-stop-results.json'),'utf8'));
for(const old of prior.results)assert.deepEqual(compact(run(old.config)),old.full);
// Deterministic bars force both reversal directions and a same-bar stop/reversal conflict.
const closes=[...Array(70).fill(100),90,90,110,90,90,110,90,90];
const synthetic=closes.map((c,i)=>({t:Date.parse('2024-01-01')+i*86400000,o:c,h:c+1,l:c-1,c,atr:1,dea:i===71||i===72?10:-1000,four:{dif:0,dea:0}}));
const fixture=run({id:'fixture',fast:25,exit:'cross',regime:'original',short:true,shortFirst:true,reverse:true,delay:1},{bars:synthetic});
assert(fixture.signals.some(s=>s.kind==='reverse'&&s.side===1));
assert(fixture.signals.some(s=>s.kind==='reverse'&&s.side===-1));
assert.equal(fixture.tradeLog[0].side,-1);
assert.equal(new Set(fixture.signals.map(s=>s.t)).size,fixture.signals.length);
const rows=results.map(r=>({id:r.config.id,total:r.full.returnPct,realized:r.full.realizedPct,dd:r.full.closeDD,trades:r.full.trades,reversals:r.reversals,toLong:r.toLong,toShort:r.toShort,y2024:r.periods.train.returnPct,y2025:r.periods.validation.returnPct,y2026:r.periods.test.returnPct,slip10:r.slip10.returnPct}));
fs.writeFileSync(path.join(dir,'reversal-results.json'),JSON.stringify({status:'post-hoc local simulation; not native TradingView',priority:'reverse before stop; no pyramiding; short allowed as first trade',shortStop:'cross above EMA52, unchanged',results},null,2));
console.log(JSON.stringify({rows,checks:'legacy parity, prefix invariance, accounting, reversal next-open price and dual-leg fees passed'},null,2));
