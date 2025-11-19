# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project Overview

This is a **comprehensive algorithmic cryptocurrency and stock trading bot**
built with Python 3.13.4+ or 3.14+, featuring advanced backtesting, live trading
capabilities, and multi-threading support using Python's free-threading (no GIL
on 3.14+).

**Version**: 0.1.0 **License**: MIT **Python**: 3.13.4+ or 3.14+ (dual mode
support)

- **3.14+**: Free-threading for true parallelism
- **3.13.4+**: GPU acceleration support (CuPy/CUDA)

## Technology Stack

- **Data Processing**: pandas 2.0.0+, numpy 2.3.4+ (Python 3.14 compatible)
- **Cryptocurrency**: ccxt 4.0.0+ (unified API for 100+ exchanges)
- **Stock Data**: yfinance (via DataFetcher)
- **Backtesting**: backtrader 1.9.78+, vectorbt (optional, 10-100x faster)
- **Technical Analysis**: TA-Lib 0.6.8+ (optional, 150+ indicators)
- **Configuration**: pydantic 2.0.0+, python-dotenv
- **CLI**: click 8.1.0+
- **TUI**: textual 0.80.0+, rich 13.0.0+
- **Machine Learning**: scikit-learn, xgboost, lightgbm (optional)
- **Package Manager**: UV (not pip)

## Common Commands

### Installation

**Dual-Python Setup (Recommended):**

This project supports dual-Python mode for optimal performance:

```bash
# 1. Install main dependencies with Python 3.14 (free-threading for main bot)
# Must have TA-Lib C library installed first - see INSTALLATION.md
uv sync --python 3.14 --prerelease=allow

# 2. Install GPU dependencies with Python 3.13.4 (for Monte Carlo GPU acceleration)
# Note: CuPy doesn't support Python 3.14 yet, use 3.13.4 for GPU support
uv sync --extra gpu --python 3.13.4 --prerelease=allow

# Usage:
# - Python 3.14: Main bot operations (backtesting, live trading, TUI) - free-threading enabled
# - Python 3.13.4: Monte Carlo simulations - GPU-accelerated with CuPy/CUDA (10-100x faster)
```

**Single-Python Setup (Alternative):**

If you only need one Python version:

```bash
# Option A: Python 3.14 only (CPU-only Monte Carlo, free-threading for main bot)
uv sync --python 3.14 --prerelease=allow

# Option B: Python 3.13.4 only (GPU-accelerated Monte Carlo, no free-threading)
uv sync --extra gpu --python 3.13.4 --prerelease=allow
```

### Running the Application

```bash
# Launch TUI (Text User Interface) - Python 3.14 (free-threading)
uv run --python 3.14 tui
# Or Python 3.13.4 (GPU acceleration)
uv run --python 3.13.4 tui

# Or run CLI directly
uv run --python 3.14 trading-bot --help
# Or with Python 3.13.4
uv run --python 3.13.4 trading-bot --help

# Backtest a strategy
uv run --python 3.14 trading-bot backtest --symbol BTC/USDT --exchange binance --strategy talib_ma

# Backtest with custom engine
uv run --python 3.14 trading-bot backtest --symbol BTC/USDT --engine custom

# Backtest with VectorBT (fastest)
uv run --python 3.14 trading-bot backtest --symbol BTC/USDT --engine vectorbt

# Monte Carlo simulation (1000 simulations)
# Python 3.14: CPU-only
uv run --python 3.14 trading-bot montecarlo --symbol BTC/USDT --exchange binance --strategy talib_ma
# Python 3.13.4: GPU-accelerated (10-100x faster)
uv run --python 3.13.4 trading-bot montecarlo --symbol BTC/USDT --exchange binance --strategy talib_ma

# Monte Carlo with different methods
uv run --python 3.14 trading-bot montecarlo --symbol BTC/USDT --method bootstrap -n 1000
uv run --python 3.14 trading-bot montecarlo --symbol BTC/USDT --method shuffle_trades -n 500
uv run --python 3.14 trading-bot montecarlo --symbol BTC/USDT --method randomize_returns -n 1000

# Paper trading (simulation)
uv run --python 3.14 trading-bot paper --symbol BTC/USDT --exchange binance

# Live trading (use with caution!)
uv run --python 3.14 trading-bot live --symbol BTC/USDT --exchange binance

# Alternative: Run directly via Python module
uv run --python 3.14 python -m trading_bot.interfaces.cli backtest --symbol BTC/USDT
uv run --python 3.14 python -m trading_bot.interfaces.tui
```

