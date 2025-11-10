# Changelog

## [0.2.0] - 2025-01-XX

### Added
- **Python 3.14 Support**: Updated to Python 3.14 with free-threading (no GIL) support
- **CCXT Integration**: Added support for 100+ cryptocurrency exchanges via CCXT
- **Backtrader Integration**: Professional backtesting framework integration
- **TA-Lib Support**: Added TA-Lib strategies with 150+ technical indicators
- **Multi-threading Utilities**: Parallel data fetching and backtesting using Python 3.14 free-threading
- **CCXT Broker**: Live cryptocurrency trading via CCXT exchanges
- **CCXT Data Fetcher**: Fetch cryptocurrency market data from any CCXT-supported exchange

### Changed
- **Python Version**: Minimum Python version updated from 3.11 to 3.14
- **NumPy Version**: Updated to 2.3.4+ for Python 3.14 compatibility
- **Dependencies**: Replaced `yfinance` and `ta` with `ccxt`, `backtrader`, and `TA-Lib`
- **Data Fetcher**: Added `CCXTDataFetcher` for cryptocurrency data
- **Backtesting**: Added `BacktraderEngine` as alternative to custom engine
- **Strategies**: Added TA-Lib based strategies (`TALibMovingAverageCrossover`, `TALibMACDStrategy`)

### Performance Improvements
- **True Parallelism**: Leverages Python 3.14 free-threading for 4x performance improvements
- **Parallel Data Fetching**: Fetch multiple symbols simultaneously
- **Parallel Backtesting**: Run multiple backtests concurrently

### Documentation
- Added `INSTALLATION.md` with detailed setup instructions
- Updated `README.md` with Python 3.14 features and CCXT usage
- Added examples for multi-threading and CCXT integration

## [0.1.0] - Initial Release

### Added
- Basic trading bot framework
- yfinance data fetcher for stocks
- Custom backtesting engine
- Moving Average Crossover strategy
- Paper trading broker
- CLI interface

