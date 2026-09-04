import type {
  CandlePoint,
  DashboardInterval,
  EmaStatus,
  MacdStatus,
  MarketDataSource,
  MarketFrame,
  VolumeStatus
} from '#shared/types/dashboard'

export type BinanceKline = [
  number,
  string,
  string,
  string,
  string,
  string,
  number,
  string,
  number,
  string,
  string,
  string
]

interface CachedFrame {
  expiresAt: number
  frame: MarketFrame
}

const frameCache = new Map<string, CachedFrame>()

const DEFAULT_FETCH_LIMIT = 1_000
const DEFAULT_CACHE_LIMIT = 5_000
const MINIMUM_FRAME_ROWS = 60

interface MarketFetchOptions {
  fetchLimit?: number
  cacheLimit?: number
}

function normalizedLimit(value: number | undefined, fallback: number, minimum: number, maximum: number): number {
  if (!Number.isFinite(value)) return fallback
  return Math.min(Math.max(Math.floor(value!), minimum), maximum)
}

function isBinanceKline(value: unknown): value is BinanceKline {
  return Array.isArray(value)
    && value.length >= 12
    && Number.isFinite(Number(value[0]))
}

export function mergeKlines(
  cachedRows: BinanceKline[],
  remoteRows: BinanceKline[],
  limit = DEFAULT_CACHE_LIMIT
): BinanceKline[] {
  const rowsByOpenTime = new Map<number, BinanceKline>()

  for (const row of [...cachedRows, ...remoteRows]) {
    if (isBinanceKline(row)) rowsByOpenTime.set(Number(row[0]), row)
  }

  return [...rowsByOpenTime.values()]
    .sort((left, right) => Number(left[0]) - Number(right[0]))
    .slice(-Math.max(limit, MINIMUM_FRAME_ROWS))
}

function calculateEma(values: number[], period: number): number[] {
  const first = values[0]
  if (first === undefined) return []

  const multiplier = 2 / (period + 1)
  const output: number[] = [first]

  for (let index = 1; index < values.length; index += 1) {
    const value = values[index]!
    const previous = output[index - 1]!
    output.push((value - previous) * multiplier + previous)
  }

  return output
}

export function calculateIndicators(rows: BinanceKline[]): CandlePoint[] {
  const closes = rows.map(row => Number(row[4]))
  const ema6 = calculateEma(closes, 6)
  const ema12 = calculateEma(closes, 12)
  const ema13 = calculateEma(closes, 13)
  const ema26 = calculateEma(closes, 26)
  const ema52 = calculateEma(closes, 52)
  const dif = ema12.map((value, index) => value - ema26[index]!)
  const dea = calculateEma(dif, 9)

  return rows.map((row, index) => ({
    time: Math.floor(row[0] / 1000),
    open: Number(row[1]),
    high: Number(row[2]),
    low: Number(row[3]),
    close: Number(row[4]),
    volume: Number(row[5]),
    ema6: ema6[index]!,
    ema13: ema13[index]!,
    ema26: ema26[index]!,
    ema52: ema52[index]!,
    dif: dif[index]!,
    dea: dea[index]!,
    histogram: dif[index]! - dea[index]!
  }))
}

function buildMacdStatus(timeframe: DashboardInterval, points: CandlePoint[]): MacdStatus {
  const latest = points.at(-1)!
  const previous = points.at(-2) ?? latest
  const delta = latest.histogram - previous.histogram

  return {
    timeframe,
    dif: latest.dif,
    dea: latest.dea,
    direction: Math.abs(delta) < 0.01 ? 'flat' : delta > 0 ? 'up' : 'down'
  }
}

function buildVolumeStatus(timeframe: DashboardInterval, points: CandlePoint[]): VolumeStatus {
  const latest = points.at(-1)!
  const recent = points.slice(-21, -1)
  const average = recent.reduce((sum, point) => sum + point.volume, 0) / Math.max(recent.length, 1)
  const ratio = average > 0 ? latest.volume / average : 1
  const contractionPct = ratio < 1 ? (1 - ratio) * 100 : null
  const state = ratio <= 0.7 ? 'ACTIVE' : ratio <= 1 ? 'READY' : 'WAITING'

  return {
    timeframe,
    state,
    contractionPct,
    ratio,
    note: state === 'ACTIVE'
      ? `Vol ratio ${ratio.toFixed(2)}`
      : state === 'READY'
        ? 'Near contraction zone'
        : 'Volume not ready'
  }
}

