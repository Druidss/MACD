#!/usr/bin/env python3
"""
交易信号检测模块

严格按照THEORY.md中定义的买卖点规则判断进场信号
"""

from typing import Dict, List, Any, Optional, Tuple


def find_previous_high(candles: List[Dict[str, Any]], lookback: int = 50) -> float:
    """
    找到前期高点

    参数:
        candles: K线数据列表
        lookback: 回看K线数量

    返回:
        前期高点价格
    """
    recent_candles = candles[-lookback:] if len(candles) > lookback else candles
    return max(c['high'] for c in recent_candles)


def detect_buy_point_1(candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    买点1: unit极限买点

    触发条件:
    1. 当前时间级别在下跌线段中 (DEA < 0)
    2. DEA在历史DEA的最高值附近 (接近极限值)
    3. 产生第一个阳K
    4. 对应的MACD缩量

    返回:
        如果检测到买点, 返回包含买点信息的字典, 否则返回None
    """
    if len(candles) < 10:
        return None

    last_k = candles[-1]
    prev_k = candles[-2]

    # 条件1: 下跌线段
    if last_k['dea'] >= 0:
        return None

    # 条件2: DEA接近历史极限值 (最低值的90%以内)
    recent_dea_values = [c['dea'] for c in candles[-50:] if c['dea'] is not None]
    min_dea = min(recent_dea_values)
    if last_k['dea'] > min_dea * 0.9:  # 不够接近极限
        return None

    # 条件3: 阳K
    is_yang_k = last_k['close'] > last_k['open']
    if not is_yang_k:
        return None

    # 条件4: MACD缩量
    is_shrinking = abs(last_k['histogram']) < abs(prev_k['histogram'])
    if not is_shrinking:
        return None

    # 找前期高点作为目标位2
    prev_high = find_previous_high(candles, lookback=50)

    return {
        'type': '买点1-极限买点',
        'entry': last_k['close'],
        'stop_loss': last_k['open'] - 2 * (last_k['high'] - last_k['low']),  # 开盘价 - 2*ATR
        'target1': last_k['ema52'],  # EMA52
        'target2': prev_high,  # 前高
        'reason': f"下跌线段极限买点：DEA={last_k['dea']:.0f}接近极限值{min_dea:.0f}，出现缩量阳K"
    }


def detect_buy_point_4(candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    买点4: 归零轴缩量买点

    触发条件:
    1. 在上涨线段中 (DEA > 0)
    2. 价格归零轴 (价格接近EMA52, 误差<1%)
    3. 出现阳K且MACD缩量
    4. 该时间级别为u1 (穿零轴后第一次有效时间级别)

    返回:
        如果检测到买点, 返回包含买点信息的字典, 否则返回None
    """
    if len(candles) < 10:
        return None

    last_k = candles[-1]
    prev_k = candles[-2]

    # 条件1: 上涨线段
    if last_k['dea'] <= 0:
        return None

    # 条件2: 价格接近EMA52 (严格标准: 1%以内)
    price_ema52_diff_pct = abs(last_k['close'] - last_k['ema52']) / last_k['ema52']
    if price_ema52_diff_pct > 0.01:  # 超过1%不算归零轴
        return None

    # 条件3: 阳K
    is_yang_k = last_k['close'] > last_k['open']
    if not is_yang_k:
        return None

    # 条件4: MACD缩量
    is_shrinking = abs(last_k['histogram']) < abs(prev_k['histogram'])
    if not is_shrinking:
        return None

    # 检查是否为u1 (DEA刚穿过0轴不久, 10根K线以内)
    zero_cross_recent = False
    for i in range(max(0, len(candles)-10), len(candles)-1):
        if candles[i]['dea'] <= 0 and candles[i+1]['dea'] > 0:
            zero_cross_recent = True
            break

    if not zero_cross_recent:
        return None

    # 找前期高点作为目标位2
    prev_high = find_previous_high(candles, lookback=50)

    return {
        'type': '买点4-归零轴缩量买点',
        'entry': last_k['close'],
        'stop_loss': last_k['ema52'] - 300,  # 击破调控止损 (EMA52-300)
        'target1': last_k['ema52'],  # EMA52
        'target2': prev_high,  # 穿过零轴之后的前高
        'reason': f"归零轴缩量买点：上涨线段u1，价格接近EMA52({price_ema52_diff_pct*100:.1f}%)，出现缩量阳K"
    }


def detect_sell_point_4(candles: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    卖点4: 归零轴缩量卖点

    触发条件:
    1. 在下跌线段中 (DEA < 0)
    2. 价格归零轴 (价格接近EMA52, 误差<1%)
    3. 出现阴K且MACD缩量
    4. 该时间级别为u1 (穿零轴后第一次有效时间级别)
    """
    if len(candles) < 10:
        return None

    last_k = candles[-1]
    prev_k = candles[-2]

    # 条件1: 下跌线段
    if last_k['dea'] >= 0:
        return None

    # 条件2: 价格接近EMA52
    price_ema52_diff_pct = abs(last_k['close'] - last_k['ema52']) / last_k['ema52']
    if price_ema52_diff_pct > 0.01:
        return None

    # 条件3: 阴K
    is_yin_k = last_k['close'] < last_k['open']
    if not is_yin_k:
        return None

    # 条件4: MACD缩量
    is_shrinking = abs(last_k['histogram']) < abs(prev_k['histogram'])
    if not is_shrinking:
        return None

    # 检查是否为u1
    zero_cross_recent = False
    for i in range(max(0, len(candles)-10), len(candles)-1):
        if candles[i]['dea'] >= 0 and candles[i+1]['dea'] < 0:
            zero_cross_recent = True
            break

    if not zero_cross_recent:
        return None

    # 找前期低点作为目标位2
    recent_candles = candles[-50:]
    prev_low = min(c['low'] for c in recent_candles)

    return {
        'type': '卖点4-归零轴缩量卖点',
        'entry': last_k['close'],
        'stop_loss': last_k['ema52'] + 300,  # 击破调控止损
        'target1': last_k['ema52'],  # EMA52
        'target2': prev_low,  # 前低
        'reason': f"归零轴缩量卖点：下跌线段u1，价格接近EMA52({price_ema52_diff_pct*100:.1f}%)，出现缩量阴K"
    }


def analyze_trading_signals(db: Dict[str, Any], timeframe: str) -> Dict[str, Any]:
    """
    分析指定时间级别的交易信号

    参数:
        db: 数据库字典
        timeframe: 时间级别 (如 '4h', '1h')

    返回:
        交易信号分析结果
    """
    if timeframe not in db['timeframes']:
        return {'has_signal': False, 'reason': f'{timeframe}数据不存在'}

    candles = db['timeframes'][timeframe]['candles']

    # 按优先级检测买卖点
    # 优先级: 买点1(极限) > 买点4(归零轴) > 卖点4(归零轴)

    # 检测买点1: 极限买点
    buy_point_1 = detect_buy_point_1(candles)
    if buy_point_1:
        return {
            'has_signal': True,
            'signal_type': 'buy',
            **buy_point_1
        }

    # 检测买点4: 归零轴缩量买点
    buy_point_4 = detect_buy_point_4(candles)
    if buy_point_4:
        return {
            'has_signal': True,
            'signal_type': 'buy',
            **buy_point_4
        }

    # 检测卖点4: 归零轴缩量卖点
    sell_point_4 = detect_sell_point_4(candles)
    if sell_point_4:
        return {
            'has_signal': True,
            'signal_type': 'sell',
            **sell_point_4
        }

    # 无明确买卖点信号
    last_k = candles[-1]
    return {
        'has_signal': False,
        'signal_type': 'wait',
        'reason': f"等待买卖点信号 (当前DEA={last_k['dea']:.0f}, 价格距EMA52={((last_k['close']-last_k['ema52'])/last_k['ema52']*100):+.1f}%)"
    }


def generate_trading_plan(db: Dict[str, Any], timeframe: str) -> Dict[str, Any]:
    """
    生成交易计划

    参数:
        db: 数据库
        timeframe: 时间级别

    返回:
        交易计划字典
    """
    signal = analyze_trading_signals(db, timeframe)
    last_k = db['timeframes'][timeframe]['candles'][-1]

    if signal['has_signal'] and signal['signal_type'] == 'buy':
        return {
            'direction': '做多',
            'entry': signal['entry'],
            'stop_loss': signal['stop_loss'],
            'target1': signal['target1'],
            'target2': signal['target2'],
            'reason': signal['reason'],
            'buy_point_type': signal['type']
        }
    elif signal['has_signal'] and signal['signal_type'] == 'sell':
        return {
            'direction': '做空',
            'entry': signal['entry'],
            'stop_loss': signal['stop_loss'],
            'target1': signal['target1'],
            'target2': signal['target2'],
            'reason': signal['reason'],
            'sell_point_type': signal['type']
        }
    else:
        # 观望状态
        return {
            'direction': '观望',
            'entry': None,
            'stop_loss': last_k['ema52'] - 300,
            'target1': None,
            'target2': None,
            'reason': signal['reason'],
            'buy_point_type': None
        }
