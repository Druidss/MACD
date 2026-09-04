<script setup lang="ts">
import type { TradingSignal } from '#shared/types/dashboard'

const props = defineProps<{
  signals: TradingSignal[]
  pending: boolean
  error?: string
}>()

const emit = defineEmits<{
  refresh: []
}>()

const formatPrice = (value: number | null) => value === null
  ? '—'
  : new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 2
    }).format(value)

const formatDate = (value: string) => new Intl.DateTimeFormat('zh-CN', {
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false
}).format(new Date(value))

const actionTone = (action: TradingSignal['action']) => {
  if (action === 'BUY' || action === 'LONG') return 'positive'
  if (action === 'SELL' || action === 'SHORT') return 'negative'
  return 'neutral'
}

const latestReceivedAt = computed(() => props.signals[0]?.receivedAt)
</script>

<template>
  <section class="signals-panel surface">
    <header class="signals-panel__header">
      <div>
        <p class="panel-kicker">TradingView webhook</p>
        <h1 class="signals-panel__title">策略信号</h1>
        <p class="signals-panel__subtitle">
          服务器接收并保存的最近信号。相同信号 ID 只记录一次。
        </p>
      </div>

      <div class="signals-panel__status">
        <span class="signal-count mono">{{ signals.length }} SIGNALS</span>
        <span v-if="latestReceivedAt" class="last-received mono">
          LAST {{ formatDate(latestReceivedAt) }}
        </span>
        <UButton
          icon="i-lucide-refresh-cw"
          color="primary"
          variant="solid"
          size="md"
          :loading="pending"
          @click="emit('refresh')"
        >
          刷新
        </UButton>
      </div>
    </header>

    <div v-if="error" class="signals-error" role="alert">
      <UIcon name="i-lucide-triangle-alert" />
      <div>
        <strong>暂时无法读取服务器信号</strong>
        <span>{{ error }}</span>
      </div>
      <UButton color="neutral" variant="soft" size="sm" @click="emit('refresh')">重试</UButton>
    </div>

    <div v-else-if="signals.length" class="signals-table">
      <div class="signals-table__head mono" aria-hidden="true">
        <span>Direction</span>
        <span>Market</span>
        <span>Strategy</span>
        <span>Signal time</span>
        <span>Price</span>
      </div>

      <article
        v-for="signal in signals"
        :key="signal.id"
        class="signal-item"
      >
        <div class="signal-direction">
          <span class="direction-mark" :class="`direction-mark--${actionTone(signal.action)}`">
            <UIcon :name="actionTone(signal.action) === 'positive' ? 'i-lucide-arrow-up-right' : actionTone(signal.action) === 'negative' ? 'i-lucide-arrow-down-right' : 'i-lucide-minus'" />
          </span>
          <strong :class="actionTone(signal.action)">{{ signal.action }}</strong>
        </div>

        <div class="signal-market">
          <strong>{{ signal.ticker }}</strong>
          <span class="mono">{{ signal.timeframe.toUpperCase() }}</span>
        </div>

        <div class="signal-strategy">
          <strong>{{ signal.strategy }}</strong>
          <span>{{ signal.message || 'Webhook signal' }}</span>
        </div>

        <time class="signal-time mono" :datetime="signal.occurredAt">
          {{ formatDate(signal.occurredAt) }}
        </time>

        <strong class="signal-price mono">{{ formatPrice(signal.price) }}</strong>
      </article>
    </div>

    <div v-else class="signals-empty">
      <span class="signals-empty__icon">
        <UIcon name="i-lucide-webhook" />
      </span>
      <strong>等待第一条 TradingView 信号</strong>
      <p>配置服务器公网 HTTPS 地址和 webhook 密钥后，收到的信号会显示在这里。</p>
      <code>https://&lt;your-domain&gt;/api/webhooks/tradingview</code>
    </div>
  </section>
</template>

<style scoped>
.signals-panel {
  min-height: 680px;
  margin-top: 24px;
  padding: 28px;
  border-radius: 28px;
}

.signals-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 28px;
  padding: 4px 4px 28px;
}

.signals-panel__title {
  margin: 8px 0 0;
  font-size: 28px;
  font-weight: 650;
  letter-spacing: -0.035em;
}

