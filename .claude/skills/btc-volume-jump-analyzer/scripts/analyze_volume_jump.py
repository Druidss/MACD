#!/usr/bin/env python3
"""
缩量放量 / MACD 能量柱跳空分析（jump.pine 的 Python 移植）

本脚本忠实复刻 jump.pine 的进出场逻辑，并在其基础上增加“真实成交量
缩量 / 放量”分析，默认作用于 BTC 6 小时 K 线。

核心来源：
  jump.pine —— MACD 能量柱跳空策略（上涨线段中回调后跳空进场）

两层分析：
  1. 能量柱跳空（histogram 回调→跳空）：完全对齐 jump.pine 的进出场判定
  2. 真实成交量缩放（volume 相对均量）：判断 缩量 / 放量 / 常量

数据来源（按优先级）：
  --input <file>   指定带指标的 JSON（含 candles: open/high/low/close/volume/dif/dea/histogram）
  默认             读取仓库数据库 data/database/btc_database.json

为保证 MACD 与 K 线数据精确：
  - dif / dea / histogram 直接采用数据库中由 IndicatorCalculator 计算的精确值
  - EMA21 / EMA52 由脚本用同一套 EMA 公式从收盘价重新计算（jump.pine 使用 EMA21/52）

用法：
  python3 analyze_volume_jump.py                       # 默认数据库 6h
  python3 analyze_volume_jump.py --timeframe 6h
  python3 analyze_volume_jump.py --input data.json --timeframe 6h --format json
  python3 analyze_volume_jump.py --stop-loss-offset 300 --zero-axis-threshold 300
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# 仓库根目录（脚本位于 <repo>/.claude/skills/btc-volume-jump-analyzer/scripts/）
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_DATA_DIR = os.environ.get("MACD_DATA_DIR", os.path.join(_REPO_ROOT, "data"))
_DB_FILE = os.path.join(_DATA_DIR, "database", "btc_database.json")


def calc_ema(values: List[float], period: int) -> List[Optional[float]]:
    """与 IndicatorCalculator 完全一致的 EMA：前 period-1 个为 None，首值用 SMA。"""
    if len(values) < period:
        return [None] * len(values)
    ema: List[Optional[float]] = [None] * (period - 1)
    multiplier = 2 / (period + 1)
    sma = sum(values[:period]) / period
    ema.append(sma)
    for i in range(period, len(values)):
        ema.append((values[i] - ema[-1]) * multiplier + ema[-1])
    return ema


def load_candles(input_file: Optional[str], timeframe: str) -> List[Dict[str, Any]]:
    """从数据库或指定文件加载指定时间级别的 K 线（含指标）。"""
    path = input_file or _DB_FILE
    if not os.path.exists(path):
        print(f"[ERROR] 数据文件不存在: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 兼容多种结构
    if "timeframes" in data and isinstance(data["timeframes"], dict):
        tf = data["timeframes"].get(timeframe)
        if tf is None:
            print(f"[ERROR] 数据中没有 {timeframe} 时间级别", file=sys.stderr)
            sys.exit(1)
        candles = tf["candles"] if "candles" in tf else tf
    elif "data" in data and isinstance(data["data"], dict):
        candles = data["data"].get(timeframe)
        if candles is None:
            print(f"[ERROR] 数据中没有 {timeframe} 时间级别", file=sys.stderr)
            sys.exit(1)
    elif "candles" in data:
        candles = data["candles"]
    else:
        print("[ERROR] 无法识别的数据结构", file=sys.stderr)
        sys.exit(1)

    if not candles:
        print(f"[ERROR] {timeframe} 无 K 线数据", file=sys.stderr)
        sys.exit(1)
    return candles


def annotate_volume(candles: List[Dict[str, Any]], vol_period: int,
                    expand_th: float, shrink_th: float) -> None:
    """为每根 K 线计算均量、量比，并标注 放量/缩量/常量。原地修改。"""
    vols = [c.get("volume", 0.0) for c in candles]
    for i, c in enumerate(candles):
        start = max(0, i - vol_period + 1)
        window = vols[start:i + 1]
        vol_ma = sum(window) / len(window) if window else 0.0
        ratio = (vols[i] / vol_ma) if vol_ma > 0 else 0.0
        c["vol_ma"] = vol_ma
        c["vol_ratio"] = ratio
        if ratio >= expand_th:
            c["vol_state"] = "放量"
        elif ratio <= shrink_th:
            c["vol_state"] = "缩量"
        else:
            c["vol_state"] = "常量"


def simulate_jump_strategy(candles: List[Dict[str, Any]], ema21: List[Optional[float]],
                           ema52: List[Optional[float]], stop_loss_offset: float,
                           zero_axis_threshold: float) -> Dict[str, Any]:
    """
    忠实复刻 jump.pine 的逐根 K 线状态机，返回当前持仓状态、止损位，
    以及最近一次进/出场信号与“当前这根 K 线是否触发进场”。
    """
    position = 0           # 0 空仓 / 1 持多
    stop_loss: Optional[float] = None
    had_pullback = False
    events: List[Dict[str, Any]] = []   # 历史进出场事件
    current_signal: Optional[Dict[str, Any]] = None  # 最新一根 K 线产生的信号

    n = len(candles)
    for i in range(n):
        c = candles[i]
        hist = c.get("histogram")
        dea = c.get("dea")
        e21 = ema21[i]
        e52 = ema52[i]
        is_last = (i == n - 1)

        # 指标未就绪
        if hist is None or dea is None or e21 is None or e52 is None or i == 0:
            continue
        prev = candles[i - 1]
        hist1 = prev.get("histogram")
        if hist1 is None:
            continue

        is_uptrend = dea > 0
        entered_this_bar = False
        entry_reason = None

        # ---------- 空仓：等待跳空进场 ----------
        if position == 0 and is_uptrend and e21 > e52 and c["close"] > e52 - stop_loss_offset:
            # 绿柱回调
            if hist >= 0 and hist1 >= 0 and hist < hist1:
                had_pullback = True
            # 红柱回调（红柱变大）
            elif hist < 0 and hist1 < 0 and hist > hist1:
                had_pullback = True

            # 跳空进场：回调后再次顺势 + 阳线 + DEA>0
            if had_pullback and c["close"] > c["open"] and dea > 0:
                if hist >= 0 and hist1 >= 0 and hist > hist1:
                    position = 1
                    stop_loss = c["open"] - stop_loss_offset
                    had_pullback = False
                    entered_this_bar = True
                    entry_reason = "绿柱回调后跳空（顺势放量）"
                elif hist < 0 and hist1 < 0 and hist < hist1:
                    position = 1
                    stop_loss = c["open"] - stop_loss_offset
                    had_pullback = False
                    entered_this_bar = True
                    entry_reason = "红柱回调后再次缩小（零轴下方跳空）"

        # ---------- 零轴附近缩量进场 ----------
        if position == 0 and e21 > e52 and dea > 0 and c["close"] > e52 - stop_loss_offset:
            near_zero = 0 < dea <= zero_axis_threshold
            red_shrinking = hist < 0 and hist1 < 0 and hist > hist1
            if near_zero and red_shrinking and c["close"] > c["open"]:
                position = 1
                stop_loss = c["open"] - stop_loss_offset
                entered_this_bar = True
                entry_reason = "零轴附近红柱缩量阳线进场"
        elif not is_uptrend:
            had_pullback = False

        if entered_this_bar:
            ev = {
                "type": "ENTRY",
                "datetime": c["datetime"],
                "price": c["close"],
                "stop_loss": stop_loss,
                "reason": entry_reason,
            }
            events.append(ev)
            if is_last:
                current_signal = {**ev, "action": "开多", "is_current_bar": True}

        # ---------- 持仓：止损管理 ----------
        if position == 1:
            if is_uptrend:
                if hist >= 0 and hist1 >= 0 and hist < hist1:
                    had_pullback = True
                elif hist < 0 and hist1 < 0 and hist > hist1:
                    had_pullback = True
                if had_pullback:
                    # 跳空上移止损到前一根 open - offset
                    if hist >= 0 and hist1 >= 0 and hist > hist1:
                        stop_loss = prev["open"] - stop_loss_offset
                        had_pullback = False
                    elif hist < 0 and hist1 < 0 and hist < hist1:
                        stop_loss = prev["open"] - stop_loss_offset
                        had_pullback = False

            # 跌破止损
            if stop_loss is not None and c["close"] < stop_loss:
                ev = {"type": "EXIT", "datetime": c["datetime"], "price": c["close"],
                      "reason": "止损出场（跌破止损线）"}
                events.append(ev)
                position = 0
                stop_loss = None
                had_pullback = False
                if is_last:
                    current_signal = {**ev, "action": "平多", "is_current_bar": True}

            # 离开上涨线段平仓
            if not is_uptrend and position == 1:
                ev = {"type": "EXIT", "datetime": c["datetime"], "price": c["close"],
                      "reason": "离开上涨线段平仓"}
                events.append(ev)
                position = 0
                stop_loss = None
                had_pullback = False
                if is_last:
                    current_signal = {**ev, "action": "平多", "is_current_bar": True}

    return {
        "position": position,
        "stop_loss": stop_loss,
        "had_pullback": had_pullback,
        "events": events,
        "current_signal": current_signal,
    }


def build_report(candles, ema21, ema52, sim, timeframe, params, recent=8) -> Dict[str, Any]:
    last = candles[-1]
    i = len(candles) - 1
    return {
        "timeframe": timeframe,
        "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_candle_time": last["datetime"],
        "params": params,
        "current": {
            "close": last["close"],
            "open": last["open"],
            "high": last["high"],
            "low": last["low"],
            "candle_color": "阳线" if last["close"] > last["open"] else ("阴线" if last["close"] < last["open"] else "十字"),
            "volume": last.get("volume"),
            "vol_ma": last.get("vol_ma"),
            "vol_ratio": last.get("vol_ratio"),
            "vol_state": last.get("vol_state"),
            "ema21": ema21[i],
            "ema52": ema52[i],
            "dif": last.get("dif"),
            "dea": last.get("dea"),
            "histogram": last.get("histogram"),
            "is_uptrend": (last.get("dea") or 0) > 0,
            "ema21_above_ema52": (ema21[i] is not None and ema52[i] is not None and ema21[i] > ema52[i]),
        },
        "strategy_state": {
            "position": "持多" if sim["position"] == 1 else "空仓",
            "stop_loss": sim["stop_loss"],
            "current_signal": sim["current_signal"],
            "recent_events": sim["events"][-5:],
        },
        "recent_bars": [
            {
                "datetime": c["datetime"],
                "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"],
                "color": "阳" if c["close"] > c["open"] else ("阴" if c["close"] < c["open"] else "—"),
                "volume": round(c.get("volume", 0), 2),
                "vol_ratio": round(c.get("vol_ratio", 0), 2),
                "vol_state": c.get("vol_state"),
                "dif": round(c["dif"], 1) if c.get("dif") is not None else None,
                "dea": round(c["dea"], 1) if c.get("dea") is not None else None,
                "histogram": round(c["histogram"], 1) if c.get("histogram") is not None else None,
                "ema21": round(ema21[len(candles) - recent + j], 1) if ema21[len(candles) - recent + j] is not None else None,
                "ema52": round(ema52[len(candles) - recent + j], 1) if ema52[len(candles) - recent + j] is not None else None,
            }
            for j, c in enumerate(candles[-recent:])
        ],
    }


def format_text(rep: Dict[str, Any]) -> str:
    cur = rep["current"]
    st = rep["strategy_state"]
    L = []
    L.append("=" * 64)
    L.append(f"BTC 缩量放量 / 能量柱跳空分析（{rep['timeframe']}）")
    L.append(f"分析时间: {rep['analysis_time']}  |  最新K线: {rep['last_candle_time']}")
    L.append("=" * 64)
    L.append("")
    L.append("【当前 K 线 / MACD（精确值）】")
    L.append(f"  收盘 {cur['close']}  开盘 {cur['open']}  高 {cur['high']}  低 {cur['low']}  ({cur['candle_color']})")
    L.append(f"  EMA21 {cur['ema21']:.1f}   EMA52 {cur['ema52']:.1f}   "
             f"({'EMA21>EMA52 多头排列' if cur['ema21_above_ema52'] else 'EMA21<EMA52 空头/纠缠'})")
    L.append(f"  DIF {cur['dif']:.2f}   DEA {cur['dea']:.2f}   Histogram {cur['histogram']:.2f}   "
             f"({'上涨线段 DEA>0' if cur['is_uptrend'] else '非上涨线段 DEA<=0'})")
    L.append("")
    L.append("【成交量 缩量/放量】")
    L.append(f"  成交量 {cur['volume']:.2f}   均量(MA) {cur['vol_ma']:.2f}   "
             f"量比 {cur['vol_ratio']:.2f}   →  {cur['vol_state']}")
    combo = f"{cur['vol_state']}{cur['candle_color']}"
    L.append(f"  量价组合: {combo}")
    L.append("")
    L.append("【跳空策略状态（jump.pine 逻辑）】")
    L.append(f"  当前持仓: {st['position']}")
    if st["stop_loss"] is not None:
        L.append(f"  止损位: {st['stop_loss']:.1f}")
    sig = st["current_signal"]
    if sig:
        L.append(f"  ★ 本根K线信号: {sig.get('action')} @ {sig.get('price')}  ——  {sig.get('reason')}")
    else:
        L.append("  本根K线: 无新进/出场信号")
    if st["recent_events"]:
        L.append("  最近事件:")
        for e in st["recent_events"]:
            sl = f"  止损={e['stop_loss']:.1f}" if e.get("stop_loss") is not None else ""
            L.append(f"    {e['datetime']}  {e['type']}  @ {e['price']}  {e['reason']}{sl}")
    L.append("")
    L.append("【最近 K 线明细】")
    L.append("  时间                O/H/L/C                          量比/状态   DIF/DEA/Hist")
    for b in rep["recent_bars"]:
        L.append(f"  {b['datetime']}  {b['open']:.0f}/{b['high']:.0f}/{b['low']:.0f}/{b['close']:.0f}({b['color']})"
                 f"  {b['vol_ratio']:.2f}/{b['vol_state']}"
                 f"  {b['dif']}/{b['dea']}/{b['histogram']}")
    L.append("")
    L.append("注: 本报告为机械信号与精确数据，最终交易判断需结合动能理论（THEORY.md）。")
    L.append("=" * 64)
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="缩量放量 / MACD 能量柱跳空分析（jump.pine 移植）")
    ap.add_argument("--timeframe", default="6h", help="时间级别（默认 6h）")
    ap.add_argument("--input", default=None, help="带指标的 JSON 文件（默认读仓库数据库）")
    ap.add_argument("--stop-loss-offset", type=float, default=300, help="止损幅度（默认 300，源自 jump.pine）")
    ap.add_argument("--zero-axis-threshold", type=float, default=300, help="零轴附近阈值（默认 300）")
    ap.add_argument("--vol-period", type=int, default=20, help="均量周期（默认 20）")
    ap.add_argument("--expand-threshold", type=float, default=1.5, help="放量量比阈值（默认 1.5）")
    ap.add_argument("--shrink-threshold", type=float, default=0.7, help="缩量量比阈值（默认 0.7）")
    ap.add_argument("--recent", type=int, default=8, help="明细展示的最近 K 线数（默认 8）")
    ap.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    ap.add_argument("--output", default=None, help="输出文件（默认 stdout）")
    args = ap.parse_args()

    candles = load_candles(args.input, args.timeframe)
    closes = [c["close"] for c in candles]
    ema21 = calc_ema(closes, 21)
    ema52 = calc_ema(closes, 52)

    annotate_volume(candles, args.vol_period, args.expand_threshold, args.shrink_threshold)
    sim = simulate_jump_strategy(candles, ema21, ema52,
                                 args.stop_loss_offset, args.zero_axis_threshold)

    params = {
        "stop_loss_offset": args.stop_loss_offset,
        "zero_axis_threshold": args.zero_axis_threshold,
        "vol_period": args.vol_period,
        "expand_threshold": args.expand_threshold,
        "shrink_threshold": args.shrink_threshold,
    }
    rep = build_report(candles, ema21, ema52, sim, args.timeframe, params, args.recent)

    out = json.dumps(rep, ensure_ascii=False, indent=2) if args.format == "json" else format_text(rep)
    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print(f"[INFO] 报告已写入 {args.output}", file=sys.stderr)
    else:
        print(out)


if __name__ == "__main__":
    main()
