---
name: btc-volume-jump-analyzer
description: 基于 jump.pine 的缩量放量 / MACD 能量柱跳空分析，默认作用于 BTC 6 小时 K 线。忠实复刻 jump.pine 的回调→跳空进场、零轴附近缩量进场、跳空移动止损逻辑，并叠加真实成交量的缩量/放量判断。当用户询问 BTC 缩量放量、能量柱跳空、jump 策略信号、6h 量价分析、放量阳/缩量回调时自动激活。
allowed-tools: Read, Bash, Grep
---

# BTC 缩量放量 / 能量柱跳空分析器

## 功能概述

本 Skill 是 `jump.pine`（MACD 能量柱跳空策略）的 Python 移植 + 增强，专注于
**缩量放量** 技术，默认分析 **BTC 6 小时 K 线**。

它提供两层分析，二者结合即为完整的“缩量放量”研判：

1. **能量柱跳空（jump.pine 原逻辑，逐根 K 线状态机）**
   - 上涨线段（DEA > 0）+ EMA21 > EMA52 + 价格站在 EMA52−止损幅度 之上
   - 检测 histogram **回调**（绿柱缩小 / 红柱放大）后再次 **跳空** 顺势进场
   - 零轴附近（0 < DEA ≤ 阈值）红柱 **缩量** 阳线进场
   - 跳空 **移动止损**（上移到前一根 open − 止损幅度）、跌破止损 / 离开上涨线段平仓

2. **真实成交量缩量 / 放量**
   - 量比 = 当前成交量 / 均量(MA, 默认 20)
   - 放量（量比 ≥ 1.5）/ 缩量（量比 ≤ 0.7）/ 常量
   - 与 K 线阴阳组合：放量阳（顺势强势）、缩量回调（健康回踩，跳空前提）、放量阴（派发警告）

> jump.pine 的核心思想：**上涨线段中，缩量回调后的放量跳空是顺势加仓点。** 本 Skill
> 把“能量柱跳空”和“真实成交量缩放”两个维度都量化出来。

## 数据精确性

- `DIF / DEA / Histogram` 直接采用数据库中由 `IndicatorCalculator` 计算的精确值
  （MACD 12/26/9），不做二次近似。
- `EMA21 / EMA52` 由脚本用与指标库一致的 EMA 公式（首值 SMA，倍数 2/(N+1)）
  从收盘价重算（jump.pine 使用 EMA21/52，数据库默认存的是 EMA26/52）。
- K 线 OHLCV 原样使用，不取整、不插值。

## 使用方法

### 一键分析（推荐）

直接提问即可，例如：
- “用缩量放量分析 BTC 6 小时”
- “BTC 6h 现在有跳空进场信号吗？”
- “BTC 6h 是放量还是缩量？”

Claude 会运行脚本并解读结果。

### 命令行

```bash
# 默认：读取仓库数据库 data/database/btc_database.json，分析 6h
python3 .claude/skills/btc-volume-jump-analyzer/scripts/analyze_volume_jump.py --timeframe 6h

# 指定数据文件（带指标的 JSON）
python3 .claude/skills/btc-volume-jump-analyzer/scripts/analyze_volume_jump.py \
  --input data/btc_indicators.json --timeframe 6h

# JSON 输出 + 写文件
python3 .claude/skills/btc-volume-jump-analyzer/scripts/analyze_volume_jump.py \
  --timeframe 6h --format json --output data/analysis_reports/6h_volume_jump.json
```

### 参数（默认值对齐 jump.pine）

| 参数 | 默认 | 说明 |
|------|------|------|
| `--timeframe` | `6h` | 时间级别 |
| `--stop-loss-offset` | `300` | 止损幅度（open − offset），源自 jump.pine |
| `--zero-axis-threshold` | `300` | 零轴附近 DEA 阈值 |
| `--vol-period` | `20` | 均量周期 |
| `--expand-threshold` | `1.5` | 放量量比阈值 |
| `--shrink-threshold` | `0.7` | 缩量量比阈值 |
| `--recent` | `8` | 明细展示的最近 K 线数 |
| `--input` | 数据库 | 自定义带指标 JSON |
| `--format` | `text` | `text` 或 `json` |

> 注：`stop-loss-offset=300` 是 jump.pine 针对 BTC 设计的固定点数偏移。不同价格/
> 时间级别下可按需调整（例如 6h 波动更大可适当放大）。

## 数据来源 / 更新

脚本读取仓库数据库 `data/database/btc_database.json`。要分析最新行情，先增量更新数据库：

```bash
python3 .claude/skills/btc-momentum-analyzer/scripts/database_manager.py --update --timeframes 6h
```

> 实时数据来自 OKX / Binance 公开 API。若运行环境网络策略屏蔽交易所 API，
> 脚本会回退到数据库现有数据并照常计算（结果对应数据库最后一根 K 线时间）。

## 输出说明

- **当前 K 线 / MACD**：精确 OHLC、EMA21/52、DIF/DEA/Histogram、线段方向
- **成交量缩量/放量**：量比、均量、状态、量价组合
- **跳空策略状态**：当前持仓、止损位、**本根 K 线是否触发进/出场**、最近事件
- **最近 K 线明细**：逐根量比/状态/MACD 速查表

## 与其他 Skill 的关系

- `btc-momentum-analyzer`：完整动能理论（线段/单位周期/背离），用于趋势大方向判断。
- `btc-6h-scheduled`：每 6 小时定时把本 Skill 与动能理论结合，对 BTC 6h 出综合报告。

## 限制

- 仅做多（与 jump.pine 一致，上涨线段顺势策略）。
- 输出为机械信号 + 精确数据；最终交易决策需结合动能理论与多时间级别联动。
- 不构成投资建议。
