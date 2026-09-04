# Momentum / Field 前后端架构

## 结论

需要一个轻量后端，但暂时不需要独立的后端项目。

原因有两个：

1. Binance 插件属于 Codex 的开发工具，部署后的网页不能直接调用它。应用运行时应调用 Binance 公共 REST/WebSocket API。
2. TradingView webhook 必须发送到一个公网 HTTPS 接口。这个接口需要校验密钥、去重、保存信号，再把信号提供给前端。

第一版用 Nuxt 自带的 Nitro server routes 同时承担 BFF 和 webhook 接收端，适合当前单用户、单实例场景。

## 当前结构

```text
Browser / Nuxt UI ---- GET /api/dashboard ----> Nuxt Nitro server ----> Binance Futures REST API
         |
         +----------- reads received signals ---------+
                                                       |
TradingView ---- POST /api/webhooks/tradingview ------>+----> local storage (.data/signals)
                  public HTTPS server address

Nuxt Nitro server ---- merge / fallback ----> local K-line cache (.data/market)
```

## 前端

- Nuxt 4 + Vue 3 + TypeScript
- Nuxt UI 提供按钮、图标及基础交互组件
- Lightweight Charts 渲染真实 K 线、EMA 和 MACD
- 颜色、圆角、间距、字体层级按照 Figma `Momentum Field / OKX Dashboard` 还原
- 默认 30 秒刷新一次，支持 1H、6H、1D 切换
- 每个周期向浏览器提供最多 1000 根 K 线；初始聚焦最近 96–120 根，完整历史可左右拖拽和缩放
- Overview、Positions、Signals 导航可切换；Signals 页面直接显示 webhook 已接收的数据
- Positions 当前明确显示“未连接”，避免误以为系统已经持有 Binance 私有 API 权限或可以自动下单

## 后端

### `GET /api/dashboard`

- 并行读取 Binance BTCUSDT 的 1H、6H、1D K 线
- 每个周期单次请求 1000 根，并与项目内 `.data/market` 文件缓存按开盘时间合并、去重
- 每个周期本地最多保留 5000 根；Binance 暂时不可用时自动回退到本地缓存
- 服务端计算 EMA 6/13/26/52、DIF、DEA、MACD 柱
- 生成缩量状态和 EMA26/52 多空状态
- 行情结果在单实例内缓存 15 秒，减少 Binance 请求

### `POST /api/webhooks/tradingview`

- 接收 TradingView JSON alert
- 使用 `NUXT_TRADINGVIEW_WEBHOOK_SECRET` 做常量时间校验
- 使用稳定哈希去重
- 单实例保存最近 100 条信号
- 返回 202；重复信号返回 200

### `GET /api/signals`

- 返回前端需要展示的最新信号
- 与 Binance 行情接口解耦；即使 Binance 暂时不可用，Signals 页面仍可读取服务器已经保存的 webhook 数据

## 当前不做

- 用户登录与多租户
- Redis、消息队列、独立微服务
- 多节点一致性与高可用
- 订单执行和 Binance 私有账户 API

## 部署建议

第一版优先部署到一台持续运行的 Node 主机或带持久卷的容器。这样 `.data/signals` 可以正常保留。

服务器需要配置公网 HTTPS 域名，并把请求转发给 Nuxt/Nitro 进程。TradingView 的 Webhook URL 固定填写：

```text
https://<your-domain>/api/webhooks/tradingview
```

服务器环境变量 `NUXT_TRADINGVIEW_WEBHOOK_SECRET` 与 TradingView alert JSON 中的 `secret` 必须一致。真实密钥只保存在服务器和 TradingView 配置中，不写入仓库或前端代码。

如果以后改成无状态 serverless，或需要长期保存/筛选信号，再将 Nitro 的 `signals` storage mount 替换为 PostgreSQL；前端和 webhook API 合约无需改变。
