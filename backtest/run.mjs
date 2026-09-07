// Read-only market requests; all generated artifacts remain under backtest/.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
const dir = path.dirname(fileURLToPath(import.meta.url));
const DAY=86400000, start=Date.parse('2024-01-01'), warm=Date.parse('2022-01-01');
const cutoff=Date.parse('2026-09-07'); // Exclusive UTC; freeze dataset for reproducibility.
const date=t=>new Date(t).toISOString().slice(0,10);
function download(interval, step) {
  const file=path.join(dir,`BTCUSDT-${interval}.json`);
  if(fs.existsSync(file)) return JSON.parse(fs.readFileSync(file,'utf8'));
  const rows=[];
  for(let t=warm;t<cutoff;){
    const url=`https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=${interval}&startTime=${t}&endTime=${cutoff-1}&limit=1000`;
    const batch=JSON.parse(execFileSync('curl.exe',['-sS','--fail','--retry','2','--max-time','40',url],{encoding:'utf8',maxBuffer:5000000}));
    assert(Array.isArray(batch)&&batch.length,'Empty data page');
    rows.push(...batch); t=Number(batch.at(-1)[0])+step;
    console.log(`Downloaded ${interval}: ${rows.length}, through ${date(t-step)}`);
  }
  fs.writeFileSync(file,JSON.stringify(rows)); return rows;
}
function ema(v,n){ const a=2/(n+1), r=[v[0]]; for(let i=1;i<v.length;i++)r.push(a*v[i]+(1-a)*r[i-1]);return r; }
function indicators(rows){
  const c=rows.map(r=>+r[4]), e12=ema(c,12),e26=ema(c,26),dif=c.map((_,i)=>e12[i]-e26[i]), dea=ema(dif,9);
  const tr=rows.map((r,i)=>Math.max(+r[2]-r[3],i?Math.abs(r[2]-c[i-1]):0,i?Math.abs(r[3]-c[i-1]):0));
  const atr=tr.map(()=>NaN);atr[13]=tr.slice(0,14).reduce((a,b)=>a+b,0)/14;for(let i=14;i<tr.length;i++)atr[i]=(13*atr[i-1]+tr[i])/14;
  return rows.map((r,i)=>({t:+r[0],o:+r[1],h:+r[2],l:+r[3],c:c[i],dif:dif[i],dea:dea[i],hist:dif[i]-dea[i],atr:atr[i]}));
}
function validate(rows,step){
  assert.equal(+rows[0][0],warm); assert.equal(+rows.at(-1)[0],cutoff-step);
  for(let i=0;i<rows.length;i++){
    const r=rows[i];assert.equal(+r[6],+r[0]+step-1);
    assert(+r[3]<=Math.min(+r[1],+r[4]) && +r[2]>=Math.max(+r[1],+r[4]));
    if(i)assert.equal(+r[0]-rows[i-1][0],step);
  }
}
const dailyRaw=download('1d',DAY),fourRaw=download('4h',DAY/6);
validate(dailyRaw,DAY);validate(fourRaw,DAY/6);
const daily=indicators(dailyRaw),four=indicators(fourRaw),fm=new Map(four.map(r=>[r.t,r]));
for(const r of daily){r.four=fm.get(r.t+DAY*5/6);assert(r.four,'Missing last intrabar');}
// Literal sequential translation of MACD.pine state assignments, including quirks.
function originalStates(bars,delayBars=25){
  let tradable=false,delay=0,down=0,up=0,attempt=false,count=0;
  return bars.map((r,i)=>{
    const p=bars[i-1],crossUp=p&&r.dea>0&&p.dea<=0,crossDown=p&&r.dea<0&&p.dea>=0;
    if(crossUp){up=1;down=0;delay=0;attempt=false;count=0;tradable=false;}
    if(crossDown){delay=1;tradable=true;attempt=false;count=0;up=0;}
    else if(delay>0&&delay<delayBars){delay++;tradable=true;}
    else if(delay>=delayBars)tradable=false;
    if(up>0&&up<2&&r.dea>0){up++;tradable=false;}
    else if(up>=2){tradable=true;up=0;}
    if(!tradable&&!attempt&&up===0)down++;else if(tradable)down=0;
    if(r.dea<0){
      if(r.dea>-60&&!attempt){attempt=true;count=1;tradable=true;}
      else if(attempt){count++;if(count<=8)tradable=true;else{attempt=false;count=0;tradable=false;}}
    }
    const transition=delay>0&&delay<delayBars, rising=r.dea>0&&tradable&&delay===0&&!attempt,breakout=attempt&&count>0&&r.dea<80,falling=!tradable;
    return {long:rising||breakout,short:falling,name:rising?'up':transition?'transition':breakout?'attempt':falling?'down':'unclassified',transition,breakout};
  });
}
const variants=[
  {id:'original',label:'原策略21/52',fast:21,exit:'cross',regime:'original',short:true},
  {id:'long_only',label:'原策略仅做多',fast:21,exit:'cross',regime:'original',short:false},
  {id:'ema25',label:'只改EMA25',fast:25,exit:'cross',regime:'original',short:false},
  {id:'level',label:'EMA25+收盘低于52−300',fast:25,exit:'level',regime:'original',short:false},
  {id:'confirm',label:'EMA25+连续2日低于52',fast:25,exit:'confirm',regime:'original',short:false},
  {id:'trail',label:'EMA25+3ATR收盘移动退出',fast:25,exit:'trail',regime:'original',short:false,atrMult:3},
  {id:'delay5',label:'EMA25+下跌确认5日',fast:25,exit:'level',regime:'original',short:false,delay:5},
  {id:'structural',label:'EMA25+结构线段+52退出',fast:25,exit:'level',regime:'structural',short:false},
  {id:'structural_trail',label:'结构线段+3ATR移动退出',fast:25,exit:'trail',regime:'structural',short:false,atrMult:3},
];
// Candidate list fixed before examining results. Train: 2024 only, validation: 2025, test: 2026.
function run(v,{from=start,to=cutoff,initial=10000,notional=10000,slip=0,fee=.001,bars=daily}={}){
  const efast=ema(bars.map(r=>r.c),v.fast),e52=ema(bars.map(r=>r.c),52),states=originalStates(bars,v.delay||25);
  let cash=initial,pos=null,pending=null,first=false,peak=initial,maxDD=0,maxCloseDD=0,closePeak=initial,exposure=0,fees=0;
  const trades=[],curve=[],signals=[];
  for(let i=1;i<bars.length;i++){
    const r=bars[i],p=bars[i-1];if(r.t<from||r.t>=to)continue;
    if(pending){
      const px=r.o*(1+pending.side*(pending.kind==='entry'?1:-1)*slip);
      if(pending.kind==='entry'){
        const qty=notional/px,entryFee=notional*fee;cash-=entryFee;fees+=entryFee;
        pos={side:pending.side,qty,entry:px,t:r.t,signal:pending.t,fee:entryFee,maxHigh:r.h,minLow:r.l,trail:NaN};
      }else{
        const exitFee=pos.qty*px*fee,net=pos.qty*pos.side*(px-pos.entry)-pos.fee-exitFee;cash+=pos.qty*pos.side*(px-pos.entry)-exitFee;fees+=exitFee;
        trades.push({entryDate:date(pos.t),exitDate:date(r.t),side:pos.side,entry:pos.entry,exit:px,net,returnPct:net/notional*100,days:(r.t-pos.t)/DAY,reason:pending.reason,mfePct:(pos.side===1?pos.maxHigh/pos.entry-1:1-pos.minLow/pos.entry)*100});pos=null;
      }pending=null;
    }
    const preEquity=cash+(pos?pos.qty*pos.side*(r.o-pos.entry):0);peak=Math.max(peak,preEquity);
    if(pos){
      exposure++;const adverse=pos.side===1?r.l:r.h;const lowEquity=cash+pos.qty*pos.side*(adverse-pos.entry);
      maxDD=Math.max(maxDD,(peak-lowEquity)/peak);
      pos.maxHigh=Math.max(pos.maxHigh,r.h);pos.minLow=Math.min(pos.minLow,r.l);
      // Trail only ratchets upward; checked at close, never filled retrospectively intrabar.
      const next=pos.maxHigh-(v.atrMult||3)*r.atr;pos.trail=Number.isFinite(pos.trail)?Math.max(pos.trail,next):next;
    }
    const equity=cash+(pos?pos.qty*pos.side*(r.c-pos.entry):0);peak=Math.max(peak,equity);closePeak=Math.max(closePeak,equity);
    maxDD=Math.max(maxDD,(peak-equity)/peak);maxCloseDD=Math.max(maxCloseDD,(closePeak-equity)/closePeak);
    let state=states[i],longAllowed=state.long;
    if(v.regime==='structural'){
      const up=efast[i]>e52[i]&&e52[i]>e52[i-1]&&r.dea>0;
      const down=efast[i]<e52[i]&&e52[i]<e52[i-1]&&r.dea<0;
      state={...state,name:up?'up':down?'down':'transition'};
      longAllowed=up; // A confirmed regime can trigger entry even without a new price cross.
    }
    const crossAbove=r.c>efast[i]&&p.c<=efast[i-1],crossBelow=r.c<efast[i]&&p.c>=efast[i-1];
    const filterLong=v.regime==='structural'||v.no4h||r.four.dif<=1500;
    let reason=null;
    if(pos){
      if(pos.side===-1){if(r.c>e52[i]&&p.c<=e52[i-1])reason='EMA52 cross';}
      else if(v.exit==='cross'){if(r.c<e52[i]-300&&p.c>=e52[i-1]-300)reason='EMA52-300 cross';}
      else if(v.exit==='level'){if(r.c<e52[i]-300)reason='EMA52-300 level';}
      else if(v.exit==='ema52'){if(r.c<e52[i])reason='EMA52 level';}
      else if(v.exit==='confirm'){if(r.c<e52[i]&&p.c<e52[i-1])reason='2 closes below EMA52';}
      else if(v.exit==='trail'){if(r.c<e52[i]-300||r.c<pos.trail)reason=r.c<pos.trail?'ATR trail close':'EMA52-300 level';}
      if(reason)pending={kind:'exit',side:pos.side,t:r.t,reason};
    }else{
      const trigger=v.regime==='structural'?r.c>efast[i]:crossAbove||(v.rearm&&state.long&&!states[i-1].long&&r.c>efast[i]);
      const trendPass=!v.filter||v.filter({i,r,bars,efast,e52});
      if(trigger&&longAllowed&&filterLong&&trendPass){pending={kind:'entry',side:1,t:r.t};first=true;}
      else if(v.short&&crossBelow&&state.short&&r.four.dea>=-1500&&first)pending={kind:'entry',side:-1,t:r.t};
    }
    curve.push({date:date(r.t),equity,close:r.c,state:state.name,side:pos?.side||0,emaFast:efast[i],ema52:e52[i],dea:r.dea,fourDif:r.four.dif,priceCross:crossAbove,longAllowed,filterLong});
    if(pending)signals.push({date:date(r.t),...pending});
  }
  const profits=trades.filter(t=>t.net>0).reduce((a,t)=>a+t.net,0),loss=-trades.filter(t=>t.net<0).reduce((a,t)=>a+t.net,0);
  const last=curve.at(-1),firstBar=bars.find(r=>r.t>=from&&r.t<to),lastBar=bars.filter(r=>r.t>=from&&r.t<to).at(-1);
  const holdQty=notional/(firstBar.o*(1+slip)),holdPnl=holdQty*(lastBar.c-firstBar.o*(1+slip))-notional*fee;
  let hp=initial,hdd=0;for(const r of bars)if(r.t>=from&&r.t<to){const e=initial+holdQty*(r.c-firstBar.o*(1+slip))-notional*fee;hp=Math.max(hp,e);hdd=Math.max(hdd,(hp-e)/hp);}
  return {id:v.id,returnPct:(last.equity/initial-1)*100,realizedPct:trades.reduce((a,t)=>a+t.net,0)/initial*100,closeDD:maxCloseDD*100,drawdown:maxDD*100,trades:trades.length,winPct:trades.length?trades.filter(t=>t.net>0).length/trades.length*100:0,pf:loss?profits/loss:null,exposurePct:exposure/curve.length*100,fees,open:pos?{side:pos.side,entryDate:date(pos.t),entry:pos.entry,unrealized:pos.qty*pos.side*(lastBar.c-pos.entry)}:null,pending,holdReturnPct:holdPnl/initial*100,holdCloseDD:hdd*100,tradeLog:trades,curve,signals};
}
const compact=r=>Object.fromEntries(Object.entries(r).filter(([k])=>!['tradeLog','curve','signals','pending'].includes(k)));
const periods={train:{from:start,to:Date.parse('2025-01-01')},validation:{from:Date.parse('2025-01-01'),to:Date.parse('2026-01-01')},test:{from:Date.parse('2026-01-01'),to:cutoff}};
const train=variants.map(v=>({v,r:run(v,periods.train)}));
// Select only on 2024: maximize net return / max(close drawdown,5%), require >=3 closed trades.
const ranked=train.filter(x=>!x.v.short&&x.r.trades>=3).sort((a,b)=>b.r.returnPct/Math.max(b.r.closeDD,5)-a.r.returnPct/Math.max(a.r.closeDD,5));
const selected=ranked[0].v;
// Added after first pass to diagnose entry-event loss: exploratory, NOT fresh holdout tests.
const exploratoryConfigs=[
  {id:'pure52',fast:25,exit:'ema52',regime:'original',short:false},
  {id:'rearm',fast:25,exit:'cross',regime:'original',short:false,rearm:true},
  {id:'no4h',fast:25,exit:'cross',regime:'original',short:false,no4h:true},
  {id:'rearm_pure52',fast:25,exit:'ema52',regime:'original',short:false,rearm:true},
];
const exploratory=exploratoryConfigs.map(v=>({config:v,full:compact(run(v)),...Object.fromEntries(Object.entries(periods).map(([k,opt])=>[k,compact(run(v,opt))]))}));
const all=variants.map(v=>({config:v,full:compact(run(v)),...Object.fromEntries(Object.entries(periods).map(([k,opt])=>[k,compact(run(v,opt))]))}));
const sensitivities=[20,21,25,30].map(fast=>({fast,...Object.fromEntries(Object.entries(periods).map(([k,opt])=>[k,compact(run({...selected,fast},opt))]))}));
const costs=[0,.0005,.001].map(slip=>({slippageBps:slip*10000,original:compact(run(variants[0],{slip})),selected:compact(run(selected,{slip}))}));
const orig=run(variants[0]),best=run(selected),states=originalStates(daily);
const stateCounts={};let overlap=0;for(let i=0;i<daily.length;i++)if(daily[i].t>=start){const s=states[i];stateCounts[s.name]=(stateCounts[s.name]||0)+1;if(s.transition&&s.breakout)overlap++;}
// Quarterly windows fixed by calendar, not handpicked troughs and peaks.
const quarters=[];for(let y=2024;y<=2026;y++)for(let m=0;m<12;m+=3){let from=Date.UTC(y,m,1),to=Math.min(Date.UTC(y,m+3,1),cutoff);if(from>=cutoff)continue;const idx=orig.curve.findIndex(r=>r.date>=date(from)),end=orig.curve.findLastIndex(r=>r.date<date(to));const b=daily.find(r=>r.t>=from),e=daily.filter(r=>r.t<to).at(-1);quarters.push({period:`${y}Q${m/3+1}`,btcPct:(e.c/b.o-1)*100,originalPnl:orig.curve[end].equity-(idx?orig.curve[idx-1].equity:10000),selectedPnl:best.curve[end].equity-(idx?best.curve[idx-1].equity:10000)});}
const sourceHash=createHash('sha256').update(fs.readFileSync(path.join(dir,'../MACD.pine'))).digest('hex');
const hashes=Object.fromEntries(['1d','4h'].map(i=>[i,createHash('sha256').update(fs.readFileSync(path.join(dir,`BTCUSDT-${i}.json`))).digest('hex')]));
const summary={sourceHash,dataHashes:hashes,source:'BINANCE:BTCUSDT spot',start:date(start),end:date(cutoff-DAY),warmupStart:date(warm),dailyCount:daily.length,fourHourCount:four.length,evaluationDays:orig.curve.length,selected:selected.id,selectionRule:'2024 return/max(close DD,5), >=3 closed trades, long-only candidates',all,exploratory,sensitivities,costs,originalSizing:compact(run(variants[0],{initial:50,notional:200})),stateCounts,overlap,quarters};
function csv(file,rows){const keys=Object.keys(rows[0]||{});fs.writeFileSync(path.join(dir,file),keys.join(',')+'\n'+rows.map(r=>keys.map(k=>JSON.stringify(r[k]??'')).join(',')).join('\n')+'\n');}
fs.writeFileSync(path.join(dir,'results.json'),JSON.stringify(summary,null,2));
csv('original-trades.csv',orig.tradeLog);csv('selected-trades.csv',best.tradeLog);csv('original-equity.csv',orig.curve);csv('selected-equity.csv',best.curve);
for(const v of [...variants,...exploratoryConfigs])csv(`${v.id}-trades.csv`,run(v).tradeLog);
// Meaningful reproducibility checks: future truncation cannot change previous equity or signals.
const prefix=run(selected,{bars:daily.filter(r=>r.t<Date.parse('2025-01-01'))});
assert.deepEqual(prefix.curve,best.curve.filter(r=>r.date<'2025-01-01'));
const prefixO=run(variants[0],{bars:daily.filter(r=>r.t<Date.parse('2025-01-01'))});
assert.deepEqual(prefixO.curve,orig.curve.filter(r=>r.date<'2025-01-01'));
assert(Math.abs(orig.curve.at(-1).equity-(10000+orig.tradeLog.reduce((a,t)=>a+t.net,0)+(orig.open?orig.open.unrealized-10000*.001:0)))<1e-7);
// State-machine boundary check: positive crossing bar pending, next bar confirms up.
const synthetic=originalStates([-5,5,6].map(dea=>({dea})));
assert.equal(synthetic[1].long,false);assert.equal(synthetic[2].name,'up');
// An under-zero attempt remains active even when DEA leaves its -60 threshold.
assert.equal(originalStates([-100,-50,-500].map(dea=>({dea})))[2].long,true);
console.log(JSON.stringify({selected:selected.id,table:[...all,...exploratory].map(r=>({id:r.config.id,full:r.full.returnPct,dd:r.full.closeDD,realized:r.full.realizedPct,train:r.train.returnPct,validation:r.validation.returnPct,test:r.test.returnPct})),checks:'OHLC continuity, intrabar mapping, prefix invariance, state boundaries and accounting passed'},null,2));
export { run, daily, compact, periods, csv, dir };