### Code Quality

```bash
# Format code
ruff format

# Lint code
ruff check

# Auto-fix linting issues
ruff check --fix

# Type checking
ty check
```

## Architecture Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                    TradingBot CLI/TUI                    │
│           (cli.py / tui.py - User Interface)            │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼────────────┐   ┌───────▼──────────────┐
│   Backtesting      │   │   Live Trading       │
│  (bot.backtest)    │   │  (bot.run_live)      │
└───────┬────────────┘   └───────┬──────────────┘
        │                        │
        ├────────┬───────────────┘
        │        │
┌───────▼────────▼──────────────────────┐
│  Data Fetchers (Fetch Market Data)    │
│  ├─ CCXTDataFetcher (crypto)         │
│  ├─ DataFetcher (yfinance/stocks)    │
│  └─ WebSocketFetcher (real-time)     │
└─────────────┬────────────────────────┘
              │
┌─────────────▼────────────────────────┐
│  Backtesting Engines (Run Strategy)   │
│  ├─ BacktestEngine (custom)          │
│  ├─ BacktraderEngine                 │
│  └─ VectorBTEngine (10-100x faster)  │
└─────────────┬────────────────────────┘
              │
┌─────────────▼────────────────────────┐
│  Trading Strategies (Generate Signals) │
│  ├─ BaseStrategy (abstract)           │
│  ├─ MovingAverageCrossover            │
│  ├─ TALibMovingAverageCrossover       │
│  ├─ TALibMACDStrategy                 │
│  ├─ AdvancedIndicators (Supertrend)   │
│  └─ MLStrategy (scikit-learn)         │
└─────────────┬────────────────────────┘
              │
        ┌─────▼──────┐
        │            │
┌───────▼──────┐  ┌──▼──────────┐
│  Brokers     │  │ Risk Mgmt   │
│ ├─ Paper     │  │ ├─ Kelly    │
│ ├─ CCXT      │  │ │ Criterion │
│ └─ Base      │  │ └─ Position │
└──────────────┘  │   Sizing    │
                  └─────────────┘
