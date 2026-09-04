# Momentum / Field Dashboard

Nuxt UI implementation of the Figma dashboard at node `1267:3993`.

## Local development

```bash
cp .env.example .env
npm install
npm run dev
```

Open `http://localhost:3000`.

## Data sources

- `GET /api/dashboard?interval=6h` fetches BTCUSDT futures candles from Binance and calculates EMA 6/13/26/52 plus MACD 12/26/9.
- `POST /api/webhooks/tradingview` accepts authenticated TradingView alerts.
- `GET /api/signals` returns the latest stored alerts.
- `GET /api/health` is a lightweight deployment health check.

The `Signals` navigation item renders received webhook events. `Positions` intentionally remains disconnected in this version because no Binance private account credentials or order-execution permissions are stored.

The Codex Binance plugin is useful during development, but it is not a runtime dependency of the deployed dashboard. The Nuxt server talks directly to Binance's public market-data API.

All MACD panels share a TradingView-inspired palette: DIF is blue, DEA is orange, expanding positive bars are teal, contracting positive bars are pale mint, expanding negative bars are red, and contracting negative bars are pale pink. Every histogram color is fully opaque.

## TradingView alert body

Set `NUXT_TRADINGVIEW_WEBHOOK_SECRET` to a long random value, then use JSON like this as the TradingView alert message:

After deployment, set the TradingView Webhook URL to:

```text
https://<your-domain>/api/webhooks/tradingview
```

```json
{
  "secret": "replace-with-the-same-secret",
  "ticker": "{{ticker}}",
  "timeframe": "{{interval}}",
  "action": "LONG",
  "price": "{{close}}",
  "strategy": "MACD segment",
  "timestamp": "{{time}}"
}
```

For the first single-user version, signals are stored in `.data/signals`. Do not use this filesystem driver when deploying to an ephemeral serverless runtime; switch the Nitro storage mount to a persistent volume or a small managed database first.
