"""Monte Carlo simulation engine for trading strategies with GPU acceleration."""

import logging
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# Try to import CuPy for GPU acceleration, fallback to NumPy
# The code will automatically fall back to NumPy if CuPy is not available
# Supports CUDA 13.x (cupy-cuda13x), 12.x (cupy-cuda12x), or 11.x (cupy-cuda11x)
try:
    import cupy as cp

    CUPY_AVAILABLE = True
    logger_gpu = logging.getLogger(__name__)
    # Try to detect CUDA version
    try:
        cuda_version = cp.cuda.runtime.runtimeGetVersion()
        major_version = cuda_version // 1000
        minor_version = (cuda_version % 1000) // 10
        logger_gpu.info(
            f"CuPy available - using GPU acceleration for Monte Carlo simulations "
            f"(CUDA {major_version}.{minor_version})"
        )
    except Exception:
        logger_gpu.info("CuPy available - using GPU acceleration for Monte Carlo simulations")
except ImportError:
    cp = np  # Fallback to NumPy if CuPy not available
    CUPY_AVAILABLE = False
    logger_gpu = logging.getLogger(__name__)
    logger_gpu.warning(
        "CuPy not available - using CPU (NumPy) for Monte Carlo simulations. "
        "Install with: uv add cupy-cuda13x"
    )

