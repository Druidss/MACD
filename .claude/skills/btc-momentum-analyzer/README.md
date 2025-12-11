# BTC 动能理论分析器

一个基于 Claude Code Skill 系统的 BTC 多时间级别动能分析工具。

## 快速开始

### 1. 首次使用：填写 THEORY.md

**这是最重要的一步！**

打开 [THEORY.md](THEORY.md)，根据你的动能理论体系填写所有章节：
- 基础概念定义（上涨线段、下跌线段）
- 高级概念定义（单位调整周期、分立调控、连续跳空）
- 背离分析规则
- **买卖点规则**（核心）
- 时间级别联动规则
- 参数配置

### 2. 测试数据获取

```bash
cd /Users/adrian/Desktop/BA/MACD/.claude/skills/btc-momentum-analyzer/scripts

# 测试获取 1小时数据
python3 fetch_btc_data.py --symbol BTC-USDT --timeframes 1h --limit 10

# 测试获取多时间级别数据
python3 fetch_btc_data.py --timeframes 1h,4h,1d --limit 50
```

如果看到 JSON 输出，说明数据获取成功！

### 3. 测试指标计算

```bash
# 获取数据并保存
python3 fetch_btc_data.py --timeframes 1h --limit 100 --output test_data.json

# 计算指标
python3 calculate_indicators.py /Users/adrian/Desktop/BA/MACD/data/test_data.json
```

检查输出中的 `ema26`, `ema52`, `dif`, `dea`, `histogram` 字段。

### 4. 在 Claude Code 中使用

现在你可以直接在 Claude Code 中提问：

```
分析当前 BTC 的动能状态
```

Claude 会自动调用这个 Skill！

## 文件结构

```
btc-momentum-analyzer/
├── SKILL.md                 # Skill 定义（已完成）
├── THEORY.md               # 动能理论定义（需要你填写）⭐
├── EXAMPLES.md             # 使用示例
├── README.md               # 本文件
└── scripts/
    ├── fetch_btc_data.py        # 数据获取（已完成）✓
    ├── calculate_indicators.py  # 指标计算（已完成）✓
    ├── analyze_momentum.py      # 动能分析（框架，需扩展）
    └── generate_report.py       # 报告生成（框架，需扩展）
```

## 当前状态

### ✅ 已完成

1. **Skill 框架** (SKILL.md)
   - 多时间级别支持（2d, 1d, 12h, 6h, 4h, 2h, 1h, 30m）
   - 自动激活条件定义
   - 使用说明

2. **数据获取** (fetch_btc_data.py)
   - OKX API 集成
   - 多时间级别并行获取
   - 缓存机制
   - 速率限制

3. **指标计算** (calculate_indicators.py)
   - EMA26, EMA52 计算
   - MACD(12, 26, 9) 计算
   - 多时间级别处理

4. **理论框架** (THEORY.md)
   - 完整的模板结构
   - 所有概念的占位符
   - 参数配置区域

5. **使用示例** (EXAMPLES.md)
   - 典型问答示例
   - 输出格式说明
   - 常见场景

### 🚧 需要完成

1. **THEORY.md 填写**
   - **优先级：最高**
   - 你需要根据自己的动能理论填写所有定义
   - 特别是买卖点规则章节

2. **analyze_momentum.py**
   - 读取 THEORY.md 规则
   - 实现线段分类器
   - 实现周期判断器
   - 实现背离检测器
   - 实现多时间级别联动分析

3. **generate_report.py**
   - 格式化输出报告
   - 生成交易信号
   - 包含详细属性判断

## 开发计划

### 阶段 1：核心分析引擎（需要完成）

**文件**：`analyze_momentum.py`

**功能**：
- 解析 THEORY.md 中的规则
- 实现所有动能理论概念的检测算法
- 输出结构化的分析结果

**建议实现顺序**：
1. 线段分类（上涨/下跌/过渡）
2. 单位调整周期判断
3. 跳空检测
4. 背离分析
5. 分立调控检测
6. 隐形信号检测
7. 多时间级别联动

### 阶段 2：报告生成器（需要完成）

**文件**：`generate_report.py`

**功能**：
- 读取分析结果
- 应用买卖点规则
- 生成易读的文本报告

**输出格式**：
- 文本报告（默认）
- JSON 格式（可选）
- 简化报告（可选）

### 阶段 3：测试和优化

**任务**：
1. 使用真实 BTC 数据测试
2. 对比 TradingView 图表验证准确性
3. 根据实盘表现调整 THEORY.md
4. 优化性能和用户体验

## 使用场景

### 场景 1：日常盘面分析

**早上起床，想知道 BTC 现在怎么样**：

