import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "nine.py"
SPEC = importlib.util.spec_from_file_location("nine", MODULE_PATH)
nine = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = nine
SPEC.loader.exec_module(nine)


def candles_from_closes(closes):
    return [
        nine.Candle(
            timestamp_ms=index * 1000,
            datetime_utc=str(index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=0.0,
        )
        for index, close in enumerate(closes)
    ]


class TDSequentialTests(unittest.TestCase):
    def test_buy_signals_at_exactly_9_and_13(self):
        results = nine.calculate_td_sequential(candles_from_closes(range(30, 10, -1)))
        signals = [(row.datetime_utc, row.signal) for row in results if row.signal]
        self.assertEqual(signals, [("12", "BUY_9"), ("16", "BUY_13")])

    def test_sell_signals_at_exactly_9_and_13(self):
        results = nine.calculate_td_sequential(candles_from_closes(range(20)))
        signals = [(row.datetime_utc, row.signal) for row in results if row.signal]
        self.assertEqual(signals, [("12", "SELL_9"), ("16", "SELL_13")])

    def test_count_resets_when_condition_breaks(self):
        closes = [20, 19, 18, 17, 16, 15, 14, 13, 12, 30, 29, 28, 27, 26]
        results = nine.calculate_td_sequential(candles_from_closes(closes))
        self.assertEqual(results[8].buy_count, 5)
        self.assertEqual(results[9].buy_count, 0)
        self.assertFalse(any(row.signal == "BUY_9" for row in results))


if __name__ == "__main__":
    unittest.main()
