# 快速开始指南

## ✅ 已完成的准备工作

### 1. 数据库已初始化

所有 8 个时间级别的历史数据已下载并计算好指标：

```
✓ 2日线   200 根K线 (约 400 天)
✓ 1日线   200 根K线 (约 200 天)
✓ 12小时  200 根K线 (约 100 天)
✓ 6小时   200 根K线 (约 50 天)
✓ 4小时   200 根K线 (约 33 天)
✓ 2小时   200 根K线 (约 16 天)
✓ 1小时   200 根K线 (约 8 天)
✓ 30分钟  200 根K线 (约 4 天)
```

每根K线包含：
- 价格数据：open, high, low, close, volume
- 指标数据：ema26, ema52, dif, dea, histogram

数据库位置：`/Users/adrian/Desktop/BA/MACD/data/database/btc_database.json`

---

## 📝 下一步：填写 THEORY.md

打开 [THEORY.md](THEORY.md) 并填写你的动能理论定义。

**最重要的章节**（按优先级）：

### 1. 参数配置（最简单）

找到文件末尾的参数配置区域，填写具体数值：

```yaml
# 示例
ema_short: 26
ema_long: 52
macd_fast: 12
macd_slow: 26
macd_signal: 9
```

### 2. 买卖点规则（最重要）

定义买点和卖点的触发条件。例如：

```markdown
### 买点类型 1：线段确认买点

**触发条件**：
必要条件（全部满足）：
1. 1h DEA 上穿 0 轴
2. EMA26 > EMA52
3. 4h 线段也为上涨线段

入场价位：当前收盘价
止损位：EMA52 - 300
```

### 3. 基础概念定义

定义上涨线段、下跌线段的判断标准。

### 4. 其他高级概念

单位调整周期、分立调控、连续跳空等，可以逐步完善。

**提示**：
- 不需要写 Python 代码，用自然语言描述即可
- 算法可以用伪代码或步骤说明
- 参数必须填写明确的数值

---

## 🚀 使用方式

填写 THEORY.md 后，你有两种使用方式：

### 方式 1：在 Claude Code 中直接提问（推荐）

```
分析当前 BTC 的动能状态
```

Claude 会自动：
1. 从数据库读取最新数据
2. 根据 THEORY.md 规则分析
3. 生成多时间级别嵌套分析报告

### 方式 2：使用命令行工具

**更新数据**（每天早上/交易前）：
```bash
cd /Users/adrian/Desktop/BA/MACD/.claude/skills/btc-momentum-analyzer/scripts
python3 database_manager.py --update
```

**查看数据库状态**：
```bash
python3 database_manager.py --status
```

**导出某个时间级别**：
```bash
python3 database_manager.py --export 1h --output btc_1h.json
```

---

## 📊 数据库说明

### 数据结构

```json
{
  "timeframes": {
    "1h": {
      "candles": [
        {
          "timestamp": 1765411200.0,
          "datetime": "2025-12-11 01:00:00",
          "open": 92013.6,
          "high": 92082.8,
          "low": 91048.1,
          "close": 91385.2,
          "volume": 335.30,
          "ema26": 91315.66,    # 已计算
          "ema52": 91484.99,    # 已计算
          "dif": -548.51,       # 黄线（已计算）
          "dea": -375.81,       # 白线（已计算）
          "histogram": -172.70  # 柱状图（已计算）
        },
        ... 200 根K线
      ]
    }
  }
}
```

### 增量更新机制

- **初次使用**：已完成，下载了 200 根K线
- **日常更新**：只获取最新 10 根K线，追加到数据库
- **更新速度**：2-5 秒（8个时间级别）
- **数据连续性**：EMA 和 MACD 计算保持连续

---

## 🎯 典型问题示例

填写 THEORY.md 后，你可以问 Claude：

**基础问题**：
- "BTC 现在是上涨线段还是下跌线段？"
- "1小时处于第几个单位调整周期？"
- "有没有连续跳空背离？"

**高级问题**：
- "分析 BTC 多时间级别的联动情况"
- "现在有买点吗？给我详细分析"
- "检测所有时间级别的黄白线背离"

**报告类问题**：
- "生成完整的 BTC 动能分析报告"
- "分析当前 BTC 的动能状态"

---

## 📁 文件结构

```
.claude/skills/btc-momentum-analyzer/
├── SKILL.md              # Skill 定义（已完成）
├── THEORY.md            # 动能理论定义（需要你填写）⭐
├── EXAMPLES.md          # 使用示例
├── README.md            # 详细说明
├── QUICKSTART.md        # 本文件
└── scripts/
    ├── fetch_btc_data.py          # 数据获取（已完成）
    ├── calculate_indicators.py    # 指标计算（已完成）
    └── database_manager.py        # 数据库管理（已完成）

data/
└── database/
    └── btc_database.json         # 数据库（已初始化，1600根K线）
```

---

## ⚙️ 维护建议

### 日常使用

**每天早上**或**交易前**运行一次更新：
```bash
python3 database_manager.py --update
```

### 定期检查

**每周检查一次**数据库状态：
```bash
python3 database_manager.py --status
```

### 重新初始化

如果需要重新下载完整历史数据：
```bash
python3 database_manager.py --init --timeframes 2d,1d,12h,6h,4h,2h,1h,30m
```

---

## 🔧 故障排除

### Q: 更新时提示 "No new candles"

**原因**：数据已是最新，无需更新
**解决**：正常现象，不影响使用

### Q: 某个时间级别数据异常

**解决**：重新初始化该时间级别
```bash
python3 database_manager.py --init --timeframes 1h
```

### Q: 想查看原始数据

**解决**：导出为 JSON 文件
```bash
python3 database_manager.py --export 1h --output check.json
```

---

## 📞 需要帮助？

在 Claude Code 中直接询问：
```
帮我检查数据库状态
如何更新 BTC 数据？
THEORY.md 应该怎么填写？
```

---

**现在开始填写 [THEORY.md](THEORY.md) 吧！** 🚀
