# Live Data Backtesting Guide

This guide shows you how to connect to live cryptocurrency data and backtest your strategies.

## Quick Start

### Step 1: Install Dependencies

```bash
uv sync
```

### Step 2: Configure Exchange

Edit `.env` file:

```env
DATA_PROVIDER=ccxt
EXCHANGE_ID=binance
EXCHANGE_SANDBOX=true
```

### Step 3: Run Your First Backtest

```bash
# Backtest BTC/USDT with TA-Lib strategy
uv run python -m trading_bot.cli backtest --symbol BTC/USDT --exchange binance --strategy talib_ma
```

## Using the CLI

### Basic Backtest

```bash
uv run python -m trading_bot.cli backtest \
  --symbol BTC/USDT \
  --exchange binance \
  --strategy talib_ma \
  --timeframe 1d \
  --limit 365
```

### Available Options

- `--symbol`: Trading pair (e.g., `BTC/USDT`, `ETH/USDT`)
- `--exchange`: Exchange ID (`binance`, `coinbase`, `kraken`, etc.)
- `--strategy`: Strategy name (`ma_crossover`, `talib_ma`, `talib_macd`)
- `--timeframe`: Candle timeframe (`1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`)
- `--limit`: Number of candles to fetch (default: 1000)
- `--start-date`: Start date (YYYY-MM-DD)
- `--end-date`: End date (YYYY-MM-DD)
- `--engine`: Backtest engine (`backtrader` or `custom`)

## Python Code Examples

### Example 1: Simple Backtest

```python
from trading_bot.bot import TradingBot
from trading_bot.config import TradingConfig
from trading_bot.strategies.ta_lib_strategy import TALibMovingAverageCrossover

# Configure
config = TradingConfig()
config.data_provider = "ccxt"
config.exchange_id = "binance"
config.exchange_sandbox = True

# Initialize
bot = TradingBot(config)
strategy = TALibMovingAverageCrossover(short_period=50, long_period=200)

# Backtest
results = bot.backtest(
    strategy=strategy,
    symbol="BTC/USDT",
    timeframe="1d",
    limit=365,
)

print(f"Return: {results['total_return_pct']:.2f}%")
```

### Example 2: Fetch Live Data Directly

```python
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

# Initialize fetcher
fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=True)

# Fetch data
data = fetcher.fetch_ohlcv(
    symbol="BTC/USDT",
    timeframe="1d",
    limit=365,
)

print(f"Fetched {len(data)} candles")
print(f"Latest price: ${data['close'].iloc[-1]:,.2f}")
```

### Example 3: Parallel Multi-Symbol Backtesting

```python
from trading_bot.utils.multithreading import parallel_fetch_data
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=True)

# Fetch multiple symbols in parallel (Python 3.14 free-threading!)
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
results = parallel_fetch_data(
    lambda s: fetcher.fetch_ohlcv(s, timeframe="1d", limit=365),
    symbols,
    max_workers=4,  # Uses all CPU cores!
)

for symbol, data in results.items():
    print(f"{symbol}: {len(data)} candles, Latest: ${data['close'].iloc[-1]:,.2f}")
```

### Example 4: Real-Time Price Data

```python
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=True)

# Get latest price
price = fetcher.get_latest_price("BTC/USDT")
print(f"BTC/USDT: ${price:,.2f}")

# Get ticker data (24h stats)
ticker = fetcher.exchange.fetch_ticker("BTC/USDT")
print(f"24h Change: {ticker['percentage']:.2f}%")
print(f"24h High: ${ticker['high']:,.2f}")
print(f"24h Low: ${ticker['low']:,.2f}")
```

## Supported Exchanges

CCXT supports 100+ exchanges. Popular ones:

- **Binance**: `binance`
- **Coinbase**: `coinbase`
- **Kraken**: `kraken`
- **Bybit**: `bybit`
- **OKX**: `okx`
- **Gate.io**: `gate`

See full list: https://docs.ccxt.com/#/README?id=exchanges

## Timeframes

Available timeframes depend on exchange, common ones:

- `1m` - 1 minute
- `5m` - 5 minutes
- `15m` - 15 minutes
- `30m` - 30 minutes
- `1h` - 1 hour
- `4h` - 4 hours
- `1d` - 1 day
- `1w` - 1 week
- `1M` - 1 month

## Data Limits

Most exchanges have rate limits. CCXT handles this automatically with `enableRateLimit: True`.

Typical limits:
- **Binance**: 1200 requests/minute
- **Coinbase**: 10,000 requests/hour
- **Kraken**: Varies by endpoint

## Sandbox vs Live

### Sandbox (Recommended for Testing)

```python
fetcher = CCXTDataFetcher(
    exchange_id="binance",
    sandbox=True,  # Use testnet
)
```

- Free to use
- No real money
- Same API as live
- Good for testing

### Live (Production)

```python
fetcher = CCXTDataFetcher(
    exchange_id="binance",
    api_key="your_api_key",
    secret="your_secret",
    sandbox=False,  # Live trading
)
```

⚠️ **Warning**: Use live mode only after thorough testing!

## Troubleshooting

### "Exchange not found"

Make sure the exchange ID is correct:
```python
import ccxt
print(ccxt.exchanges)  # List all supported exchanges
```

### "Rate limit exceeded"

CCXT handles rate limits automatically. If you see this:
- Reduce `limit` parameter
- Add delays between requests
- Use sandbox mode (higher limits)

### "No data returned"

- Check symbol format (use `/` separator: `BTC/USDT`)
- Verify exchange supports the symbol
- Try a different timeframe
- Check exchange status

### "TA-Lib import error"

Make sure TA-Lib C library is installed (see `INSTALLATION.md`).

## Next Steps

1. **Test Strategies**: Run backtests on multiple symbols
2. **Optimize Parameters**: Find best MA periods, RSI thresholds, etc.
3. **Paper Trading**: Test strategies with simulated trading
4. **Live Trading**: Deploy to live exchange (with caution!)

## Example Scripts

See `examples/` directory:
- `live_data_backtest.py` - Comprehensive examples
- `quick_start_live.py` - Minimal example

## Resources

- [CCXT Documentation](https://docs.ccxt.com/)
- [Backtrader Documentation](https://www.backtrader.com/)
- [TA-Lib Documentation](https://ta-lib.org/)
- [Exchange API Status](https://status.ccxt.com/)

