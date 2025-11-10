.v# Trading Bot

A comprehensive algorithmic trading bot built with Python 3.14, featuring
**free-threading** (no GIL), cryptocurrency trading via CCXT, advanced
backtesting with Backtrader, and technical analysis with TA-Lib.

## 🚀 Features

- 📊 **CCXT Integration**: Trade on 100+ cryptocurrency exchanges with a unified
  API
- ⚡ **VectorBT Backtesting**: Ultra-fast vectorized backtesting (10-100x faster than event-driven)
- 🎯 **Backtrader Backtesting**: Professional-grade backtesting framework (alternative)
- 📡 **WebSocket Streaming**: Real-time data streaming with sub-millisecond latency
- 📈 **TA-Lib Indicators**: 150+ technical analysis indicators
- 🆕 **Advanced Indicators**: Supertrend, Bollinger Bands, Ichimoku Cloud
- 🤖 **ML Strategies**: Machine learning-based trading strategies
- 🛡️ **Advanced Risk Management**: Kelly Criterion, ATR-based stops, dynamic position sizing
- 🎯 **Multi-Strategy Orchestration**: Run multiple strategies in parallel
- 🔄 **Python 3.14 Free-Threading**: True parallelism with multi-threading
  support
- 💰 **Paper Trading**: Simulate trading without risking real money
- 📝 **Comprehensive Logging**: Detailed logging and result tracking
- 🧵 **Parallel Processing**: Multi-threaded data fetching and backtesting

## 🆕 Latest Upgrades (2024)

See [UPGRADE_SUMMARY.md](docs/@docs/UPGRADE_SUMMARY.md) for complete details.

### Major Improvements:
- ⚡ **VectorBT Integration**: 10-100x faster backtesting with vectorized operations
- 📡 **WebSocket Streaming**: Real-time data with <50ms latency
- 🛡️ **Advanced Risk Management**: Kelly Criterion and dynamic position sizing
- 📊 **New Strategies**: Supertrend, Bollinger Bands, Ichimoku Cloud
- 🤖 **ML Framework**: Machine learning-based strategies with scikit-learn
- 🎯 **Multi-Strategy**: Parallel execution and portfolio optimization

## 🆕 What's New in Python 3.14

Python 3.14 introduces **free-threading** (removal of the Global Interpreter
Lock), enabling:

- **True parallelism** on multi-core CPUs
- **4x performance improvements** for CPU-bound tasks
- **Concurrent data fetching** for multiple symbols
- **Parallel backtesting** across multiple strategies

## Installation

### Prerequisites

- **Python 3.14** or higher
- **TA-Lib C Library** (must be installed first)
- **UV** package manager

See [INSTALLATION.md](INSTALLATION.md) for detailed installation instructions.

### Quick Install

```bash
# 1. Install TA-Lib C library (see INSTALLATION.md)
# 2. Install dependencies
uv sync
```

## Quick Start

### Launch the TUI (Text User Interface)

```bash
# Launch the interactive TUI (using uv with Python 3.14)
uv run --python .venv\Scripts\python.exe -m trading_bot.cli tui

# Or activate venv first, then use uv
.venv\Scripts\activate
uv run -m trading_bot.cli tui
```

The TUI provides an interactive interface for:

- Fetching live market data
- Running backtests
- Viewing results
- Managing strategies

### Backtesting with Backtrader

```bash
# Backtest a TA-Lib strategy on cryptocurrency
uv run python -m trading_bot.cli backtest --symbol BTC/USDT --exchange binance --strategy talib_ma
```

### Backtesting with Custom Engine

```bash
# Backtest using the custom engine
uv run python -m trading_bot.cli backtest --symbol BTC/USDT --engine custom
```

### Paper Trading

```bash
# Run paper trading on Binance
uv run python -m trading_bot.cli paper --symbol BTC/USDT --exchange binance
```

## Project Structure

```
TradingBOT/
├── src/trading_bot/
│   ├── data/
│   │   ├── fetcher.py          # yfinance data fetcher (stocks)
│   │   └── ccxt_fetcher.py    # CCXT data fetcher (crypto)
│   ├── strategies/
│   │   ├── base.py             # Base strategy class
│   │   ├── moving_average.py  # Simple MA crossover
│   │   └── ta_lib_strategy.py # TA-Lib strategies (MA, MACD)
│   ├── backtesting/
│   │   ├── engine.py           # Custom backtesting engine
│   │   └── backtrader_engine.py # Backtrader integration
│   ├── broker/
│   │   ├── base.py             # Base broker interface
│   │   ├── paper.py            # Paper trading broker
│   │   └── ccxt_broker.py      # CCXT cryptocurrency broker
│   ├── utils/
│   │   ├── logging.py          # Logging utilities
│   │   └── multithreading.py  # Python 3.14 multi-threading utilities
│   ├── bot.py                  # Main bot orchestrator
│   └── cli.py                  # Command-line interface
├── examples/                   # Example scripts
├── data/                       # Cached market data
├── logs/                       # Log files
└── results/                    # Backtest results
```