```
早上好，分析一下 BTC 现在的动能状态
```

Skill 会自动：
- 获取 8 个时间级别的最新数据
- 分析线段状态和周期
- 给出操作建议

### 场景 2：寻找买卖点

**想开单，但不确定时机**：

```
BTC 有买点吗？给我详细分析
```

Skill 会：
- 根据 THEORY.md 中的买点规则判断
- 检查多时间级别联动
- 给出入场价位、止损止盈

### 场景 3：风险检测

**已经持仓，担心回调**：

```
检测 BTC 是否有背离信号
```

Skill 会：
- 扫描所有时间级别的背离
- 分析风险等级
- 建议是否止盈或减仓

### 场景 4：周期判断

**想知道当前处于哪个交易阶段**：

```
BTC 1小时现在处于第几个单位调整周期？
```

Skill 会：
- 分析柱状图的扩张-收缩模式
- 判断周期编号
- 评估当前阶段的风险

## 技术细节

### 数据源

- **主要**：OKX API（免费，支持所有时间级别）
- **备用**：本地缓存（10 分钟过期）

### 指标计算

- **EMA26, EMA52**：使用标准 EMA 公式
- **MACD(12, 26, 9)**：
  - DIF = EMA12 - EMA26
  - DEA = EMA9(DIF)
  - Histogram = DIF - DEA

### 缓存策略

- 缓存位置：`/Users/adrian/Desktop/BA/MACD/data/`
- 缓存有效期：10 分钟（所有时间级别）
- 缓存格式：JSON

### 性能

- 数据获取：5-10 秒（8 个时间级别）
- 指标计算：2-3 秒
- 动能分析：取决于 THEORY.md 规则复杂度

## 常见问题

### Q1：为什么 Skill 没有自动激活？

**可能原因**：
1. 问题中没有包含关键词（BTC、动能、线段、MACD 等）
2. `.claude/skills/` 目录位置不正确

**解决方法**：
- 确保问题包含相关关键词
- 检查 Skill 目录是否在项目根目录的 `.claude/skills/` 下

### Q2：THEORY.md 应该怎么填写？

**建议步骤**：
1. 先填写基础概念（上涨线段、下跌线段的定义）
2. 再填写买卖点规则（核心）
3. 填写参数配置
4. 逐步完善高级概念和背离规则

**不确定的概念**：
- 可以先用自然语言描述
- 不需要写完整的 Python 代码
- 算法伪代码即可

### Q3：如何验证分析结果的准确性？

**方法**：
1. 对比 TradingView 图表
   - 检查 MACD 数值是否一致
   - 检查 EMA 是否一致

2. 回测历史数据
   - 导出 TradingView 历史数据
   - 运行 Skill 分析
   - 对比实际行情走势

3. 实盘跟踪
   - 记录 Skill 的建议
   - 跟踪实际行情表现
   - 根据结果调整 THEORY.md

### Q4：analyze_momentum.py 太复杂，怎么办？

**简化方案**：

如果不想编写完整的 Python 分析脚本，可以：

1. **最小化实现**：
   - 只实现线段分类和基本的买卖点判断
   - 忽略高级功能（分立调控、隐形信号）

2. **使用现有策略**：
   - 参考 MACD.pine 的逻辑
   - 将 Pine Script 翻译成 Python

3. **请 Claude 帮助**：
   - 提供你的 THEORY.md
   - 要求 Claude 生成对应的 Python 代码

### Q5：可以不用 OKX API 吗？

**可以！**

替代方案：
1. **手动导出数据**：
   - 从 TradingView 导出 CSV
   - 放入 `data/` 目录
   - 修改 `fetch_btc_data.py` 读取 CSV

2. **使用其他 API**：
   - Binance API
   - Bybit API
   - 修改 `fetch_btc_data.py` 的 API 端点

## 下一步

### 立即行动

1. **打开 THEORY.md**，开始填写你的动能理论
2. **测试数据获取**，确保 API 可用
3. **测试指标计算**，验证数值准确性

### 需要帮助时

在 Claude Code 中询问：
```
帮我实现 analyze_momentum.py 中的线段分类功能
```

提供你填写的 THEORY.md 内容，Claude 会生成对应的代码。

## 版本历史

| 日期       | 版本  | 更新内容                   |
|------------|-------|----------------------------|
| 2025-12-10 | 0.1.0 | 初始框架创建               |
|            |       | - 数据获取脚本             |
|            |       | - 指标计算脚本             |
|            |       | - Skill 定义              |
|            |       | - THEORY.md 模板          |

---

**开始使用**：填写 [THEORY.md](THEORY.md)，然后在 Claude Code 中提问 "分析 BTC 动能" 即可！
