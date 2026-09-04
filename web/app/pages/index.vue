<script setup lang="ts">
import type { DashboardInterval, DashboardPayload, SignalsPayload } from '#shared/types/dashboard'

type DashboardView = 'overview' | 'positions' | 'signals'

const activeInterval = ref<DashboardInterval>('6h')
const activeView = ref<DashboardView>('overview')
const query = computed(() => ({ interval: activeInterval.value }))

const {
  data: dashboard,
  error: marketError,
  status: marketStatus,
  refresh: refreshMarket
} = await useFetch<DashboardPayload>('/api/dashboard', {
  query,
  key: 'momentum-dashboard'
})

const {
  data: signalFeed,
  error: signalsError,
  status: signalsStatus,
  refresh: refreshSignals
} = await useFetch<SignalsPayload>('/api/signals', {
  key: 'momentum-signals'
})

const pending = computed(() => activeView.value === 'signals'
  ? signalsStatus.value === 'pending'
  : activeView.value === 'overview' && marketStatus.value === 'pending')
const activeFrame = computed(() => dashboard.value?.frames[activeInterval.value])
const updatedAt = computed(() => activeView.value === 'signals'
  ? signalFeed.value?.generatedAt
  : dashboard.value?.generatedAt)
const runtimeConfig = useRuntimeConfig()
let pollTimer: ReturnType<typeof setInterval> | undefined

function changeInterval(value: DashboardInterval) {
  activeInterval.value = value
}

function requestRefresh() {
  if (activeView.value === 'signals') {
    void refreshSignals()
    return
  }

  if (activeView.value === 'overview') void refreshMarket()
}

onMounted(() => {
  pollTimer = setInterval(() => {
    void refreshMarket()
    void refreshSignals()
  }, Number(runtimeConfig.public.dashboardPollMs) || 30_000)
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <main class="dashboard-shell">
    <DashboardHeader
      :pending="pending"
      :updated-at="updatedAt"
      :active-view="activeView"
      @refresh="requestRefresh"
      @change-view="activeView = $event"
    />

    <template v-if="activeView === 'overview'">
      <div v-if="marketError" class="error-banner" role="alert">
        <UIcon name="i-lucide-triangle-alert" />
        <div>
          <strong>Binance 数据暂时不可用</strong>
          <span>{{ marketError.statusMessage || marketError.message }}</span>
        </div>
        <UButton color="neutral" variant="soft" size="sm" @click="requestRefresh">重试</UButton>
      </div>

      <template v-else-if="dashboard && activeFrame">
        <MarketPanel
          :frame="activeFrame"
          :active-interval="activeInterval"
          @change-interval="changeInterval"
        />
        <StrategyGrid :frames="dashboard.frames" />
      </template>

      <div v-else class="dashboard-loading surface" aria-live="polite">
        <span class="loading-orbit" />
        <p>Loading market field…</p>
      </div>
    </template>

    <SignalsPanel
      v-else-if="activeView === 'signals'"
      :signals="signalFeed?.signals || []"
      :pending="pending"
      :error="signalsError?.statusMessage || signalsError?.message"
      @refresh="requestRefresh"
    />

    <PositionsPanel v-else />
  </main>
</template>

<style scoped>
.error-banner {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  margin-top: 24px;
  padding: 16px 18px;
  border: 1px solid rgba(252, 70, 171, 0.36);
  border-radius: 16px;
  background: rgba(252, 70, 171, 0.08);
}

.error-banner > svg {
  width: 22px;
  height: 22px;
  color: var(--momentum-brand-pink);
}

.error-banner div {
  display: grid;
  gap: 2px;
}

.error-banner strong {
  font-size: 13px;
}

.error-banner span {
  color: var(--momentum-text-secondary);
  font-size: 11px;
}

.dashboard-loading {
  display: grid;
  min-height: 640px;
  margin-top: 24px;
  place-content: center;
  justify-items: center;
  gap: 16px;
  border-radius: 28px;
  color: var(--momentum-text-secondary);
  font-size: 12px;
}

.loading-orbit {
  width: 34px;
  height: 34px;
  border: 2px solid var(--momentum-surface-subtle);
  border-top-color: var(--momentum-brand-lime);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 560px) {
  .error-banner {
    grid-template-columns: auto 1fr;
  }

  .error-banner button {
    grid-column: 1 / -1;
  }
}
</style>
