---
name: btc-6h-scheduled
description: BTC 6 小时定时综合分析。每 6 小时对 BTC 6h K 线运行一次，结合动能理论（btc-momentum-analyzer / THEORY.md）与缩量放量能量柱跳空（btc-volume-jump-analyzer / jump.pine），并保证 MACD 与 K 线数据精确。生成带时间戳的综合报告。当用户要建立 BTC 6h 定时任务/轮询、每 6 小时分析、自动盯盘、综合动能+缩量放量时使用。
allowed-tools: Read, Bash, Grep
---

# BTC 6 小时定时综合分析

## 功能概述

把两套分析按 **6 小时为周期** 自动跑在 BTC 6h K 线上：

1. **动能理论**（`btc-momentum-analyzer` / `THEORY.md`）：多时间级别线段、单位调整
   周期、背离、机械买卖点。
2. **缩量放量 / 能量柱跳空**（`btc-volume-jump-analyzer` / `jump.pine`）：6h 量价缩放
   与回调→跳空进场信号。

并 **保证 MACD 与 K 线数据精确**：DIF/DEA/Histogram 用 `IndicatorCalculator`
精确计算，EMA21/52 用一致的 EMA 公式从收盘价重算，OHLCV 原样使用。

每次运行输出一份带时间戳的综合报告：
`data/analysis_reports/<YYYY-MM-DD_HHMM>_6h_combined.md`

## 编排脚本

```bash
# 更新数据库（网络可用时拉最新行情）并生成报告
python3 .claude/skills/btc-6h-scheduled/scripts/run_6h_analysis.py

# 跳过更新，直接用现有数据库（网络受限环境）
python3 .claude/skills/btc-6h-scheduled/scripts/run_6h_analysis.py --no-update

# 自定义参与级别（默认 1d,12h,6h,4h；6h 为主）
python3 .claude/skills/btc-6h-scheduled/scripts/run_6h_analysis.py --timeframes 1d,12h,6h,4h
```

流程：① 增量更新数据库（失败自动回退）→ ② 读取精确指标 → ③ 动能机械买卖点
→ ④ 缩量放量/跳空 → ⑤ 写综合 Markdown 报告。

## 如何“每 6 小时”定时运行

有两种方式，按你的运行环境选择：

### 方式 A：操作系统 cron（无人值守，纯机械报告）

适合在自己的机器/服务器上长期运行，产出精确数据 + 机械信号快照。

```bash
crontab -e
# 每 6 小时整点运行（0/6/12/18 时）：
0 */6 * * * /绝对路径/到/仓库/.claude/skills/btc-6h-scheduled/scripts/cron_6h.sh
```

- 包装脚本 `cron_6h.sh` 会自动定位仓库根目录、更新数据库、生成报告。
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

1. **多时间级别线段速览**：1d/12h/6h/4h 的精确 DIF/DEA/Hist 与线段方向
2. **动能理论机械买卖点**：按 `THEORY.md` 规则的买/卖/观望信号
3. **缩量放量 / 能量柱跳空（6h）**：量价状态、跳空持仓与本根 K 线信号、最近明细
4. **需结合动能理论研判**：留给 Claude 用 `THEORY.md` 深入判断的清单

## 数据与网络

- 实时数据来自 OKX/Binance 公开 API（`database_manager.py --update`）。
- 若运行环境网络策略屏蔽交易所 API，更新会自动回退到数据库现有数据，报告照常生成
  （对应数据库最后一根 K 线时间）。
- 数据库路径：`data/database/btc_database.json`（可用环境变量 `MACD_DATA_DIR` 覆盖）。

## 相关 Skill

- `btc-momentum-analyzer` —— 动能理论与 `THEORY.md`
- `btc-volume-jump-analyzer` —— 缩量放量 / jump.pine 逻辑

> 本 Skill 为分析参考，不构成投资建议。
