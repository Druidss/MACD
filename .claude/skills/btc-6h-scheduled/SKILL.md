---
name: btc-6h-scheduled
description: BTC 6 小时定时综合分析。每 6 小时对 BTC 6h K 线运行一次，结合动能理论（btc-momentum-analyzer / THEORY.md）与缩量放量能量柱跳空（btc-volume-jump-analyzer / jump.pine），并保证 MACD 与 K 线数据精确。生成带时间戳的综合报告。当用户要建立 BTC 6h 定时任务/轮询、每 6 小时分析、自动盯盘、综合动能+缩量放量时使用。
allowed-tools: Read, Bash, Grep
---

# BTC 6 小时定时综合分析

## 功能概述

把分析按 **6 小时为周期** 自动跑在 BTC 6h K 线上。当前主链路已简化为：

```
Binance 已收盘K线 → 内存计算 EMA26/EMA52 + MACD → THEORY.md 动能报告 → Markdown/JSON
```

不再要求先维护 `data/database/btc_database.json`；旧数据库链路仅保留给历史报告兼容。

并 **保证 MACD 与 K 线数据精确**：DIF/DEA/Histogram 与 EMA26/52 从 Binance
已收盘 OHLCV 直接重算，报告中保留每个时间级别的 K 线时间、EMA26/EMA52、DIF/DEA/Hist 供核对。

每次运行输出一份带时间戳的综合报告：
`data/analysis_reports/<YYYY-MM-DD_HHMM>_6h_combined.md`

## 编排脚本

```bash
# Binance 直取直算并生成报告（默认 futures BTCUSDT）
python3 .claude/skills/btc-6h-scheduled/scripts/run_6h_analysis.py

# 自定义参与级别（默认 1d,12h,6h,4h,2h,1h,30m；6h 为主）
python3 .claude/skills/btc-6h-scheduled/scripts/run_6h_analysis.py --timeframes 1d,12h,6h,4h,2h,1h,30m

# 直接调用底层脚本
python3 scripts/binance_momentum_report.py --market futures --symbol BTCUSDT --stdout
```

流程：① 获取 Binance 已收盘 K 线 → ② 内存计算 EMA/MACD → ③ 判断 DEA 线段、归零轴、
Unit1/Unit2、6h 与上下级别关系 → ④ 写综合 Markdown 报告。

## 如何“每 6 小时”定时运行

有两种方式，按你的运行环境选择：

### 方式 A：操作系统 cron（无人值守，纯机械报告）

适合在自己的机器/服务器上长期运行，产出精确数据 + 机械信号快照。

```bash
crontab -e
# 每 6 小时整点后运行（0/6/12/18 UTC K线收盘后）：
0 */6 * * * /绝对路径/到/仓库/.claude/skills/btc-6h-scheduled/scripts/cron_6h.sh
```

- 包装脚本 `cron_6h.sh` 会自动定位仓库根目录、从 Binance 拉数据、生成报告。
- 运行日志：`data/analysis_reports/cron_6h.log`
- 手动测试：`bash .claude/skills/btc-6h-scheduled/scripts/cron_6h.sh`

### 方式 B：Claude 定时轮询（含动能理论“看形态”研判）

动能理论中线段确认、背离、单位周期等需要“看 MACD 形态判断”的部分由 Claude 完成。
若希望每 6 小时得到 **带 Claude 研判** 的完整结论，在一个长驻 Claude Code 会话中用
`/loop` 技能：

```
/loop 6h 用 btc-6h-scheduled 生成最新 6h 报告，然后结合 THEORY.md 给出动能研判与缩量放量结论
```

Claude 会每 6 小时：运行编排脚本 → 读取报告 → 套用 `THEORY.md` 做线段/背离/周期
判断 + 缩量放量研判 → 给出综合结论。

> 注：`/loop` 在会话存续期间生效；关闭会话即停止。需要 7×24 长期无人值守时用方式 A，
> 并在需要研判时让 Claude 读取最新报告。

## 报告结构

1. **多时间级别数值核对**：1d/12h/6h/4h/2h/1h/30m 的 EMA26/EMA52、DIF/DEA/Hist
2. **6h 主级别判断**：归零轴、Unit1/Unit2、是否正在形成 U2
3. **6h 与上下级别关系**：上级约束、下级确认/矛盾
4. **当前可执行结论**：等待、顺势多单条件、失效风险线

## 数据与网络

- 实时数据来自 Binance 公开 Kline API；默认 `futures BTCUSDT`，也可用 `--market spot`。
- 若运行环境网络策略屏蔽交易所 API，优先使用 Codex 的 `$binance` 连接器做即时核对；线上部署建议用 VPS/Docker/systemd timer。
- 旧数据库路径：`data/database/btc_database.json`（仅历史兼容）。

## 相关 Skill

- `btc-momentum-analyzer` —— 动能理论与 `THEORY.md`
- `btc-volume-jump-analyzer` —— 缩量放量 / jump.pine 逻辑

> 本 Skill 为分析参考，不构成投资建议。
