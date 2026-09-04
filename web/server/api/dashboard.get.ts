import { dashboardIntervals, type DashboardInterval, type DashboardPayload } from '#shared/types/dashboard'

export default defineEventHandler(async (event): Promise<DashboardPayload> => {
  const query = getQuery(event)
  const requested = typeof query.interval === 'string' ? query.interval : '6h'
  const selectedInterval: DashboardInterval = dashboardIntervals.includes(requested as DashboardInterval)
    ? requested as DashboardInterval
    : '6h'
  const symbol = 'BTCUSDT'
  const config = useRuntimeConfig(event)

  try {
    const entries = await Promise.all(
      dashboardIntervals.map(async timeframe => [
        timeframe,
        await fetchMarketFrame(config.binanceBaseUrl, symbol, timeframe)
      ] as const)
    )
    const frames = Object.fromEntries(entries) as DashboardPayload['frames']

    return {
      generatedAt: new Date().toISOString(),
      source: 'binance-futures',
      symbol,
      selectedInterval,
      frames
    }
  } catch (error) {
    console.error('Dashboard market fetch failed', error)
    throw createError({
      statusCode: 502,
      statusMessage: 'Unable to load Binance market data'
    })
  }
})