```

### Key Components

**User Interfaces** ([interfaces/](src/trading_bot/interfaces/))

- `CLI` ([cli.py](src/trading_bot/interfaces/cli.py)): Command-line interface
  with Click
- `TUI` ([tui.py](src/trading_bot/interfaces/tui.py)): Interactive terminal UI
  with Textual
- `TUI Widgets` ([tui_widgets.py](src/trading_bot/interfaces/tui_widgets.py)):
  Reusable TUI components

**TradingBot** ([bot.py](src/trading_bot/bot.py))

- Central orchestrator class
- Initializes data fetchers based on configuration
- Selects appropriate backtesting engine
- Manages live trading via brokers
- Coordinates strategy execution

**Data Fetchers** ([data/](src/trading_bot/data/))

- `CCXTDataFetcher`: Fetches cryptocurrency OHLCV data from 100+ exchanges
- `DataFetcher`: Fetches stock data via yfinance
- `WebSocketFetcher`: Real-time data streaming (<50ms latency)

**Strategies** ([strategies/](src/trading_bot/strategies/))

- All inherit from `BaseStrategy` abstract class
- `MovingAverageCrossover`: Pandas-based MA crossover
- `TALibMovingAverageCrossover`: TA-Lib SMA/EMA crossover with RSI filter
- `TALibMACDStrategy`: MACD + Signal line
- `AdvancedIndicators`: Supertrend, Bollinger Bands, Ichimoku
- `MLStrategy`: scikit-learn RandomForest/XGBoost

**Backtesting Engines** ([backtesting/](src/trading_bot/backtesting/))

- `BacktestEngine`: Pure Python, most flexible (~1-10 candles/sec)
- `BacktraderEngine`: Professional framework (~10-100 candles/sec)
- `VectorBTEngine`: Ultra-fast vectorized, 10-100x faster
- `MonteCarloEngine`: Statistical simulation for risk analysis and strategy
  robustness

**Broker Interfaces** ([broker/](src/trading_bot/broker/))

- All inherit from `BaseBroker`
- `PaperBroker`: Simulates trading without real money
- `CCXTBroker`: Live trading via CCXT with sandbox mode support

**Configuration** ([config.py](src/trading_bot/config.py))

- Uses Pydantic for validation
- `TradingConfig`: Main settings (from .env file)
- `BacktestConfiguration`: Backtest template management
- `BacktestHistory`: History tracking and persistence

**Multi-Threading**
([utils/multithreading.py](src/trading_bot/utils/multithreading.py))

- Python 3.14 free-threading utilities
- `parallel_fetch_data()`: Concurrent data fetching
- `parallel_backtest()`: Parallel strategy testing
- True CPU parallelism without GIL overhead

## Data Flow

### Backtesting Flow

```
1. CLI/TUI receives: symbol, strategy, dates, parameters
2. TradingBot.backtest() called
3. Data fetcher retrieves historical data (CCXTDataFetcher or DataFetcher)
4. Backtesting engine selected (VectorBT > Backtrader > Custom)
5. Engine runs strategy.generate_signals(data)
6. Trades executed based on signals
7. Metrics calculated (returns, Sharpe, drawdown, etc.)
8. Results saved to results/
```

### Live Trading Flow

```
1. CLI/TUI creates Broker (CCXTBroker or PaperBroker) and Strategy
2. TradingBot.run_live() called
3. Loop every check_interval (default 60s):
   a. Fetch recent market data
   b. Strategy.generate_signals()
   c. Check current positions
   d. Execute trades if signals generated
   e. Log results
