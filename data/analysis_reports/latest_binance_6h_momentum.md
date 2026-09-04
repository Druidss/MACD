# BTC Binance U2 动能短报告

- 生成时间: 2026-09-04 06:59:28 UTC
- 数据源: Binance futures `BTCUSDT`
- K线口径: 只使用已收盘 K 线；只列已经进入 U2 的时间级别
- 判断口径: `.agents/skills/btc-momentum-analyzer/THEORY.md` 的 DEA 线段、Unit1/Unit2、EMA52 触及规则

- 已存在U2级别：6h
- 与1日线关系：1d 为 上涨方向，6h同向共振。
- 做单进场点：顺 1d 多单，等 6h 回踩/反抽不破 EMA52 `77,007.40` 后，DIF 重新转向 DEA 且 K 线收回该级别 EMA52。

> 本报告是机械化动能分析快照，不构成投资建议。
