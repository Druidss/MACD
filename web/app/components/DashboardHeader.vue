<script setup lang="ts">
import type { DashboardPayload } from '#shared/types/dashboard'

const props = defineProps<{
  pending: boolean
  updatedAt?: string
  source?: DashboardPayload['source']
  activeView: 'overview' | 'positions' | 'signals'
}>()

const emit = defineEmits<{
  refresh: []
  changeView: [value: 'overview' | 'positions' | 'signals']
}>()

const navigation = [
  { label: 'Overview', value: 'overview' },
  { label: 'Positions', value: 'positions' },
  { label: 'Signals', value: 'signals' }
] as const

const updatedLabel = computed(() => {
  if (!props.updatedAt) return 'CONNECTING'

  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  }).format(new Date(props.updatedAt))
})

const sourceLabel = computed(() => {
  if (props.source === 'local-cache') return 'LOCAL CACHE'
  if (props.source === 'mixed') return 'BINANCE + CACHE'
  return 'BINANCE'
})
</script>

<template>
  <header class="dashboard-header surface">
    <div class="brand-lockup">
      <div class="brand-mark">M</div>
      <strong>MOMENTUM / FIELD</strong>
    </div>

    <nav class="primary-nav" aria-label="Primary navigation">
      <button
        v-for="item in navigation"
        :key="item.value"
        class="primary-nav__item"
        :class="{ 'primary-nav__item--active': activeView === item.value }"
        :aria-current="activeView === item.value ? 'page' : undefined"
        type="button"
        @click="emit('changeView', item.value)"
      >
        {{ item.label }}
      </button>
    </nav>

    <div class="market-connection">
      <div class="market-pill">
        <span class="live-dot" :class="{ 'live-dot--cache': source === 'local-cache' }" />
        <span>{{ sourceLabel }} · BTCUSDT</span>
        <span class="connection-time mono">{{ updatedLabel }}</span>
      </div>
      <UButton
        class="refresh-button"
        icon="i-lucide-refresh-cw"
        color="primary"
        variant="solid"
        size="lg"
        square
        :loading="pending"
        aria-label="Refresh market data"
        @click="emit('refresh')"
      />
    </div>
  </header>
</template>

<style scoped>
.dashboard-header {
  display: grid;
  grid-template-columns: 280px minmax(360px, 430px) 310px;
  align-items: center;
  justify-content: space-between;
  min-height: 72px;
  padding: 12px 16px;
  border-radius: 20px;
}

.brand-lockup,
.market-connection {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-lockup strong {
  font-size: 20px;
  font-weight: 650;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 12px;
  background: var(--momentum-brand-lime);
  color: #0c0c0e;
  font-size: 12px;
  font-weight: 750;
}

.primary-nav {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  height: 48px;
  padding: 4px;
  border-radius: 24px;
  background: var(--momentum-surface-subtle);
}

.primary-nav__item {
  min-width: 0;
  border: 0;
  border-radius: 20px;
  background: transparent;
  color: rgba(255, 255, 255, 0.58);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
}

.primary-nav__item--active {
  background: var(--momentum-surface-card);
  color: white;
}

.market-connection {
  justify-content: flex-end;
}

.market-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 18px;
  border-radius: 20px;
  background: var(--momentum-surface-subtle);
  font-size: 11px;
  font-weight: 650;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.live-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--momentum-brand-lime);
  box-shadow: 0 0 12px rgba(189, 254, 48, 0.58);
}

.live-dot--cache {
  background: #ffb340;
  box-shadow: 0 0 12px rgba(255, 179, 64, 0.5);
}

.connection-time {
  color: var(--momentum-text-muted);
  font-size: 9px;
}

.refresh-button {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  color: #0c0c0e;
}

@media (max-width: 1120px) {
  .dashboard-header {
    grid-template-columns: 1fr auto;
    gap: 12px;
  }

  .primary-nav {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}

@media (max-width: 640px) {
  .dashboard-header {
    grid-template-columns: 1fr auto;
    padding: 12px;
  }

  .brand-lockup strong {
    font-size: 15px;
  }

  .market-pill {
    display: none;
  }
}
</style>