function buildEmaStatus(timeframe: DashboardInterval, points: CandlePoint[]): EmaStatus {
  const latest = points.at(-1)!
  const spreadPct = ((latest.ema26 - latest.ema52) / latest.ema52) * 100
  const state = spreadPct >= 0 ? 'LONG' : 'SHORT'

  return {
    timeframe,
    state,
    spreadPct,
    note: `EMA26 ${state === 'LONG' ? 'above' : 'below'} 52`
  }
}

export function buildMarketFrame(
  timeframe: DashboardInterval,
  rows: BinanceKline[],
  dataSource: MarketDataSource = 'binance-futures',
  availablePoints = rows.length
): MarketFrame {
  if (rows.length < MINIMUM_FRAME_ROWS) {
    throw createError({ statusCode: 502, statusMessage: `Insufficient Binance data for ${timeframe}` })
  }

  const points = calculateIndicators(rows)
  const latest = points.at(-1)!
  const previous = points.at(-2) ?? latest

  return {
    timeframe,
    points,
    dataSource,
    availablePoints,
    lastPrice: latest.close,
    priceChangePct: ((latest.close - previous.close) / previous.close) * 100,
    macd: buildMacdStatus(timeframe, points),
    volume: buildVolumeStatus(timeframe, points),
    ema: buildEmaStatus(timeframe, points)
  }
}

export async function fetchMarketFrame(
  baseUrl: string,
  symbol: string,
  timeframe: DashboardInterval,
  options: MarketFetchOptions = {}
): Promise<MarketFrame> {
  const fetchLimit = normalizedLimit(options.fetchLimit, DEFAULT_FETCH_LIMIT, MINIMUM_FRAME_ROWS, 1_500)
  const cacheLimit = normalizedLimit(options.cacheLimit, DEFAULT_CACHE_LIMIT, fetchLimit, 50_000)
  const cacheKey = `${baseUrl}:${symbol}:${timeframe}:${fetchLimit}:${cacheLimit}`
  const cached = frameCache.get(cacheKey)

  if (cached && cached.expiresAt > Date.now()) {
    return cached.frame
  }

  const storage = useStorage<BinanceKline[]>('market')
  const storageKey = `${symbol.toLowerCase()}/${timeframe}`
  let locallyStoredRows: BinanceKline[] = []

  try {
    const storedRows = await storage.getItem(storageKey)
    locallyStoredRows = Array.isArray(storedRows) ? storedRows.filter(isBinanceKline) : []
  } catch (error) {
    console.warn(`Unable to read local market cache for ${symbol} ${timeframe}`, error)
  }

  let frame: MarketFrame

  try {
    const remoteRows = await $fetch<BinanceKline[]>(`${baseUrl}/fapi/v1/klines`, {
      query: {
        symbol,
        interval: timeframe,
        limit: fetchLimit
      },
      timeout: 8_000,
      retry: 1
    })
    const mergedRows = mergeKlines(locallyStoredRows, remoteRows, cacheLimit)

    try {
      await storage.setItem(storageKey, mergedRows)
    } catch (error) {
      console.warn(`Unable to write local market cache for ${symbol} ${timeframe}`, error)
    }

    frame = buildMarketFrame(
      timeframe,
      mergedRows.slice(-fetchLimit),
      'binance-futures',
      mergedRows.length
    )
  } catch (error) {
    if (locallyStoredRows.length < MINIMUM_FRAME_ROWS) throw error

    console.warn(`Binance unavailable; using local market cache for ${symbol} ${timeframe}`, error)
    frame = buildMarketFrame(
      timeframe,
      locallyStoredRows.slice(-fetchLimit),
      'local-cache',
      locallyStoredRows.length
    )
  }

  frameCache.set(cacheKey, { frame, expiresAt: Date.now() + 15_000 })
  return frame
}