## Key Libraries

### CCXT (Cryptocurrency Trading)

- Unified API for 100+ exchanges
- Real-time and historical data
- Order placement and management

### Backtrader (Backtesting)

- Professional backtesting framework
- Built-in analyzers (Sharpe ratio, drawdown, etc.)
- Strategy optimization tools

### TA-Lib (Technical Analysis)

- 150+ technical indicators
- High-performance C implementation
- Industry-standard indicators

### NumPy 2.3.4+ (Numerical Computing)

- Python 3.14 compatible
- Enhanced performance
- Multi-dimensional arrays

## Usage Examples

### Example 1: Backtest TA-Lib Strategy

```python
from trading_bot.bot import TradingBot
from trading_bot.strategies.ta_lib_strategy import TALibMovingAverageCrossover
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

# Initialize bot
bot = TradingBot()

# Create CCXT data fetcher
fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=True)

# Fetch data
data = fetcher.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=365)

# Create strategy
strategy = TALibMovingAverageCrossover(short_period=50, long_period=200)

# Run backtest
results = bot.backtest(strategy, data, symbol="BTC/USDT")
print(f"Total Return: {results['total_return_pct']:.2f}%")
```

### Example 2: Parallel Data Fetching (Python 3.14)

```python
from trading_bot.utils.multithreading import parallel_fetch_data
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

fetcher = CCXTDataFetcher(exchange_id="binance")

# Fetch multiple symbols in parallel (true parallelism!)
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
results = parallel_fetch_data(
    lambda s: fetcher.fetch_ohlcv(s, timeframe="1d", limit=30),
    symbols,
    max_workers=4  # Uses all CPU cores with Python 3.14!
)

for symbol, data in results.items():
    print(f"{symbol}: {len(data)} candles")
```

### Example 3: Live Trading with CCXT

```python
from trading_bot.bot import TradingBot
from trading_bot.broker.ccxt_broker import CCXTBroker
from trading_bot.strategies.ta_lib_strategy import TALibMACDStrategy

# Initialize broker (use sandbox=True for testing!)
broker = CCXTBroker(
    exchange_id="binance",
    api_key="your_api_key",
    secret="your_secret",
    sandbox=True,
)

# Initialize bot
bot = TradingBot()
bot.set_broker(broker)

# Create strategy
strategy = TALibMACDStrategy()

# Run live trading
bot.run_live(strategy, symbol="BTC/USDT")
```

## Multi-Threading with Python 3.14

Python 3.14's free-threading enables true parallelism:

```python
from trading_bot.utils.multithreading import parallel_backtest

# Backtest multiple symbols in parallel
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]

def backtest_symbol(symbol):
    # Your backtest logic here
    return {"symbol": symbol, "return": 0.15}

results = parallel_backtest(backtest_symbol, symbols, max_workers=4)
# All backtests run simultaneously on different CPU cores!
```

## Configuration

Edit `.env` file:

```env
# Exchange Settings
EXCHANGE_ID=binance
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET=your_secret
EXCHANGE_SANDBOX=true

# Trading Settings
INITIAL_CAPITAL=10000
MAX_POSITION_SIZE=0.1
RISK_PER_TRADE=0.02

# Data Settings
DATA_PROVIDER=ccxt
CACHE_DATA=true
```

## Available Strategies

- **MovingAverageCrossover**: Simple MA crossover (pandas-based)
- **TALibMovingAverageCrossover**: MA crossover using TA-Lib (faster, more
  accurate)
- **TALibMACDStrategy**: MACD strategy using TA-Lib

## Supported Exchanges (via CCXT)

100+ exchanges including:

- Binance
- Coinbase
- Kraken
- Bybit
- OKX
- And many more...

See [CCXT Exchange List](https://docs.ccxt.com/#/README?id=exchanges) for full
list.

## Performance Benefits

With Python 3.14 free-threading:

- **4x faster** parallel data fetching
- **True CPU parallelism** for backtesting
- **Concurrent strategy evaluation**
- **Multi-core utilization**

## Risk Warning

⚠️ **DISCLAIMER**: This is educational software. Trading involves substantial
risk of loss. Always:

- Test strategies thoroughly with backtesting
- Start with paper trading (sandbox mode)
- Use only capital you can afford to lose
- Understand the risks involved in algorithmic trading

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Author

Created by Shaun (savagelysubtle)

## Resources

- [Python 3.14 Release Notes](https://docs.python.org/3/whatsnew/3.14.html)
- [CCXT Documentation](https://docs.ccxt.com/)
- [Backtrader Documentation](https://www.backtrader.com/)
- [TA-Lib Documentation](https://ta-lib.org/)
- [NumPy 2.3.4 Release Notes](https://numpy.org/devdocs/release/2.3.4-notes.html)
