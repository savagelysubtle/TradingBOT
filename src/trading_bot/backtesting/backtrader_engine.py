"""Backtrader integration for backtesting."""

import logging
from datetime import datetime
from pathlib import Path

import backtrader as bt
import pandas as pd

from trading_bot.strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class BacktraderStrategy(bt.Strategy):
    """Wrapper to use BaseStrategy with Backtrader."""

    params = (
        ("strategy", None),
        ("short_window", 50),
        ("long_window", 200),
    )

    def __init__(self):
        """Initialize Backtrader strategy wrapper."""
        self.strategy = self.params.strategy  # type: ignore[assignment]
        if self.strategy:
            # Generate signals from strategy
            self.data_with_signals = self.strategy.generate_signals(
                self._get_dataframe(),
            )
            self.signal_index = 0

    def _get_dataframe(self) -> pd.DataFrame:  # type: ignore[return]
        """Convert Backtrader data feed to DataFrame."""
        data_list = []
        for i in range(len(self.data)):
            data_list.append(
                {
                    "open": self.data.open[i],
                    "high": self.data.high[i],
                    "low": self.data.low[i],
                    "close": self.data.close[i],
                    "volume": self.data.volume[i],
                },
            )
        return pd.DataFrame(data_list)  # type: ignore[call-overload]

    def next(self):
        """Called for each bar."""
        if not self.strategy or self.signal_index >= len(self.data_with_signals):
            return

        current_signal = self.data_with_signals["signal"].iloc[self.signal_index]

        if current_signal == 1 and not self.position:
            # Buy signal
            size = self.strategy.calculate_position_size(
                self.data.close[0],
                self.broker.getcash(),
            )
            if size > 0:
                self.buy(size=int(size))
                logger.debug(f"BUY signal at {self.data.datetime.date(0)}")

        elif current_signal == -1 and self.position:
            # Sell signal
            self.sell(size=self.position.size)
            logger.debug(f"SELL signal at {self.data.datetime.date(0)}")

        self.signal_index += 1


class BacktraderEngine:
    """Backtrader-based backtesting engine."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.001,
    ):
        """Initialize Backtrader engine.

        Args:
            initial_capital: Starting capital
            commission: Commission rate per trade
        """
        self.initial_capital = initial_capital
        self.commission = commission

    def run(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,  # type: ignore[type-arg]
        symbol: str = "UNKNOWN",
    ) -> dict:
        """Run backtest using Backtrader.

        Args:
            strategy: Trading strategy to test
            data: Historical OHLCV data
            symbol: Symbol being traded

        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running Backtrader backtest for {strategy.name} on {symbol}")

        # Create Cerebro engine
        cerebro = bt.Cerebro()

        # Add strategy
        cerebro.addstrategy(
            BacktraderStrategy,
            strategy=strategy,  # type: ignore[arg-type]
        )

        # Convert DataFrame to Backtrader data feed
        # Note: backtrader doesn't have type stubs, so we suppress type checking
        bt_data = bt.feeds.PandasData(  # type: ignore
            dataname=data,  # type: ignore
            datetime=None,  # type: ignore
            open=0,  # type: ignore
            high=1,  # type: ignore
            low=2,  # type: ignore
            close=3,  # type: ignore
            volume=4,  # type: ignore
            openinterest=-1,  # type: ignore
        )
        cerebro.adddata(bt_data)

        # Set initial capital
        cerebro.broker.setcash(self.initial_capital)

        # Set commission
        cerebro.broker.setcommission(commission=self.commission)

        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        # Run backtest
        results = cerebro.run()

        # Extract results
        strat = results[0]
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()

        # Calculate final value
        final_value = cerebro.broker.getvalue()

        # Calculate buy-and-hold return
        buy_hold_return = (data["close"].iloc[-1] - data["close"].iloc[0]) / data["close"].iloc[0]

        results_dict = {
            "strategy": strategy.name,
            "symbol": symbol,
            "initial_capital": self.initial_capital,
            "final_value": final_value,
            "total_return": (final_value - self.initial_capital) / self.initial_capital,
            "total_return_pct": ((final_value - self.initial_capital) / self.initial_capital) * 100,
            "buy_hold_return": buy_hold_return,
            "buy_hold_return_pct": buy_hold_return * 100,
            "sharpe_ratio": sharpe.get("sharperatio", 0.0),
            "max_drawdown": drawdown.get("max", {}).get("drawdown", 0.0),
            "max_drawdown_pct": abs(drawdown.get("max", {}).get("drawdown", 0.0)) * 100,
            "total_trades": trades.get("total", {}).get("total", 0),
            "winning_trades": trades.get("won", {}).get("total", 0),
            "losing_trades": trades.get("lost", {}).get("total", 0),
            "win_rate": (
                trades.get("won", {}).get("total", 0) / trades.get("total", {}).get("total", 1)
            ),
            "win_rate_pct": (
                trades.get("won", {}).get("total", 0) / trades.get("total", {}).get("total", 1)
            )
            * 100,
        }

        logger.info(
            f"Backtest completed: Return={results_dict['total_return_pct']:.2f}%, "
            f"Sharpe={results_dict['sharpe_ratio']:.2f}",
        )

        return results_dict

    def save_results(
        self,
        results: dict,
        output_dir: Path | None = None,
    ) -> Path:
        """Save backtest results to files."""
        output_dir = output_dir or Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_dir = output_dir / f"{results['strategy']}_{results['symbol']}_{timestamp}"
        result_dir.mkdir(parents=True, exist_ok=True)

        # Save summary
        summary_file = result_dir / "summary.txt"
        with open(summary_file, "w") as f:
            f.write("Backtrader Backtest Results\n")
            f.write(f"{'=' * 50}\n\n")
            for key, value in results.items():
                f.write(f"{key}: {value}\n")

        logger.info(f"Results saved to {result_dir}")
        return result_dir
