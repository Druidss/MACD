#!/bin/bash

# BTC 动能分析器 - 快速测试（改进版）
# 使用方法：./quick_test.sh

echo "========================================="
echo "BTC 动能分析器 - 快速测试"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/Users/adrian/Desktop/BA/MACD/data"

mkdir -p "$DATA_DIR"

echo "[1/3] 获取数据..."
echo "正在从 OKX API 获取 100 根 1h K 线（约 4 天数据）..."

python3 "$SCRIPT_DIR/fetch_btc_data.py" \
  --symbol BTC-USDT \
  --timeframes 1h \
  --limit 100 \
  --output quick_test.json 2>&1 | grep -E "SUCCESS|ERROR|Fetched"

if [ $? -ne 0 ]; then
  echo "✗ 数据获取失败"
  exit 1
fi

echo ""
echo "[2/3] 计算指标..."
echo "正在计算 EMA26, EMA52 和 MACD..."

python3 "$SCRIPT_DIR/calculate_indicators.py" \
  "$DATA_DIR/quick_test.json" \
  --output quick_test_indicators.json 2>&1 | grep -E "Calculating|calculated|ERROR"

if [ $? -ne 0 ]; then
  echo "✗ 指标计算失败"
  exit 1
fi

echo ""
echo "[3/3] 查看结果..."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  最新 BTC 1小时 动能分析"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 << 'EOF'
import json

with open('/Users/adrian/Desktop/BA/MACD/data/quick_test_indicators.json') as f:
    data = json.load(f)

candles = data['data']['1h']
last = candles[-1]

print(f"\n时间：{last['datetime']}")
print(f"收盘价：{last['close']:.2f} USDT")

if last['ema26']:
    print(f"\n【EMA 均线】")
    print(f"  EMA26：{last['ema26']:.2f}")
    print(f"  EMA52：{last['ema52']:.2f}")

    ema_trend = "多头排列 ✓" if last['ema26'] > last['ema52'] else "空头排列 ✗"
    print(f"  排列：{ema_trend}")

    print(f"\n【MACD 指标】")
    print(f"  DIF（黄线）：{last['dif']:.2f}")
    print(f"  DEA（白线）：{last['dea']:.2f}")
    print(f"  Histogram：{last['histogram']:.2f}")

    segment = "上涨线段 ✓" if last['dea'] > 0 else "下跌线段 ✗"
    print(f"  线段状态：{segment}")

    # 动能分析
    hist = last['histogram']
    prev = candles[-2]['histogram'] if candles[-2]['histogram'] else 0

    if hist > 0:
        trend = "扩张（动能增强）" if hist > prev else "收缩（动能减弱）"
        print(f"  正柱：{trend}")
    else:
        trend = "扩张（下跌加速）" if hist < prev else "收缩（下跌减缓）"
        print(f"  负柱：{trend}")
else:
    print("\n⚠️ 指标计算失败（数据不足）")
    print("需要至少 60 根 K 线才能计算完整指标")

print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
EOF

if [ $? -eq 0 ]; then
  echo ""
  echo "✓ 测试完成！"
  echo ""
  echo "📊 数据说明："
  echo "  - 数据来源：OKX API"
  echo "  - 时间级别：1 小时"
  echo "  - K 线数量：100 根"
  echo ""
  echo "🎯 下一步："
  echo "  1. 填写 THEORY.md 定义你的动能理论"
  echo "  2. 在 Claude Code 中提问：分析 BTC 动能"
  echo ""
else
  echo "✗ 测试失败"
  exit 1
fi

echo "========================================="
