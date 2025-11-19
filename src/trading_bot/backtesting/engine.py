"""Backtesting engine for evaluating trading strategies."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from trading_bot.risk.kelly_criterion import (
    calculate_metrics_from_backtest,
    fractional_kelly,
    kelly_criterion,
)
from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Backtesting engine for trading strategies."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
        slippage: float = 0.0005,
    ):
        """Initialize backtesting engine.

        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade (0.001 = 0.1%)
            slippage: Slippage rate per trade (0.0005 = 0.05%)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,  # type: ignore[type-arg]
        symbol: str = "UNKNOWN",
    ) -> dict:
        """Run backtest on a strategy.

        Args:
            strategy: Trading strategy to test
            data: Historical OHLCV data
            symbol: Symbol being traded

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest for {strategy.name} on {symbol}")

        # Generate signals
        data_with_signals = strategy.generate_signals(data)

        # Initialize portfolio
        cash = self.initial_capital
        shares = 0.0
        portfolio_value = cash
        trades: list[dict] = []

        # Track portfolio value over time
        portfolio_history = []

        # Run simulation
        for i in range(len(data_with_signals)):
            current_price = data_with_signals["close"].iloc[i]
            current_date = data_with_signals.index[i]

            # Check for buy signal
            if strategy.should_buy(data_with_signals, i) and shares == 0:
                logger.info(f"BUY SIGNAL DETECTED at {current_date}, price={current_price:.4f}")
                position_size = strategy.calculate_position_size(
                    current_price,
                    portfolio_value,
                )
                logger.info(f"Position size calculated: {position_size:.6f} shares, portfolio_value={portfolio_value:.2f}")
                cost = position_size * current_price * (1 + self.commission + self.slippage)
                logger.info(f"Trade cost: ${cost:.2f}, available cash: ${cash:.2f}")

                if cost <= cash:
                    shares = position_size
                    cash -= cost
                    trades.append(
                        {
                            "date": current_date,
                            "type": "BUY",
                            "price": current_price,
                            "shares": shares,
                            "cost": cost,
                        },
                    )
                    logger.info(
                        f"TRADE EXECUTED: BUY {shares:.6f} shares @ ${current_price:.4f} (cost: ${cost:.2f})",
                    )
                else:
                    logger.warning(f"TRADE SKIPPED: Insufficient funds. Cost: ${cost:.2f}, Cash: ${cash:.2f}")

            # Check for sell signal
            elif strategy.should_sell(data_with_signals, i) and shares > 0:
                logger.info(f"SELL SIGNAL DETECTED at {current_date}, price={current_price:.4f}, shares={shares:.6f}")
                proceeds = shares * current_price * (1 - self.commission - self.slippage)
                cash += proceeds

                pnl = proceeds - (shares * trades[-1]["price"])
                trades.append(
                    {
                        "date": current_date,
                        "type": "SELL",
                        "price": current_price,
                        "shares": shares,
                        "proceeds": proceeds,
                        "pnl": pnl,
                    },
                )
                logger.info(
                    f"TRADE EXECUTED: SELL {shares:.6f} shares @ ${current_price:.4f} "
                    f"(PnL: ${pnl:.2f})",
                )
                shares = 0.0

            # Calculate current portfolio value
            portfolio_value = cash + (shares * current_price)
            portfolio_history.append(
                {
                    "date": current_date,
                    "cash": cash,
                    "shares": shares,
                    "portfolio_value": portfolio_value,
                    "price": current_price,
                },
            )

        # Calculate final metrics
        final_value = portfolio_value
        total_return = (final_value - self.initial_capital) / self.initial_capital

        # Calculate buy-and-hold return for comparison
        buy_hold_return = (
            data_with_signals["close"].iloc[-1] - data_with_signals["close"].iloc[0]
        ) / data_with_signals["close"].iloc[0]

        # Calculate trade statistics
        buy_trades = [t for t in trades if t["type"] == "BUY"]
        sell_trades = [t for t in trades if t["type"] == "SELL"]

        winning_trades = [t for t in sell_trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in sell_trades if t.get("pnl", 0) < 0]

        win_rate = len(winning_trades) / len(sell_trades) if sell_trades else 0.0

        avg_win = (
            sum(t["pnl"] for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        )
        avg_loss = (
            sum(t["pnl"] for t in losing_trades) / len(losing_trades) if losing_trades else 0.0
        )

        # Calculate maximum drawdown
        portfolio_df = pd.DataFrame(portfolio_history)  # type: ignore[call-overload]
        portfolio_df.set_index("date", inplace=True)
        portfolio_df["cummax"] = portfolio_df["portfolio_value"].cummax()
        portfolio_df["drawdown"] = (
            portfolio_df["portfolio_value"] - portfolio_df["cummax"]
        ) / portfolio_df["cummax"]
        max_drawdown = portfolio_df["drawdown"].min()

        # Calculate Kelly Criterion metrics
        kelly_metrics = calculate_metrics_from_backtest(sell_trades)
        kelly_full = kelly_criterion(kelly_metrics.win_rate, kelly_metrics.reward_risk_ratio)
        kelly_half = fractional_kelly(kelly_full, 0.5)
        kelly_quarter = fractional_kelly(kelly_full, 0.25)

        results = {
            "strategy": strategy.name,
            "symbol": symbol,
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "buy_hold_return": buy_hold_return,
            "buy_hold_return_pct": buy_hold_return * 100,
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
            "trades": trades,
            "portfolio_history": portfolio_history,
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
            f"Backtest completed: Return={total_return * 100:.2f}%, "
            f"Win Rate={win_rate * 100:.2f}%, Max DD={max_drawdown * 100:.2f}%",
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
        result_dir = output_dir / f"{results['strategy']}_{results['symbol']}_{timestamp}"
        result_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary_file = result_dir / "summary.txt"
        with open(summary_file, "w") as f:
            f.write("Backtest Results\n")
            f.write(f"{'=' * 50}\n\n")
            f.write(f"Strategy: {results['strategy']}\n")
            f.write(f"Symbol: {results['symbol']}\n")
            f.write(f"Initial Capital: ${results['initial_capital']:,.2f}\n")
            f.write(f"Final Value: ${results['final_value']:,.2f}\n")
            f.write(f"Total Return: {results['total_return_pct']:.2f}%\n")
            f.write(f"Buy & Hold Return: {results['buy_hold_return_pct']:.2f}%\n")
            f.write(f"Total Trades: {results['total_trades']}\n")
            f.write(f"Winning Trades: {results['winning_trades']}\n")
            f.write(f"Losing Trades: {results['losing_trades']}\n")
            f.write(f"Win Rate: {results['win_rate_pct']:.2f}%\n")
            f.write(f"Average Win: ${results['avg_win']:.2f}\n")
            f.write(f"Average Loss: ${results['avg_loss']:.2f}\n")
            f.write(f"Profit Factor: {results['profit_factor']:.2f}\n")
            f.write(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%\n")

        # Save trades
        trades_df = pd.DataFrame(results["trades"])  # type: ignore[call-overload]
        trades_file = result_dir / "trades.csv"
        trades_df.to_csv(trades_file, index=False)

        # Save portfolio history
        portfolio_df = pd.DataFrame(results["portfolio_history"])  # type: ignore[call-overload]
        portfolio_df.set_index("date", inplace=True)
        portfolio_file = result_dir / "portfolio_history.csv"
        portfolio_df.to_csv(portfolio_file)

        logger.info(f"Results saved to {result_dir}")
        return result_dir
