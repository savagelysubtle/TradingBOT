"""Integration of walk-forward optimization with existing backtest engines."""

import logging
from typing import Any, Dict

import pandas as pd

from trading_bot.backtesting.parameter_optimizer import SimpleGridOptimizer
from trading_bot.backtesting.walk_forward_backtest import WalkForwardBacktester
from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


def create_wfo_backtest_func(engine, strategy: BaseStrategy):
    """Create a backtest function compatible with WFO optimizer.

    Args:
        engine: Backtest engine instance (BacktestEngine, VectorBTEngine, etc.)
        strategy: Strategy instance

    Returns:
        Function that takes (data, **params) and returns results dict
    """
    def backtest_func(data: pd.DataFrame, **params: Any) -> Dict[str, Any]:
        """Run backtest with given parameters.

        Args:
            data: Historical OHLCV data
            **params: Strategy parameters to override

        Returns:
            Backtest results dictionary
        """
        # Create a temporary strategy instance with overridden parameters
        # or use the existing strategy with params passed to generate_signals
        results = engine.run(
            strategy=strategy,
            data=data,
            symbol="WFO",
        )

        # For WFO, we need to pass params to generate_signals
        # The strategy.generate_signals() now accepts **params
        # But the engine calls it without params, so we need to handle this differently

        # Actually, we'll modify the approach: create a wrapper strategy
        # that uses params when generating signals
        return results

    return backtest_func


class WFOBacktestWrapper:
    """Wrapper to run WFO using existing backtest engines."""

    def __init__(self, engine, strategy: BaseStrategy):
        """Initialize WFO wrapper.

        Args:
            engine: Backtest engine instance
            strategy: Strategy instance
        """
        self.engine = engine
        self.strategy = strategy

    def _create_backtest_func(self):
        """Create backtest function that accepts parameters."""

        def backtest_func(data: pd.DataFrame, **params: Any) -> Dict[str, Any]:
            """Run backtest with parameter overrides.

            This function temporarily modifies strategy parameters, runs backtest, then restores.
            """
            # Temporarily modify the strategy's parameters
            original_params = {}
            for key, value in params.items():
                if hasattr(self.strategy, key):
                    original_params[key] = getattr(self.strategy, key)
                    setattr(self.strategy, key, value)

            try:
                # Run backtest - strategy will use modified parameters via generate_signals
                results = self.engine.run(
                    strategy=self.strategy,
                    data=data,
                    symbol="WFO",
                )
            finally:
                # Restore original parameters
                for key, value in original_params.items():
                    setattr(self.strategy, key, value)

            return results

        return backtest_func

    def run_wfo(
        self,
        data: pd.DataFrame,
        num_periods: int = 5,
        in_sample_pct: float = 0.70,
        out_of_sample_pct: float = 0.30,
        metric: str = "sharpe_ratio",
        **param_ranges: Dict[str, list[float]],
    ) -> Dict[str, Any]:
        """Run walk-forward optimization.

        Args:
            data: Historical data
            num_periods: Number of walk-forward periods
            in_sample_pct: Percentage for in-sample data
            out_of_sample_pct: Percentage for out-of-sample data
            metric: Metric to optimize
            **param_ranges: Parameter ranges (if None, uses strategy.get_parameter_ranges())

        Returns:
            WFO results dictionary
        """
        # Get parameter ranges from strategy if not provided
        if not param_ranges:
            param_ranges = self.strategy.get_parameter_ranges()

        if not param_ranges:
            raise ValueError(
                "No parameter ranges provided and strategy.get_parameter_ranges() returned empty dict"
            )

        # Create backtest function
        backtest_func = self._create_backtest_func()

        # Create optimizer
        optimizer = SimpleGridOptimizer(backtest_func, metric=metric)

        # Create WFO backtester
        wfo = WalkForwardBacktester(backtest_func, optimizer)

        # Run WFO
        results = wfo.run(
            data=data,
            num_periods=num_periods,
            in_sample_pct=in_sample_pct,
            out_of_sample_pct=out_of_sample_pct,
            metric=metric,
            **param_ranges,
        )

        return results

