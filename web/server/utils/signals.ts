import { createHash, timingSafeEqual } from 'node:crypto'
import { z } from 'zod'
import type { TradingSignal } from '#shared/types/dashboard'

export const tradingViewPayloadSchema = z.object({
  secret: z.string().optional(),
  passphrase: z.string().optional(),
  ticker: z.string().min(1).default('BTCUSDT'),
  timeframe: z.string().min(1).default('6h'),
  action: z.enum(['BUY', 'SELL', 'LONG', 'SHORT', 'CLOSE']),
  price: z.coerce.number().finite().optional(),
  strategy: z.string().min(1).default('TradingView'),
  message: z.string().max(2_000).optional(),
  timestamp: z.union([z.string(), z.number()]).optional(),
  id: z.string().optional()
})

export type TradingViewPayload = z.infer<typeof tradingViewPayloadSchema>

export function secretsMatch(received: string | undefined, expected: string): boolean {
  if (!received || !expected) return false

  const left = Buffer.from(received)
  const right = Buffer.from(expected)
  return left.length === right.length && timingSafeEqual(left, right)
}

function parseOccurredAt(value: string | number | undefined): string {
  if (value === undefined) return new Date().toISOString()
  const date = typeof value === 'number'
    ? new Date(value < 10_000_000_000 ? value * 1000 : value)
    : new Date(value)

  return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString()
}

export function normalizeSignal(payload: TradingViewPayload): TradingSignal {
  const occurredAt = parseOccurredAt(payload.timestamp)
  const identity = payload.id ?? [
    payload.ticker,
    payload.timeframe,
    payload.action,
    payload.strategy,
    occurredAt
  ].join(':')

  return {
    id: createHash('sha256').update(identity).digest('hex').slice(0, 24),
    ticker: payload.ticker.toUpperCase(),
    timeframe: payload.timeframe,
    action: payload.action,
    price: payload.price ?? null,
    strategy: payload.strategy,
    message: payload.message ?? null,
    occurredAt,
    receivedAt: new Date().toISOString()
  }
}

export async function listSignals(limit = 30): Promise<TradingSignal[]> {
  const storage = useStorage<TradingSignal[]>('signals')
  const signals = await storage.getItem('events') ?? []
  return signals.slice(0, Math.min(Math.max(limit, 1), 100))
}

export async function storeSignal(signal: TradingSignal): Promise<{ signal: TradingSignal, duplicate: boolean }> {
  const storage = useStorage<TradingSignal[]>('signals')
  const signals = await storage.getItem('events') ?? []
  const existing = signals.find(item => item.id === signal.id)

  if (existing) return { signal: existing, duplicate: true }

  await storage.setItem('events', [signal, ...signals].slice(0, 100))
  return { signal, duplicate: false }
}
