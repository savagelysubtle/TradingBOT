"""Visualization utilities for backtest results using matplotlib."""

import logging
from pathlib import Path

import matplotlib.pyplot as plt  # type: ignore[import-untyped]
import pandas as pd

logger = logging.getLogger(__name__)


def plot_backtest_results(
    results: dict,
    data: pd.DataFrame,  # type: ignore[type-arg]
    signals: pd.DataFrame,  # type: ignore[type-arg]
    output_dir: Path | None = None,
) -> Path:
    """Create comprehensive visualization of backtest results.

    Args:
        results: Backtest results dictionary
        data: Original OHLCV data
        signals: DataFrame with signals
        output_dir: Directory to save plots

    Returns:
        Path to saved plot file
    """
    output_dir = output_dir or Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(4, 2, hspace=0.3, wspace=0.3)

    # Plot 1: Price chart with buy/sell signals
    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(data.index, data["close"], label="Close Price", linewidth=1.5, alpha=0.7)

    # Add moving averages if available
    if "ma_short" in signals.columns:
        ax1.plot(signals.index, signals["ma_short"], label="Short MA", alpha=0.6, linewidth=1)
    if "ma_long" in signals.columns:
        ax1.plot(signals.index, signals["ma_long"], label="Long MA", alpha=0.6, linewidth=1)

    # Mark buy/sell signals
    buy_signals = signals[signals["signal"] == 1]
    sell_signals = signals[signals["signal"] == -1]

    if len(buy_signals) > 0:
        ax1.scatter(
            buy_signals.index,
            buy_signals["close"],
            color="green",
            marker="^",
            s=100,
            label="Buy Signal",
            zorder=5,
        )
    if len(sell_signals) > 0:
        ax1.scatter(
            sell_signals.index,
            sell_signals["close"],
            color="red",
            marker="v",
            s=100,
            label="Sell Signal",
            zorder=5,
        )

    ax1.set_title(f"{results['strategy']} - {results['symbol']}", fontsize=14, fontweight="bold")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Price ($)")
    ax1.legend(loc="best")
    ax1.grid(True, alpha=0.3)

    # Plot 2: Portfolio value over time
    ax2 = fig.add_subplot(gs[1, 0])
    if results.get("portfolio_history"):
        portfolio_df = pd.DataFrame(results["portfolio_history"])  # type: ignore[call-overload]
        if "date" in portfolio_df.columns:
            portfolio_df.set_index("date", inplace=True)
        portfolio_df["portfolio_value"].plot(ax=ax2, color="blue", linewidth=2)
        ax2.axhline(
            y=results["initial_capital"], color="gray", linestyle="--", label="Initial Capital"
        )
        ax2.set_title("Portfolio Value Over Time", fontsize=12, fontweight="bold")
        ax2.set_xlabel("Date")
        ax2.set_ylabel("Portfolio Value ($)")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

    # Plot 3: Drawdown
    ax3 = fig.add_subplot(gs[1, 1])
    if results.get("portfolio_history"):
        portfolio_df = pd.DataFrame(results["portfolio_history"])  # type: ignore[call-overload]
        if "date" in portfolio_df.columns:
            portfolio_df.set_index("date", inplace=True)
        if "portfolio_value" in portfolio_df.columns:
            portfolio_df["cummax"] = portfolio_df["portfolio_value"].cummax()
            portfolio_df["drawdown"] = (
                (portfolio_df["portfolio_value"] - portfolio_df["cummax"]) / portfolio_df["cummax"]
            ) * 100
            portfolio_df["drawdown"].plot(
                ax=ax3, color="red", linewidth=1.5, kind="area", alpha=0.3
            )
            ax3.set_title("Drawdown (%)", fontsize=12, fontweight="bold")
            ax3.set_xlabel("Date")
            ax3.set_ylabel("Drawdown (%)")
            ax3.grid(True, alpha=0.3)
            ax3.fill_between(
                portfolio_df.index, portfolio_df["drawdown"], 0, alpha=0.3, color="red"
            )

    # Plot 4: Returns distribution
    ax4 = fig.add_subplot(gs[2, 0])
    if results.get("trades"):
        trades_df = pd.DataFrame(results["trades"])  # type: ignore[call-overload]
        if "pnl" in trades_df.columns:
            pnl_values = trades_df[trades_df["pnl"].notna()]["pnl"]
            if len(pnl_values) > 0:
                ax4.hist(pnl_values, bins=20, color="skyblue", edgecolor="black", alpha=0.7)
                ax4.axvline(x=0, color="red", linestyle="--", linewidth=2)
                ax4.set_title("Trade P&L Distribution", fontsize=12, fontweight="bold")
                ax4.set_xlabel("Profit/Loss ($)")
                ax4.set_ylabel("Frequency")
                ax4.grid(True, alpha=0.3)

    # Plot 5: Performance metrics bar chart
    ax5 = fig.add_subplot(gs[2, 1])
    metrics = {
        "Total Return": results.get("total_return_pct", 0),
        "Buy & Hold": results.get("buy_hold_return_pct", 0),
        "Win Rate": results.get("win_rate_pct", 0),
    }
    colors = ["green" if v > 0 else "red" for v in metrics.values()]
    ax5.bar(
        list(metrics.keys()), list(metrics.values()), color=colors, alpha=0.7, edgecolor="black"
    )  # type: ignore[call-overload]
    ax5.set_title("Performance Metrics (%)", fontsize=12, fontweight="bold")
    ax5.set_ylabel("Percentage (%)")
    ax5.grid(True, alpha=0.3, axis="y")
    ax5.axhline(y=0, color="black", linestyle="-", linewidth=0.5)

    # Plot 6: Trade analysis
    ax6 = fig.add_subplot(gs[3, :])
    if results.get("trades"):
        trades_df = pd.DataFrame(results["trades"])  # type: ignore[call-overload]
        if len(trades_df) > 0 and "date" in trades_df.columns:
            trades_df["date"] = pd.to_datetime(trades_df["date"])  # type: ignore[call-overload]
            trades_df = trades_df.sort_values("date")

            # Cumulative P&L
            if "pnl" in trades_df.columns:
                trades_df["cumulative_pnl"] = trades_df["pnl"].fillna(0).cumsum()
                ax6.plot(
                    trades_df["date"],
                    trades_df["cumulative_pnl"],
                    marker="o",
                    linewidth=2,
                    markersize=4,
                    color="blue",
                )
                ax6.axhline(y=0, color="gray", linestyle="--", linewidth=1)
                ax6.set_title("Cumulative P&L Over Time", fontsize=12, fontweight="bold")
                ax6.set_xlabel("Date")
                ax6.set_ylabel("Cumulative P&L ($)")
                ax6.grid(True, alpha=0.3)

    # Add summary text
    fig.suptitle(
        f"Backtest Summary: {results['strategy']} | "
        f"Return: {results.get('total_return_pct', 0):.2f}% | "
        f"Trades: {results.get('total_trades', 0)} | "
        f"Win Rate: {results.get('win_rate_pct', 0):.2f}%",
        fontsize=16,
        fontweight="bold",
        y=0.995,
    )

    # Save plot
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")  # type: ignore[attr-defined]
    # Sanitize symbol for filename (replace / with _)
    symbol_safe = str(results['symbol']).replace("/", "_")
    plot_file = (
        output_dir / f"backtest_plot_{results['strategy']}_{symbol_safe}_{timestamp}.png"
    )
    plt.savefig(plot_file, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Plot saved to {plot_file}")
    return plot_file


def plot_simple_results(
    results: dict,
    output_dir: Path | None = None,
) -> Path:
    """Create a simple visualization of backtest results.

    Args:
        results: Backtest results dictionary
        output_dir: Directory to save plot

    Returns:
        Path to saved plot file
    """
    output_dir = output_dir or Path("results")
    output_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"Backtest Results: {results['strategy']} - {results['symbol']}",
        fontsize=14,
        fontweight="bold",
    )

    # Portfolio value
    if results.get("portfolio_history"):
        portfolio_df = pd.DataFrame(results["portfolio_history"])  # type: ignore[call-overload]
        if "date" in portfolio_df.columns:
            portfolio_df.set_index("date", inplace=True)
        if "portfolio_value" in portfolio_df.columns:
            axes[0, 0].plot(portfolio_df.index, portfolio_df["portfolio_value"], linewidth=2)
            axes[0, 0].set_title("Portfolio Value")
            axes[0, 0].set_ylabel("Value ($)")
            axes[0, 0].grid(True, alpha=0.3)

    # Metrics comparison
    metrics = {
        "Return": results.get("total_return_pct", 0),
        "Buy&Hold": results.get("buy_hold_return_pct", 0),
    }
    axes[0, 1].bar(metrics.keys(), metrics.values(), color=["green", "blue"], alpha=0.7)
    axes[0, 1].set_title("Returns Comparison")
    axes[0, 1].set_ylabel("Return (%)")
    axes[0, 1].grid(True, alpha=0.3, axis="y")

    # Trade statistics
    trade_stats = {
        "Total": results.get("total_trades", 0),
        "Wins": results.get("winning_trades", 0),
        "Losses": results.get("losing_trades", 0),
    }
    axes[1, 0].bar(
        trade_stats.keys(), trade_stats.values(), color=["gray", "green", "red"], alpha=0.7
    )
    axes[1, 0].set_title("Trade Statistics")
    axes[1, 0].set_ylabel("Count")
    axes[1, 0].grid(True, alpha=0.3, axis="y")

    # Performance metrics
    perf_metrics = {
        "Win Rate": results.get("win_rate_pct", 0),
        "Max DD": abs(results.get("max_drawdown_pct", 0)),
    }
    axes[1, 1].bar(perf_metrics.keys(), perf_metrics.values(), color=["green", "red"], alpha=0.7)
    axes[1, 1].set_title("Performance Metrics")
    axes[1, 1].set_ylabel("Percentage (%)")
    axes[1, 1].grid(True, alpha=0.3, axis="y")

    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")  # type: ignore[attr-defined]
    # Sanitize symbol for filename (replace / with _)
    symbol_safe = str(results['symbol']).replace("/", "_")
    plot_file = (
        output_dir / f"backtest_simple_{results['strategy']}_{symbol_safe}_{timestamp}.png"
    )
    plt.savefig(plot_file, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info(f"Simple plot saved to {plot_file}")
    return plot_file
