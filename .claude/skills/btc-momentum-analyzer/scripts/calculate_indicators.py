#!/usr/bin/env python3
"""
技术指标计算脚本

计算 EMA26, EMA52 和 MACD(12, 26, 9)

使用方法：
  python3 calculate_indicators.py input.json
  python3 calculate_indicators.py input.json --ema-periods 26,52 --macd-params 12,26,9

作者：Claude
日期：2025-12-10
"""

import json
import sys
import argparse
from typing import List, Dict, Any, Optional


class IndicatorCalculator:
    """技术指标计算器"""

    def __init__(self, ema_periods: List[int] = [26, 52], macd_params: tuple = (12, 26, 9)):
        self.ema_periods = ema_periods
        self.macd_fast, self.macd_slow, self.macd_signal = macd_params

    def calculate_ema(self, values: List[float], period: int) -> List[Optional[float]]:
        """
        计算指数移动平均线 (EMA)

        参数：
            values: 价格数组
            period: EMA 周期

        返回：
            EMA 值列表，前 period-1 个值为 None
        """
        if len(values) < period:
            return [None] * len(values)

        ema = [None] * (period - 1)
        multiplier = 2 / (period + 1)

        # 第一个 EMA 使用 SMA
        sma = sum(values[: period]) / period
        ema.append(sma)

        # 后续 EMA
        for i in range(period, len(values)):
            ema_val = (values[i] - ema[-1]) * multiplier + ema[-1]
            ema.append(ema_val)

        return ema

    def calculate_macd(
        self, closes: List[float]
    ) -> Dict[str, List[Optional[float]]]:
        """
        计算 MACD 指标

        返回：
            {
                "dif": DIF 值列表（黄线，快线 - 慢线）
                "dea": DEA 值列表（白线，DIF 的 EMA）
                "histogram": 柱状图列表（DIF - DEA）
            }
        """
        # 计算快慢 EMA
        ema_fast = self.calculate_ema(closes, self.macd_fast)
        ema_slow = self.calculate_ema(closes, self.macd_slow)

        # 计算 DIF
        dif = []
        for f, s in zip(ema_fast, ema_slow):
            if f is not None and s is not None:
                dif.append(f - s)
            else:
                dif.append(None)

        # 计算 DEA（DIF 的 EMA）
        valid_dif = [d for d in dif if d is not None]
        if len(valid_dif) < self.macd_signal:
            dea = [None] * len(dif)
        else:
            dea_values = self.calculate_ema(valid_dif, self.macd_signal)

            # 对齐到原始数组长度
            dea = [None] * (len(dif) - len(dea_values)) + dea_values

        # 计算 Histogram
        histogram = []
        for d, e in zip(dif, dea):
            if d is not None and e is not None:
                histogram.append(d - e)
            else:
                histogram.append(None)

        return {"dif": dif, "dea": dea, "histogram": histogram}

    def annotate_candles(
        self, candles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        为 K 线数据添加指标注释

        参数：
            candles: K 线数据列表

        返回：
            带有指标的 K 线数据
        """
        if not candles:
            return []

        # 提取收盘价
        closes = [c["close"] for c in candles]

        # 计算 EMA
        ema_values = {}
        for period in self.ema_periods:
            ema_values[f"ema{period}"] = self.calculate_ema(closes, period)

        # 计算 MACD
        macd = self.calculate_macd(closes)

        # 注释到 K 线数据
        result = []
        for i, candle in enumerate(candles):
            annotated = {**candle}  # 复制原始数据

            # 添加 EMA
            for period in self.ema_periods:
                annotated[f"ema{period}"] = ema_values[f"ema{period}"][i]

            # 添加 MACD
            annotated["dif"] = macd["dif"][i]
            annotated["dea"] = macd["dea"][i]
            annotated["histogram"] = macd["histogram"][i]

            result.append(annotated)

        return result

    def process_multi_timeframe(
        self, data: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        处理多时间级别数据

        参数：
            data: 多时间级别的 K 线数据字典

        返回：
            带有指标注释的多时间级别数据
        """
        result = {}

        for timeframe, candles in data.items():
            print(f"[INFO] Calculating indicators for {timeframe}...", file=sys.stderr)
            result[timeframe] = self.annotate_candles(candles)

        return result


def main():
    parser = argparse.ArgumentParser(description="Calculate technical indicators")

    parser.add_argument("input", type=str, help="Input JSON file with candle data")

    parser.add_argument(
        "--ema-periods",
        type=str,
        default="26,52",
        help="Comma-separated EMA periods (default: 26,52)",
    )

    parser.add_argument(
        "--macd-params",
        type=str,
        default="12,26,9",
        help="MACD parameters: fast,slow,signal (default: 12,26,9)",
    )

    parser.add_argument(
        "--output", type=str, help="Output JSON file (optional, defaults to stdout)"
    )

    args = parser.parse_args()

    # 解析参数
    try:
        ema_periods = [int(p.strip()) for p in args.ema_periods.split(",")]
        macd_params = tuple(int(p.strip()) for p in args.macd_params.split(","))

        if len(macd_params) != 3:
            raise ValueError("MACD params must be 3 integers: fast,slow,signal")

    except ValueError as e:
        print(f"[ERROR] Invalid parameters: {e}", file=sys.stderr)
        sys.exit(1)

    # 加载输入数据
    try:
        with open(args.input, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON decode error: {e}", file=sys.stderr)
        sys.exit(1)

    # 提取 K 线数据
    if "data" in input_data:
        # 多时间级别格式
        candles_data = input_data["data"]
        is_multi_timeframe = True
    else:
        # 单一时间级别格式
        candles_data = input_data
        is_multi_timeframe = False

    # 创建计算器
    calculator = IndicatorCalculator(ema_periods, macd_params)

    # 计算指标
    if is_multi_timeframe:
        result_data = calculator.process_multi_timeframe(candles_data)
    else:
        result_data = calculator.annotate_candles(candles_data)

    # 构建输出
    output = {
        "symbol": input_data.get("symbol", "BTC-USDT"),
        "exchange": input_data.get("exchange", "okx"),
        "calculation_time": input_data.get("fetch_time", "unknown"),
        "ema_periods": ema_periods,
        "macd_params": macd_params,
        "data": result_data,
    }

    if is_multi_timeframe:
        output["timeframes"] = list(result_data.keys())

    # 输出结果
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Indicators written to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))

    # 统计信息
    if is_multi_timeframe:
        print(f"[INFO] Indicators calculated for:", file=sys.stderr)
        for tf in result_data.keys():
            print(f"  {tf}: {len(result_data[tf])} candles", file=sys.stderr)
    else:
        print(
            f"[INFO] Indicators calculated for {len(result_data)} candles",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
