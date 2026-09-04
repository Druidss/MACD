<script setup lang="ts">
import { dashboardIntervals, type DashboardInterval, type MarketFrame } from '#shared/types/dashboard'

const props = defineProps<{
  frame: MarketFrame
  activeInterval: DashboardInterval
}>()

const emit = defineEmits<{
  changeInterval: [value: DashboardInterval]
}>()

const formatPrice = (value: number) => new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 1
}).format(value)

const priceChange = computed(() => `${props.frame.priceChangePct >= 0 ? '+' : ''}${props.frame.priceChangePct.toFixed(2)}%`)
</script>

<template>
  <section class="market-panel surface">
    <div class="market-panel__header">
      <div class="market-summary">
        <div class="asset-mark">₿</div>
        <div>
          <p>BTC / USDT</p>
          <strong>{{ formatPrice(frame.lastPrice) }}</strong>
        </div>
        <span
          class="change-badge mono"
          :class="{ 'change-badge--negative': frame.priceChangePct < 0 }"
        >
          {{ priceChange }}
        </span>
      </div>

      <div class="timeframe-tabs" aria-label="Chart timeframe">
        <button
          v-for="timeframe in dashboardIntervals"
          :key="timeframe"
          type="button"
          class="timeframe-tabs__item"
          :class="{ 'timeframe-tabs__item--active': activeInterval === timeframe }"
          @click="emit('changeInterval', timeframe)"
        >
          {{ timeframe.toUpperCase() }}
        </button>
      </div>

      <div class="ema-legend mono">
        <span><i class="ema-dot ema-dot--6" />EMA 6</span>
        <span><i class="ema-dot ema-dot--13" />EMA 13</span>
        <span><i class="ema-dot ema-dot--26" />EMA 26</span>
        <span><i class="ema-dot ema-dot--52" />EMA 52</span>
      </div>
    </div>

    <div class="price-chart-card">
      <div class="chart-range-meta mono">
        {{ frame.points.length }} BARS · {{ frame.dataSource === 'local-cache' ? 'CACHE' : 'LIVE' }} · DRAG / ZOOM
      </div>
      <TradingChart mode="price" :points="frame.points" />
    </div>

    <div class="macd-chart-card">
      <div class="macd-chart-label mono">
        <strong>MACD 12 / 26 / 9</strong>
        <span><i class="macd-dot macd-dot--dif" />DIF</span>
        <span><i class="macd-dot macd-dot--dea" />DEA</span>
        <span><i class="macd-dot macd-dot--positive-contracting" />绿缩</span>
        <span><i class="macd-dot macd-dot--negative-contracting" />红缩</span>
      </div>
      <TradingChart mode="macd" :points="frame.points" />
    </div>
  </section>
</template>

<style scoped>
.market-panel {
  display: grid;
  grid-template-rows: 72px minmax(300px, 340px) minmax(180px, 220px);
  gap: 16px;
  min-height: 720px;
  margin-top: 24px;
  padding: 24px;
  border-radius: 28px;
}

.market-panel__header {
  display: grid;
  grid-template-columns: 390px 330px 1fr;
  align-items: center;
  justify-content: space-between;
}

.market-summary {
  display: flex;
  align-items: center;
  gap: 12px;
}

.asset-mark {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 50%;
  background: var(--momentum-brand-lime);
  color: #0c0c0e;
  font-size: 20px;
  font-weight: 700;
}

.market-summary p {
  margin: 0 0 2px;
  color: var(--momentum-text-secondary);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
}

.market-summary strong {
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -0.02em;
}

.change-badge {
  min-width: 88px;
  margin-left: 12px;
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--momentum-brand-lime);
  color: #0c0c0e;
  font-size: 12px;
  text-align: center;
}

.change-badge--negative {
  background: var(--momentum-brand-pink);
  color: white;
}

.timeframe-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  height: 56px;
  padding: 4px;
  border-radius: 28px;
  background: var(--momentum-surface-subtle);
}

.timeframe-tabs__item {
  border: 0;
  border-radius: 24px;
  background: transparent;
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
  font-weight: 650;
}

.timeframe-tabs__item--active {
  background: var(--momentum-brand-lime);
  color: #0c0c0e;
}

.ema-legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: clamp(12px, 2.2vw, 32px);
  color: rgba(255, 255, 255, 0.72);
  font-size: 11px;
}

.ema-legend span {
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.ema-dot,
.macd-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.ema-dot--6 { background: #a9adb7; }
.ema-dot--13 { background: var(--momentum-brand-blue); }
.ema-dot--26 { background: var(--momentum-brand-lime); }
.ema-dot--52 { background: var(--momentum-brand-pink); }

.price-chart-card,
.macd-chart-card {
  position: relative;
  min-width: 0;
  overflow: hidden;
  border-radius: 20px;
  background: var(--momentum-surface-subtle);
}

.price-chart-card {
  padding: 18px 12px 6px;
}

.chart-range-meta {
  position: absolute;
  z-index: 2;
  top: 12px;
  right: 16px;
  color: var(--momentum-text-muted);
  font-size: 8px;
  letter-spacing: 0.04em;
  pointer-events: none;
}

.macd-chart-card {
  padding: 30px 12px 8px;
}

.macd-chart-label {
  position: absolute;
  z-index: 2;
  top: 16px;
  left: 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--momentum-text-secondary);
  font-size: 9px;
}

.macd-chart-label strong {
  color: white;
  font-weight: 500;
}

.macd-chart-label span {
  display: flex;
  align-items: center;
  gap: 5px;
}

.macd-dot--dif { background: #2f6bff; }
.macd-dot--dea { background: #ff7a00; }
.macd-dot--positive-contracting { background: #b8ded9; }
.macd-dot--negative-contracting { background: #ffc8cf; }

@media (max-width: 1120px) {
  .market-panel {
    grid-template-rows: auto minmax(300px, 340px) minmax(180px, 220px);
  }

  .market-panel__header {
    grid-template-columns: 1fr 330px;
    gap: 16px;
  }

  .ema-legend {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }
}

@media (max-width: 720px) {
  .market-panel {
    min-height: auto;
    padding: 14px;
    border-radius: 22px;
  }

  .market-panel__header {
    grid-template-columns: 1fr;
  }

  .timeframe-tabs {
    width: 100%;
  }

  .ema-legend {
    gap: 14px;
    overflow-x: auto;
  }

  .market-summary {
    flex-wrap: wrap;
  }

  .change-badge {
    margin-left: auto;
  }
}
</style>
