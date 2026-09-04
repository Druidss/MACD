export const macdColors = {
  dif: '#2f6bff',
  dea: '#ff7a00',
  positive: '#2aaea2',
  negative: '#ff4d5c',
  positiveContracting: '#b8ded9',
  negativeContracting: '#ffc8cf'
} as const

export type MacdHistogramState =
  | 'positive'
  | 'negative'
  | 'positive-contracting'
  | 'negative-contracting'

export function getMacdHistogramState(current: number, previous?: number): MacdHistogramState {
  if (current >= 0) {
    const isContracting = previous !== undefined && previous >= 0 && current < previous
    return isContracting ? 'positive-contracting' : 'positive'
  }

  const isContracting = previous !== undefined && previous < 0 && current > previous
  return isContracting ? 'negative-contracting' : 'negative'
}

export function getMacdHistogramColor(current: number, previous?: number): string {
  const state = getMacdHistogramState(current, previous)

  return {
    positive: macdColors.positive,
    negative: macdColors.negative,
    'positive-contracting': macdColors.positiveContracting,
    'negative-contracting': macdColors.negativeContracting
  }[state]
}
