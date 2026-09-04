<script setup lang="ts">
import { dashboardIntervals, type DashboardPayload } from '#shared/types/dashboard'

defineProps<{
  frames: DashboardPayload['frames']
}>()

const signed = (value: number, digits = 0) => `${value >= 0 ? '+' : ''}${value.toFixed(digits)}`
const percent = (value: number) => `${signed(value, 2)}%`
</script>

<template>
  <section class="strategy-grid">
    <article class="strategy-panel strategy-panel--macd">
      <header class="strategy-panel__header">
        <p class="panel-kicker">Multi-timeframe MACD</p>
        <h2 class="panel-title">多周期 MACD</h2>
      </header>

      <div
        v-for="timeframe in dashboardIntervals"
        :key="timeframe"
        class="macd-timeframe"
      >
        <div class="macd-timeframe__header mono">
          <strong>{{ timeframe.toUpperCase() }}</strong>
          <span>
            <em>{{ frames[timeframe].points.length }} B · DRAG</em>
            <i>DIF {{ signed(frames[timeframe].macd.dif) }}</i>
            <b>DEA {{ signed(frames[timeframe].macd.dea) }}</b>
          </span>
        </div>
        <TradingChart mode="mini" :points="frames[timeframe].points" />
      </div>
    </article>

    <article class="strategy-panel">
      <header class="strategy-panel__header">
        <p class="panel-kicker">Volume contraction</p>
        <h2 class="panel-title">零轴缩量仓位</h2>
      </header>

      <div class="signal-stack">
        <div
          v-for="timeframe in dashboardIntervals"
          :key="timeframe"
          class="signal-row"
        >
          <UIcon
            :name="frames[timeframe].volume.state === 'ACTIVE' ? 'i-lucide-trending-up' : 'i-lucide-activity'"
            class="signal-row__icon"
            :class="{ 'signal-row__icon--active': frames[timeframe].volume.state === 'ACTIVE' }"
          />
          <div class="signal-row__copy">
            <strong>{{ timeframe.toUpperCase() }}</strong>
            <span :class="{ positive: frames[timeframe].volume.state === 'ACTIVE' }">
              {{ frames[timeframe].volume.state }}
            </span>
          </div>
          <div class="signal-row__metric mono">
            <strong>
              {{ frames[timeframe].volume.contractionPct === null ? '—' : `+${frames[timeframe].volume.contractionPct.toFixed(1)}%` }}
            </strong>
            <span>{{ frames[timeframe].volume.note }}</span>
          </div>
        </div>
      </div>
    </article>

    <article class="strategy-panel">
      <header class="strategy-panel__header">
        <p class="panel-kicker">EMA 26 / 52</p>
        <h2 class="panel-title">EMA26 / 52 均线仓位</h2>
      </header>

      <div class="signal-stack">
        <div
          v-for="timeframe in dashboardIntervals"
          :key="timeframe"
          class="signal-row"
        >
          <UIcon
            :name="frames[timeframe].ema.state === 'LONG' ? 'i-lucide-trending-up' : 'i-lucide-trending-down'"
            class="signal-row__icon"
            :class="frames[timeframe].ema.state === 'LONG' ? 'signal-row__icon--active' : 'signal-row__icon--short'"
          />
          <div class="signal-row__copy">
            <strong>{{ timeframe.toUpperCase() }}</strong>
            <span :class="frames[timeframe].ema.state === 'LONG' ? 'positive' : 'negative'">
              {{ frames[timeframe].ema.state }}
            </span>
          </div>
          <div class="signal-row__metric mono">
            <strong>{{ percent(frames[timeframe].ema.spreadPct) }}</strong>
            <span>{{ frames[timeframe].ema.note }}</span>
          </div>
        </div>
      </div>
    </article>
  </section>
</template>

<style scoped>
.strategy-grid {
  display: grid;
  grid-template-columns: minmax(0, 2.18fr) repeat(2, minmax(270px, 1fr));
  align-items: start;
  gap: 24px;
  margin-top: 24px;
}

.strategy-panel {
  min-width: 0;
  min-height: 392px;
  padding: 24px;
  border: 1px solid var(--momentum-border-subtle);
  border-radius: 20px;
  background: var(--momentum-surface-card);
}

.strategy-panel--macd {
  display: grid;
  gap: 16px;
  min-height: 680px;
}

.strategy-panel__header {
  min-height: 48px;
}

.macd-timeframe {
  height: 168px;
  padding: 16px;
  overflow: hidden;
  border: 1px solid var(--momentum-border-subtle);
  border-radius: 12px;
  background: var(--momentum-surface-subtle);
}

.macd-timeframe__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 16px;
  font-size: 11px;
}

.macd-timeframe__header strong {
  font-size: 12px;
  font-weight: 500;
}

.macd-timeframe__header span {
  display: flex;
  gap: 16px;
  font-size: 9px;
  font-style: normal;
}

.macd-timeframe__header i,
.macd-timeframe__header b,
.macd-timeframe__header em {
  font-style: normal;
  font-weight: 500;
}

.macd-timeframe__header em { color: var(--momentum-text-muted); }
.macd-timeframe__header i { color: #2f6bff; }
.macd-timeframe__header b { color: #ff7a00; }

.signal-stack {
  display: grid;
  gap: 16px;
  margin-top: 16px;
}

.signal-row {
  display: grid;
  grid-template-columns: 26px 1fr minmax(92px, auto);
  align-items: center;
  min-height: 64px;
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.02);
  border-radius: 12px;
  background: var(--momentum-surface-subtle);
}

.signal-row__icon {
  width: 18px;
  height: 18px;
  color: #c4c6cc;
}

.signal-row__icon--active { color: var(--momentum-brand-lime); }
.signal-row__icon--short { color: var(--momentum-brand-pink); }

.signal-row__copy,
.signal-row__metric {
  display: grid;
  gap: 5px;
}

.signal-row__copy strong {
  font-size: 12px;
  font-weight: 650;
}

.signal-row__copy span {
  color: var(--momentum-text-secondary);
  font-family: "IBM Plex Mono Variable", monospace;
  font-size: 9px;
}

.signal-row__copy .positive { color: var(--momentum-brand-lime); }
.signal-row__copy .negative { color: var(--momentum-brand-pink); }

.signal-row__metric {
  justify-items: end;
  min-width: 0;
  text-align: right;
}

.signal-row__metric strong {
  color: white;
  font-size: 11px;
  font-weight: 500;
}

.signal-row__metric span {
  max-width: 110px;
  overflow: hidden;
  color: var(--momentum-text-muted);
  font-size: 8px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1120px) {
  .strategy-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .strategy-panel--macd {
    grid-column: 1 / -1;
  }
}

@media (max-width: 680px) {
  .strategy-grid {
    grid-template-columns: 1fr;
  }

  .strategy-panel--macd {
    grid-column: auto;
  }

  .strategy-panel {
    padding: 18px;
  }
}
</style>
