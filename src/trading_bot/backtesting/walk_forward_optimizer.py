"""Walk-forward optimization for strategy parameter tuning."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable

import numpy as np
import pandas as pd

from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """Walk-forward optimization for systematic parameter tuning."""

    def __init__(
        self,
        initial_training_window: int = 365,  # days
        validation_window: int = 90,  # days
        step_size: int = 30,  # days
        min_samples: int = 100,
    ):
        """Initialize walk-forward optimizer.

        Args:
            initial_training_window: Initial training period in days
            validation_window: Validation period in days
            step_size: How many days to advance each step
            min_samples: Minimum samples required for optimization
        """
        self.initial_training_window = initial_training_window
        self.validation_window = validation_window
        self.step_size = step_size
        self.min_samples = min_samples

    def optimize(
        self,
        strategy_class: type[BaseStrategy],
        data: pd.DataFrame,
        parameter_ranges: dict[str, list[float]],
        metric: str = "sharpe_ratio",
        n_trials: int = 50,
    ) -> dict[str, Any]:
        """Run walk-forward optimization.

        Args:
            strategy_class: Strategy class to optimize
            data: Historical data for optimization
            parameter_ranges: Dictionary of parameter ranges to test
            metric: Metric to optimize (sharpe_ratio, total_return, max_drawdown, etc.)
            n_trials: Number of parameter combinations to test per window

        Returns:
            Dictionary with optimization results and best parameters
        """
        logger.info("Starting walk-forward optimization")

        # Ensure data has datetime index
        if not isinstance(data.index, pd.DatetimeIndex):
            data.index = pd.to_datetime(data.index)

        # Generate optimization windows
        windows = self._generate_windows(data)

        if len(windows) < 2:
            logger.warning("Insufficient data for walk-forward optimization")
            return {"error": "insufficient_data"}

        results = []
        best_params_overall = None
        best_score_overall = float('-inf') if metric in ['sharpe_ratio', 'total_return'] else float('inf')

        for i, (train_start, train_end, val_start, val_end) in enumerate(windows):
            logger.info(f"Optimizing window {i+1}/{len(windows)}: {train_start.date()} to {val_end.date()}")

            # Get data for this window
            train_data = data.loc[train_start:train_end]
            val_data = data.loc[val_start:val_end]

            if len(train_data) < self.min_samples:
                logger.warning(f"Insufficient training data in window {i+1}, skipping")
                continue

            # Optimize parameters for this window
            best_params, best_score = self._optimize_window(
                strategy_class, train_data, val_data, parameter_ranges, metric, n_trials
            )

            results.append({
                'window': i + 1,
                'train_start': train_start,
                'train_end': train_end,
                'val_start': val_start,
                'val_end': val_end,
                'best_params': best_params,
                'best_score': best_score,
            })

            # Track overall best parameters (weighted by recency)
            weight = (i + 1) / len(windows)  # More recent windows have higher weight
            if self._is_better_score(best_score, best_score_overall, metric):
                best_params_overall = best_params
                best_score_overall = best_score

        return {
            'optimization_results': results,
            'best_params_overall': best_params_overall,
            'best_score_overall': best_score_overall,
            'total_windows': len(results),
            'metric': metric,
        }

    def _generate_windows(self, data: pd.DataFrame) -> list[tuple]:
        """Generate training/validation windows."""
        windows = []
        start_date = data.index[0]
        end_date = data.index[-1]

        current_train_end = start_date + timedelta(days=self.initial_training_window)

        while current_train_end + timedelta(days=self.validation_window) <= end_date:
            train_start = start_date
            train_end = current_train_end
            val_start = current_train_end + timedelta(days=1)
            val_end = val_start + timedelta(days=self.validation_window - 1)

            windows.append((train_start, train_end, val_start, val_end))

            # Advance to next window
            current_train_end += timedelta(days=self.step_size)

        return windows

    def _optimize_window(
        self,
        strategy_class: type[BaseStrategy],
        train_data: pd.DataFrame,
        val_data: pd.DataFrame,
        parameter_ranges: dict[str, list[float]],
        metric: str,
        n_trials: int,
    ) -> tuple[dict[str, Any], float]:
        """Optimize parameters for a single window."""
        best_params = {}
        best_score = float('-inf') if metric in ['sharpe_ratio', 'total_return'] else float('inf')

        # Generate parameter combinations
        param_combinations = self._generate_param_combinations(parameter_ranges, n_trials)

        for params in param_combinations:
            try:
                # Create strategy with these parameters
                strategy = strategy_class(**params)

                # Run backtest on training data
                train_results = self._evaluate_strategy(strategy, train_data, metric)

                # If training performance is good, validate on validation data
                if self._meets_minimum_criteria(train_results, metric):
                    val_results = self._evaluate_strategy(strategy, val_data, metric)

                    # Use validation score for parameter selection
                    score = val_results[metric]

                    if self._is_better_score(score, best_score, metric):
                        best_score = score
                        best_params = params.copy()

            except Exception as e:
                logger.debug(f"Parameter combination failed: {params}, error: {e}")
                continue

        return best_params, best_score

    def _generate_param_combinations(
        self,
        parameter_ranges: dict[str, list[float]],
        n_trials: int
    ) -> list[dict[str, Any]]:
        """Generate parameter combinations for optimization."""
        combinations = []

        for _ in range(n_trials):
            params = {}
            for param_name, param_values in parameter_ranges.items():
                # Random selection from parameter range
                params[param_name] = np.random.choice(param_values)
            combinations.append(params)

        return combinations

    def _evaluate_strategy(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        metric: str
    ) -> dict[str, Any]:
        """Evaluate strategy performance on given data."""
        # This is a simplified evaluation - in practice you'd use the full backtesting engine
        signals = strategy.generate_signals(data)

        # Calculate basic metrics (simplified version)
        returns = []
        position = 0
        entry_price = 0

        for idx, row in signals.iterrows():
            if row['signal'] == 1 and position == 0:  # Buy signal
                position = 1
                entry_price = row['close']
            elif row['signal'] == -1 and position == 1:  # Sell signal
                if entry_price > 0:
                    ret = (row['close'] - entry_price) / entry_price
                    returns.append(ret)
                position = 0
                entry_price = 0

        if not returns:
            return {metric: 0.0}

        returns = np.array(returns)

        if metric == 'total_return':
            score = np.sum(returns)
        elif metric == 'sharpe_ratio':
            if len(returns) > 1:
                score = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            else:
                score = 0
        elif metric == 'max_drawdown':
            cumulative = np.cumsum(returns)
            peak = np.maximum.accumulate(cumulative)
            drawdown = peak - cumulative
            score = np.max(drawdown) if len(drawdown) > 0 else 0
        else:
            score = np.mean(returns)  # Default to average return

        return {metric: score}

    def _meets_minimum_criteria(self, results: dict[str, Any], metric: str) -> bool:
        """Check if results meet minimum criteria for further evaluation."""
        # Simple check - can be made more sophisticated
        score = results.get(metric, 0)
        return score > -0.5  # Avoid completely terrible strategies

    def _is_better_score(self, new_score: float, best_score: float, metric: str) -> bool:
        """Check if new score is better than current best."""
        if metric in ['sharpe_ratio', 'total_return']:
            return new_score > best_score
        else:  # For metrics like max_drawdown (lower is better)
            return new_score < best_score
