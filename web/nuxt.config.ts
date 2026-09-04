export default defineNuxtConfig({
  compatibilityDate: '2026-09-01',
  devtools: { enabled: true },
  modules: ['@nuxt/ui'],
  ui: {
    fonts: false,
    colorMode: false
  },
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      htmlAttrs: { lang: 'zh-CN', class: 'dark' },
      title: 'Momentum / Field',
      meta: [
        { name: 'description', content: 'BTC multi-timeframe momentum dashboard' },
        { name: 'theme-color', content: '#000000' }
      ]
    }
  },
  runtimeConfig: {
    tradingviewWebhookSecret: '',
    binanceBaseUrl: 'https://fapi.binance.com',
    marketFetchLimit: 1_000,
    marketCacheLimit: 5_000,
    public: {
      dashboardPollMs: 30_000
    }
  },
  nitro: {
    storage: {
      signals: {
        driver: 'fs',
        base: './.data/signals'
      },
      market: {
        driver: 'fs',
        base: './.data/market'
      }
    }
  },
  typescript: {
    strict: true,
    typeCheck: true
  }
})
