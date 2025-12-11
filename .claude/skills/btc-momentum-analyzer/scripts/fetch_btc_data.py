#!/usr/bin/env python3
"""
BTC 数据获取脚本

支持从 OKX API 获取多时间级别的 BTC K线数据
时间级别：2d, 1d, 12h, 6h, 4h, 2h, 1h, 30m

使用方法：
  python3 fetch_btc_data.py --symbol BTC-USDT --timeframes 1h,4h --limit 100
  python3 fetch_btc_data.py --timeframes all --cache

作者：Claude
日期：2025-12-10
"""

import json
import sys
import os
import argparse
from datetime import datetime, timedelta
from urllib import request, error, parse
from typing import List, Dict, Any, Optional
import time

# OKX API 配置
OKX_API_BASE = "https://www.okx.com/api/v5"
OKX_CANDLES_ENDPOINT = f"{OKX_API_BASE}/market/candles"

# 时间级别映射（OKX 格式）
TIMEFRAME_MAP = {
    "2d": "2D",
    "1d": "1D",
    "12h": "12H",
    "6h": "6H",
    "4h": "4H",
    "2h": "2H",
    "1h": "1H",
    "30m": "30m",
}

# 默认时间级别
DEFAULT_TIMEFRAMES = ["2d", "1d", "12h", "6h", "4h", "2h", "1h", "30m"]

# 缓存目录
CACHE_DIR = "/Users/adrian/Desktop/BA/MACD/data"


