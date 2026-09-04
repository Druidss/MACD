import { describe, expect, it } from 'vitest'
import { calculateIndicators, type BinanceKline } from '../server/utils/market'
import { normalizeSignal, secretsMatch, tradingViewPayloadSchema } from '../server/utils/signals'
import { getMacdHistogramColor, getMacdHistogramState, macdColors } from '../shared/utils/macd-style'

function makeRows(length = 80): BinanceKline[] {
  return Array.from({ length }, (_, index) => {
    const close = 60_000 + index * 25
    return [
      1_700_000_000_000 + index * 3_600_000,
      String(close - 5),
      String(close + 20),
      String(close - 20),
      String(close),
      String(100 + index),
      1_700_003_599_999 + index * 3_600_000,
      '0',
      100,
      '0',
      '0',
      '0'
    ]
  })
}

describe('market indicators', () => {
  it('creates chart-ready EMA and MACD values for every candle', () => {
    const points = calculateIndicators(makeRows())

    expect(points).toHaveLength(80)
    expect(points.at(-1)?.ema6).toBeGreaterThan(points.at(-1)?.ema52 ?? 0)
    expect(points.at(-1)?.dif).toBeGreaterThan(0)
    expect(Number.isFinite(points.at(-1)?.histogram)).toBe(true)
    expect(points.at(-1)?.time).toBeTypeOf('number')
  })
})

describe('MACD histogram styling', () => {
  it('uses the normal positive and negative colors for expanding bars', () => {
    expect(getMacdHistogramState(12, 8)).toBe('positive')
    expect(getMacdHistogramColor(12, 8)).toBe(macdColors.positive)
    expect(getMacdHistogramState(-12, -8)).toBe('negative')
    expect(getMacdHistogramColor(-12, -8)).toBe(macdColors.negative)
  })

  it('uses solid pastel colors for contracting bars', () => {
    expect(getMacdHistogramState(8, 12)).toBe('positive-contracting')
    expect(getMacdHistogramColor(8, 12)).toBe('#b8ded9')
    expect(getMacdHistogramState(-8, -12)).toBe('negative-contracting')
    expect(getMacdHistogramColor(-8, -12)).toBe('#ffc8cf')
  })

  it('does not mark a zero-axis color transition as contraction', () => {
    expect(getMacdHistogramState(1, -1)).toBe('positive')
    expect(getMacdHistogramState(-1, 1)).toBe('negative')
  })
})

describe('TradingView webhook normalization', () => {
  it('validates and normalizes a signal', () => {
    const parsed = tradingViewPayloadSchema.parse({
      secret: 'test-secret',
      ticker: 'btcusdt',
      timeframe: '6h',
      action: 'LONG',
      price: '63520.4',
      strategy: 'MACD segment',
      timestamp: 1_700_000_000
    })
    const signal = normalizeSignal(parsed)

    expect(signal.ticker).toBe('BTCUSDT')
    expect(signal.price).toBe(63_520.4)
    expect(signal.id).toHaveLength(24)
  })

  it('compares webhook secrets safely', () => {
    expect(secretsMatch('correct', 'correct')).toBe(true)
    expect(secretsMatch('wrong', 'correct')).toBe(false)
    expect(secretsMatch(undefined, 'correct')).toBe(false)
  })
})
