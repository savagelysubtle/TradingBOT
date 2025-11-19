"""VectorBT-based backtesting engine for ultra-fast vectorized backtesting."""

import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import vectorbt as vbt  # type: ignore[import-untyped]

    VECTORBT_AVAILABLE = True
except ImportError:
    VECTORBT_AVAILABLE = False
    vbt = None

from trading_bot.risk.kelly_criterion import (
    calculate_metrics_from_backtest,
    fractional_kelly,
    kelly_criterion,
)
from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class VectorBTEngine:
    """VectorBT-based backtesting engine - 10-100x faster than event-driven engines."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        """Initialize VectorBT engine.

        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade (0.001 = 0.1%)
            slippage: Slippage rate per trade (0.0005 = 0.05%)

        Raises:
            ImportError: If VectorBT is not installed
        """
        if not VECTORBT_AVAILABLE:
            raise ImportError(
                "VectorBT is not installed. Install with: uv add --optional vectorbt "
                "or: pip install vectorbt"
            )
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,  # type: ignore[type-arg]
        symbol: str = "UNKNOWN",
    ) -> dict:
        """Run ultra-fast vectorized backtest using VectorBT.

        Args:
            strategy: Trading strategy to test
            data: Historical OHLCV data
            symbol: Symbol being traded

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running VectorBT backtest for {strategy.name} on {symbol}")

        # Ensure data is sorted by datetime index (chronological order)
        data = data.sort_index()

        # Generate signals using strategy
        data_with_signals = strategy.generate_signals(data)

        # Extract signals as boolean arrays
        entries = data_with_signals["signal"] == 1
        exits = data_with_signals["signal"] == -1

        # Calculate total fees (commission + slippage)
        total_fees = self.commission + self.slippage

        # Create portfolio from signals (vectorized!)
        # Note: vectorbt doesn't have complete type stubs
        portfolio = vbt.Portfolio.from_signals(  # type: ignore[attr-defined]
            data_with_signals["close"],
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=total_fees,
            freq="1D",  # Daily frequency
            direction="longonly",
        )

        # Extract performance metrics
        stats = portfolio.stats()

        # Calculate buy-and-hold return
        first_close = data_with_signals["close"].iloc[0]
        last_close = data_with_signals["close"].iloc[-1]
        buy_hold_return = (last_close - first_close) / first_close
        logger.info(f"Buy-hold calculation: first_close={first_close:.2f}, last_close={last_close:.2f}, return={buy_hold_return:.4f} ({buy_hold_return*100:.2f}%)")
        logger.info(f"Data shape: {data_with_signals.shape}, date range: {data_with_signals.index[0]} to {data_with_signals.index[-1]}")

        # Get trade statistics
        trades = portfolio.trades.records_readable
        logger.debug(f"VectorBT trades records: {len(trades)} entries")
        if len(trades) > 0:
            logger.debug(f"Trades columns: {list(trades.columns)}")
            logger.debug(f"First few trades:\n{trades.head()}")

        winning_trades = (
            trades[trades["PnL"] > 0] if len(trades) > 0 else pd.DataFrame()  # type: ignore[call-overload]
        )
        losing_trades = (
            trades[trades["PnL"] < 0] if len(trades) > 0 else pd.DataFrame()  # type: ignore[call-overload]
        )

        total_trades = len(trades)
        winning_count = len(winning_trades)
        losing_count = len(losing_trades)

        logger.info(f"Trade statistics: total={total_trades}, winning={winning_count}, losing={losing_count}")

        win_rate = winning_count / total_trades if total_trades > 0 else 0.0
        avg_win = winning_trades["PnL"].mean() if len(winning_trades) > 0 else 0.0
        avg_loss = losing_trades["PnL"].mean() if len(losing_trades) > 0 else 0.0

        logger.info(f"Trade stats: total={total_trades}, winning={winning_count}, losing={losing_count}, win_rate={win_rate:.4f}, win_rate_pct={win_rate*100:.2f}")

        # Extract key metrics from stats
        final_value = portfolio.value().iloc[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # Get drawdown
        drawdown = portfolio.drawdown()
        max_drawdown = drawdown.min()

        # Calculate Sharpe ratio (annualized)
        returns = portfolio.returns()
        sharpe_ratio = (
            returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0.0  # type: ignore[attr-defined]
        )

        # Calculate Kelly Criterion metrics
        # Convert VectorBT trades to format expected by calculate_metrics_from_backtest
        trades_list = []
        if len(trades) > 0:
            for _, trade in trades.iterrows():  # type: ignore[attr-defined]
                trades_list.append({"pnl": float(trade["PnL"])})

        kelly_metrics = calculate_metrics_from_backtest(trades_list)
        kelly_full = kelly_criterion(kelly_metrics.win_rate, kelly_metrics.reward_risk_ratio)
        kelly_half = fractional_kelly(kelly_full, 0.5)
        kelly_quarter = fractional_kelly(kelly_full, 0.25)

        results = {
            "strategy": strategy.name,
            "symbol": symbol,
            "initial_capital": self.initial_capital,
            "final_value": float(final_value),
            "total_return": float(total_return),
            "total_return_pct": float(total_return * 100),
            "buy_hold_return": float(buy_hold_return),
            "buy_hold_return_pct": float(buy_hold_return * 100),
            "total_trades": int(total_trades),
            "winning_trades": int(winning_count),
            "losing_trades": int(losing_count),
            "win_rate": float(win_rate),
            "win_rate_pct": float(win_rate * 100),
            "avg_win": float(avg_win),
            "avg_loss": float(avg_loss),
            "profit_factor": (abs(avg_win / avg_loss) if avg_loss != 0 else 0.0),
            "max_drawdown": float(max_drawdown),
            "max_drawdown_pct": float(max_drawdown * 100),
            "sharpe_ratio": float(sharpe_ratio),
            "portfolio": portfolio,  # Keep portfolio object for advanced analysis
            "stats": stats,  # Full stats object
            # Kelly Criterion metrics
            "kelly_metrics": {
                "win_rate": kelly_metrics.win_rate,
                "avg_win_pct": kelly_metrics.avg_win_pct,
                "avg_loss_pct": kelly_metrics.avg_loss_pct,
                "reward_risk_ratio": kelly_metrics.reward_risk_ratio,
                "total_trades": kelly_metrics.total_trades,
                "full_kelly": kelly_full,
                "half_kelly": kelly_half,
                "quarter_kelly": kelly_quarter,
            },
        }

        logger.info(
            f"VectorBT backtest completed: Return={total_return * 100:.2f}%, "
            f"Sharpe={sharpe_ratio:.2f}, Win Rate={win_rate * 100:.2f}%",
        )

        return results

    def save_results(
        self,
        results: dict,
        output_dir: Path | None = None,
    ) -> Path:
        """Save backtest results to files.

        Args:
            results: Backtest results dictionary
            output_dir: Directory to save results

        Returns:
            Path to saved results directory
        """
        output_dir = output_dir or Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = output_dir / f"{results['strategy']}_{results['symbol']}_vectorbt_{timestamp}"
        result_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary_file = result_dir / "summary.txt"
        with open(summary_file, "w") as f:
            f.write("VectorBT Backtest Results\n")
            f.write(f"{'=' * 50}\n\n")
            for key, value in results.items():
                if key not in ["portfolio", "stats"]:  # Skip complex objects
                    f.write(f"{key}: {value}\n")

        # Save portfolio value history
        portfolio = results.get("portfolio")
        if portfolio:
            portfolio_value = portfolio.value()
            portfolio_value.to_csv(result_dir / "portfolio_value.csv")

            # Save trades
            trades = portfolio.trades.records_readable
            if len(trades) > 0:
                trades.to_csv(result_dir / "trades.csv", index=False)

            # Save drawdown
            drawdown = portfolio.drawdown()
            drawdown.to_csv(result_dir / "drawdown.csv")

        logger.info(f"VectorBT results saved to {result_dir}")
        return result_dir