.signals-panel__subtitle {
  margin: 8px 0 0;
  color: var(--momentum-text-secondary);
  font-size: 12px;
}

.signals-panel__status {
  display: flex;
  align-items: center;
  gap: 14px;
}

.signal-count,
.last-received {
  color: var(--momentum-text-muted);
  font-size: 9px;
}

.signal-count {
  padding: 8px 12px;
  border-radius: 999px;
  background: var(--momentum-surface-subtle);
  color: var(--momentum-brand-lime);
}

.signals-table {
  display: grid;
  gap: 8px;
}

.signals-error {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border: 1px solid rgba(252, 70, 171, 0.36);
  border-radius: 14px;
  background: rgba(252, 70, 171, 0.08);
}

.signals-error > svg {
  width: 21px;
  height: 21px;
  color: var(--momentum-brand-pink);
}

.signals-error div {
  display: grid;
  gap: 3px;
}

.signals-error strong { font-size: 12px; }
.signals-error span { color: var(--momentum-text-secondary); font-size: 10px; }

.signals-table__head,
.signal-item {
  display: grid;
  grid-template-columns: 150px 160px minmax(220px, 1fr) 170px 130px;
  align-items: center;
  gap: 18px;
}

.signals-table__head {
  padding: 0 18px 8px;
  color: var(--momentum-text-muted);
  font-size: 9px;
  text-transform: uppercase;
}

.signal-item {
  min-height: 76px;
  padding: 14px 18px;
  border: 1px solid var(--momentum-border-subtle);
  border-radius: 14px;
  background: var(--momentum-surface-subtle);
}

.signal-direction,
.signal-market,
.signal-strategy {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.signal-market,
.signal-strategy {
  align-items: flex-start;
  flex-direction: column;
  gap: 3px;
}

.direction-mark {
  display: grid;
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.06);
}

.direction-mark svg {
  width: 17px;
  height: 17px;
}

.direction-mark--positive {
  background: rgba(189, 254, 48, 0.12);
  color: var(--momentum-brand-lime);
}

.direction-mark--negative {
  background: rgba(252, 70, 171, 0.12);
  color: var(--momentum-brand-pink);
}

.positive { color: var(--momentum-brand-lime); }
.negative { color: var(--momentum-brand-pink); }
.neutral { color: var(--momentum-text-secondary); }

.signal-direction strong,
.signal-market strong,
.signal-strategy strong,
.signal-price {
  font-size: 12px;
  font-weight: 600;
}

.signal-market span,
.signal-strategy span,
.signal-time {
  overflow: hidden;
  color: var(--momentum-text-muted);
  font-size: 9px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.signal-price {
  text-align: right;
}

.signals-empty {
  display: grid;
  min-height: 500px;
  place-content: center;
  justify-items: center;
  text-align: center;
}

.signals-empty__icon {
  display: grid;
  width: 54px;
  height: 54px;
  margin-bottom: 18px;
  place-items: center;
  border-radius: 16px;
  background: rgba(189, 254, 48, 0.1);
  color: var(--momentum-brand-lime);
}

.signals-empty__icon svg {
  width: 24px;
  height: 24px;
}

.signals-empty strong {
  font-size: 17px;
}

.signals-empty p {
  max-width: 480px;
  margin: 8px 0 16px;
  color: var(--momentum-text-secondary);
  font-size: 11px;
}

.signals-empty code {
  padding: 10px 14px;
  border-radius: 10px;
  background: var(--momentum-surface-subtle);
  color: var(--momentum-brand-lime);
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
}

@media (max-width: 980px) {
  .signals-table__head {
    display: none;
  }

  .signal-item {
    grid-template-columns: 130px 120px 1fr;
  }

  .signal-time,
  .signal-price {
    grid-column: auto;
  }
}

@media (max-width: 700px) {
  .signals-panel {
    padding: 18px;
  }

  .signals-panel__header,
  .signals-panel__status {
    align-items: flex-start;
    flex-direction: column;
  }

  .signal-item {
    grid-template-columns: 1fr 1fr;
  }

  .signal-strategy {
    grid-column: 1 / -1;
  }

  .signal-price {
    text-align: left;
  }

  .signals-error {
    grid-template-columns: auto 1fr;
  }

  .signals-error button {
    grid-column: 1 / -1;
  }
}
</style>
