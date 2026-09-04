#!/usr/bin/env python3
"""
Binance direct BTC momentum report.

This is the lightweight replacement for the old "fetch -> merge database ->
read database -> report" flow.  Each run fetches fresh Binance klines, keeps
only confirmed candles by default, calculates EMA26/EMA52 + MACD in memory, and
prints/writes a reusable momentum-theory report focused on the 6h timeframe.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib import error, parse, request


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPORTS_DIR = os.path.join(REPO_ROOT, "data", "analysis_reports")

DEFAULT_TIMEFRAMES = ["1d", "12h", "6h", "4h", "2h", "1h", "30m"]
BINANCE_INTERVALS = {
    "1d": "1d",
    "12h": "12h",
    "6h": "6h",
    "4h": "4h",
    "2h": "2h",
    "1h": "1h",
    "30m": "30m",
}

MARKET_ENDPOINTS = {
    "futures": "https://fapi.binance.com/fapi/v1/klines",
    "spot": "https://api.binance.com/api/v3/klines",
}

# THEORY.md says the zero-axis threshold should scale by timeframe.  These are
# intentionally conservative and shown in every report so the user can audit
# the "near zero axis" judgment instead of treating it as hidden magic.
ZERO_AXIS_DEA_THRESHOLD = {
    "30m": 70.0,
    "1h": 100.0,
    "2h": 140.0,
    "4h": 220.0,
    "6h": 300.0,
    "12h": 450.0,
    "1d": 650.0,
    "2d": 900.0,
}

PRICE_NEAR_EMA52_PCT = 0.01


@dataclass
class TimeframeAnalysis:
    timeframe: str
    last_open_time_utc: str
    last_close_time_utc: str
    close: float
    ema26: Optional[float]
    ema52: Optional[float]
    dif: Optional[float]
    dea: Optional[float]
    histogram: Optional[float]
    segment: str
    segment_bars: Optional[int]
    unit_phase: str
    u2_status: str
    zero_axis_status: str
    price_vs_ema52_pct: Optional[float]
    hist_state: str
    dif_dea_state: str
    notes: List[str]


def fmt_ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def fmt_num(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:,.{digits}f}"


def sign(value: Optional[float]) -> int:
    if value is None:
        return 0
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def calculate_ema(values: List[float], period: int) -> List[Optional[float]]:
    if len(values) < period:
        return [None] * len(values)
    ema: List[Optional[float]] = [None] * (period - 1)
    multiplier = 2 / (period + 1)
    current = sum(values[:period]) / period
    ema.append(current)
    for value in values[period:]:
        current = (value - current) * multiplier + current
        ema.append(current)
    return ema


def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal_period: int = 9) -> Dict[str, List[Optional[float]]]:
    ema_fast = calculate_ema(closes, fast)
    ema_slow = calculate_ema(closes, slow)

    dif: List[Optional[float]] = []
    for fast_v, slow_v in zip(ema_fast, ema_slow):
        dif.append(fast_v - slow_v if fast_v is not None and slow_v is not None else None)

    valid_dif = [x for x in dif if x is not None]
    if len(valid_dif) < signal_period:
        dea = [None] * len(dif)
    else:
        dea_values = calculate_ema(valid_dif, signal_period)
        dea = [None] * (len(dif) - len(dea_values)) + dea_values

    histogram: List[Optional[float]] = []
    for dif_v, dea_v in zip(dif, dea):
        histogram.append(dif_v - dea_v if dif_v is not None and dea_v is not None else None)

    return {"dif": dif, "dea": dea, "histogram": histogram}


def annotate_indicators(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    closes = [c["close"] for c in candles]
    ema26 = calculate_ema(closes, 26)
    ema52 = calculate_ema(closes, 52)
    macd = calculate_macd(closes, 12, 26, 9)

    out: List[Dict[str, Any]] = []
    for i, candle in enumerate(candles):
        enriched = dict(candle)
        enriched["ema26"] = ema26[i]
        enriched["ema52"] = ema52[i]
        enriched["dif"] = macd["dif"][i]
        enriched["dea"] = macd["dea"][i]
        enriched["histogram"] = macd["histogram"][i]
        out.append(enriched)
    return out


def binance_url(market: str) -> str:
    try:
        return MARKET_ENDPOINTS[market]
    except KeyError:
        raise ValueError(f"unsupported market {market!r}; choose one of {', '.join(MARKET_ENDPOINTS)}")


def parse_binance_kline(row: List[Any], now_ms: int) -> Dict[str, Any]:
    open_time = int(row[0])
    close_time = int(row[6])
    return {
        "open_time": open_time,
        "close_time": close_time,
        "datetime": fmt_ts(open_time),
        "close_datetime": fmt_ts(close_time),
        "open": float(row[1]),
        "high": float(row[2]),
        "low": float(row[3]),
        "close": float(row[4]),
        "volume": float(row[5]),
        "quote_volume": float(row[7]),
        "trades": int(row[8]),
        "closed": close_time < now_ms,
    }


def fetch_binance_klines(symbol: str, timeframe: str, market: str, limit: int, include_open_candle: bool) -> List[Dict[str, Any]]:
    if timeframe not in BINANCE_INTERVALS:
        raise ValueError(f"Binance has no native interval for {timeframe}; native={','.join(BINANCE_INTERVALS)}")

    params = {
        "symbol": symbol,
        "interval": BINANCE_INTERVALS[timeframe],
        "limit": str(min(max(limit, 60), 1000)),
    }
    url = f"{binance_url(market)}?{parse.urlencode(params)}"
    req = request.Request(url, headers={"User-Agent": "MACD-momentum-report/1.0"})

    with request.urlopen(req, timeout=20) as response:
        raw = json.loads(response.read().decode("utf-8"))

    if not isinstance(raw, list):
        raise RuntimeError(f"unexpected Binance response: {raw}")

    now_ms = int(time.time() * 1000)
    candles = [parse_binance_kline(row, now_ms) for row in raw]
    if not include_open_candle:
        candles = [c for c in candles if c["closed"]]
    return candles


def derive_2d_from_1d(candles_1d: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    closed = [c for c in candles_1d if c["closed"]]
    if len(closed) % 2 == 1:
        closed = closed[1:]

    derived: List[Dict[str, Any]] = []
    for i in range(0, len(closed), 2):
        group = closed[i : i + 2]
        if len(group) < 2:
            continue
        first, second = group[0], group[1]
        derived.append({
            "open_time": first["open_time"],
            "close_time": second["close_time"],
            "datetime": first["datetime"],
            "close_datetime": second["close_datetime"],
            "open": first["open"],
            "high": max(x["high"] for x in group),
            "low": min(x["low"] for x in group),
            "close": second["close"],
            "volume": sum(x["volume"] for x in group),
            "quote_volume": sum(x["quote_volume"] for x in group),
            "trades": sum(x["trades"] for x in group),
            "closed": all(x["closed"] for x in group),
            "derived_from": "1d UTC pairs",
        })
    return derived[-limit:]


def fetch_all_timeframes(symbol: str, market: str, timeframes: List[str], limit: int, include_open_candle: bool) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    needs_2d = "2d" in timeframes

    for timeframe in timeframes:
        if timeframe == "2d":
            continue
        out[timeframe] = annotate_indicators(fetch_binance_klines(symbol, timeframe, market, limit, include_open_candle))

    if needs_2d:
        one_day = out.get("1d")
        if one_day is None:
            one_day = annotate_indicators(fetch_binance_klines(symbol, "1d", market, min(1000, limit * 2 + 80), include_open_candle))
        out["2d"] = annotate_indicators(derive_2d_from_1d(one_day, limit))

    return {tf: out[tf] for tf in timeframes if tf in out}


def last_valid(values: Iterable[Optional[float]]) -> Optional[float]:
    for value in reversed(list(values)):
        if value is not None:
            return value
    return None


def find_segment_start(candles: List[Dict[str, Any]], direction: int) -> Optional[int]:
    if direction == 0:
        return None
    for i in range(len(candles) - 1, 0, -1):
        prev = sign(candles[i - 1].get("dea"))
        cur = sign(candles[i].get("dea"))
        if cur == direction and prev != direction:
            return i
    for i, candle in enumerate(candles):
        if sign(candle.get("dea")) == direction:
            return i
    return None


def candle_touched_ema52(candle: Dict[str, Any], direction: int, tolerance_pct: float = PRICE_NEAR_EMA52_PCT) -> bool:
    ema52 = candle.get("ema52")
    if ema52 is None:
        return False
    upper = ema52 * (1 + tolerance_pct)
    lower = ema52 * (1 - tolerance_pct)
    # Up segment: a return to EMA52 is generally a pullback down into EMA52.
    # Down segment: a return to EMA52 is generally a rebound up into EMA52.
    if direction > 0:
        return candle["low"] <= upper and candle["high"] >= lower
    if direction < 0:
        return candle["high"] >= lower and candle["low"] <= upper
    return lower <= candle["close"] <= upper


def find_ema52_touch(candles: List[Dict[str, Any]], start_index: Optional[int], direction: int) -> Optional[int]:
    if start_index is None:
        return None
    for i in range(start_index, len(candles)):
        if candle_touched_ema52(candles[i], direction):
            return i
    return None


def histogram_state(candles: List[Dict[str, Any]]) -> str:
    recent = [c.get("histogram") for c in candles[-4:] if c.get("histogram") is not None]
    if len(recent) < 3:
        return "数据不足"
    abs_recent = [abs(x) for x in recent]
    if abs_recent[-1] < abs_recent[-2] < abs_recent[-3]:
        return "连续缩量"
    if abs_recent[-1] > abs_recent[-2] > abs_recent[-3]:
        return "连续放量"
    if recent[-1] > recent[-2]:
        return "柱体回升"
    if recent[-1] < recent[-2]:
        return "柱体回落"
    return "横向"


def dif_dea_state(last: Dict[str, Any], prev: Dict[str, Any]) -> str:
    dif = last.get("dif")
    dea = last.get("dea")
    prev_dif = prev.get("dif")
    prev_dea = prev.get("dea")
    if None in (dif, dea, prev_dif, prev_dea):
        return "数据不足"
    crossed_up = prev_dif <= prev_dea and dif > dea
    crossed_down = prev_dif >= prev_dea and dif < dea
    if crossed_up:
        return "金叉/黄线上穿白线"
    if crossed_down:
        return "死叉/黄线下穿白线"
    return "DIF在DEA上方" if dif > dea else "DIF在DEA下方"


def analyze_timeframe(timeframe: str, candles: List[Dict[str, Any]]) -> TimeframeAnalysis:
    if len(candles) < 60:
        raise ValueError(f"{timeframe}: not enough candles after filtering confirmed bars")

    last = candles[-1]
    prev = candles[-2]
    direction = sign(last.get("dea"))
    segment = "上涨线段(DEA>0)" if direction > 0 else "下跌线段(DEA<0)" if direction < 0 else "零轴"
    start_index = find_segment_start(candles, direction)
    touch_index = find_ema52_touch(candles, start_index, direction)
    segment_bars = len(candles) - start_index if start_index is not None else None

    ema52 = last.get("ema52")
    price_vs_ema52_pct = (last["close"] - ema52) / ema52 * 100 if ema52 else None
    zero_threshold = ZERO_AXIS_DEA_THRESHOLD.get(timeframe, 300.0)
    dea = last.get("dea")
    prev_dea = prev.get("dea")
    hist = last.get("histogram")
    h_state = histogram_state(candles)

    near_zero = dea is not None and abs(dea) <= zero_threshold
    dea_toward_zero = False
    if dea is not None and prev_dea is not None:
        dea_toward_zero = abs(dea) < abs(prev_dea)
    hist_against_segment = (direction > 0 and hist is not None and hist < 0) or (direction < 0 and hist is not None and hist > 0)

    if near_zero and dea_toward_zero:
        zero_axis_status = f"归零轴中(|DEA|≤{zero_threshold:g})"
    elif near_zero:
        zero_axis_status = f"零轴附近(|DEA|≤{zero_threshold:g})"
    elif dea_toward_zero and hist_against_segment:
        zero_axis_status = "向零轴回归"
    else:
        zero_axis_status = "远离零轴/未回归"

    if touch_index is not None and start_index is not None and touch_index > start_index:
        unit_phase = "U2"
        u2_status = "已进入U2：本线段内价格已触及EMA52"
    else:
        unit_phase = "U1"
        close_to_ema = price_vs_ema52_pct is not None and abs(price_vs_ema52_pct) <= PRICE_NEAR_EMA52_PCT * 150
        if close_to_ema or (dea_toward_zero and hist_against_segment):
            u2_status = "将形成U2：U1回归EMA52/零轴过程中"
        else:
            u2_status = "未形成U2：尚未触及EMA52"

    notes: List[str] = []
    if timeframe == "2d":
        notes.append("2d 为 1d UTC K线两两聚合，Binance 无原生 2d interval")
    if near_zero:
        notes.append("DEA 已进入该级别零轴阈值区")
    if hist_against_segment:
        notes.append("MACD柱体与当前线段方向相反，说明在回调/反抽")
    if price_vs_ema52_pct is not None and abs(price_vs_ema52_pct) <= 1:
        notes.append("价格距离 EMA52 不超过 1%，符合归零轴价格条件")

    return TimeframeAnalysis(
        timeframe=timeframe,
        last_open_time_utc=last["datetime"],
        last_close_time_utc=last["close_datetime"],
        close=last["close"],
        ema26=last.get("ema26"),
        ema52=last.get("ema52"),
        dif=last.get("dif"),
        dea=last.get("dea"),
        histogram=last.get("histogram"),
        segment=segment,
        segment_bars=segment_bars,
        unit_phase=unit_phase,
        u2_status=u2_status,
        zero_axis_status=zero_axis_status,
        price_vs_ema52_pct=price_vs_ema52_pct,
        hist_state=h_state,
        dif_dea_state=dif_dea_state(last, prev),
        notes=notes,
    )


def relation_word(base: TimeframeAnalysis, other: TimeframeAnalysis) -> str:
    base_up = base.dea is not None and base.dea > 0
    other_up = other.dea is not None and other.dea > 0
    if base_up == other_up:
        return "同向共振"
    return "方向矛盾"


def build_decision(analyses: Dict[str, TimeframeAnalysis]) -> List[str]:
    six = analyses.get("6h")
    if six is None:
        return ["缺少 6h 数据，无法生成 6h 主结论。"]

    parents = [analyses[tf] for tf in ["1d", "12h"] if tf in analyses]
    children = [analyses[tf] for tf in ["4h", "2h", "1h", "30m"] if tf in analyses]
    parent_up = sum(1 for x in parents if x.dea is not None and x.dea > 0)
    child_up = sum(1 for x in children if x.dea is not None and x.dea > 0)
    parent_aligned = bool(parents) and parent_up == len(parents)
    child_aligned = child_up >= max(1, len(children) // 2)

    lines: List[str] = []
    lines.append(f"6h 当前判断：{six.segment}，{six.zero_axis_status}，{six.u2_status}。")

    if "将形成U2" in six.u2_status:
        if parent_aligned:
            lines.append("交易含义：大级别若仍在上方，6h 这里更像上涨线段的归零轴回调；不要追空，等 4h/2h 重新放量或 DIF 上穿 DEA 后再评估多单。")
        else:
            lines.append("交易含义：6h 正在回归零轴但大级别不支持，优先观望，若 6h DEA 穿零轴则按线段切换处理。")
    elif six.unit_phase == "U2":
        if parent_aligned and child_aligned:
            lines.append("交易含义：6h 已进入 U2 且上下级别部分共振，可以等待小级别回踩不破 EMA52 后寻找顺势多单。")
        elif child_aligned and not parent_aligned:
            lines.append("交易含义：6h 已进入 U2，下级别已有部分同向，但 1d/12h 上级仍然矛盾；多单只能等小级别二次确认，避免把 6h U2 末端当成大级别启动。")
        elif parent_aligned and not child_aligned:
            lines.append("交易含义：上级别支持 6h U2，但下级别尚未修复；等 4h/2h/1h 至少两个级别重新同向后再评估顺势多单。")
        else:
            lines.append("交易含义：6h 已进入 U2，但上下级别都没有形成共振，先观望，避免在 U2 末端追单。")
    else:
        lines.append("交易含义：6h 尚未进入 U2，当前不属于归零轴完成后的高质量触发区，优先等待。")

    if six.dea is not None and six.dea < 0:
        lines.append("风险线：6h DEA 已在零轴下方，除非快速收回，否则按下跌线段/空头段对待。")
    elif six.price_vs_ema52_pct is not None:
        lines.append(f"核对点：6h close 距 EMA52 为 {six.price_vs_ema52_pct:+.2f}%，这决定它是“已触及EMA52进入U2”还是“仍在U1回归中”。")

    return lines


def existing_u2(analysis: TimeframeAnalysis) -> bool:
    return analysis.unit_phase == "U2"


def direction_label(analysis: TimeframeAnalysis) -> str:
    if analysis.dea is None:
        return "方向不明"
    return "上涨方向" if analysis.dea > 0 else "下跌方向" if analysis.dea < 0 else "零轴附近"


def build_entry_point(analyses: Dict[str, TimeframeAnalysis], u2_items: List[TimeframeAnalysis]) -> str:
    one_day = analyses.get("1d")
    if not u2_items:
        return "做单进场点：暂无；等待至少一个时间级别确认进入 U2。"
    if one_day is None or one_day.dea is None:
        return "做单进场点：暂无；缺少 1d 方向，不能判断顺势进场。"

    aligned = [item for item in u2_items if relation_word(one_day, item) == "同向共振"]
    if not aligned:
        return "做单进场点：暂无；当前 U2 级别与 1d 方向矛盾，等最小 U2 级别与 1d 同向后再进。"

    priority = {tf: i for i, tf in enumerate(["30m", "1h", "2h", "4h", "6h", "12h", "1d", "2d"])}
    trigger = sorted(aligned, key=lambda item: priority.get(item.timeframe, 99))[0]
    side = "多单" if one_day.dea > 0 else "空单"
    return (
        f"做单进场点：顺 1d {side}，等 {trigger.timeframe} 回踩/反抽不破 EMA52 "
        f"`{fmt_num(trigger.ema52)}` 后，DIF 重新转向 DEA 且 K 线收回该级别 EMA52。"
    )


def summarize_u2_vs_1d(analyses: Dict[str, TimeframeAnalysis], u2_items: List[TimeframeAnalysis]) -> str:
    if not u2_items:
        return "与1日线关系：暂无已存在 U2 级别可比较。"
    one_day = analyses.get("1d")
    if one_day is None:
        return "与1日线关系：缺少 1d 数据，无法比较。"
    parts = []
    for item in u2_items:
        relation = "自身" if item.timeframe == "1d" else relation_word(one_day, item)
        parts.append(f"{item.timeframe}{relation}")
    return f"与1日线关系：1d 为 {direction_label(one_day)}，" + "，".join(parts) + "。"


def build_markdown(symbol: str, market: str, analyses: Dict[str, TimeframeAnalysis], candles: Dict[str, List[Dict[str, Any]]]) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ordered = [tf for tf in DEFAULT_TIMEFRAMES + ["2d"] if tf in analyses]
    if "2d" in analyses:
        ordered = ["2d"] + [tf for tf in DEFAULT_TIMEFRAMES if tf in analyses]

    lines: List[str] = []
    lines.append("# BTC Binance 6h 动能报告")
    lines.append("")
    lines.append(f"- 生成时间: {generated}")
    lines.append(f"- 数据源: Binance {market} `{symbol}`")
    lines.append("- K线口径: 默认只使用已收盘 K 线；时间为 UTC；指标为 EMA26/EMA52 + MACD(12,26,9)")
    lines.append("- 理论口径: `THEORY.md` 的 DEA 线段、归零轴、Unit1/Unit2、EMA52 触及规则")
    lines.append("")

    lines.append("## 1. 多时间级别数值核对")
    lines.append("")
    lines.append("| 级别 | 最新已收盘K线(UTC) | Close | EMA26 | EMA52 | DIF | DEA | Hist | 线段 | Unit/U2 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for tf in ordered:
        a = analyses[tf]
        lines.append(
            f"| {tf} | {a.last_open_time_utc} | {fmt_num(a.close)} | {fmt_num(a.ema26)} | {fmt_num(a.ema52)} | "
            f"{fmt_num(a.dif)} | {fmt_num(a.dea)} | {fmt_num(a.histogram)} | {a.segment} | {a.unit_phase} / {a.u2_status} |"
        )
    lines.append("")

    if "6h" in analyses:
        six = analyses["6h"]
        lines.append("## 2. 6h 主级别：归零轴 / U2 判断")
        lines.append("")
        lines.append(f"- 当前 6h K线: `{six.last_open_time_utc}` → `{six.last_close_time_utc}`，收盘 `{fmt_num(six.close)}`")
        lines.append(f"- EMA26/EMA52: `{fmt_num(six.ema26)}` / `{fmt_num(six.ema52)}`，Close 距 EMA52 `{six.price_vs_ema52_pct:+.2f}%`" if six.price_vs_ema52_pct is not None else "- EMA52 数据不足")
        lines.append(f"- DIF/DEA/Hist: `{fmt_num(six.dif)}` / `{fmt_num(six.dea)}` / `{fmt_num(six.histogram)}`")
        lines.append(f"- 线段: {six.segment}；Unit: {six.unit_phase}；U2状态: {six.u2_status}")
        lines.append(f"- 零轴状态: {six.zero_axis_status}；柱体: {six.hist_state}；黄白线: {six.dif_dea_state}")
        if six.notes:
            lines.append(f"- 审计备注: {'；'.join(six.notes)}")
        lines.append("")

    lines.append("## 3. 6h 与上下级别关系")
    lines.append("")
    lines.append("| 关系 | 级别 | 线段 | Unit | 零轴/动能 | 与6h关系 |")
    lines.append("|---|---|---|---|---|---|")
    six = analyses.get("6h")
    for label, tf in [("上级", "1d"), ("上级", "12h"), ("主级别", "6h"), ("下级", "4h"), ("下级", "2h"), ("下级", "1h"), ("下级", "30m")]:
        if tf not in analyses:
            continue
        a = analyses[tf]
        relation = "主级别" if tf == "6h" or six is None else relation_word(six, a)
        lines.append(f"| {label} | {tf} | {a.segment} | {a.unit_phase} | {a.zero_axis_status} / {a.hist_state} | {relation} |")
    lines.append("")

    lines.append("## 4. 当前可执行结论")
    lines.append("")
    for item in build_decision(analyses):
        lines.append(f"- {item}")
    lines.append("")

    if "6h" in candles:
        lines.append("## 5. 6h 最近K线明细（用于核对）")
        lines.append("")
        lines.append("| 时间(UTC) | O/H/L/C | EMA26 | EMA52 | DIF/DEA/Hist | Volume |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for c in candles["6h"][-8:]:
            lines.append(
                f"| {c['datetime']} | {fmt_num(c['open'], 1)}/{fmt_num(c['high'], 1)}/{fmt_num(c['low'], 1)}/{fmt_num(c['close'], 1)} "
                f"| {fmt_num(c.get('ema26'), 1)} | {fmt_num(c.get('ema52'), 1)} "
                f"| {fmt_num(c.get('dif'), 1)}/{fmt_num(c.get('dea'), 1)}/{fmt_num(c.get('histogram'), 1)} | {fmt_num(c['volume'], 3)} |"
            )
        lines.append("")

    lines.append("> 本报告是机械化动能分析快照，不构成投资建议。")
    return "\n".join(lines)


def build_u2_compact_markdown(symbol: str, market: str, analyses: Dict[str, TimeframeAnalysis]) -> str:
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    ordered = [tf for tf in ["2d"] + DEFAULT_TIMEFRAMES if tf in analyses]
    u2_items = [analyses[tf] for tf in ordered if existing_u2(analyses[tf])]

    lines: List[str] = []
    lines.append("# BTC Binance U2 动能短报告")
    lines.append("")
    lines.append(f"- 生成时间: {generated}")
    lines.append(f"- 数据源: Binance {market} `{symbol}`")
    lines.append("- K线口径: 只使用已收盘 K 线；只列已经进入 U2 的时间级别")
    lines.append("- 判断口径: `.agents/skills/btc-momentum-analyzer/THEORY.md` 的 DEA 线段、Unit1/Unit2、EMA52 触及规则")
    lines.append("")

    if u2_items:
        lines.append("- 已存在U2级别：" + "、".join(item.timeframe for item in u2_items))
    else:
        lines.append("- 已存在U2级别：无")
    lines.append(f"- {summarize_u2_vs_1d(analyses, u2_items)}")
    lines.append(f"- {build_entry_point(analyses, u2_items)}")
    lines.append("")

    lines.append("> 本报告是机械化动能分析快照，不构成投资建议。")
    return "\n".join(lines)


def write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def parse_timeframes(value: str) -> List[str]:
    if value.lower() == "all":
        return ["2d"] + DEFAULT_TIMEFRAMES
    timeframes = [x.strip() for x in value.split(",") if x.strip()]
    invalid = [x for x in timeframes if x != "2d" and x not in BINANCE_INTERVALS]
    if invalid:
        raise argparse.ArgumentTypeError(f"unsupported timeframe(s): {','.join(invalid)}")
    return timeframes


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a direct Binance BTC momentum report.")
    parser.add_argument("--symbol", default="BTCUSDT", help="Binance symbol, default BTCUSDT")
    parser.add_argument("--market", choices=sorted(MARKET_ENDPOINTS), default="futures", help="Binance market endpoint")
    parser.add_argument("--timeframes", type=parse_timeframes, default=DEFAULT_TIMEFRAMES, help="Comma-separated timeframes or all")
    parser.add_argument("--limit", type=int, default=720, help="Candles per native timeframe, max 1000")
    parser.add_argument("--include-open-candle", action="store_true", help="Include the currently forming candle")
    parser.add_argument("--output", default=None, help="Markdown output path; default writes data/analysis_reports timestamped file")
    parser.add_argument("--json-output", default=None, help="Optional JSON output path")
    parser.add_argument("--report-style", choices=["full", "u2-compact"], default="full", help="Markdown report style")
    parser.add_argument("--stdout", action="store_true", help="Also print Markdown to stdout")
    args = parser.parse_args()

    try:
        candles = fetch_all_timeframes(args.symbol, args.market, args.timeframes, args.limit, args.include_open_candle)
        analyses = {tf: analyze_timeframe(tf, tf_candles) for tf, tf_candles in candles.items()}
    except (error.URLError, TimeoutError) as exc:
        print(f"[ERROR] Binance network request failed: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"[ERROR] Report generation failed: {exc}", file=sys.stderr)
        return 1

    if args.report_style == "u2-compact":
        markdown = build_u2_compact_markdown(args.symbol, args.market, analyses)
    else:
        markdown = build_markdown(args.symbol, args.market, analyses, candles)

    if args.output:
        out_path = args.output
    else:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
        out_path = os.path.join(REPORTS_DIR, f"{stamp}_binance_6h_momentum.md")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(markdown + "\n")

    if args.json_output:
        payload = {
            "symbol": args.symbol,
            "market": args.market,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "timeframes": args.timeframes,
            "analyses": {tf: asdict(a) for tf, a in analyses.items()},
            "latest_candles": {tf: tf_candles[-8:] for tf, tf_candles in candles.items()},
            "thresholds": {
                "zero_axis_dea": ZERO_AXIS_DEA_THRESHOLD,
                "price_near_ema52_pct": PRICE_NEAR_EMA52_PCT,
            },
        }
        write_json(args.json_output, payload)

    if args.stdout:
        print(markdown)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
