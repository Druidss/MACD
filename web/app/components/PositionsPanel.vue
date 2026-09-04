<template>
  <section class="positions-panel surface">
    <span class="positions-panel__icon">
      <UIcon name="i-lucide-wallet-cards" />
    </span>
    <p class="panel-kicker">Private account data</p>
    <h1>仓位数据暂未连接</h1>
    <p>
      当前版本只读取 Binance 公共行情和 TradingView 信号，不保存 Binance API Key，也不会自动下单。
    </p>
  </section>
</template>

<style scoped>
.positions-panel {
  display: grid;
  min-height: 680px;
  margin-top: 24px;
  padding: 28px;
  place-content: center;
  justify-items: center;
  border-radius: 28px;
  text-align: center;
}

.positions-panel__icon {
  display: grid;
  width: 58px;
  height: 58px;
  margin-bottom: 18px;
  place-items: center;
  border-radius: 18px;
  background: rgba(189, 254, 48, 0.1);
  color: var(--momentum-brand-lime);
}

.positions-panel__icon svg {
  width: 26px;
  height: 26px;
}

.positions-panel h1 {
  margin: 8px 0 0;
  font-size: 24px;
  font-weight: 650;
}

.positions-panel > p:last-child {
  max-width: 520px;
  margin: 10px 0 0;
  color: var(--momentum-text-secondary);
  font-size: 12px;
  line-height: 1.7;
}
</style>
