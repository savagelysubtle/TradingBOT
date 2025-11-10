"""Walk-forward optimization backtester for strategy validation."""

import logging
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd

from trading_bot.backtesting.parameter_optimizer import SimpleGridOptimizer
from trading_bot.backtesting.walk_forward_minimal import (
    calculate_wfe,
    split_walk_forward,
    wfe_status,
)

logger = logging.getLogger(__name__)


class WalkForwardBacktester:
    """Perform walk-forward optimization on a trading strategy."""

    def __init__(self, backtest_func: Callable, optimizer: SimpleGridOptimizer | None = None):
        """Initialize WFO backtester.

        Args:
            backtest_func: Function to run backtest with given parameters
            optimizer: Optimizer instance (if None, creates SimpleGridOptimizer)
        """
        self.backtest_func = backtest_func
        self.optimizer = optimizer

    def run(
        self,
        data: pd.DataFrame,
        num_periods: int = 5,
        in_sample_pct: float = 0.70,
        out_of_sample_pct: float = 0.30,
        metric: str = "sharpe_ratio",
        **param_ranges: Dict[str, List[float]],
    ) -> Dict[str, Any]:
        """Execute complete walk-forward backtest.

        Args:
            data: Historical data
            num_periods: Number of walk-forward periods
            in_sample_pct: Percentage for in-sample (training) data
            out_of_sample_pct: Percentage for out-of-sample (testing) data
            metric: Metric to optimize ('sharpe_ratio', 'total_return', 'profit_factor')
            **param_ranges: Parameter ranges for optimization

        Returns:
            Dictionary with WFO results including WFE and period-by-period breakdown
        """
        # Split data into walk-forward periods
        splits = split_walk_forward(
            data,
            in_sample_pct=in_sample_pct,
            out_of_sample_pct=out_of_sample_pct,
            num_periods=num_periods,
        )

        results = {
            "periods": [],
            "in_sample_returns": [],
            "out_of_sample_returns": [],
            "optimal_params_history": [],
            "in_sample_metrics": [],
            "out_of_sample_metrics": [],
        }

        logger.info(f"\n{'='*60}")
        logger.info(f"WALK-FORWARD OPTIMIZATION: {len(splits)} PERIODS")
        logger.info(f"{'='*60}\n")

        for period_num, (is_data, oos_data) in enumerate(splits, 1):
            logger.info(f"PERIOD {period_num}/{len(splits)}")
            logger.info(f"{'─'*60}")
            logger.info(
                f"In-sample:     {len(is_data)} bars ({is_data.index[0]} to {is_data.index[-1]})"
            )
            logger.info(
                f"Out-of-sample: {len(oos_data)} bars ({oos_data.index[0]} to {oos_data.index[-1]})"
            )

            # Step 1: Optimize on in-sample data
            logger.info("\nOptimizing parameters...")
            if self.optimizer is None:
                optimizer = SimpleGridOptimizer(self.backtest_func, metric=metric)
            else:
                optimizer = self.optimizer
                optimizer.metric = metric

            optimizer.results = []  # Reset
            best_params = optimizer.optimize(is_data, **param_ranges)

            # Get in-sample results (best result)
            if optimizer.results:
                best_result = max(optimizer.results, key=lambda x: x["score"])
                is_results = best_result["results"]
            else:
                # Fallback: run backtest with best params
                is_results = self.backtest_func(is_data, **best_params)

            is_return = is_results.get("total_return", 0.0)

            # Step 2: Test on out-of-sample data
            logger.info("Testing on out-of-sample...")
            oos_results = self.backtest_func(oos_data, **best_params)
            oos_return = oos_results.get("total_return", 0.0)

            # Store results
            results["periods"].append(
                {
                    "period": period_num,
                    "is_start": str(is_data.index[0]),
                    "is_end": str(is_data.index[-1]),
                    "oos_start": str(oos_data.index[0]),
                    "oos_end": str(oos_data.index[-1]),
                }
            )

            results["in_sample_returns"].append(is_return)
            results["out_of_sample_returns"].append(oos_return)
            results["optimal_params_history"].append(best_params)
            results["in_sample_metrics"].append(is_results)
            results["out_of_sample_metrics"].append(oos_results)

            # Calculate WFE for this period
            period_wfe = calculate_wfe(is_return, oos_return)

            logger.info("\nResults:")
            logger.info(f"  In-sample:  {is_return:+.2%}")
            logger.info(f"  Out-of-sample: {oos_return:+.2%}")
            logger.info(f"  WFE: {period_wfe:.1%}\n")

        # Calculate overall metrics
        results["overall"] = self._calculate_overall_metrics(results)

        return results

    def _calculate_overall_metrics(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate aggregate WFO metrics.

        Args:
            results: WFO results dictionary

        Returns:
            Dictionary with overall metrics including WFE
        """
        is_returns = results["in_sample_returns"]
        oos_returns = results["out_of_sample_returns"]

        avg_is = np.mean(is_returns) if is_returns else 0.0
        avg_oos = np.mean(oos_returns) if oos_returns else 0.0
        wfe = calculate_wfe(avg_is, avg_oos)

        # Calculate parameter stability (how much parameters change between periods)
        param_changes = []
        optimal_params = results["optimal_params_history"]
        for i in range(1, len(optimal_params)):
            params_prev = optimal_params[i - 1]
            params_curr = optimal_params[i]

            # Count how many parameters changed
            changes = sum(
                1
                for k in params_prev
                if params_prev.get(k) != params_curr.get(k)
            )
            param_changes.append(changes)

        avg_param_changes = np.mean(param_changes) if param_changes else 0.0

        return {
            "avg_in_sample_return": avg_is,
            "avg_out_of_sample_return": avg_oos,
            "wfe": wfe,
            "num_periods": len(is_returns),
            "status": wfe_status(wfe),
            "avg_parameter_changes": avg_param_changes,
        }


