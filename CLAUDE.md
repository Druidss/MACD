# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains TradingView Pine Script strategies for BTC trading, primarily focused on EMA (Exponential Moving Average) and MACD (Moving Average Convergence Divergence) indicators. The strategies are designed for 1-hour and 4-hour timeframes on Bitcoin.

## Core Trading Strategies

### 1. MACD.pine - EMA + MACD Segment Breakthrough Strategy

Main strategy file implementing a comprehensive EMA21/52/144 + MACD multi-timeframe system.

**Key Concepts:**
- **Segment Classification**: Market is divided into 4 phases with color-coded backgrounds:
  - Green (上涨线段): Uptrend segment when DEA > 0
  - Light Orange (浅橙过渡): Transition period after uptrend (delay period)
  - Purple (浅紫色突破尝试): Below-zero breakthrough attempt (DEA between threshold and 0)
  - Red (下跌线段): Downtrend segment

- **Entry Rules**:
  - Long: Cross above EMA21 during green uptrend or purple breakthrough segments
  - Short: Cross below EMA21 during red downtrend segments (only after first long trade is opened)
  - 4-hour MACD filters applied (DIF <= 1500 for longs, DEA >= -1500 for shorts)

- **Exit Rules**:
  - Long stop loss: Close below EMA52-300
  - Short stop loss: Close above EMA52

- **Segment Confirmation Logic**:
  - Uptrend requires `min_downtrend_bars` (default 2) confirmation bars after DEA crosses above 0
  - Downtrend requires `delay_bars` (default 25) confirmation bars after DEA crosses below 0
  - Below-zero breakthrough: When DEA > threshold (default -60) but < 0, allows `below_zero_timeout` bars (default 8) to cross above 0

**Important Parameters** (MACD.pine):
- Initial capital: 50 USDT
- Default position size: 200 USDT cash
- Commission: 0.1%
- EMA periods: 21, 52, 144
- MACD: fast=12, slow=26, signal=9

### 2. jump.pine - MACD Histogram Jump Strategy

Strategy based on MACD histogram "jumps" (volume gaps) in uptrend segments.

**Core Logic**:
- Only trades during uptrend (DEA > 0) and when EMA21 > EMA52
- Detects histogram pullbacks (回调) followed by gaps (跳空)
- Entry on gap continuation after pullback, with stop loss at open - stopLossOffset
- Trailing stop loss: Moves up to previous bar's open - stopLossOffset on subsequent gaps
- Special zero-axis entry: When DEA is near zero (< zeroAxisThreshold=300) and red histogram is shrinking

**Important Parameters** (jump.pine):
- Initial capital: 50 USDT
- Default position size: 100 USDT cash
- stopLossOffset: 300 (points below open for stop loss)
- zeroAxisThreshold: 300 (DEA threshold for zero-axis entries)

### 3. YinYangCrown_Detector.pine - Library

State machine for detecting "Yin Yang Crown" (阴阳冕) patterns in MACD histogram. This is a library file, not a standalone strategy.

## File Structure

```
.
├── MACD.pine                      # Main EMA+MACD segment strategy
├── jump.pine                      # Histogram jump/gap strategy
├── YinYangCrown_Detector.pine     # Pattern detection library
├── README.md                      # Strategy documentation with parameters and logic updates
├── prompt_jump.md                 # Development notes for jump.pine
├── 回测笔记.md                     # Backtesting notes
└── attach/                        # Screenshots for documentation
```

## Development Notes

### README.md Structure
The README.md contains:
- Parameter settings for BTC 1h/4h timeframes
- Entry/exit conditions for each strategy version
- Historical development log with dates showing strategy evolution
- Specific line references (e.g., "MACD.pine:175-187" for batch closing logic)
- Backtesting scenarios with screenshots

### Key Evolution Points (from README.md)
- 2025-10-14: Added batch closing (50% at previous high, remaining at EMA52 break)
- 2025-10-15: Removed cooldown mechanism, added short entries on EMA21 breaks during downtrends
- 2025-10-16: Changed segment transition logic from fixed bar count to EMA21/EMA52 relationship
- 2025-10-18: Added consolidation filter, profit threshold checks
- 2025-10-19: Fuzzy stop loss at EMA52-200

### Important Trading Rules
1. **Position Sizing**: Base capital 50 USDT, position size 200 USDT (4x leverage implied)
2. **First Trade Rule**: Short entries only allowed after first long trade is opened (see MACD.pine:182)
3. **4H MACD Filter**: Critical for avoiding poor entries (threshold=1000 in 1h BTC, see README.md:6)
4. **Segment Colors**: Visual system helps identify trading zones - only trade longs in green/purple backgrounds

## Testing and Validation

No automated test commands. Strategies are validated through:
1. TradingView's built-in backtesting on historical BTC data
2. Manual backtesting notes recorded in 回测笔记.md
3. Visual verification using the color-coded segment backgrounds

## Code Modification Guidelines

When modifying strategies:
1. Update the corresponding documentation in README.md with date headers
2. Reference specific line numbers when documenting changes (e.g., "MACD.pine:175-187")
3. Test parameter changes on both 1h and 4h timeframes
4. Pay attention to segment classification logic - it's the foundation of the entry system
5. Maintain the 4-state segment system (uptrend/transition/breakthrough/downtrend)
6. Be cautious with the `first_trade_opened` flag logic - it prevents shorts before first long

## Language Note

The codebase uses mixed Chinese and English. Pine Script code is in English with Chinese comments. Documentation (README.md, 回测笔记.md) is primarily in Chinese.
