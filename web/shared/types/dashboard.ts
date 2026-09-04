export const dashboardIntervals = ['1h', '6h', '1d'] as const

export type DashboardInterval = typeof dashboardIntervals[number]
export type MarketDataSource = 'binance-futures' | 'local-cache'

export interface CandlePoint {
  time: number
  open: number
  high: number
  low: number
  close: number
  volume: number
  ema6: number
  ema13: number
  ema26: number
  ema52: number
  dif: number
  dea: number
  histogram: number
}

export interface MacdStatus {
  timeframe: DashboardInterval
  dif: number
  dea: number
  direction: 'up' | 'down' | 'flat'
}

export interface VolumeStatus {
  timeframe: DashboardInterval
  state: 'ACTIVE' | 'READY' | 'WAITING'
  contractionPct: number | null
  ratio: number
  note: string
}

export interface EmaStatus {
  timeframe: DashboardInterval
  state: 'LONG' | 'SHORT'
  spreadPct: number
  note: string
}

export interface MarketFrame {
  timeframe: DashboardInterval
  points: CandlePoint[]
  dataSource: MarketDataSource
  availablePoints: number
  lastPrice: number
  priceChangePct: number
  macd: MacdStatus
  volume: VolumeStatus
  ema: EmaStatus
}

export interface TradingSignal {
  id: string
  ticker: string
  timeframe: string
  action: 'BUY' | 'SELL' | 'LONG' | 'SHORT' | 'CLOSE'
  price: number | null
  strategy: string
  message: string | null
  occurredAt: string
  receivedAt: string
}

export interface DashboardPayload {
  generatedAt: string
  source: MarketDataSource | 'mixed'
  symbol: string
  selectedInterval: DashboardInterval
  frames: Record<DashboardInterval, MarketFrame>
}

export interface SignalsPayload {
  generatedAt: string
  signals: TradingSignal[]
}
