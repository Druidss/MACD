export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)

  if (!config.tradingviewWebhookSecret) {
    throw createError({
      statusCode: 503,
      statusMessage: 'TradingView webhook secret is not configured'
    })
  }

  const payload = tradingViewPayloadSchema.safeParse(await readBody(event))

  if (!payload.success) {
    throw createError({
      statusCode: 400,
      statusMessage: 'Invalid TradingView webhook payload',
      data: payload.error.flatten()
    })
  }

  if (!secretsMatch(payload.data.secret ?? payload.data.passphrase, config.tradingviewWebhookSecret)) {
    throw createError({ statusCode: 401, statusMessage: 'Invalid webhook secret' })
  }

  const result = await storeSignal(normalizeSignal(payload.data))
  setResponseStatus(event, result.duplicate ? 200 : 202)

  return {
    ok: true,
    duplicate: result.duplicate,
    signal: result.signal
  }
})
