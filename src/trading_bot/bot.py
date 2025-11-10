"""Main trading bot orchestrator."""

import logging
from typing import Optional

import pandas as pd
from trading_bot.backtesting.engine import BacktestEngine
from trading_bot.broker.base import BaseBroker
from trading_bot.config import TradingConfig, load_config
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.data.fetcher import DataFetcher
from trading_bot.strategies.base import BaseStrategy
from trading_bot.utils.logging import setup_logging

# Optional imports
try:
    from trading_bot.backtesting.backtrader_engine import BacktraderEngine
except ImportError:
    BacktraderEngine = None  # type: ignore[assignment, misc]

try:
    from trading_bot.backtesting.vectorbt_engine import VectorBTEngine
except ImportError:
    VectorBTEngine = None  # type: ignore[assignment, misc]

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator."""

    def __init__(self, config: Optional[TradingConfig] = None):
        """Initialize trading bot.

        Args:
            config: Trading configuration (defaults to loading from .env)
        """
        logger.info("Initializing TradingBot")
        self.config = config or load_config()
        setup_logging(
            log_level=self.config.log_level,
            log_file=self.config.log_file,
        )
        logger.info(f"TradingBot configuration: data_provider={self.config.data_provider}, exchange={self.config.exchange_id}")

        # Initialize data fetcher based on provider
        if self.config.data_provider.lower() == "ccxt":
            logger.debug(f"Initializing CCXTDataFetcher for {self.config.exchange_id}")
            self.data_fetcher = CCXTDataFetcher(
                exchange_id=self.config.exchange_id,
                cache_dir=self.config.data_dir,
                use_cache=self.config.cache_data,
                api_key=self.config.exchange_api_key,
                secret=self.config.exchange_secret,
                sandbox=self.config.exchange_sandbox,
            )
            logger.info(f"CCXTDataFetcher initialized: exchange={self.config.exchange_id}, sandbox={self.config.exchange_sandbox}")
        else:
            logger.debug("Initializing DataFetcher (yfinance)")
            self.data_fetcher = DataFetcher(
                cache_dir=self.config.data_dir,
                use_cache=self.config.cache_data,
            )
            logger.info("DataFetcher initialized")

        self.broker: Optional[BaseBroker] = None
        logger.info("TradingBot initialization complete")

    def set_broker(self, broker: BaseBroker) -> None:
        """Set the broker for live trading.

        Args:
            broker: Broker instance
        """
        logger.info(f"Setting broker: {type(broker).__name__}")
        self.broker = broker
        logger.debug("Broker set successfully")

    def backtest(
        self,
        strategy: BaseStrategy,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: Optional[str] = "1y",
        timeframe: str = "1d",
        limit: int = 1000,
        use_backtrader: Optional[bool] = None,
        data: Optional[pd.DataFrame] = None,  # type: ignore[type-arg]
    ) -> dict:
        """Run a backtest on a strategy.

        Args:
            strategy: Trading strategy to test
            symbol: Trading symbol (e.g., 'BTC/USDT' for crypto, 'AAPL' for stocks)
            start_date: Start date for backtest (YYYY-MM-DD)
            end_date: End date for backtest (YYYY-MM-DD)
            period: Period for data (if dates not provided, for yfinance)
            timeframe: Timeframe for CCXT ('1m', '5m', '1h', '1d', etc.)
            limit: Maximum number of candles to fetch (for CCXT)
            use_backtrader: Use Backtrader engine (None = auto-detect from config)
            data: Pre-fetched data DataFrame (optional, will fetch if not provided)

        Returns:
            Backtest results dictionary
        """
        logger.info(f"Starting backtest for {strategy.name} on {symbol}")

        # Use provided data or fetch if not provided
        if data is not None:
            logger.debug(f"Using pre-fetched data: {len(data)} rows")
        else:
            # Fetch data
            if isinstance(self.data_fetcher, CCXTDataFetcher):
                # CCXT fetcher
                data = self.data_fetcher.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                )
            else:
                # yfinance fetcher
                data = self.data_fetcher.fetch_ohlcv(
                    symbol,
                    start_date=start_date,
                    end_date=end_date,
                    period=period,
                )

        # Choose backtesting engine
        use_bt = use_backtrader
        if use_bt is None:
            engine_name = self.config.backtest_engine.lower()
            if engine_name == "vectorbt":
                try:
                    use_vectorbt = True
                except ImportError:
                    logger.warning(
                        "VectorBT not available, falling back to custom engine. "
                        "Install with: uv add --optional vectorbt"
                    )
                    use_vectorbt = False
            elif engine_name == "backtrader":
                use_bt = True
            else:
                use_vectorbt = False
        else:
            use_vectorbt = False

        if use_vectorbt:
            # Use VectorBT for ultra-fast vectorized backtesting
            if VectorBTEngine is None:
                raise ImportError("VectorBT engine is not available. Install it with: uv add vectorbt")
            try:
                engine = VectorBTEngine(initial_capital=self.config.initial_capital)
                results = engine.run(strategy, data, symbol=symbol)
                result_dir = engine.save_results(results, output_dir=self.config.results_dir)
            except ImportError:
                logger.warning(
                    "VectorBT not available, falling back to custom engine. "
                    "Install with: uv add --optional vectorbt"
                )
                engine = BacktestEngine(initial_capital=self.config.initial_capital)
                results = engine.run(strategy, data, symbol=symbol)
                result_dir = engine.save_results(results, output_dir=self.config.results_dir)
        elif use_bt:
            # Use Backtrader engine
            if BacktraderEngine is None:
                raise ImportError("Backtrader engine is not available. Install it with: uv add backtrader")
            engine = BacktraderEngine(initial_capital=self.config.initial_capital)
            results = engine.run(strategy, data, symbol=symbol)
            result_dir = engine.save_results(results, output_dir=self.config.results_dir)
        else:
            # Use custom engine
            engine = BacktestEngine(initial_capital=self.config.initial_capital)
            results = engine.run(strategy, data, symbol=symbol)
            result_dir = engine.save_results(results, output_dir=self.config.results_dir)

        logger.info(f"Backtest results saved to {result_dir}")

        return results

    def run_live(
        self,
        strategy: BaseStrategy,
        symbol: str,
        check_interval: int = 60,
    ) -> None:
        """Run bot in live trading mode.

        Args:
            strategy: Trading strategy to use
            symbol: Stock symbol to trade
            check_interval: Seconds between strategy checks
        """
        if not self.broker:
            raise ValueError("Broker must be set before running live trading")

        logger.info(f"Starting live trading for {strategy.name} on {symbol}")

        # Get recent data
        data = self.broker.get_market_data(symbol, period="1mo")

        # Generate signals
        data_with_signals = strategy.generate_signals(data)

        # Get latest signal
        latest_signal = data_with_signals["signal"].iloc[-1]
        current_price = data_with_signals["close"].iloc[-1]

        # Get account info
        account = self.broker.get_account()
        positions = self.broker.get_positions()
        current_position = next(
            (p for p in positions if p["symbol"] == symbol),
            None,
        )

        # Execute trades based on signals
        if latest_signal == 1 and not current_position:
            # Buy signal
            position_size = strategy.calculate_position_size(
                current_price,
                account["equity"],
                risk_per_trade=self.config.risk_per_trade,
            )
            if position_size > 0:
                try:
                    self.broker.place_order(
                        symbol=symbol,
                        quantity=position_size,
                        side="buy",
                    )
                    logger.info(f"Placed BUY order for {position_size:.2f} {symbol}")
                except Exception as e:
                    logger.error(f"Failed to place buy order: {e}")

        elif latest_signal == -1 and current_position:
            # Sell signal
            try:
                self.broker.place_order(
                    symbol=symbol,
                    quantity=current_position["quantity"],
                    side="sell",
                )
                logger.info(
                    f"Placed SELL order for {current_position['quantity']:.2f} {symbol}",
                )
            except Exception as e:
                logger.error(f"Failed to place sell order: {e}")

        logger.info(
            f"Signal: {latest_signal}, Price: ${current_price:.2f}, "
            f"Account: ${account['equity']:.2f}",
        )