4. Continue until stopped
```

## Development Patterns

### Creating a New Strategy

All strategies must inherit from `BaseStrategy`:

```python
from trading_bot.strategies.base import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    def __init__(self, param1: int, param2: float):
        super().__init__()
        self.param1 = param1
        self.param2 = param2

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals from market data.

        Args:
            data: DataFrame with OHLCV data (columns: open, high, low, close, volume)

        Returns:
            DataFrame with added 'signal' column (1=buy, -1=sell, 0=hold)
        """
        # Your signal logic here
        data['signal'] = 0  # Start with no signal
        # ... implement your strategy
        return data
```

### Data Fetching

**Cryptocurrency** (CCXT):

```python
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher

fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=True)
data = fetcher.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=365)
```

**Stocks** (yfinance):

```python
from trading_bot.data.fetcher import DataFetcher

fetcher = DataFetcher()
data = fetcher.fetch("AAPL", start_date="2023-01-01", end_date="2024-01-01")
```

**Real-time WebSocket**:

```python
from trading_bot.data.websocket_fetcher import WebSocketFetcher

fetcher = WebSocketFetcher(exchange_id="binance")
await fetcher.subscribe(["BTC/USDT", "ETH/USDT"])
```

### Python 3.14+ Free-Threading

Leverage true parallelism without GIL (Python 3.14+ only):

```python
from trading_bot.utils.multithreading import parallel_fetch_data, parallel_backtest

# Parallel data fetching
symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]
results = parallel_fetch_data(
    lambda s: fetcher.fetch_ohlcv(s, timeframe="1d", limit=30),
    symbols,
    max_workers=4  # Uses all CPU cores
)

# Parallel backtesting
def backtest_symbol(symbol):
    # Your backtest logic
    return results

results = parallel_backtest(backtest_symbol, symbols, max_workers=4)
```

### Monte Carlo Simulation

Monte Carlo simulation helps assess strategy robustness and risk by running
hundreds/thousands of simulations with different scenarios.

**⚠️ Dual-Python Setup for Optimal Performance:**

This project supports **dual-Python mode** to maximize performance:

- **Python 3.14**: Use for main bot operations (backtesting, live trading, TUI) - enables free-threading for true parallelism
- **Python 3.13.4**: Use for Monte Carlo simulations - enables GPU acceleration with CuPy (10-100x faster)

**GPU Acceleration Note:**

- Python 3.14: CPU-only (CuPy doesn't support 3.14 yet) - automatically falls back to NumPy
- Python 3.13.4 + `--extra gpu`: GPU-accelerated with CUDA (10-100x faster)
- **Important:** Match CuPy CUDA version to your driver (check with `nvidia-smi`)
  - Driver supports CUDA 12.x → use `cupy-cuda12x` (default in pyproject.toml)
  - Driver supports CUDA 13.x → update pyproject.toml to use `cupy-cuda13x`
- The Monte Carlo engine will warn you if running on Python 3.14 without GPU
- If you get "CUDA driver version is insufficient" error, check your driver's CUDA version and match CuPy accordingly

**Three Simulation Methods:**

1. **Bootstrap Resampling**: Randomly samples from historical data with
   replacement

   - Tests how strategy performs on different sequences of market data
   - Preserves statistical properties of original data
   - Best for: Understanding strategy sensitivity to data sequence

2. **Shuffle Trades**: Randomizes the order of trades

   - Tests if trade sequence affects performance
   - Assumes individual trades are independent
   - Best for: Identifying sequence-dependent strategies

3. **Randomize Returns**: Adds random noise to historical returns
   - Tests strategy robustness to market volatility
   - Generates synthetic price paths
   - Best for: Stress testing under varying market conditions

**CLI Usage:**

```bash
# RECOMMENDED: Use helper script for GPU acceleration (Python 3.13.4)
# Windows PowerShell:
.\scripts\montecarlo-gpu.ps1 --symbol BTC/USDT --strategy talib_ma

# Linux/Mac:
./scripts/montecarlo-gpu.sh --symbol BTC/USDT --strategy talib_ma

# Or manually specify Python version:
# Python 3.14: CPU-only (for main bot operations)
uv run --python 3.14 trading-bot montecarlo --symbol BTC/USDT --strategy talib_ma

# Python 3.13.4: GPU-accelerated (10-100x faster for Monte Carlo)
uv run --python 3.13.4 trading-bot montecarlo --symbol BTC/USDT --strategy talib_ma

# Specify method and number of simulations
uv run --python 3.13.4 trading-bot montecarlo --symbol BTC/USDT --method shuffle_trades -n 500

# With seed for reproducibility
uv run --python 3.13.4 trading-bot montecarlo --symbol BTC/USDT --seed 42 -n 1000

# Force CPU-only mode (if GPU causes issues)
uv run --python 3.13.4 trading-bot montecarlo --symbol BTC/USDT --strategy talib_ma --force-cpu
```

**Cancellation:**

Monte Carlo simulations can be cancelled gracefully:

- **TUI**: Click the "❌ Cancel Simulation" button during simulation
- **CLI/Terminal**: Press `Ctrl+C` to cancel (works in both TUI and CLI modes)
- **Scripts**: Use the `--force-cpu` flag for CPU-only mode if GPU issues occur

Cancellation is handled gracefully - the simulation will stop at the next checkpoint and clean up properly.

**Python API:**

```python
from trading_bot.backtesting.monte_carlo_engine import MonteCarloEngine
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.strategies.ta_lib_strategy import TALibMovingAverageCrossover
from trading_bot.utils.monte_carlo_viz import plot_monte_carlo_results

# Fetch data
fetcher = CCXTDataFetcher(exchange_id="binance")
data = fetcher.fetch_ohlcv("BTC/USDT", timeframe="1d", limit=365)

# Create strategy
strategy = TALibMovingAverageCrossover(short_period=50, long_period=200)

# Create Monte Carlo engine
mc_engine = MonteCarloEngine(
    initial_capital=10000.0,
    commission=0.001,
    slippage=0.0005,
    n_simulations=1000,
    random_seed=42,  # Optional: for reproducibility
)

# Run simulation
results = mc_engine.run(strategy, data, "BTC/USDT", method="bootstrap")

# Key metrics
print(f"Mean Return: {results['mean_return'] * 100:.2f}%")
print(f"Probability of Profit: {results['probability_of_profit'] * 100:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Value at Risk (95%): {results['var_95'] * 100:.2f}%")
print(f"Worst Drawdown: {results['worst_drawdown'] * 100:.2f}%")

# Save results and create visualizations
mc_engine.save_results(results)
plot_monte_carlo_results(results, show=True)
```

**Key Metrics from Monte Carlo:**

- **Probability of Profit**: Percentage of simulations with positive returns
- **Sharpe Ratio**: Risk-adjusted return (mean / std dev)
- **Value at Risk (VaR)**: 5th percentile return (95% confidence worst case)
- **Conditional VaR (CVaR)**: Average of worst 5% of returns
- **Return Distribution**: Mean, median, std dev, percentiles
- **Drawdown Statistics**: Mean, worst, distribution

**Interpreting Results:**

- Probability of Profit ≥ 70% = High confidence
- Sharpe Ratio ≥ 1.0 = Good risk-adjusted returns
- Worst Drawdown ≤ 20% = Acceptable risk
- Wide return distribution = High uncertainty

## Configuration Management

### Environment Variables (.env)

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

# Backtesting
BACKTEST_ENGINE=custom  # or vectorbt, backtrader

# Logging
LOG_LEVEL=INFO
```

### Configuration Hierarchy

1. Environment file (`.env`) - Exchange credentials, trading parameters
2. `TradingConfig` (Pydantic) - Validates and types all settings
3. Backtest templates - Saved configurations in `~/.trading_bot/templates/`

## Code Style

- **Formatter**: Ruff (Black-compatible)
- **Type Checker**: ty (Astral's fast type checker)
- **Line Length**: 100 characters
- **Target Versions**: Python 3.13.4+ or 3.14+ (dual mode support)
- **Quote Style**: Double quotes
- **Indent Style**: Spaces (4 spaces)

### Import Organization

1. Standard library imports
2. Third-party imports
3. First-party imports (`trading_bot`)
4. Local folder imports

### Type Hints

- Always use type hints for function parameters and return types
- Use `typing` module for complex types
- Use `Optional[T]` for nullable types
- Use `Path` from `pathlib` for file paths

### Documentation

- Use Google-style docstrings
- Include type information in docstrings
- Document complex algorithms and trading logic

## Important Notes

### Data Formats

- **Crypto symbols**: `BTC/USDT` (base/quote format)
- **Stock symbols**: `AAPL` (ticker symbol)
- **Timeframes**: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w` (crypto) or `1d`,
  `1mo`, `1y` (stocks)

### Directory Structure

- `data/` - Cached market data to avoid redundant API calls
- `logs/` - Application logs with timestamps
- `results/` - Backtest result JSON files with metrics
- `examples/` - Reference scripts for common tasks
- `docs/@docs/` - Summary and planning documents

### Running Commands

**Always use `uv`** (not pip) for package management and running scripts:

```bash
# Run CLI commands
uv run python -m trading_bot.cli <command>

# Or with venv activated
.venv\Scripts\activate
uv run -m trading_bot.cli <command>

# Run Python scripts
uv run python script.py
```

### Results Storage

- Backtest results saved to `results/` directory
- Each backtest creates a subdirectory with strategy name and symbol
- Results include: summary.txt, trades.csv, portfolio_history.csv

### Risk Warning

⚠️ This is educational software. Trading involves substantial risk of loss.
Always:

- Test strategies thoroughly with backtesting
- Start with paper trading (sandbox mode)
- Use only capital you can afford to lose
- Understand the risks involved in algorithmic trading

## Key Entry Points

- **CLI**:
  [src/trading_bot/interfaces/cli.py](src/trading_bot/interfaces/cli.py) -
  Command-line interface
- **TUI**:
  [src/trading_bot/interfaces/tui.py](src/trading_bot/interfaces/tui.py) - Text
  User Interface
- **Main Bot**: [src/trading_bot/bot.py](src/trading_bot/bot.py) - Main
  orchestrator
- **Configuration**: [src/trading_bot/config.py](src/trading_bot/config.py) -
  Settings management

## Additional Documentation

- [INSTALLATION.md](INSTALLATION.md) - Detailed installation instructions
- [README.md](README.md) - Project overview and features
- [UPGRADE_SUMMARY.md](docs/@docs/UPGRADE_SUMMARY.md) - Version upgrade details