from trading_bot.backtesting.engine import BacktestEngine
from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class MonteCarloEngine:
    """Monte Carlo simulation engine for evaluating strategy robustness."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
        n_simulations: int = 1000,
        random_seed: int | None = None,
    ):
        """Initialize Monte Carlo engine.

        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade (0.001 = 0.1%)
            slippage: Slippage rate per trade (0.0005 = 0.05%)
            n_simulations: Number of Monte Carlo simulations to run
            random_seed: Random seed for reproducibility
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.n_simulations = n_simulations
        self.random_seed = random_seed

        if random_seed is not None:
            if CUPY_AVAILABLE:
                cp.random.seed(random_seed)
            else:
                np.random.seed(random_seed)

        # Base backtest engine
        self.backtest_engine = BacktestEngine(
            initial_capital=initial_capital,
            commission=commission,
            slippage=slippage,
        )

    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str = "UNKNOWN",
        method: str = "bootstrap",
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict:
        """Run Monte Carlo simulation on a strategy.

        Args:
            strategy: Trading strategy to test
            data: Historical OHLCV data
            symbol: Symbol being traded
            method: Simulation method ('bootstrap', 'shuffle_trades', 'randomize_returns')
            progress_callback: Optional callback function called with completion count during simulation

        Returns:
            Dictionary with Monte Carlo simulation results
        """
        logger.info(
            f"Running Monte Carlo simulation for {strategy.name} on {symbol} "
            f"({self.n_simulations} simulations, method={method})"
        )

        if method == "bootstrap":
            results = self._run_bootstrap(strategy, data, symbol, progress_callback)
        elif method == "shuffle_trades":
            results = self._run_shuffle_trades(strategy, data, symbol, progress_callback)
        elif method == "randomize_returns":
            results = self._run_randomize_returns(strategy, data, symbol, progress_callback)
        else:
            raise ValueError(
                f"Unknown method: {method}. Use 'bootstrap', 'shuffle_trades', or 'randomize_returns'"
            )

        return results

    def _run_bootstrap(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict:
        """Bootstrap resampling: randomly sample from historical data with replacement.

        This tests how the strategy performs on different sequences of historical data.
        """
        logger.info("Running bootstrap resampling Monte Carlo simulation")

        simulation_results = []
        data_length = len(data)

        for i in range(self.n_simulations):
            if (i + 1) % 100 == 0:
                logger.info(f"Simulation {i + 1}/{self.n_simulations}")

            # Randomly sample indices with replacement (GPU-accelerated if available)
            if CUPY_AVAILABLE:
                sampled_indices_gpu = cp.random.choice(data_length, size=data_length, replace=True)
                sampled_indices = cp.asnumpy(
                    sampled_indices_gpu
                )  # Convert back to NumPy for pandas
            else:
                sampled_indices = np.random.choice(data_length, size=data_length, replace=True)
            sampled_data = data.iloc[sampled_indices].copy()

            # Reset index to maintain chronological order
            sampled_data.reset_index(drop=True, inplace=True)

            # Run backtest on sampled data
            result = self.backtest_engine.run(strategy, sampled_data, symbol)
            simulation_results.append(result)

            # Call progress callback if provided
            if progress_callback is not None:
                progress_callback(i + 1)

        return self._aggregate_results(simulation_results, symbol, strategy.name, "bootstrap")

    def _run_shuffle_trades(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict:
        """Shuffle trade sequence: randomize the order of trades.

        This tests if the sequence of trades affects the overall performance.
        """
        logger.info("Running trade shuffle Monte Carlo simulation")

        # First run the base backtest to get trades
        base_result = self.backtest_engine.run(strategy, data, symbol)
        trades = base_result["trades"]

        if len(trades) == 0:
            logger.warning("No trades generated, returning base result")
            return self._aggregate_results([base_result], symbol, strategy.name, "shuffle_trades")

        simulation_results = []

        for i in range(self.n_simulations):
            if (i + 1) % 100 == 0:
                logger.info(f"Simulation {i + 1}/{self.n_simulations}")

            # Shuffle trades and recalculate portfolio value (GPU-accelerated if available)
            shuffled_result = self._simulate_shuffled_trades(
                trades,
                self.initial_capital,
            )
            simulation_results.append(shuffled_result)

            # Call progress callback if provided
            if progress_callback is not None:
                progress_callback(i + 1)

        return self._aggregate_results(
            simulation_results,
            symbol,
            strategy.name,
            "shuffle_trades",
        )

    def _run_randomize_returns(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict:
        """Randomize returns: add random noise to historical returns.

        This tests strategy robustness to market volatility variations.
        """
        logger.info("Running randomized returns Monte Carlo simulation")

        simulation_results = []

        # Calculate historical returns
        returns = data["close"].pct_change().dropna()
        mean_return = returns.mean()
        std_return = returns.std()

        for i in range(self.n_simulations):
            if (i + 1) % 100 == 0:
                logger.info(f"Simulation {i + 1}/{self.n_simulations}")

            # Create synthetic price series (GPU-accelerated if available)
            if CUPY_AVAILABLE:
                synthetic_returns_gpu = cp.random.normal(mean_return, std_return, len(data))
                synthetic_returns = cp.asnumpy(synthetic_returns_gpu)  # Convert to NumPy for pandas
            else:
                synthetic_returns = np.random.normal(mean_return, std_return, len(data))
            synthetic_prices = data["close"].iloc[0] * (1 + synthetic_returns).cumprod()

            # Create synthetic OHLCV data
            synthetic_data = data.copy()
            synthetic_data["close"] = synthetic_prices

            # Adjust OHLC to be consistent with close
            price_ratio = synthetic_data["close"] / data["close"]
            synthetic_data["open"] = data["open"] * price_ratio
            synthetic_data["high"] = data["high"] * price_ratio
            synthetic_data["low"] = data["low"] * price_ratio

            # Run backtest on synthetic data
            result = self.backtest_engine.run(strategy, synthetic_data, symbol)
            simulation_results.append(result)

            # Call progress callback if provided
            if progress_callback is not None:
                progress_callback(i + 1)

        return self._aggregate_results(
            simulation_results,
            symbol,
            strategy.name,
            "randomize_returns",
        )

    def _simulate_shuffled_trades(
        self,
        trades: list[dict],
        initial_capital: float,
    ) -> dict:
        """Simulate portfolio performance with shuffled trades."""
        # Separate buy and sell trades
        buy_trades = [t for t in trades if t["type"] == "BUY"]
        sell_trades = [t for t in trades if t["type"] == "SELL"]

        # Shuffle sell trades (preserving buy-sell pairing logic)
        # Note: Python list shuffle doesn't benefit from GPU, but we keep it here for consistency
        import random

        random.shuffle(sell_trades)

        # Calculate metrics from shuffled trades
        total_pnl = sum(t.get("pnl", 0) for t in sell_trades)
        final_value = initial_capital + total_pnl

        total_return = (final_value - initial_capital) / initial_capital

        winning_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in sell_trades if t.get("pnl", 0) < 0]

        win_rate = len(winning_trades) / len(sell_trades) if sell_trades else 0.0

        avg_win = (
            sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        )
        avg_loss = (
            sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        )

        # Calculate drawdown from shuffled trades
        portfolio_values = [initial_capital]
        for trade in sell_trades:
            portfolio_values.append(portfolio_values[-1] + trade.get("pnl", 0))

        max_value = portfolio_values[0]
        max_drawdown = 0.0
        for value in portfolio_values:
            max_value = max(max_value, value)
            drawdown = (value - max_value) / max_value
            max_drawdown = min(max_drawdown, drawdown)

        return {
            "final_value": final_value,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "total_trades": len(buy_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "win_rate_pct": win_rate * 100,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": abs(avg_win / avg_loss) if avg_loss != 0 else 0.0,
            "max_drawdown": max_drawdown,
            "max_drawdown_pct": max_drawdown * 100,
        }

    def _aggregate_results(
        self,
        simulation_results: list[dict],
        symbol: str,
        strategy_name: str,
        method: str,
    ) -> dict:
        """Aggregate Monte Carlo simulation results."""
        # Extract key metrics and convert to GPU arrays if available
        returns = [r["total_return"] for r in simulation_results]
        final_values = [r["final_value"] for r in simulation_results]
        max_drawdowns = [r["max_drawdown"] for r in simulation_results]
        win_rates = [r["win_rate"] for r in simulation_results]
        profit_factors = [r["profit_factor"] for r in simulation_results]

        # Convert to GPU arrays for faster statistical calculations (if CuPy available)
        if CUPY_AVAILABLE:
            returns_gpu = cp.asarray(returns)
            final_values_gpu = cp.asarray(final_values)
            max_drawdowns_gpu = cp.asarray(max_drawdowns)
            win_rates_gpu = cp.asarray(win_rates)
            profit_factors_gpu = cp.asarray(profit_factors)

            # Calculate statistics on GPU
            mean_return = float(cp.mean(returns_gpu))
            median_return = float(cp.median(returns_gpu))
            std_return = float(cp.std(returns_gpu))
            min_return = float(cp.min(returns_gpu))
            max_return = float(cp.max(returns_gpu))
            percentile_5 = float(cp.percentile(returns_gpu, 5))
            percentile_25 = float(cp.percentile(returns_gpu, 25))
            percentile_75 = float(cp.percentile(returns_gpu, 75))
            percentile_95 = float(cp.percentile(returns_gpu, 95))

            mean_final_value = float(cp.mean(final_values_gpu))
            median_final_value = float(cp.median(final_values_gpu))
            std_final_value = float(cp.std(final_values_gpu))
            min_final_value = float(cp.min(final_values_gpu))
            max_final_value = float(cp.max(final_values_gpu))

            mean_max_drawdown = float(cp.mean(max_drawdowns_gpu))
            median_max_drawdown = float(cp.median(max_drawdowns_gpu))
            worst_drawdown = float(cp.min(max_drawdowns_gpu))
            best_drawdown = float(cp.max(max_drawdowns_gpu))

            mean_win_rate = float(cp.mean(win_rates_gpu))
            median_win_rate = float(cp.median(win_rates_gpu))

            mean_profit_factor = float(cp.mean(profit_factors_gpu))
            median_profit_factor = float(cp.median(profit_factors_gpu))

            var_95 = float(cp.percentile(returns_gpu, 5))
            # Conditional VaR: mean of returns <= VaR
            cvar_mask = returns_gpu <= var_95
            cvar_95 = float(cp.mean(returns_gpu[cvar_mask])) if cp.any(cvar_mask) else var_95

            sharpe_ratio = float(mean_return / std_return) if std_return != 0 else 0.0
        else:
            # CPU fallback using NumPy
            mean_return = np.mean(returns)
            median_return = np.median(returns)
            std_return = np.std(returns)
            min_return = np.min(returns)
            max_return = np.max(returns)
            percentile_5 = np.percentile(returns, 5)
            percentile_25 = np.percentile(returns, 25)
            percentile_75 = np.percentile(returns, 75)
            percentile_95 = np.percentile(returns, 95)

            mean_final_value = np.mean(final_values)
            median_final_value = np.median(final_values)
            std_final_value = np.std(final_values)
            min_final_value = np.min(final_values)
            max_final_value = np.max(final_values)

            mean_max_drawdown = np.mean(max_drawdowns)
            median_max_drawdown = np.median(max_drawdowns)
            worst_drawdown = np.min(max_drawdowns)
            best_drawdown = np.max(max_drawdowns)

            mean_win_rate = np.mean(win_rates)
            median_win_rate = np.median(win_rates)

            mean_profit_factor = np.mean(profit_factors)
            median_profit_factor = np.median(profit_factors)

            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) != 0 else 0.0
            var_95 = np.percentile(returns, 5)
            cvar_95 = np.mean([r for r in returns if r <= np.percentile(returns, 5)])

        # Calculate statistics
        results = {
            "strategy": strategy_name,
            "symbol": symbol,
            "method": method,
            "n_simulations": self.n_simulations,
            "initial_capital": self.initial_capital,
            "gpu_accelerated": CUPY_AVAILABLE,  # Indicate if GPU was used
            # Return statistics
            "mean_return": mean_return,
            "median_return": median_return,
            "std_return": std_return,
            "min_return": min_return,
            "max_return": max_return,
            "percentile_5": percentile_5,
            "percentile_25": percentile_25,
            "percentile_75": percentile_75,
            "percentile_95": percentile_95,
            # Final value statistics
            "mean_final_value": mean_final_value,
            "median_final_value": median_final_value,
            "std_final_value": std_final_value,
            "min_final_value": min_final_value,
            "max_final_value": max_final_value,
            # Drawdown statistics
            "mean_max_drawdown": mean_max_drawdown,
            "median_max_drawdown": median_max_drawdown,
            "worst_drawdown": worst_drawdown,
            "best_drawdown": best_drawdown,
            # Win rate statistics
            "mean_win_rate": mean_win_rate,
            "median_win_rate": median_win_rate,
            # Profit factor statistics
            "mean_profit_factor": mean_profit_factor,
            "median_profit_factor": median_profit_factor,
            # Probability of profit
            "probability_of_profit": sum(1 for r in returns if r > 0) / len(returns),
            # Risk metrics
            "sharpe_ratio": sharpe_ratio,
            "var_95": var_95,  # Value at Risk (95% confidence)
            "cvar_95": cvar_95,  # Conditional VaR
            # All simulation results
            "all_returns": returns,
            "all_final_values": final_values,
            "all_max_drawdowns": max_drawdowns,
            "simulation_results": simulation_results,
        }

        logger.info(
            f"Monte Carlo completed: Mean Return={results['mean_return'] * 100:.2f}%, "
            f"Std={results['std_return'] * 100:.2f}%, "
            f"Prob(Profit)={results['probability_of_profit'] * 100:.2f}%"
        )

        return results

    def save_results(
        self,
        results: dict,
        output_dir: Path | None = None,
    ) -> Path:
        """Save Monte Carlo simulation results to files.

        Args:
            results: Monte Carlo results dictionary
            output_dir: Directory to save results

        Returns:
            Path to saved results directory
        """
        output_dir = output_dir or Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = (
            output_dir / f"montecarlo_{results['strategy']}_{results['symbol']}_{timestamp}"
        )
        result_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary_file = result_dir / "summary.txt"
        with open(summary_file, "w") as f:
            f.write("Monte Carlo Simulation Results\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"Strategy: {results['strategy']}\n")
            f.write(f"Symbol: {results['symbol']}\n")
            f.write(f"Method: {results['method']}\n")
            f.write(f"Number of Simulations: {results['n_simulations']}\n")
            f.write(f"Initial Capital: ${results['initial_capital']:,.2f}\n\n")

            f.write("Return Statistics\n")
            f.write(f"{'-' * 50}\n")
            f.write(f"Mean Return: {results['mean_return'] * 100:.2f}%\n")
            f.write(f"Median Return: {results['median_return'] * 100:.2f}%\n")
            f.write(f"Std Dev: {results['std_return'] * 100:.2f}%\n")
            f.write(f"Min Return: {results['min_return'] * 100:.2f}%\n")
            f.write(f"Max Return: {results['max_return'] * 100:.2f}%\n")
            f.write(f"5th Percentile: {results['percentile_5'] * 100:.2f}%\n")
            f.write(f"25th Percentile: {results['percentile_25'] * 100:.2f}%\n")
            f.write(f"75th Percentile: {results['percentile_75'] * 100:.2f}%\n")
            f.write(f"95th Percentile: {results['percentile_95'] * 100:.2f}%\n\n")

            f.write("Final Value Statistics\n")
            f.write(f"{'-' * 50}\n")
            f.write(f"Mean Final Value: ${results['mean_final_value']:,.2f}\n")
            f.write(f"Median Final Value: ${results['median_final_value']:,.2f}\n")
            f.write(f"Std Dev: ${results['std_final_value']:,.2f}\n")
            f.write(f"Min Final Value: ${results['min_final_value']:,.2f}\n")
            f.write(f"Max Final Value: ${results['max_final_value']:,.2f}\n\n")

            f.write("Risk Metrics\n")
            f.write(f"{'-' * 50}\n")
            f.write(f"Mean Max Drawdown: {results['mean_max_drawdown'] * 100:.2f}%\n")
            f.write(f"Median Max Drawdown: {results['median_max_drawdown'] * 100:.2f}%\n")
            f.write(f"Worst Drawdown: {results['worst_drawdown'] * 100:.2f}%\n")
            f.write(f"Best Drawdown: {results['best_drawdown'] * 100:.2f}%\n")
            f.write(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}\n")
            f.write(f"Value at Risk (95%): {results['var_95'] * 100:.2f}%\n")
            f.write(f"Conditional VaR (95%): {results['cvar_95'] * 100:.2f}%\n\n")

            f.write("Performance Metrics\n")
            f.write(f"{'-' * 50}\n")
            f.write(f"Probability of Profit: {results['probability_of_profit'] * 100:.2f}%\n")
            f.write(f"Mean Win Rate: {results['mean_win_rate'] * 100:.2f}%\n")
            f.write(f"Mean Profit Factor: {results['mean_profit_factor']:.2f}\n\n")

            f.write("System Information\n")
            f.write(f"{'-' * 50}\n")
            f.write(
                f"GPU Accelerated: {'Yes (CuPy)' if results.get('gpu_accelerated', False) else 'No (CPU/NumPy)'}\n"
            )

        # Save detailed results
        detailed_df = pd.DataFrame(
            {
                "simulation": range(1, results["n_simulations"] + 1),
                "return": results["all_returns"],
                "final_value": results["all_final_values"],
                "max_drawdown": results["all_max_drawdowns"],
            }
        )
        detailed_file = result_dir / "simulations.csv"
        detailed_df.to_csv(detailed_file, index=False)

        logger.info(f"Monte Carlo results saved to {result_dir}")
        return result_dir
