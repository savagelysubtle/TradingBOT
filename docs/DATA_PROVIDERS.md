# Data Providers Guide

This document covers all available data providers for both **static (historical)** and **live (real-time)** market data for backtesting and live trading.

## Current Implementation

### ✅ Already Integrated

#### 1. **CCXT** (Cryptocurrency)
- **Type**: Historical + Live
- **Exchanges**: 100+ (Binance, Coinbase, Kraken, etc.)
- **Status**: ✅ Fully integrated
- **Usage**:
```python
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

# Historical data
fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=True)
data = fetcher.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=365)

# Live data (via WebSocket)
from trading_bot.data.websocket_fetcher import WebSocketDataFetcher
ws = WebSocketDataFetcher(exchange="binance")
```

#### 2. **yfinance** (Stocks)
- **Type**: Historical only
- **Coverage**: US stocks, ETFs, indices
- **Status**: ✅ Fully integrated
- **Usage**:
```python
from trading_bot.data.fetcher import DataFetcher

fetcher = DataFetcher()
data = fetcher.fetch_ohlcv("AAPL", period="1y", interval="1d")
```

## Additional Providers (Can Be Added)

### 1. **Alpha Vantage** (Stocks + Crypto)
- **Type**: Historical + Live (delayed)
- **Free Tier**: 5 API calls/minute, 500 calls/day
- **Installation**:
```bash
uv add alpha-vantage
```
- **Usage Example**:
```python
from alpha_vantage.timeseries import TimeSeries
from alpha_vantage.cryptocurrencies import CryptoCurrencies

# Stocks
ts = TimeSeries(key='YOUR_API_KEY', output_format='pandas')
data, meta = ts.get_daily(symbol='AAPL', outputsize='full')

# Crypto
cc = CryptoCurrencies(key='YOUR_API_KEY', output_format='pandas')
data, meta = cc.get_digital_currency_daily(symbol='BTC', market='USD')
```

### 2. **Polygon.io** (Stocks + Crypto)
- **Type**: Historical + Live
- **Free Tier**: Limited
- **Paid**: $29/month+
- **Installation**:
```bash
uv add polygon-api-client
```
- **Usage Example**:
```python
from polygon import RESTClient

client = RESTClient("YOUR_API_KEY")

# Historical data
aggs = client.get_aggs(
    ticker="AAPL",
    multiplier=1,
    timespan="day",
    from_="2023-01-01",
    to="2024-01-01"
)

# Live data (WebSocket)
from polygon.websocket import WebSocketClient

ws_client = WebSocketClient("YOUR_API_KEY")
ws_client.subscribe("T.AAPL")  # Trades
```

### 3. **Quandl/Nasdaq Data Link** (Stocks + Commodities)
- **Type**: Historical
- **Free Tier**: Limited datasets
- **Installation**:
```bash
uv add quandl
```
- **Usage Example**:
```python
import quandl

quandl.ApiConfig.api_key = "YOUR_API_KEY"
data = quandl.get("WIKI/AAPL", start_date="2023-01-01", end_date="2024-01-01")
```

### 4. **IEX Cloud** (Stocks)
- **Type**: Historical + Live
- **Free Tier**: 50,000 messages/month
- **Installation**:
```bash
uv add iexfinance
```
- **Usage Example**:
```python
from iexfinance.stocks import Stock
from iexfinance.refdata import get_symbols

# Historical
aapl = Stock("AAPL", token="YOUR_TOKEN")
data = aapl.get_historical_prices()

# Live
quote = aapl.get_quote()
```

### 5. **Finnhub** (Stocks + Crypto)
- **Type**: Historical + Live
- **Free Tier**: 60 API calls/minute
- **Installation**:
```bash
uv add finnhub-python
```
- **Usage Example**:
```python
import finnhub

finnhub_client = finnhub.Client(api_key="YOUR_API_KEY")

# Historical
data = finnhub_client.stock_candles('AAPL', 'D', 1590988249, 1591852249)

# Live (WebSocket)
finnhub_client.stock_websocket()
```

### 6. **Yahoo Finance (yfinance)** - Enhanced
- **Type**: Historical (can be extended for live)
- **Status**: ✅ Already integrated
- **Note**: Can add live ticker updates

### 7. **Binance API** (Direct - Crypto)
- **Type**: Historical + Live
- **Status**: ✅ Available via CCXT
- **Direct Usage** (if needed):
```python
import requests

# Historical
url = "https://api.binance.com/api/v3/klines"
params = {
    "symbol": "BTCUSDT",
    "interval": "1d",
    "limit": 365
}
response = requests.get(url, params=params)
```

### 8. **CoinGecko** (Crypto)
- **Type**: Historical + Live (free, no API key needed)
- **Installation**:
```bash
uv add pycoingecko
```
- **Usage Example**:
```python
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()

# Historical
data = cg.get_coin_market_chart_by_id('bitcoin', 'usd', '365days')
```

