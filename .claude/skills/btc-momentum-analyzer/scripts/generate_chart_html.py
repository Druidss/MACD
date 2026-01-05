#!/usr/bin/env python3
"""
生成BTC动能分析图表HTML

使用Lightweight Charts库创建交互式K线图和MACD指标图
支持多时间级别展示，OKX黑色风格，荧光绿/红配色

使用方法：
  python3 generate_chart_html.py
  python3 generate_chart_html.py --timeframes 1d,4h,1h --output report.html

作者：Claude
日期：2026-01-05
"""

import json
import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict, Any

# 数据库路径
DATABASE_FILE = "/Users/adrian/Desktop/BA/MACD/data/database/btc_database.json"


def load_database() -> Dict[str, Any]:
    """加载数据库"""
    with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_trading_analysis(db: Dict[str, Any]) -> Dict[str, Any]:
    """生成交易分析报告"""
    # 获取关键时间级别数据
    tf_2d = db['timeframes']['2d']['candles'][-1]
    tf_1d = db['timeframes']['1d']['candles'][-1]
    tf_12h = db['timeframes']['12h']['candles'][-1]
    tf_4h = db['timeframes']['4h']['candles'][-1]
    tf_1h = db['timeframes']['1h']['candles'][-1]

    current_price = tf_1d['close']

    # 判断市场状态
    large_trend = "下跌" if tf_2d['dea'] < 0 else "上涨"
    mid_trend = "上涨" if tf_12h['dea'] > 0 else "下跌"
    small_trend = "上涨" if tf_4h['dea'] > 0 else "下跌"

    # 3日交易计划
    day3_plan = {
        'direction': '做多' if tf_4h['dea'] > 0 and tf_12h['dea'] > 0 else '观望',
        'entry': current_price if tf_4h['dea'] > 0 else None,
        'stop_loss': tf_4h['ema52'] - 300,
        'target1': tf_1d['ema26'],
        'target2': tf_1d['ema52'],
        'reason': f"小周期({tf_4h['dea']:.0f})带动，12h即将确认" if tf_4h['dea'] > 0 else "等待12h确认"
    }

    # 1周交易计划
    week_plan = {
        'direction': '做多' if tf_12h['dea'] > 0 else '观望',
        'entry_zone': f"{current_price * 0.98:.0f}-{current_price * 1.02:.0f}",
        'stop_loss': tf_1d['ema52'] - 500,
        'target1': tf_2d['ema26'],
        'target2': (tf_2d['ema26'] + tf_2d['ema52']) / 2,
        'reason': f"1d下跌线段中反弹，DEA={tf_1d['dea']:.0f}" if tf_1d['dea'] < 0 else "1d上涨确认"
    }

    # 1月交易计划
    month_plan = {
        'direction': '等待' if tf_2d['dea'] < -1000 else '谨慎做多',
        'entry_condition': "2d DEA上穿0轴确认" if tf_2d['dea'] < 0 else "趋势延续",
        'stop_loss': tf_2d['ema52'] - 1000,
        'target': tf_2d['ema52'] if tf_2d['dea'] < 0 else tf_2d['ema26'] * 1.05,
        'reason': f"2d下跌线段，DEA={tf_2d['dea']:.0f}，等待变盘" if tf_2d['dea'] < 0 else "2d上涨趋势"
    }

    return {
        'day3': day3_plan,
        'week': week_plan,
        'month': month_plan,
        'current_price': current_price,
        'large_trend': large_trend,
        'mid_trend': mid_trend,
        'small_trend': small_trend
    }


