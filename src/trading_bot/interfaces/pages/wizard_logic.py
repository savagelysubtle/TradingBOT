"""Wizard page business logic for the Trading Bot TUI."""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict

import pandas as pd

from trading_bot.bot import TradingBot
from trading_bot.config import BacktestConfiguration
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.strategies.base import BaseStrategy

if TYPE_CHECKING:
    from trading_bot.interfaces.pages.wizard_page import WizardPage

from trading_bot.strategies.strategy_registry import _strategy_registry

logger = logging.getLogger(__name__)


class WizardLogic:
    """Business logic for wizard operations."""

    def __init__(self, app: "WizardPage"):
        self.app = app

    def sync_config_from_inputs(self) -> None:
        """Synchronize backtest_config from wizard input widgets."""
        logger.debug("Syncing configuration from wizard inputs")
        try:
            limit_value = self.app.query_one("#wizard-limit", "Input").value
            limit = int(limit_value) if limit_value else 365

            start_date_value = self.app.query_one("#wizard-start-date", "Input").value
            end_date_value = self.app.query_one("#wizard-end-date", "Input").value

            exchange_value = str(self.app.query_one("#wizard-exchange", "Select").value)
            symbol_value = self.app.query_one("#wizard-symbol", "Input").value
            timeframe_value = str(self.app.query_one("#wizard-timeframe", "Select").value)
            strategy_value = str(self.app.query_one("#wizard-strategy", "Select").value)
            engine_value = str(self.app.query_one("#wizard-engine", "Select").value)

            logger.debug(
                f"Syncing config: exchange={exchange_value}, symbol={symbol_value}, timeframe={timeframe_value}, strategy={strategy_value}, engine={engine_value}, limit={limit}"
            )

            self.app.backtest_config.update(
                exchange=exchange_value,
                symbol=symbol_value,
                timeframe=timeframe_value,
                limit=limit,
                start_date=start_date_value if start_date_value else None,
                end_date=end_date_value if end_date_value else None,
                strategy_name=strategy_value,
                engine=engine_value,
            )
            logger.debug("Configuration synced successfully")
        except Exception as e:
            logger.exception(f"Failed to sync config: {e}")

    def update_wizard_progress(self) -> None:
        """Update wizard progress indicator based on filled fields."""
        try:
            # Determine current step based on completed fields
            step = 1
            step_text = "Data Configuration"

            # Check if Step 1 is complete (all data fields filled)
            if (
                self.app.backtest_config.symbol
                and "/" in self.app.backtest_config.symbol
                and self.app.backtest_config.limit >= 50
            ):
                step = 2
                step_text = "Strategy Selection"

                # Check if Step 2 is complete (strategy selected)
                if self.app.backtest_config.strategy_name:
                    step = 3
                    step_text = "Ready to Run"

            # Update progress widget
            progress_widget = self.app.query_one("#wizard-progress", "WizardProgressWidget")
            progress_widget.update_progress(step, step_text)
        except Exception as e:
            logger.debug(f"Failed to update wizard progress: {e}")

    def validate_config(self) -> list[str]:
        """Validate configuration and return list of errors."""
        from trading_bot.utils.validation import BacktestValidator

        logger.debug("Validating backtest configuration using BacktestValidator")

        # Get available strategies and exchanges for validation
        available_strategies = []
        for _, internal_name in self.app._get_available_strategies():
            if _strategy_registry.is_available(internal_name):
                available_strategies.append(internal_name)

        available_exchanges = ["binance", "coinbase", "kraken"]  # Common exchanges

        results = BacktestValidator.validate_all(
            symbol=self.app.backtest_config.symbol,
            limit=self.app.backtest_config.limit,
            timeframe=self.app.backtest_config.timeframe,
            start_date=self.app.backtest_config.start_date,
            end_date=self.app.backtest_config.end_date,
            strategy_name=self.app.backtest_config.strategy_name,
            exchange=self.app.backtest_config.exchange,
            available_strategies=available_strategies,
            available_exchanges=available_exchanges,
            strategy_params=self.app.backtest_config.strategy_params,
        )

        # Update validation panel
        try:
            panel = self.app.query_one("#wizard-validation-panel", "ValidationPanel")
            panel.update_results(results)
            logger.debug("Validation panel updated with results")
        except Exception as e:
            logger.exception(f"Failed to update validation panel: {e}")

        # Return errors for backward compatibility
        errors = [r.message for r in results if not r.is_valid and r.severity == "error"]
        if errors:
            logger.warning(f"Configuration validation found {len(errors)} errors: {errors}")
        else:
            logger.debug("Configuration validation passed")
        return errors

    def validate_strategy_params(self, params: dict) -> list[str]:
        """Validate strategy parameters."""
        logger.debug(f"Validating strategy parameters: {params}")
        errors = []

        if self.app.backtest_config.strategy_name in ["ma_crossover", "talib_ma"]:
            long_period = params.get("long_window") or params.get("long_period", 200)
            short_period = params.get("short_window") or params.get("short_period", 50)

            if long_period >= self.app.backtest_config.limit:
                errors.append(
                    f"Long MA period ({long_period}) is too large for {self.app.backtest_config.limit} candles. "
                    f"Need at least {long_period + 50} candles for reliable signals."
                )
            elif long_period > self.app.backtest_config.limit * 0.5:
                self.app.notify(
                    f"⚠ Long MA period ({long_period}) is large relative to data ({self.app.backtest_config.limit} candles). "
                    f"Consider using shorter periods (e.g., {max(20, int(self.app.backtest_config.limit * 0.1))}/{max(50, int(self.app.backtest_config.limit * 0.3))}) "
                    f"or more candles ({long_period + 100}+)",
                    severity="warning",
                )

            if short_period >= long_period:
                errors.append(
                    f"Short MA period ({short_period}) must be less than long MA period ({long_period})"
                )

        if errors:
            logger.warning(f"Strategy parameter validation found {len(errors)} errors: {errors}")
        else:
            logger.debug("Strategy parameter validation passed")
        return errors

    def prepare_fetch_kwargs(self) -> dict:
        """Prepare fetch kwargs for data fetching."""
        logger.debug("Preparing fetch kwargs")
        fetch_kwargs: dict[str, str | int] = {
            "symbol": self.app.backtest_config.symbol,
            "timeframe": self.app.backtest_config.timeframe,
        }

        if self.app.backtest_config.start_date and self.app.backtest_config.end_date:
            fetch_kwargs["start_date"] = self.app.backtest_config.start_date
            fetch_kwargs["end_date"] = self.app.backtest_config.end_date
            start = datetime.strptime(self.app.backtest_config.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.app.backtest_config.end_date, "%Y-%m-%d")
            days = (end - start).days

            if self.app.backtest_config.timeframe == "1d":
                calculated_limit = int(days * 1.2)
            elif self.app.backtest_config.timeframe == "1h":
                calculated_limit = int(days * 24 * 1.2)
            elif self.app.backtest_config.timeframe == "4h":
                calculated_limit = int(days * 6 * 1.2)
            elif self.app.backtest_config.timeframe == "15m":
                calculated_limit = int(days * 96 * 1.2)
            elif self.app.backtest_config.timeframe == "5m":
                calculated_limit = int(days * 288 * 1.2)
            elif self.app.backtest_config.timeframe == "1m":
                calculated_limit = int(days * 1440 * 1.2)
            else:
                calculated_limit = int(days * 1.2)
            fetch_kwargs["limit"] = calculated_limit
            logger.debug(
                f"Calculated limit from date range: {calculated_limit} candles ({days} days)"
            )
        else:
            fetch_kwargs["limit"] = self.app.backtest_config.limit
            logger.debug(f"Using configured limit: {self.app.backtest_config.limit}")

        logger.debug(f"Fetch kwargs prepared: {fetch_kwargs}")
        return fetch_kwargs

    def prepare_backtest_kwargs(
        self,
        strategy: BaseStrategy,
        use_backtrader: bool,
        data: pd.DataFrame | None = None,
    ) -> dict:
        """Prepare backtest kwargs.

        Args:
            strategy: The trading strategy
            use_backtrader: Whether to use backtrader engine
            data: Pre-fetched data DataFrame (optional)
        """
        logger.debug("Preparing backtest kwargs")
        backtest_kwargs = {
            "strategy": strategy,
            "symbol": self.app.backtest_config.symbol,
            "timeframe": self.app.backtest_config.timeframe,
        }

        # Include pre-fetched data if provided (avoids re-fetching with stale cache)
        if data is not None:
            backtest_kwargs["data"] = data
            logger.debug(f"Including pre-fetched data in backtest kwargs: {len(data)} rows")

        if self.app.backtest_config.start_date and self.app.backtest_config.end_date:
            backtest_kwargs["start_date"] = self.app.backtest_config.start_date
            backtest_kwargs["end_date"] = self.app.backtest_config.end_date
            start = datetime.strptime(self.app.backtest_config.start_date, "%Y-%m-%d")
            end = datetime.strptime(self.app.backtest_config.end_date, "%Y-%m-%d")
            days = (end - start).days
            if self.app.backtest_config.timeframe == "1d":
                backtest_kwargs["limit"] = int(days * 1.2)
            elif self.app.backtest_config.timeframe == "1h":
                backtest_kwargs["limit"] = int(days * 24 * 1.2)
            elif self.app.backtest_config.timeframe == "4h":
                backtest_kwargs["limit"] = int(days * 6 * 1.2)
            elif self.app.backtest_config.timeframe == "15m":
                backtest_kwargs["limit"] = int(days * 96 * 1.2)
            elif self.app.backtest_config.timeframe == "5m":
                backtest_kwargs["limit"] = int(days * 288 * 1.2)
            elif self.app.backtest_config.timeframe == "1m":
                backtest_kwargs["limit"] = int(days * 1440 * 1.2)
            else:
                backtest_kwargs["limit"] = int(days * 1.2)
        else:
            backtest_kwargs["limit"] = self.app.backtest_config.limit

        if self.app.backtest_config.engine != "vectorbt":
            backtest_kwargs["use_backtrader"] = use_backtrader

        logger.debug(f"Backtest kwargs prepared: {list(backtest_kwargs.keys())}")
        return backtest_kwargs

    def create_strategy(self, config: BacktestConfiguration) -> BaseStrategy | None:
        """Create strategy instance from configuration using dynamic registry.

        Args:
            config: Backtest configuration with strategy name and parameters

        Returns:
            Strategy instance or None if strategy not found/available
        """
        strategy_name = config.strategy_name
        params = config.strategy_params
        logger.debug(f"Creating strategy: {strategy_name} with params: {params}")

        # Get strategy class from registry
        strategy_class = _strategy_registry.get_strategy_class(strategy_name)
        if strategy_class is None:
            logger.error(f"Strategy '{strategy_name}' not found or not available")
            return None
        logger.debug(f"Found strategy class: {strategy_class.__name__}")

        # Create strategy instance with parameters
        # Each strategy has different parameter names, so we need to map them
        # Note: Strategies handle the 'name' parameter internally via super().__init__()
        try:
            if strategy_name == "ma_crossover":
                return strategy_class(  # type: ignore[call-arg]
                    short_window=int(params.get("short_window", 50)),
                    long_window=int(params.get("long_window", 200)),
                    use_rsi=bool(params.get("use_rsi", False)),
                )
            elif strategy_name == "talib_ma":
                return strategy_class(  # type: ignore[call-arg]
                    short_period=int(params.get("short_period", 50)),
                    long_period=int(params.get("long_period", 200)),
                )
            elif strategy_name == "talib_macd":
                return strategy_class()  # type: ignore[call-arg]
            elif strategy_name == "supertrend":
                return strategy_class(  # type: ignore[call-arg]
                    period=int(params.get("period", 10)),
                    multiplier=float(params.get("multiplier", 3.0)),
                )
            elif strategy_name == "bollinger":
                return strategy_class(  # type: ignore[call-arg]
                    period=int(params.get("period", 20)),
                    std_dev=float(params.get("std_dev", 2.0)),
                )
            elif strategy_name == "ichimoku":
                return strategy_class()  # type: ignore[call-arg]
            elif strategy_name == "ml_randomforest":
                return strategy_class(lookback=int(params.get("lookback", 50)))  # type: ignore[call-arg]
            elif strategy_name == "stop_hunt":
                return strategy_class(  # type: ignore[call-arg]
                    support_lookback=int(params.get("support_lookback", 20)),
                    cluster_min_factors=int(params.get("cluster_min_factors", 3)),
                    entry_distance_pct=float(params.get("entry_distance_pct", 0.5)),
                    volume_spike_multiplier=float(params.get("volume_spike_multiplier", 2.0)),
                )
            else:
                # Try to create with params as kwargs (for strategies with standard init)
                # Filter out None values and convert types appropriately
                filtered_params: dict[str, Any] = {}
                for k, v in params.items():
                    if v is not None:
                        # Try to preserve type, but convert if needed
                        filtered_params[k] = v
                logger.debug(f"Creating strategy with filtered params: {filtered_params}")
                return strategy_class(**filtered_params)  # type: ignore[call-arg]
        except Exception as e:
            logger.exception(f"Failed to create strategy '{strategy_name}': {e}")
            return None

