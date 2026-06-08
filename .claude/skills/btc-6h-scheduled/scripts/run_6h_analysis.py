#!/usr/bin/env python3
"""
BTC 6 小时定时综合分析编排器

每 6 小时运行一次，对 BTC 6h 进行综合分析，结合：
  1. 动能理论（btc-momentum-analyzer）—— 多时间级别线段 + 机械买卖点信号
  2. 缩量放量 / 能量柱跳空（btc-volume-jump-analyzer）—— 6h 量价与跳空信号

并保证 MACD 与 K 线数据精确（直接复用 IndicatorCalculator 的指标计算）。

流程：
  1. 尝试增量更新数据库（OKX/Binance）。网络被屏蔽时回退到现有数据库。
  2. 读取 1d / 12h / 6h / 4h 精确指标数据。
  3. 运行动能理论机械买卖点检测（trading_signals）。
  4. 运行缩量放量 / 跳空分析（analyze_volume_jump）。
  5. 把综合报告写入 data/analysis_reports/<时间戳>_6h_combined.md

注意：动能理论中需要“看 MACD 形态判断”的部分（线段确认、背离、单位周期）
由 Claude 在读取本报告与 THEORY.md 后完成；本脚本只产出精确数据 + 机械信号，
确保定时任务即使无人值守也能留下可追溯的精确快照。

用法：
  python3 run_6h_analysis.py                  # 更新数据库并生成报告
  python3 run_6h_analysis.py --no-update      # 跳过更新，直接用现有数据库
  python3 run_6h_analysis.py --timeframes 1d,12h,6h,4h
"""

import argparse
import json
import os
import sys
from datetime import datetime

# 路径定位
_THIS = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS, "..", "..", "..", ".."))
_DATA_DIR = os.environ.get("MACD_DATA_DIR", os.path.join(_REPO_ROOT, "data"))
_REPORTS_DIR = os.path.join(_DATA_DIR, "analysis_reports")
_MOMENTUM_SCRIPTS = os.path.join(_REPO_ROOT, ".claude", "skills", "btc-momentum-analyzer", "scripts")
_JUMP_SCRIPTS = os.path.join(_REPO_ROOT, ".claude", "skills", "btc-volume-jump-analyzer", "scripts")

sys.path.insert(0, _MOMENTUM_SCRIPTS)
sys.path.insert(0, _JUMP_SCRIPTS)

from database_manager import BTCDatabase  # noqa: E402
from trading_signals import analyze_trading_signals  # noqa: E402
import analyze_volume_jump as vj  # noqa: E402


def try_update(db: BTCDatabase, timeframes, do_update: bool) -> str:
    """尝试增量更新数据库，失败则回退。返回状态描述。"""
    if not do_update:
        return "跳过更新（--no-update），使用数据库现有数据"
    try:
        db.update_database(timeframes)
        return "数据库已尝试增量更新（网络可用时为最新行情）"
    except Exception as e:  # 网络被屏蔽 / API 失败
        return f"更新失败，回退到现有数据库（原因: {e}）"


def segment_state(last_candle) -> str:
    dea = last_candle.get("dea")
    if dea is None:
        return "数据不足"
    if dea > 0:
        return "上涨线段(DEA>0)"
    if dea < 0:
        return "下跌线段(DEA<0)"
    return "零轴"