def generate_html(timeframes: List[str], output_file: str, analysis_text: str = None):
    """
    生成HTML图表文件

    参数：
        timeframes: 要展示的时间级别列表
        output_file: 输出HTML文件路径
        analysis_text: 分析文本（可选）
    """
    db = load_database()

    # 生成交易分析
    trading_analysis = generate_trading_analysis(db)

    # 准备数据
    charts_data = {}
    for tf in timeframes:
        if tf not in db['timeframes']:
            print(f"[WARN] {tf} not in database", file=sys.stderr)
            continue

        candles = db['timeframes'][tf]['candles']

        # 取最近200根K线用于展示
        display_candles = candles[-200:]

        # 准备K线数据（使用字符串日期格式）
        candlestick_data = []
        for c in display_candles:
            if c['ema26'] is not None:  # 确保有指标数据
                # 转换为YYYY-MM-DD格式
                date_str = c['datetime'].split(' ')[0]
                candlestick_data.append({
                    'time': date_str,
                    'open': round(c['open'], 2),
                    'high': round(c['high'], 2),
                    'low': round(c['low'], 2),
                    'close': round(c['close'], 2)
                })

        # 准备MACD数据
        dif_data = []
        dea_data = []
        histogram_data = []

        for c in display_candles:
            if c['dif'] is not None and c['dea'] is not None:
                date_str = c['datetime'].split(' ')[0]
                dif_data.append({
                    'time': date_str,
                    'value': round(c['dif'], 2)
                })
                dea_data.append({
                    'time': date_str,
                    'value': round(c['dea'], 2)
                })

                # Histogram颜色
                color = '#00ff88' if c['histogram'] >= 0 else '#ff4466'
                histogram_data.append({
                    'time': date_str,
                    'value': round(c['histogram'], 2),
                    'color': color
                })

        # 准备EMA数据
        ema26_data = []
        ema52_data = []
        for c in display_candles:
            date_str = c['datetime'].split(' ')[0]
            if c['ema26'] is not None:
                ema26_data.append({
                    'time': date_str,
                    'value': round(c['ema26'], 2)
                })
            if c['ema52'] is not None:
                ema52_data.append({
                    'time': date_str,
                    'value': round(c['ema52'], 2)
                })

        # 最新数据
        last = candles[-1]

        # 生成动能分析文本
        momentum_analysis = []

        # 线段分析
        segment_type = "上涨线段" if last['dea'] > 0 else "下跌线段"
        momentum_analysis.append(f"当前处于{segment_type}，DEA={last['dea']:.2f}")

        # 柱状图趋势分析
        if len(candles) >= 3:
            h1, h2, h3 = candles[-1]['histogram'], candles[-2]['histogram'], candles[-3]['histogram']
            if h1 and h2 and h3:
                if h1 > h2 and h2 > h3:
                    momentum_analysis.append("柱状图连续跳空扩张，动能增强")
                elif h1 < h2 and h2 < h3:
                    momentum_analysis.append("柱状图连续收缩，动能减弱")
                elif abs(h1) < abs(h2):
                    momentum_analysis.append("柱状图收缩中，注意变盘")

        # 价格与EMA52关系
        price_ema_diff = last['close'] - last['ema52']
        price_ema_pct = (price_ema_diff / last['ema52']) * 100
        if abs(price_ema_pct) < 2:
            momentum_analysis.append(f"价格接近EMA52（{price_ema_pct:+.1f}%），归零轴状态")
        elif price_ema_diff > 0:
            momentum_analysis.append(f"价格在EMA52上方{price_ema_diff:.0f}点")
        else:
            momentum_analysis.append(f"价格在EMA52下方{abs(price_ema_diff):.0f}点")

        # DEA位置判断
        if abs(last['dea']) < 100:
            momentum_analysis.append("DEA接近0轴，关注穿零轴信号")
        elif last['dea'] > 500:
            momentum_analysis.append("DEA较高，上涨动能充足")
        elif last['dea'] < -500:
            momentum_analysis.append("DEA较低，下跌动能较强")

        charts_data[tf] = {
            'candlestick': candlestick_data,
            'dif': dif_data,
            'dea': dea_data,
            'histogram': histogram_data,
            'ema26': ema26_data,
            'ema52': ema52_data,
            'momentum_analysis': momentum_analysis,
            'latest': {
                'datetime': last['datetime'],
                'close': last['close'],
                'dif': last['dif'],
                'dea': last['dea'],
                'histogram': last['histogram'],
                'ema26': last['ema26'],
                'ema52': last['ema52'],
                'segment': '上涨线段 ↑' if last['dea'] > 0 else '下跌线段 ↓'
            }
        }

    # 生成HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BTC 动能分析报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            color: #e0e0e0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 20px;
            min-height: 100vh;
        }}

        .header {{
            text-align: center;
            padding: 30px 0;
            background: rgba(20, 20, 20, 0.6);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            margin-bottom: 30px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .header h1 {{
            font-size: 2.5em;
            background: linear-gradient(90deg, #00ff88 0%, #00cc66 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}

        .header .subtitle {{
            color: #888;
            font-size: 1em;
        }}

        .trading-plans {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }}

        .plan-card {{
            background: rgba(20, 20, 20, 0.6);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .plan-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(0, 255, 136, 0.3);
        }}

        .plan-title {{
            font-size: 1.5em;
            color: #00ff88;
            font-weight: 600;
        }}

        .plan-direction {{
            padding: 5px 15px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 0.9em;
        }}

        .plan-direction.long {{
            background: rgba(0, 255, 136, 0.2);
            color: #00ff88;
        }}

        .plan-direction.short {{
            background: rgba(255, 68, 102, 0.2);
            color: #ff4466;
        }}

        .plan-direction.wait {{
            background: rgba(255, 187, 0, 0.2);
            color: #ffbb00;
        }}

        .plan-item {{
            margin-bottom: 15px;
        }}

        .plan-label {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}

        .plan-value {{
            color: #e0e0e0;
            font-size: 1.1em;
            font-weight: 600;
        }}

        .plan-value.price {{
            color: #00ff88;
            font-size: 1.3em;
        }}

        .plan-reason {{
            margin-top: 15px;
            padding: 12px;
            background: rgba(255, 255, 255, 0.03);
            border-radius: 10px;
            font-size: 0.9em;
            color: #999;
            line-height: 1.5;
        }}

        @media (max-width: 1200px) {{
            .trading-plans {{
                grid-template-columns: 1fr;
            }}
        }}

        .timeframe-section {{
            margin-bottom: 40px;
            background: rgba(20, 20, 20, 0.6);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}

        .timeframe-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(0, 255, 136, 0.3);
        }}

        .timeframe-title {{
            font-size: 1.8em;
            color: #00ff88;
            font-weight: 600;
        }}

        .timeframe-info {{
            display: flex;
            gap: 30px;
            font-size: 0.95em;
        }}

        .info-item {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }}

        .info-label {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 3px;
        }}

        .info-value {{
            color: #e0e0e0;
            font-weight: 600;
        }}

        .info-value.positive {{
            color: #00ff88;
        }}

        .info-value.negative {{
            color: #ff4466;
        }}

        .charts-container {{
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 20px;
        }}

        .charts-main {{
            display: flex;
            flex-direction: column;
            gap: 15px;
        }}

        .chart-wrapper {{
            background: rgba(10, 10, 10, 0.8);
            border-radius: 15px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .chart-title {{
            color: #888;
            font-size: 0.9em;
            margin-bottom: 10px;
            font-weight: 500;
        }}

        .analysis-panel {{
            background: rgba(10, 10, 10, 0.8);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }}

        .analysis-title {{
            color: #00ff88;
            font-size: 1.1em;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        .signal-item {{
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 10px;
            background: rgba(0, 255, 136, 0.1);
            border-left: 3px solid #00ff88;
        }}

        .signal-item.sell {{
            background: rgba(255, 68, 102, 0.1);
            border-left-color: #ff4466;
        }}

        .signal-label {{
            color: #00ff88;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}

        .signal-item.sell .signal-label {{
            color: #ff4466;
        }}

        .signal-value {{
            color: #e0e0e0;
            font-size: 1.05em;
            font-weight: 500;
        }}

        .metric-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }}

        .metric-item {{
            background: rgba(255, 255, 255, 0.03);
            padding: 10px;
            border-radius: 8px;
        }}

        .metric-label {{
            color: #666;
            font-size: 0.8em;
            margin-bottom: 3px;
        }}

        .metric-value {{
            color: #e0e0e0;
            font-size: 1em;
            font-weight: 600;
        }}

        @media (max-width: 1200px) {{
            .charts-container {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>BTC 动能理论分析报告</h1>
        <div class="subtitle">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 基于600根K线数据 | 当前价格: {trading_analysis['current_price']:.2f} USDT</div>
    </div>

    <!-- 交易计划板块 -->
    <div class="trading-plans">
        <!-- 3日计划 -->
        <div class="plan-card">
            <div class="plan-header">
                <div class="plan-title">3日计划</div>
                <div class="plan-direction {'long' if '做多' in trading_analysis['day3']['direction'] else 'wait'}">{trading_analysis['day3']['direction']}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">进场位置</div>
                <div class="plan-value price">{f"{trading_analysis['day3']['entry']:.2f}" if trading_analysis['day3']['entry'] else '等待信号'}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">止损位</div>
                <div class="plan-value">{trading_analysis['day3']['stop_loss']:.2f}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">目标位 1</div>
                <div class="plan-value">{trading_analysis['day3']['target1']:.2f}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">目标位 2</div>
                <div class="plan-value">{trading_analysis['day3']['target2']:.2f}</div>
            </div>
            <div class="plan-reason">
                {trading_analysis['day3']['reason']}
            </div>
        </div>

        <!-- 1周计划 -->
        <div class="plan-card">
            <div class="plan-header">
                <div class="plan-title">1周计划</div>
                <div class="plan-direction {'long' if '做多' in trading_analysis['week']['direction'] else 'wait'}">{trading_analysis['week']['direction']}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">进场区间</div>
                <div class="plan-value price">{trading_analysis['week']['entry_zone']}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">止损位</div>
                <div class="plan-value">{trading_analysis['week']['stop_loss']:.2f}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">目标位 1</div>
                <div class="plan-value">{trading_analysis['week']['target1']:.2f}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">目标位 2</div>
                <div class="plan-value">{trading_analysis['week']['target2']:.2f}</div>
            </div>
            <div class="plan-reason">
                {trading_analysis['week']['reason']}
            </div>
        </div>

        <!-- 1月计划 -->
        <div class="plan-card">
            <div class="plan-header">
                <div class="plan-title">1月计划</div>
                <div class="plan-direction wait">{trading_analysis['month']['direction']}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">进场条件</div>
                <div class="plan-value">{trading_analysis['month']['entry_condition']}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">止损位</div>
                <div class="plan-value">{trading_analysis['month']['stop_loss']:.2f}</div>
            </div>
            <div class="plan-item">
                <div class="plan-label">目标位</div>
                <div class="plan-value">{trading_analysis['month']['target']:.2f}</div>
            </div>
            <div class="plan-reason">
                {trading_analysis['month']['reason']}
            </div>
        </div>
    </div>
"""

    # 为每个时间级别生成图表
    for tf in timeframes:
        if tf not in charts_data:
            continue

        data = charts_data[tf]
        latest = data['latest']

        # 判断颜色
        dea_color = 'positive' if latest['dea'] > 0 else 'negative'
        hist_color = 'positive' if latest['histogram'] > 0 else 'negative'

        html_content += f"""
    <div class="timeframe-section">
        <div class="timeframe-header">
            <div class="timeframe-title">{tf.upper()} 级别</div>
            <div class="timeframe-info">
                <div class="info-item">
                    <div class="info-label">最新时间</div>
                    <div class="info-value">{latest['datetime']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">收盘价</div>
                    <div class="info-value">{latest['close']:.2f}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">线段状态</div>
                    <div class="info-value {dea_color}">{latest['segment']}</div>
                </div>
            </div>
        </div>

        <div class="charts-container">
            <div class="charts-main">
                <div class="chart-wrapper">
                    <div class="chart-title">K线图 + EMA26/52</div>
                    <div id="candlestick-{tf}" style="height: 400px;"></div>
                </div>

                <div class="chart-wrapper">
                    <div class="chart-title">MACD 指标</div>
                    <div id="macd-{tf}" style="height: 200px;"></div>
                </div>
            </div>

            <div class="analysis-panel">
                <div class="analysis-title">技术指标</div>

                <div class="metric-grid">
                    <div class="metric-item">
                        <div class="metric-label">EMA26</div>
                        <div class="metric-value">{latest['ema26']:.2f}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">EMA52</div>
                        <div class="metric-value">{latest['ema52']:.2f}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">DIF (黄线)</div>
                        <div class="metric-value">{latest['dif']:.2f}</div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label">DEA (白线)</div>
                        <div class="metric-value {dea_color}">{latest['dea']:.2f}</div>
                    </div>
                    <div class="metric-item" style="grid-column: 1 / -1;">
                        <div class="metric-label">Histogram</div>
                        <div class="metric-value {hist_color}">{latest['histogram']:.2f}</div>
                    </div>
                </div>

                <div style="margin-top: 20px;">
                    <div class="analysis-title" style="font-size: 0.95em;">动能分析</div>
                    {''.join([f'<div class="signal-item"><div class="signal-value" style="font-size: 0.9em;">{analysis}</div></div>' for analysis in data['momentum_analysis']])}
                </div>

                <div style="margin-top: 15px;">
                    <div class="analysis-title" style="font-size: 0.95em;">关键位置</div>
                    <div class="signal-item">
                        <div class="signal-label">当前价格</div>
                        <div class="signal-value">{latest['close']:.2f} USDT</div>
                    </div>
                    <div class="signal-item">
                        <div class="signal-label">支撑位 (EMA52)</div>
                        <div class="signal-value">{latest['ema52']:.2f}</div>
                    </div>
                    <div class="signal-item sell">
                        <div class="signal-label">止损参考 (EMA52-300)</div>
                        <div class="signal-value">{latest['ema52'] - 300:.2f}</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
"""

    # JavaScript代码
    html_content += """
    <script>
        const chartsData = """ + json.dumps(charts_data, indent=2) + """;

        // 创建图表
        Object.keys(chartsData).forEach(tf => {
            const data = chartsData[tf];

            // K线图
            const candlestickChart = LightweightCharts.createChart(
                document.getElementById(`candlestick-${tf}`),
                {
                    layout: {
                        background: { color: '#0a0a0a' },
                        textColor: '#888',
                    },
                    grid: {
                        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    },
                    crosshair: {
                        mode: LightweightCharts.CrosshairMode.Normal,
                    },
                    rightPriceScale: {
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                    },
                    timeScale: {
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        timeVisible: true,
                    },
                }
            );

            const candlestickSeries = candlestickChart.addCandlestickSeries({
                upColor: '#00ff88',
                downColor: '#ff4466',
                borderUpColor: '#00ff88',
                borderDownColor: '#ff4466',
                wickUpColor: '#00ff88',
                wickDownColor: '#ff4466',
            });
            candlestickSeries.setData(data.candlestick);

            // EMA26
            const ema26Series = candlestickChart.addLineSeries({
                color: '#ffa500',
                lineWidth: 2,
                title: 'EMA26',
            });
            ema26Series.setData(data.ema26);

            // EMA52
            const ema52Series = candlestickChart.addLineSeries({
                color: '#00ccff',
                lineWidth: 2,
                title: 'EMA52',
            });
            ema52Series.setData(data.ema52);

            // MACD图
            const macdChart = LightweightCharts.createChart(
                document.getElementById(`macd-${tf}`),
                {
                    layout: {
                        background: { color: '#0a0a0a' },
                        textColor: '#888',
                    },
                    grid: {
                        vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    },
                    crosshair: {
                        mode: LightweightCharts.CrosshairMode.Normal,
                    },
                    rightPriceScale: {
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                    },
                    timeScale: {
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        timeVisible: true,
                    },
                }
            );

            // Histogram
            const histogramSeries = macdChart.addHistogramSeries({
                priceFormat: {
                    type: 'price',
                },
            });
            histogramSeries.setData(data.histogram);

            // DIF (黄线)
            const difSeries = macdChart.addLineSeries({
                color: '#ffeb3b',
                lineWidth: 2,
                title: 'DIF',
            });
            difSeries.setData(data.dif);

            // DEA (白线)
            const deaSeries = macdChart.addLineSeries({
                color: '#ffffff',
                lineWidth: 2,
                title: 'DEA',
            });
            deaSeries.setData(data.dea);

            // 同步时间轴
            candlestickChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                macdChart.timeScale().setVisibleLogicalRange(range);
            });

            macdChart.timeScale().subscribeVisibleLogicalRangeChange(range => {
                candlestickChart.timeScale().setVisibleLogicalRange(range);
            });

            // 自适应大小
            window.addEventListener('resize', () => {
                candlestickChart.applyOptions({
                    width: document.getElementById(`candlestick-${tf}`).clientWidth
                });
                macdChart.applyOptions({
                    width: document.getElementById(`macd-${tf}`).clientWidth
                });
            });
        });
    </script>
</body>
</html>
"""

    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"[SUCCESS] HTML report generated: {output_file}", file=sys.stderr)
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Generate BTC momentum analysis HTML chart")

    parser.add_argument(
        '--timeframes',
        type=str,
        default='2d,1d,4h',
        help='Comma-separated timeframes (default: 2d,1d,4h)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='/Users/adrian/Desktop/BA/MACD/data/btc_analysis_report.html',
        help='Output HTML file path'
    )

    args = parser.parse_args()

    # 解析时间级别
    timeframes = [tf.strip() for tf in args.timeframes.split(',')]

    # 生成HTML
    output_file = generate_html(timeframes, args.output)

    print(f"\n{'='*60}")
    print(f"HTML报告已生成: {output_file}")
    print(f"时间级别: {', '.join(timeframes)}")
    print(f"{'='*60}\n")

    # 在macOS上自动打开浏览器
    import platform
    if platform.system() == 'Darwin':
        os.system(f'open "{output_file}"')
        print("✓ 已在浏览器中打开报告")


if __name__ == '__main__':
    main()
