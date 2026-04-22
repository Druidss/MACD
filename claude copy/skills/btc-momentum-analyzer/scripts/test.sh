#!/bin/bash

# BTC 动能分析器 - 快速测试脚本
# 使用方法：./test.sh

echo "========================================="
echo "BTC 动能分析器 - 测试脚本"
echo "========================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="/Users/adrian/Desktop/BA/MACD/data"

mkdir -p "$DATA_DIR"

echo "[1/3] 测试数据获取（OKX API）..."
echo "获取 1小时 BTC 数据（最近 100 根 K 线，约 4 天）..."
python3 "$SCRIPT_DIR/fetch_btc_data.py" \
  --symbol BTC-USDT \
  --timeframes 1h \
  --limit 100 \
  --output test_1h.json

if [ $? -eq 0 ]; then
  echo "✓ 数据获取成功"
  echo ""
else
  echo "✗ 数据获取失败"
  exit 1
fi

echo "[2/3] 测试指标计算..."
echo "计算 EMA26, EMA52 和 MACD..."
python3 "$SCRIPT_DIR/calculate_indicators.py" \
  "$DATA_DIR/test_1h.json" \
  --output test_1h_indicators.json

if [ $? -eq 0 ]; then
  echo "✓ 指标计算成功"
  echo ""
else
  echo "✗ 指标计算失败"
  exit 1
fi

echo "[3/3] 查看结果..."
echo "最后一根 K 线的指标："
python3 -c "
import json
import sys

with open('$DATA_DIR/test_1h_indicators.json') as f:
    data = json.load(f)

candles = data['data']['1h']
last_candle = candles[-1]

print(f\"时间：{last_candle['datetime']}\")
print(f\"收盘价：{last_candle['close']:.2f}\")
print(f\"EMA26：{last_candle['ema26']:.2f if last_candle['ema26'] else 'N/A'}\")
print(f\"EMA52：{last_candle['ema52']:.2f if last_candle['ema52'] else 'N/A'}\")
print(f\"DIF：{last_candle['dif']:.2f if last_candle['dif'] else 'N/A'}\")
print(f\"DEA：{last_candle['dea']:.2f if last_candle['dea'] else 'N/A'}\")
print(f\"Histogram：{last_candle['histogram']:.2f if last_candle['histogram'] else 'N/A'}\")
"

if [ $? -eq 0 ]; then
  echo ""
  echo "✓ 测试完成！所有功能正常"
  echo ""
  echo "下一步："
  echo "1. 填写 THEORY.md 中的动能理论定义"
  echo "2. 在 Claude Code 中提问：分析 BTC 动能"
else
  echo "✗ 结果展示失败"
  exit 1
fi

echo "========================================="
echo "测试完成"
echo "========================================="
