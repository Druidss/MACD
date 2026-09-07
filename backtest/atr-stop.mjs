// User-requested 2ATR buffer; post-hoc exploration, no fresh holdout.
import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {run,daily,compact,periods,csv,dir} from './run.mjs';
const results=[];
for(const rearm of [false,true])for(const exit of ['cross','level','atr_cross','atr_level']){
  const v={id:`${rearm?'rearm':'ema25'}_${exit}`,fast:25,regime:'original',short:false,rearm,exit};
  const r=run(v);
  const prefix=run(v,{bars:daily.filter(b=>b.t<Date.parse('2025-01-01'))});
  assert.deepEqual(prefix.curve,r.curve.filter(b=>b.date<'2025-01-01'));
  assert(Math.abs(r.curve.at(-1).equity-(10000+r.tradeLog.reduce((s,t)=>s+t.net,0)+(r.open?r.open.unrealized-10:0)))<1e-7);
  for(const t of r.tradeLog){
    const idx=daily.findIndex(b=>b.t===Date.parse(t.exitDate)),b=daily[idx-1],p=daily[idx-2];
    const c=r.curve.find(c=>c.date===new Date(b.t).toISOString().slice(0,10));
    assert.equal(t.exit,daily[idx].o);
    if(exit.startsWith('atr_')){
      assert(b.c<c.ema52-2*b.atr);
      if(exit==='atr_cross'){
        const previous=r.curve.find(c=>c.date===new Date(p.t).toISOString().slice(0,10));
        assert(p.c>=previous.ema52-2*p.atr);
      }
    }
  }
  results.push({config:v,full:compact(r),periods:Object.fromEntries(Object.entries(periods).map(([k,p])=>[k,compact(run(v,p))])),slip10:compact(run(v,{slip:.001}))});
  csv(`atr-${v.id}-trades.csv`,r.tradeLog);
}
const buffers=daily.filter(b=>b.t>=Date.parse('2024-01-01')).map(b=>2*b.atr).sort((a,b)=>a-b);
const bufferStats={min:buffers[0],median:buffers[Math.floor(buffers.length/2)],max:buffers.at(-1)};
fs.writeFileSync(path.join(dir,'atr-stop-results.json'),JSON.stringify({status:'post-hoc exploration',formula:'EMA52 - 2 * ATR14; dynamic daily; close signal, next-open fill',bufferStats,results},null,2));
console.log(JSON.stringify({bufferStats,table:results.map(r=>({id:r.config.id,return:r.full.returnPct,dd:r.full.closeDD,trades:r.full.trades,realized:r.full.realizedPct,y2024:r.periods.train.returnPct,y2025:r.periods.validation.returnPct,y2026:r.periods.test.returnPct})),checks:'prefix invariance, accounting, exit formula and next-open fills passed'},null,2));
