#!/usr/bin/env python3
"""
BTC 6h scheduled report entrypoint.

The primary path is now direct Binance kline -> in-memory EMA/MACD -> markdown
report.  The old database update flow remains in the repository for historical
reports, but scheduled runs should use this script so they do not depend on a
local btc_database.json sync step.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys


THIS = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(THIS, "..", "..", "..", ".."))
REPORT_SCRIPT = os.path.join(REPO_ROOT, "scripts", "binance_momentum_report.py")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Binance direct BTC 6h momentum report.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--market", choices=["futures", "spot"], default="futures")
    parser.add_argument("--timeframes", default="1d,12h,6h,4h,2h,1h,30m")
    parser.add_argument("--limit", type=int, default=720)
    parser.add_argument("--output", default=None)
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--include-open-candle", action="store_true")
    parser.add_argument("--stdout", action="store_true")

    # Backward-compatible no-op: older docs/cron commands used --no-update.
    parser.add_argument("--no-update", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--stop-loss-offset", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--zero-axis-threshold", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()

    cmd = [
        sys.executable,
        REPORT_SCRIPT,
        "--symbol",
        args.symbol,
        "--market",
        args.market,
        "--timeframes",
        args.timeframes,
        "--limit",
        str(args.limit),
    ]
    if args.output:
        cmd.extend(["--output", args.output])
    if args.json_output:
        cmd.extend(["--json-output", args.json_output])
    if args.include_open_candle:
        cmd.append("--include-open-candle")
    if args.stdout:
        cmd.append("--stdout")

    return subprocess.call(cmd, cwd=REPO_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
