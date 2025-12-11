#!/usr/bin/env python3
"""
BTC 数据库管理器 - 增量更新系统

功能：
1. 初始化：下载完整历史数据并计算指标
2. 增量更新：只获取最新K线，追加到数据库
3. MACD 形态分析：基于历史数据分析各种形态

使用方法：
  # 初始化数据库
  python3 database_manager.py --init --timeframes 1h,4h,1d

  # 增量更新
  python3 database_manager.py --update

  # 查看数据库状态
  python3 database_manager.py --status

作者：Claude
日期：2025-12-11
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse

# 导入现有的脚本功能
sys.path.insert(0, os.path.dirname(__file__))
from fetch_btc_data import BTCDataFetcher
from calculate_indicators import IndicatorCalculator

# 数据库配置
DATABASE_DIR = "/Users/adrian/Desktop/BA/MACD/data/database"
DATABASE_FILE = os.path.join(DATABASE_DIR, "btc_database.json")

# 默认时间级别
ALL_TIMEFRAMES = ["2d", "1d", "12h", "6h", "4h", "2h", "1h", "30m"]

# 每个时间级别的初始数据量（足够计算稳定的指标）
INITIAL_LIMITS = {
    "2d": 200,    # 约 400 天
    "1d": 200,    # 约 200 天
    "12h": 200,   # 约 100 天
    "6h": 200,    # 约 50 天
    "4h": 200,    # 约 33 天
    "2h": 200,    # 约 16 天
    "1h": 200,    # 约 8 天
    "30m": 200,   # 约 4 天
}


class BTCDatabase:
    """BTC 数据库管理器"""

    def __init__(self):
        self.database_dir = DATABASE_DIR
        self.database_file = DATABASE_FILE
        self.fetcher = BTCDataFetcher()
        self.calculator = IndicatorCalculator(ema_periods=[26, 52], macd_params=(12, 26, 9))

        # 确保数据库目录存在
        os.makedirs(self.database_dir, exist_ok=True)

    def load_database(self) -> Optional[Dict[str, Any]]:
        """加载数据库"""
        if not os.path.exists(self.database_file):
            return None

        try:
            with open(self.database_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load database: {e}", file=sys.stderr)
            return None

    def save_database(self, database: Dict[str, Any]):
        """保存数据库"""
        try:
            with open(self.database_file, "w", encoding="utf-8") as f:
                json.dump(database, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Database saved to {self.database_file}", file=sys.stderr)
        except Exception as e:
            print(f"[ERROR] Failed to save database: {e}", file=sys.stderr)

    def initialize_database(self, timeframes: List[str]):
        """
        初始化数据库：下载完整历史数据并计算指标

        参数：
            timeframes: 要初始化的时间级别列表
        """
        print("[INFO] Initializing database...", file=sys.stderr)
        print(f"[INFO] Timeframes: {', '.join(timeframes)}", file=sys.stderr)

        database = {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "timeframes": {},
        }

        for tf in timeframes:
            print(f"\n[INFO] Initializing {tf}...", file=sys.stderr)

            # 获取历史数据
            limit = INITIAL_LIMITS.get(tf, 200)
            candles = self.fetcher.fetch_from_okx(tf, limit)

            if not candles:
                print(f"[WARN] Failed to fetch {tf} data, skipping...", file=sys.stderr)
                continue

            # 计算指标
            candles_with_indicators = self.calculator.annotate_candles(candles)

            # 保存到数据库
            database["timeframes"][tf] = {
                "candles": candles_with_indicators,
                "last_timestamp": candles_with_indicators[-1]["timestamp"],
                "last_updated": datetime.now().isoformat(),
                "count": len(candles_with_indicators),
            }

            print(f"[SUCCESS] {tf}: {len(candles_with_indicators)} candles initialized", file=sys.stderr)

        # 保存数据库
        self.save_database(database)
        print(f"\n[SUCCESS] Database initialized with {len(database['timeframes'])} timeframes", file=sys.stderr)

        return database

    def update_database(self, timeframes: Optional[List[str]] = None):
        """
        增量更新数据库：只获取最新的K线

        参数：
            timeframes: 要更新的时间级别（None = 更新所有）
        """
        print("[INFO] Updating database...", file=sys.stderr)

        # 加载现有数据库
        database = self.load_database()
        if not database:
            print("[ERROR] Database not found. Please initialize first with --init", file=sys.stderr)
            return None

        # 确定要更新的时间级别
        if timeframes is None:
            timeframes = list(database["timeframes"].keys())

        updated_count = 0

        for tf in timeframes:
            if tf not in database["timeframes"]:
                print(f"[WARN] {tf} not in database, skipping...", file=sys.stderr)
                continue

            print(f"\n[INFO] Updating {tf}...", file=sys.stderr)

            # 获取现有数据
            tf_data = database["timeframes"][tf]
            existing_candles = tf_data["candles"]
            last_timestamp = tf_data["last_timestamp"]

            # 获取新数据（只取最近的10根，确保能覆盖最新K线）
            new_candles = self.fetcher.fetch_from_okx(tf, limit=10)

            if not new_candles:
                print(f"[WARN] Failed to fetch {tf} data, skipping...", file=sys.stderr)
                continue

            # 找出真正新增的K线（时间戳大于最后一根）
            new_candles_filtered = [
                c for c in new_candles if c["timestamp"] > last_timestamp
            ]

            if not new_candles_filtered:
                print(f"[INFO] {tf}: No new candles", file=sys.stderr)
                continue

            # 合并数据（保留旧数据 + 新数据）
            # 注意：我们需要重新计算最近的指标，因为EMA是滚动计算的
            all_candles_raw = existing_candles + new_candles_filtered

            # 提取原始OHLCV数据（去掉指标，准备重新计算）
            all_candles_ohlcv = []
            for c in all_candles_raw:
                all_candles_ohlcv.append({
                    "timestamp": c["timestamp"],
                    "datetime": c["datetime"],
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                    "volume": c["volume"],
                })

            # 重新计算所有指标（确保EMA连续性）
            all_candles_with_indicators = self.calculator.annotate_candles(all_candles_ohlcv)

            # 更新数据库
            database["timeframes"][tf] = {
                "candles": all_candles_with_indicators,
                "last_timestamp": all_candles_with_indicators[-1]["timestamp"],
                "last_updated": datetime.now().isoformat(),
                "count": len(all_candles_with_indicators),
            }

            print(
                f"[SUCCESS] {tf}: Added {len(new_candles_filtered)} new candles, total {len(all_candles_with_indicators)}",
                file=sys.stderr,
            )
            updated_count += 1

        # 更新数据库元信息
        database["last_updated"] = datetime.now().isoformat()

        # 保存数据库
        self.save_database(database)
        print(f"\n[SUCCESS] Updated {updated_count} timeframes", file=sys.stderr)

        return database

    def get_timeframe_data(self, timeframe: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定时间级别的数据（带指标）

        参数：
            timeframe: 时间级别
            limit: 返回最近N根K线（None = 全部）

        返回：
            K线数据列表（包含指标）
        """
        database = self.load_database()
        if not database:
            return []

        if timeframe not in database["timeframes"]:
            return []

        candles = database["timeframes"][timeframe]["candles"]

        if limit:
            return candles[-limit:]
        else:
            return candles

    def get_status(self) -> Dict[str, Any]:
        """获取数据库状态"""
        database = self.load_database()
        if not database:
            return {"status": "not_initialized"}

        status = {
            "status": "initialized",
            "version": database.get("version", "unknown"),
            "created_at": database.get("created_at", "unknown"),
            "last_updated": database.get("last_updated", "unknown"),
            "timeframes": {},
        }

        for tf, data in database["timeframes"].items():
            status["timeframes"][tf] = {
                "count": data["count"],
                "last_candle": data["candles"][-1]["datetime"] if data["candles"] else "N/A",
                "last_timestamp": data["last_timestamp"],
            }

        return status

    def export_timeframe(self, timeframe: str, output_file: str):
        """
        导出指定时间级别的数据到文件

        参数：
            timeframe: 时间级别
            output_file: 输出文件路径
        """
        candles = self.get_timeframe_data(timeframe)

        if not candles:
            print(f"[ERROR] No data for {timeframe}", file=sys.stderr)
            return

        output_data = {
            "symbol": "BTC-USDT",
            "exchange": "okx",
            "timeframe": timeframe,
            "export_time": datetime.now().isoformat(),
            "count": len(candles),
            "candles": candles,
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        print(f"[SUCCESS] Exported {len(candles)} candles to {output_file}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="BTC Database Manager - Incremental Update System")

    # 操作模式
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--init", action="store_true", help="Initialize database with historical data")
    mode_group.add_argument("--update", action="store_true", help="Update database with latest candles")
    mode_group.add_argument("--status", action="store_true", help="Show database status")
    mode_group.add_argument("--export", type=str, metavar="TIMEFRAME", help="Export timeframe data to file")

    # 可选参数
    parser.add_argument(
        "--timeframes",
        type=str,
        default=None,
        help="Comma-separated timeframes (e.g., 1h,4h,1d). Default: all for init, existing for update",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file for export (required with --export)",
    )

    args = parser.parse_args()

    # 创建数据库管理器
    db = BTCDatabase()

    # 解析时间级别
    if args.timeframes:
        timeframes = [tf.strip() for tf in args.timeframes.split(",")]
    else:
        timeframes = None

    # 执行操作
    if args.init:
        # 初始化
        if timeframes is None:
            timeframes = ALL_TIMEFRAMES
        db.initialize_database(timeframes)

    elif args.update:
        # 增量更新
        db.update_database(timeframes)

    elif args.status:
        # 显示状态
        status = db.get_status()

        if status["status"] == "not_initialized":
            print("Database not initialized. Run with --init first.")
            sys.exit(1)

        print("\n" + "=" * 60)
        print("BTC Database Status")
        print("=" * 60)
        print(f"Version: {status['version']}")
        print(f"Created: {status['created_at']}")
        print(f"Last Updated: {status['last_updated']}")
        print(f"\nTimeframes: {len(status['timeframes'])}")
        print("-" * 60)

        for tf, info in status["timeframes"].items():
            print(f"{tf:6s}  {info['count']:4d} candles  Last: {info['last_candle']}")

        print("=" * 60)

    elif args.export:
        # 导出数据
        if not args.output:
            print("[ERROR] --output is required with --export", file=sys.stderr)
            sys.exit(1)

        db.export_timeframe(args.export, args.output)


if __name__ == "__main__":
    main()
