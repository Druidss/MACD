export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const limit = Number(query.limit ?? 30)

  return {
    generatedAt: new Date().toISOString(),
    signals: await listSignals(Number.isFinite(limit) ? limit : 30)
  }
})