### 9. **FRED (Federal Reserve Economic Data)**
- **Type**: Historical (Economic indicators)
- **Installation**:
```bash
uv add fredapi
```
- **Usage Example**:
```python
from fredapi import Fred

fred = Fred(api_key='YOUR_API_KEY')
data = fred.get_series('DEXUSEU', start='2023-01-01')
```

### 10. **Tradier** (Stocks + Options)
- **Type**: Historical + Live
- **Free Tier**: Sandbox only
- **Installation**:
```bash
uv add tradier-python
```

## Recommended Setup for Backtesting

### For Cryptocurrency:
1. **Primary**: CCXT (already integrated) ✅
   - Best coverage (100+ exchanges)
   - Both historical and live
   - Free (no API key needed for public data)

2. **Alternative**: CoinGecko (free, no API key)
   - Good for historical data
   - No rate limits for basic usage

### For Stocks:
1. **Primary**: yfinance (already integrated) ✅
   - Free, no API key needed
   - Good historical coverage

2. **Enhanced**: Alpha Vantage (free tier)
   - More reliable than yfinance
   - Requires API key (free)

3. **Professional**: Polygon.io (paid)
   - Best quality and reliability
   - Real-time data
   - $29/month+

## Hybrid Approach: Static + Live

### Strategy 1: Use Static for Backtesting, Live for Paper Trading

```python
# Backtesting: Use cached/historical data
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

fetcher = CCXTDataFetcher(exchange_id="binance", use_cache=True)
historical_data = fetcher.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=365)

# Paper Trading: Use live data
from trading_bot.data.websocket_fetcher import WebSocketDataFetcher

ws = WebSocketDataFetcher(exchange="binance")
# Stream live data for paper trading
```

### Strategy 2: Combine Multiple Sources

```python
# Use yfinance for stocks
stock_fetcher = DataFetcher()
stock_data = stock_fetcher.fetch_ohlcv("AAPL", period="1y")

# Use CCXT for crypto
crypto_fetcher = CCXTDataFetcher(exchange_id="binance")
crypto_data = crypto_fetcher.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=365)
```

## Adding a New Data Provider

To add a new data provider:

1. **Create fetcher class** in `src/trading_bot/data/`:
```python
# src/trading_bot/data/new_provider_fetcher.py
class NewProviderFetcher:
    def fetch_ohlcv(self, symbol, **kwargs):
        # Implementation
        pass
```

2. **Update bot.py** to support it:
```python
# In TradingBot.__init__
if self.config.data_provider == "new_provider":
    self.data_fetcher = NewProviderFetcher(...)
```

3. **Add to config.py**:
```python
data_provider: str = Field(default="ccxt", alias="DATA_PROVIDER")
# Options: "ccxt", "yfinance", "new_provider"
```

## Data Quality Comparison

| Provider | Historical | Live | Free Tier | Rate Limits | Quality |
|----------|------------|------|-----------|-------------|---------|
| **CCXT** | ✅ | ✅ | ✅ | Moderate | ⭐⭐⭐⭐⭐ |
| **yfinance** | ✅ | ❌ | ✅ | Low | ⭐⭐⭐ |
| **Alpha Vantage** | ✅ | ⚠️ Delayed | ✅ | 5/min | ⭐⭐⭐⭐ |
| **Polygon.io** | ✅ | ✅ | ❌ | High | ⭐⭐⭐⭐⭐ |
| **CoinGecko** | ✅ | ✅ | ✅ | Low | ⭐⭐⭐⭐ |
| **Finnhub** | ✅ | ✅ | ✅ | 60/min | ⭐⭐⭐⭐ |

## Best Practices

1. **Cache Data**: Always use caching to avoid rate limits
2. **Use Sandbox**: Test with sandbox/testnet first
3. **Rate Limiting**: Respect API rate limits
4. **Error Handling**: Handle API failures gracefully
5. **Fallback**: Have multiple data sources as backup

## Current Recommendations

For your trading bot:

✅ **Keep using CCXT** for crypto (best option)
✅ **Keep using yfinance** for stocks (free and works)
✅ **Consider adding Alpha Vantage** if yfinance becomes unreliable
✅ **Use WebSocketFetcher** for live crypto data (already integrated)

## Example: Multi-Source Data Fetcher

```python
class UnifiedDataFetcher:
    """Fetches data from multiple sources with fallback."""

    def __init__(self):
        self.crypto_fetcher = CCXTDataFetcher(exchange_id="binance")
        self.stock_fetcher = DataFetcher()

    def fetch(self, symbol, **kwargs):
        if "/" in symbol:  # Crypto
            return self.crypto_fetcher.fetch_ohlcv(symbol, **kwargs)
        else:  # Stock
            return self.stock_fetcher.fetch_ohlcv(symbol, **kwargs)
```

## Resources

- [CCXT Documentation](https://docs.ccxt.com/)
- [yfinance Documentation](https://github.com/ranaroussi/yfinance)
- [Alpha Vantage API](https://www.alphavantage.co/documentation/)
- [Polygon.io API](https://polygon.io/docs)
- [CoinGecko API](https://www.coingecko.com/en/api)

