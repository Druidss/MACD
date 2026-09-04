<script setup lang="ts">
import type { IChartApi, ISeriesApi, UTCTimestamp } from 'lightweight-charts'
import type { CandlePoint } from '#shared/types/dashboard'
import { getMacdHistogramColor, macdColors } from '#shared/utils/macd-style'

const props = defineProps<{
  points: CandlePoint[]
  mode: 'price' | 'macd' | 'mini'
}>()

const container = ref<HTMLElement>()
const chartError = ref('')

let chart: IChartApi | undefined
let candleSeries: ISeriesApi<'Candlestick'> | undefined
let ema6Series: ISeriesApi<'Line'> | undefined
let ema13Series: ISeriesApi<'Line'> | undefined
let ema26Series: ISeriesApi<'Line'> | undefined
let ema52Series: ISeriesApi<'Line'> | undefined
let histogramSeries: ISeriesApi<'Histogram'> | undefined
let difSeries: ISeriesApi<'Line'> | undefined
let deaSeries: ISeriesApi<'Line'> | undefined
let resizeObserver: ResizeObserver | undefined

const visiblePointStart = () => Math.max(0, props.points.length - (props.mode === 'mini' ? 72 : 56))

function setSeriesData() {
  const startIndex = visiblePointStart()
  const points = props.points.slice(startIndex)

  candleSeries?.setData(points.map(point => ({
    time: point.time as UTCTimestamp,
    open: point.open,
    high: point.high,
    low: point.low,
    close: point.close
  })))

  const lineData = (key: 'ema6' | 'ema13' | 'ema26' | 'ema52') => points.map(point => ({
    time: point.time as UTCTimestamp,
    value: point[key]
  }))

  ema6Series?.setData(lineData('ema6'))
  ema13Series?.setData(lineData('ema13'))
  ema26Series?.setData(lineData('ema26'))
  ema52Series?.setData(lineData('ema52'))

  histogramSeries?.setData(points.map((point, index) => ({
    time: point.time as UTCTimestamp,
    value: point.histogram,
    color: getMacdHistogramColor(point.histogram, props.points[startIndex + index - 1]?.histogram)
  })))
  difSeries?.setData(points.map(point => ({ time: point.time as UTCTimestamp, value: point.dif })))
  deaSeries?.setData(points.map(point => ({ time: point.time as UTCTimestamp, value: point.dea })))
  chart?.timeScale().fitContent()
}

onMounted(async () => {
  await nextTick()
  if (!container.value) return

  try {
    const {
      CandlestickSeries,
      ColorType,
      CrosshairMode,
      HistogramSeries,
      LineSeries,
      createChart
    } = await import('lightweight-charts')

    const isMini = props.mode === 'mini'
    const isPrice = props.mode === 'price'

    chart = createChart(container.value, {
      width: container.value.clientWidth,
      height: container.value.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: isMini ? 'transparent' : '#777b84',
        fontFamily: 'IBM Plex Mono, monospace',
        fontSize: 10,
        attributionLogo: false
      },
      grid: {
        vertLines: { visible: false },
        horzLines: isMini || props.mode === 'macd' ? { visible: false } : { color: '#2a2b2f' }
      },
      crosshair: isMini
        ? { vertLine: { visible: false }, horzLine: { visible: false } }
        : { mode: CrosshairMode.Normal },
      leftPriceScale: { visible: false },
      rightPriceScale: {
        visible: !isMini,
        borderVisible: false,
        scaleMargins: isPrice ? { top: 0.12, bottom: 0.18 } : { top: 0.14, bottom: 0.14 }
      },
      timeScale: {
        visible: isPrice,
        borderVisible: false,
        timeVisible: isPrice,
        secondsVisible: false,
        rightOffset: isMini ? 0 : 2,
        barSpacing: isMini ? 6 : 11
      },
      handleScale: isPrice,
      handleScroll: isPrice
    })

    if (isPrice) {
      candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: '#bdfe30',
        downColor: '#fc46ab',
        wickUpColor: '#bdfe30',
        wickDownColor: '#fc46ab',
        borderVisible: false,
        priceLineVisible: false,
        lastValueVisible: false
      })

      const lineOptions = {
        lineWidth: 1 as const,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false
      }

      ema6Series = chart.addSeries(LineSeries, { ...lineOptions, color: '#a9adb7' })
      ema13Series = chart.addSeries(LineSeries, { ...lineOptions, color: '#8ab8cb' })
      ema26Series = chart.addSeries(LineSeries, { ...lineOptions, color: '#bdfe30' })
      ema52Series = chart.addSeries(LineSeries, { ...lineOptions, color: '#fc46ab' })
    } else {
      histogramSeries = chart.addSeries(HistogramSeries, {
        priceLineVisible: false,
        lastValueVisible: false,
        base: 0
      })
      difSeries = chart.addSeries(LineSeries, {
        color: macdColors.dif,
        lineWidth: isMini ? 2 : 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false
      })
      deaSeries = chart.addSeries(LineSeries, {
        color: macdColors.dea,
        lineWidth: isMini ? 2 : 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false
      })
    }

    setSeriesData()
    container.value.dataset.chartMounted = 'true'

    resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return

      chart?.applyOptions({
        width: Math.floor(entry.contentRect.width),
        height: Math.floor(entry.contentRect.height)
      })
    })
    resizeObserver.observe(container.value)
  } catch (error) {
    chartError.value = error instanceof Error ? error.message : 'Chart could not be rendered.'
    console.error('Trading chart initialization failed', error)
  }
})

watch(() => props.points, setSeriesData, { deep: false })

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  chart?.remove()
})
</script>

<template>
  <div
    ref="container"
    class="trading-chart"
    :class="`trading-chart--${mode}`"
  >
    <span v-if="chartError" class="trading-chart__error">{{ chartError }}</span>
  </div>
</template>

<style scoped>
.trading-chart {
  width: 100%;
  height: 100%;
}

.trading-chart--price { min-height: 280px; }
.trading-chart--macd { min-height: 150px; }
.trading-chart--mini { min-height: 104px; }

.trading-chart__error {
  display: grid;
  height: 100%;
  place-items: center;
  color: var(--momentum-brand-pink);
  font-size: 11px;
}
</style>