class BTCDataFetcher:
    """BTC 数据获取器"""

    def __init__(self, symbol: str = "BTC-USDT", exchange: str = "okx"):
        self.symbol = symbol
        self.exchange = exchange.lower()
        self.session_requests = 0
        self.last_request_time = 0

    def _rate_limit(self):
        """速率限制：OKX 允许 20 req/2s"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if self.session_requests >= 20 and time_since_last < 2:
            sleep_time = 2 - time_since_last
            print(f"[INFO] Rate limit: sleeping {sleep_time:.2f}s", file=sys.stderr)
            time.sleep(sleep_time)
            self.session_requests = 0

        self.last_request_time = time.time()
        self.session_requests += 1

    def fetch_from_okx(
        self, timeframe: str, limit: int = 100
    ) -> Optional[List[Dict[str, Any]]]:
        """
        从 OKX API 获取 K 线数据

        参数：
            timeframe: 时间级别（1h, 4h, 1d 等）
            limit: K 线数量（最大 300）

        返回：
            K 线数据列表，格式：
            [
                {
                    "timestamp": 1638316800,
                    "datetime": "2021-12-01 00:00:00",
                    "open": 57000.0,
                    "high": 58000.0,
                    "low": 56500.0,
                    "close": 57500.0,
                    "volume": 1234.56
                },
                ...
            ]
        """
        # 转换时间级别格式
        bar = TIMEFRAME_MAP.get(timeframe)
        if not bar:
            print(f"[ERROR] Unsupported timeframe: {timeframe}", file=sys.stderr)
            return None

        # 限制 limit 最大值
        limit = min(limit, 300)

        # 构建请求参数
        params = {"instId": self.symbol, "bar": bar, "limit": str(limit)}

        url = f"{OKX_CANDLES_ENDPOINT}?{parse.urlencode(params)}"

        print(f"[INFO] Fetching {timeframe} data from OKX...", file=sys.stderr)
        print(f"[DEBUG] URL: {url}", file=sys.stderr)

        try:
            self._rate_limit()

            req = request.Request(url)
            req.add_header("User-Agent", "Mozilla/5.0")

            with request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            # 检查响应
            if data.get("code") != "0":
                print(
                    f"[ERROR] OKX API error: {data.get('msg', 'Unknown error')}",
                    file=sys.stderr,
                )
                return None

            # 解析数据
            candles_raw = data.get("data", [])
            if not candles_raw:
                print(f"[WARN] No data returned for {timeframe}", file=sys.stderr)
                return []

            # 转换为标准格式
            candles = []
            for candle in candles_raw:
                # OKX 格式: [timestamp, open, high, low, close, volume, volumeCcy, volumeCcyQuote, confirm]
                try:
                    timestamp_ms = int(candle[0])
                    candles.append(
                        {
                            "timestamp": timestamp_ms / 1000,  # 转换为秒
                            "datetime": datetime.fromtimestamp(
                                timestamp_ms / 1000
                            ).strftime("%Y-%m-%d %H:%M:%S"),
                            "open": float(candle[1]),
                            "high": float(candle[2]),
                            "low": float(candle[3]),
                            "close": float(candle[4]),
                            "volume": float(candle[5]),
                        }
                    )
                except (IndexError, ValueError) as e:
                    print(
                        f"[WARN] Failed to parse candle: {candle}, error: {e}",
                        file=sys.stderr,
                    )
                    continue

            # OKX 返回的数据是从新到旧，需要反转
            candles.reverse()

            print(
                f"[SUCCESS] Fetched {len(candles)} candles for {timeframe}",
                file=sys.stderr,
            )
            return candles

        except error.URLError as e:
            print(f"[ERROR] Network error: {e}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON decode error: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
            return None

    def fetch_multiple_timeframes(
        self, timeframes: List[str], limit: int = 100
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取多个时间级别的数据

        参数：
            timeframes: 时间级别列表
            limit: 每个时间级别的 K 线数量

        返回：
            字典，key 为时间级别，value 为 K 线数据
        """
        results = {}

        for tf in timeframes:
            candles = self.fetch_from_okx(tf, limit)
            if candles:
                results[tf] = candles
            else:
                print(f"[WARN] Failed to fetch {tf} data", file=sys.stderr)

        return results

    def save_to_cache(self, data: Dict[str, List[Dict[str, Any]]], filename: str):
        """
        保存数据到缓存文件

        参数：
            data: 多时间级别数据
            filename: 文件名（不含路径）
        """
        os.makedirs(CACHE_DIR, exist_ok=True)
        filepath = os.path.join(CACHE_DIR, filename)

        # 添加元数据
        output = {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "timeframes": list(data.keys()),
            "data": data,
        }

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

            print(f"[INFO] Data saved to {filepath}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Failed to save cache: {e}", file=sys.stderr)

    def load_from_cache(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        从缓存文件加载数据

        返回：
            缓存的数据，如果文件不存在或过期则返回 None
        """
        filepath = os.path.join(CACHE_DIR, filename)

        if not os.path.exists(filepath):
            print(f"[INFO] Cache file not found: {filepath}", file=sys.stderr)
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 检查缓存时间（可选：根据时间级别设置不同的过期时间）
            fetch_time_str = data.get("fetch_time")
            if fetch_time_str:
                fetch_time = datetime.strptime(fetch_time_str, "%Y-%m-%d %H:%M:%S")
                age_minutes = (datetime.now() - fetch_time).total_seconds() / 60

                # 简单策略：所有缓存 10 分钟过期
                if age_minutes > 10:
                    print(
                        f"[INFO] Cache expired ({age_minutes:.1f} min old)",
                        file=sys.stderr,
                    )
                    return None

            print(f"[INFO] Loaded data from cache: {filepath}", file=sys.stderr)
            return data

        except Exception as e:
            print(f"[ERROR] Failed to load cache: {e}", file=sys.stderr)
            return None


def main():
    parser = argparse.ArgumentParser(description="Fetch BTC candle data from OKX API")

    parser.add_argument(
        "--symbol",
        type=str,
        default="BTC-USDT",
        help="Trading symbol (default: BTC-USDT)",
    )

    parser.add_argument(
        "--timeframes",
        type=str,
        default="1h",
        help='Comma-separated timeframes or "all" (default: 1h). '
        "Supported: 2d,1d,12h,6h,4h,2h,1h,30m",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of candles per timeframe (default: 100, max: 300)",
    )

    parser.add_argument(
        "--exchange", type=str, default="okx", help="Exchange name (default: okx)"
    )

    parser.add_argument(
        "--cache",
        action="store_true",
        help="Save data to cache file",
    )

    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Try to use cached data first",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output filename (optional, defaults to stdout)",
    )

    args = parser.parse_args()

    # 解析时间级别
    if args.timeframes.lower() == "all":
        timeframes = DEFAULT_TIMEFRAMES
    else:
        timeframes = [tf.strip() for tf in args.timeframes.split(",")]

    # 验证时间级别
    invalid_tf = [tf for tf in timeframes if tf not in TIMEFRAME_MAP]
    if invalid_tf:
        print(f"[ERROR] Invalid timeframes: {invalid_tf}", file=sys.stderr)
        print(
            f"[INFO] Supported timeframes: {', '.join(TIMEFRAME_MAP.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 创建数据获取器
    fetcher = BTCDataFetcher(symbol=args.symbol, exchange=args.exchange)

    # 尝试从缓存加载
    result_data = None
    cache_filename = f"btc_cache_{'-'.join(timeframes)}.json"

    if args.use_cache:
        cached = fetcher.load_from_cache(cache_filename)
        if cached and cached.get("data"):
            result_data = cached["data"]
            print(f"[INFO] Using cached data", file=sys.stderr)

    # 如果没有缓存或缓存过期，从 API 获取
    if not result_data:
        print(
            f"[INFO] Fetching data for timeframes: {', '.join(timeframes)}",
            file=sys.stderr,
        )
        result_data = fetcher.fetch_multiple_timeframes(timeframes, args.limit)

        if not result_data:
            print("[ERROR] Failed to fetch data", file=sys.stderr)
            sys.exit(1)

        # 保存到缓存
        if args.cache:
            fetcher.save_to_cache(result_data, cache_filename)

    # 输出结果
    output_json = {
        "symbol": args.symbol,
        "exchange": args.exchange,
        "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timeframes": list(result_data.keys()),
        "data": result_data,
    }

    if args.output:
        # 输出到文件
        output_path = args.output
        if not output_path.startswith("/"):
            output_path = os.path.join(CACHE_DIR, output_path)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_json, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Data written to {output_path}", file=sys.stderr)
    else:
        # 输出到 stdout
        print(json.dumps(output_json, indent=2, ensure_ascii=False))

    print(f"[INFO] Total candles fetched:", file=sys.stderr)
    for tf, candles in result_data.items():
        print(f"  {tf}: {len(candles)} candles", file=sys.stderr)


if __name__ == "__main__":
    main()
