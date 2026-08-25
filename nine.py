#!/usr/bin/env python3
"""Run the simplified TD 9/13 logic from ``nine.pine`` locally.

The implementation intentionally matches the Pine script:

* buy condition: close < close[4]
* sell condition: close > close[4]
* each side counts consecutive matching bars and resets to zero otherwise
* signals are emitted only when the corresponding count equals 9 or 13

No third-party Python packages are required.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BINANCE_SPOT_URL = "https://data-api.binance.vision/api/v3/klines"
BINANCE_FUTURES_URL = "https://fapi.binance.com/fapi/v1/klines"


@dataclass(frozen=True)
class Candle:
    timestamp_ms: int
    datetime_utc: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time_ms: int | None = None


@dataclass(frozen=True)
class TDResult:
    timestamp_ms: int
    datetime_utc: str
    close: float
    buy_count: int
    sell_count: int
    signal: str | None


def _utc_text(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()


def _to_timestamp_ms(value: Any, fallback_index: int) -> int:
    if value is None:
        return fallback_index
    number = float(value)
    return int(number * 1000 if abs(number) < 10_000_000_000 else number)


def _candle_from_mapping(item: dict[str, Any], index: int) -> Candle:
    timestamp_ms = _to_timestamp_ms(
        item.get("timestamp", item.get("timestamp_ms", item.get("open_time"))), index
    )
    datetime_utc = str(item.get("datetime") or item.get("datetime_utc") or _utc_text(timestamp_ms))
    return Candle(
        timestamp_ms=timestamp_ms,
        datetime_utc=datetime_utc,
        open=float(item["open"]),
        high=float(item["high"]),
        low=float(item["low"]),
        close=float(item["close"]),
        volume=float(item.get("volume", 0.0)),
        close_time_ms=(
            int(item["close_time_ms"])
            if item.get("close_time_ms") is not None
            else None
        ),
    )


def load_candles(path: Path, timeframe: str | None = None) -> list[Candle]:
    """Load candles from CSV, a JSON list, or btc_database.json."""
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            items = list(csv.DictReader(handle))
    else:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict) and "timeframes" in payload:
            if not timeframe:
                available = ", ".join(payload["timeframes"].keys())
                raise ValueError(f"--timeframe is required for this database; available: {available}")
            try:
                items = payload["timeframes"][timeframe]["candles"]
            except KeyError as exc:
                raise ValueError(f"timeframe not found in database: {timeframe}") from exc
        elif isinstance(payload, dict) and isinstance(payload.get("candles"), list):
            items = payload["candles"]
        else:
            raise ValueError("unsupported JSON structure")

    candles = [_candle_from_mapping(item, index) for index, item in enumerate(items)]
    candles.sort(key=lambda candle: candle.timestamp_ms)
    return candles


def fetch_binance_candles(
    symbol: str,
    interval: str,
    limit: int,
    market: str = "spot",
    include_open_candle: bool = False,
) -> list[Candle]:
    """Fetch public Binance K-lines without an API key."""
    if not 1 <= limit <= 1000:
        raise ValueError("Binance limit must be between 1 and 1000")
    base_url = BINANCE_SPOT_URL if market == "spot" else BINANCE_FUTURES_URL
    query = urllib.parse.urlencode(
        {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    )
    request = urllib.request.Request(
        f"{base_url}?{query}",
        headers={"User-Agent": "MACD-nine-sequential/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            rows = json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Binance HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Binance request failed: {exc.reason}") from exc

    now_ms = int(time.time() * 1000)
    candles: list[Candle] = []
    for row in rows:
        close_time_ms = int(row[6])
        if not include_open_candle and close_time_ms >= now_ms:
            continue
        timestamp_ms = int(row[0])
        candles.append(
            Candle(
                timestamp_ms=timestamp_ms,
                datetime_utc=_utc_text(timestamp_ms),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                close_time_ms=close_time_ms,
            )
        )
    return candles


def calculate_td_sequential(candles: Iterable[Candle]) -> list[TDResult]:
    """Calculate the exact consecutive 9/13 logic used by nine.pine."""
    ordered = list(candles)
    buy_count = 0
    sell_count = 0
    results: list[TDResult] = []

    for index, candle in enumerate(ordered):
        if index >= 4:
            buy_condition = candle.close < ordered[index - 4].close
            sell_condition = candle.close > ordered[index - 4].close
        else:
            buy_condition = False
            sell_condition = False

        buy_count = buy_count + 1 if buy_condition else 0
        sell_count = sell_count + 1 if sell_condition else 0

        signal: str | None = None
        if buy_count in (9, 13):
            signal = f"BUY_{buy_count}"
        elif sell_count in (9, 13):
            signal = f"SELL_{sell_count}"

        results.append(
            TDResult(
                timestamp_ms=candle.timestamp_ms,
                datetime_utc=candle.datetime_utc,
                close=candle.close,
                buy_count=buy_count,
                sell_count=sell_count,
                signal=signal,
            )
        )
    return results


def _write_json(path: Path, results: list[TDResult], metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": metadata,
        "signals": [asdict(row) for row in results if row.signal],
        "rows": [asdict(row) for row in results],
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _print_report(results: list[TDResult], last: int) -> None:
    signals = [row for row in results if row.signal]
    latest = results[-1]
    print(
        f"Latest: {latest.datetime_utc} close={latest.close:.2f} "
        f"buy_count={latest.buy_count} sell_count={latest.sell_count}"
    )
    print(f"Signals found: {len(signals)}")
    for row in signals[-last:]:
        print(f"{row.datetime_utc}  {row.signal:<7} close={row.close:.2f}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Local Python port of nine.pine TD Sequential Lite 9/13"
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path, help="CSV or JSON candle file")
    source.add_argument(
        "--source",
        choices=("binance",),
        default="binance",
        help="Live market data source (default: binance)",
    )
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="6h", help="Binance interval (default: 6h)")
    parser.add_argument("--market", choices=("spot", "futures"), default="spot")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument(
        "--timeframe",
        help="Timeframe key when --input points to btc_database.json",
    )
    parser.add_argument(
        "--include-open-candle",
        action="store_true",
        help="Include Binance's currently forming candle",
    )
    parser.add_argument("--last", type=int, default=20, help="Signals to print")
    parser.add_argument("--output", type=Path, help="Write full JSON result")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.input:
            candles = load_candles(args.input, args.timeframe)
            metadata = {"source": str(args.input), "timeframe": args.timeframe}
        else:
            candles = fetch_binance_candles(
                symbol=args.symbol,
                interval=args.interval,
                limit=args.limit,
                market=args.market,
                include_open_candle=args.include_open_candle,
            )
            metadata = {
                "source": "binance",
                "market": args.market,
                "symbol": args.symbol.upper(),
                "interval": args.interval,
                "include_open_candle": args.include_open_candle,
            }
        if len(candles) < 13:
            raise ValueError("at least 13 candles are required")
        results = calculate_td_sequential(candles)
        _print_report(results, max(args.last, 0))
        if args.output:
            _write_json(args.output, results, metadata)
            print(f"JSON written: {args.output}")
        return 0
    except (FileNotFoundError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
