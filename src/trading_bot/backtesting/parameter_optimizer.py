"""Parameter optimizer for walk-forward optimization using grid search."""

import logging
from itertools import product
from typing import Any, Callable, Dict, List

import numpy as np

logger = logging.getLogger(__name__)


class SimpleGridOptimizer:
    """Exhaustive grid search optimizer for strategy parameters."""

    def __init__(self, backtest_func: Callable, metric: str = "sharpe_ratio"):
        """Initialize optimizer.

        Args:
            backtest_func: Function that takes params dict and returns results dict
            metric: Metric to optimize ('sharpe_ratio', 'total_return', 'profit_factor')
        """
        self.backtest_func = backtest_func
        self.metric = metric
        self.results: List[Dict[str, Any]] = []

    def optimize(self, data, **param_ranges: Dict[str, List[float]]) -> Dict[str, float]:
        """Run grid search optimization.

        Args:
            data: Historical data to backtest on
            **param_ranges: Parameter name -> list of values
                           e.g., short_ma=[5, 10, 15], long_ma=[50, 100, 150]

        Returns:
            Best parameters as dict

        Example:
            >>> optimizer = SimpleGridOptimizer(backtest_func=my_backtest)
            >>> best = optimizer.optimize(
            ...     data,
            ...     short_ma=[10, 20, 30],
            ...     long_ma=[50, 100, 150],
            ...     stop_loss=[0.02, 0.05, 0.10]
            ... )
        """
        # Generate all parameter combinations
        param_names = list(param_ranges.keys())
        param_lists = list(param_ranges.values())

        combinations = list(product(*param_lists))
        total = len(combinations)

        logger.info(f"Grid Search: {total} combinations")

        best_params = None
        best_score = -np.inf

        for idx, combo in enumerate(combinations, 1):
            # Build parameter dict
            params = dict(zip(param_names, combo))

            # Run backtest
            try:
                backtest_results = self.backtest_func(data, **params)
                score = backtest_results.get(self.metric, -np.inf)
            except Exception as e:
                logger.debug(f"Backtest failed for params {params}: {e}")
                score = -np.inf

            # Store result
            self.results.append(
                {
                    "params": params,
                    "score": score,
                    "results": backtest_results,
                }
            )

            # Track best
            if score > best_score:
                best_score = score
                best_params = params

            # Progress logging
            if idx % max(1, total // 10) == 0:
                logger.info(f"  {idx}/{total} - Best Score: {best_score:.4f}")

        logger.info(f"Best Parameters: {best_params}")
        logger.info(f"Best Score: {best_score:.4f}")

        return best_params or {}

    def get_top_params(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return top N parameter combinations.

        Args:
            n: Number of top results to return

        Returns:
            List of result dictionaries sorted by score (descending)
        """
        sorted_results = sorted(self.results, key=lambda x: x["score"], reverse=True)
        return sorted_results[:n]