def build_markdown(db_dict, timeframes, vj_report, signals, update_status) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    L = []
    L.append(f"# BTC 6 小时定时综合分析报告")
    L.append("")
    L.append(f"- 生成时间: {now}")
    L.append(f"- 数据状态: {update_status}")
    L.append(f"- 数据库最后更新: {db_dict.get('last_updated', 'unknown')}")
    L.append("")

    # 多时间级别线段速览
    L.append("## 一、多时间级别线段速览（精确 MACD）")
    L.append("")
    L.append("| 级别 | 最新K线 | 收盘 | DIF | DEA | Hist | 线段 |")
    L.append("|------|---------|------|-----|-----|------|------|")
    for tf in timeframes:
        tfd = db_dict["timeframes"].get(tf)
        if not tfd or not tfd["candles"]:
            L.append(f"| {tf} | - | - | - | - | - | 无数据 |")
            continue
        c = tfd["candles"][-1]
        L.append(f"| {tf} | {c['datetime']} | {c['close']:.1f} | "
                 f"{(c.get('dif') or 0):.1f} | {(c.get('dea') or 0):.1f} | "
                 f"{(c.get('histogram') or 0):.1f} | {segment_state(c)} |")
    L.append("")

    # 动能理论机械买卖点
    L.append("## 二、动能理论机械买卖点（THEORY.md 规则）")
    L.append("")
    for tf in timeframes:
        sig = signals.get(tf, {})
        if sig.get("has_signal"):
            L.append(f"- **{tf}**: 🔔 {sig.get('type')} | 进场 {sig.get('entry')} | "
                     f"止损 {sig.get('stop_loss')} | 目标1 {sig.get('target1')} / 目标2 {sig.get('target2')}")
            L.append(f"  - 依据: {sig.get('reason')}")
        else:
            L.append(f"- {tf}: 无机械买卖点 —— {sig.get('reason', '观望')}")
    L.append("")

    # 缩量放量 / 跳空（6h）
    cur = vj_report["current"]
    st = vj_report["strategy_state"]
    L.append("## 三、缩量放量 / 能量柱跳空（6h, jump.pine 逻辑）")
    L.append("")
    L.append(f"- K 线: 收 {cur['close']} 开 {cur['open']} 高 {cur['high']} 低 {cur['low']} ({cur['candle_color']})")
    L.append(f"- EMA26 {cur['ema26']:.1f} / EMA52 {cur['ema52']:.1f} "
             f"({'多头排列' if cur['ema26_above_ema52'] else '空头/纠缠'})")
    L.append(f"- DIF {cur['dif']:.2f} / DEA {cur['dea']:.2f} / Hist {cur['histogram']:.2f} "
             f"({'上涨线段' if cur['is_uptrend'] else '非上涨线段'})")
    L.append(f"- 成交量 {cur['volume']:.2f} / 均量 {cur['vol_ma']:.2f} / 量比 {cur['vol_ratio']:.2f} "
             f"→ **{cur['vol_state']}{cur['candle_color']}**")
    L.append(f"- 跳空策略持仓: **{st['position']}**" +
             (f" | 止损 {st['stop_loss']:.1f}" if st['stop_loss'] is not None else ""))
    if st["current_signal"]:
        s = st["current_signal"]
        L.append(f"- ★ 本根K线信号: **{s.get('action')} @ {s.get('price')}** —— {s.get('reason')}")
    else:
        L.append("- 本根K线: 无新跳空进/出场信号")
    L.append("")
    L.append("### 6h 最近 K 线明细")
    L.append("")
    L.append("| 时间 | O/H/L/C | 量比/状态 | DIF/DEA/Hist |")
    L.append("|------|---------|-----------|--------------|")
    for b in vj_report["recent_bars"]:
        L.append(f"| {b['datetime']} | {b['open']:.0f}/{b['high']:.0f}/{b['low']:.0f}/{b['close']:.0f}({b['color']}) "
                 f"| {b['vol_ratio']:.2f}/{b['vol_state']} | {b['dif']}/{b['dea']}/{b['histogram']} |")
    L.append("")

    # 待 Claude 研判
    L.append("## 四、需结合动能理论研判（Claude）")
    L.append("")
    L.append("以上为精确数据与机械信号。请结合 `THEORY.md` 进一步判断：")
    L.append("- 各级别线段是否确认（DEA 短暂穿零轴的模糊处理）、当前处于第几个单位调整周期")
    L.append("- 连续跳空 / 分立跳空 / 黄白线背离 / 隐形信号 / 归零轴 是否成立")
    L.append("- 大周期（1d/12h）对 6h 的联动与共振/矛盾")
    L.append("- 6h 缩量回调后是否具备放量跳空顺势做多条件")
    L.append("")
    L.append("> 本报告为定时任务自动生成的精确快照，不构成投资建议。")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description="BTC 6h 定时综合分析编排器")
    ap.add_argument("--timeframes", default="1d,12h,6h,4h",
                    help="参与分析的时间级别（默认 1d,12h,6h,4h；6h 为主）")
    ap.add_argument("--no-update", action="store_true", help="跳过数据库更新")
    ap.add_argument("--stop-loss-offset", type=float, default=300)
    ap.add_argument("--zero-axis-threshold", type=float, default=300)
    ap.add_argument("--output", default=None, help="报告输出路径（默认写入 analysis_reports 带时间戳）")
    args = ap.parse_args()

    timeframes = [t.strip() for t in args.timeframes.split(",")]

    db = BTCDatabase()
    update_status = try_update(db, timeframes, do_update=not args.no_update)

    db_dict = db.load_database()
    if not db_dict:
        print("[ERROR] 数据库不存在，请先运行 database_manager.py --init", file=sys.stderr)
        sys.exit(1)

    # 动能理论机械信号
    signals = {}
    for tf in timeframes:
        try:
            signals[tf] = analyze_trading_signals(db_dict, tf)
        except Exception as e:
            signals[tf] = {"has_signal": False, "reason": f"分析异常: {e}"}

    # 缩量放量 / 跳空（6h）
    candles_6h = db_dict["timeframes"]["6h"]["candles"]
    closes = [c["close"] for c in candles_6h]
    ema26 = vj.calc_ema(closes, 26)
    ema52 = vj.calc_ema(closes, 52)
    vj.annotate_volume(candles_6h, 20, 1.5, 0.7)
    sim = vj.simulate_jump_strategy(candles_6h, ema26, ema52,
                                    args.stop_loss_offset, args.zero_axis_threshold)
    vj_report = vj.build_report(candles_6h, ema26, ema52, sim, "6h", {
        "stop_loss_offset": args.stop_loss_offset,
        "zero_axis_threshold": args.zero_axis_threshold,
    }, recent=8)

    md = build_markdown(db_dict, timeframes, vj_report, signals, update_status)

    if args.output:
        out_path = args.output
    else:
        os.makedirs(_REPORTS_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        out_path = os.path.join(_REPORTS_DIR, f"{stamp}_6h_combined.md")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(md + "\n")

    print(f"[SUCCESS] 6h 综合分析报告已生成: {out_path}", file=sys.stderr)
    print(out_path)


if __name__ == "__main__":
    main()
