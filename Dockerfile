FROM python:3.12-slim

WORKDIR /app

# This project uses only Python standard library for the Binance report path.
COPY . /app

RUN chmod +x /app/scripts/binance_momentum_report.py \
    /app/.claude/skills/btc-6h-scheduled/scripts/run_6h_analysis.py \
    /app/.claude/skills/btc-6h-scheduled/scripts/cron_6h.sh

CMD ["python", "scripts/binance_momentum_report.py", "--market", "futures", "--symbol", "BTCUSDT", "--timeframes", "1d,12h,6h,4h,2h,1h,30m"]
