# Crypto OB Telegram Scanner

Scans the top 250 crypto assets by CoinGecko market cap, keeps Binance Spot USDT pairs,
and checks the supplied Order Block logic on 4H, 1D and 1W closed candles.

The GitHub Actions workflow runs every 5 minutes and sends a Telegram message when a
new OB is created on the latest closed candle. GitHub scheduled workflows can be delayed,
so this is not a tick-by-tick WebSocket service.

No Binance API key is required.
