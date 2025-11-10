"""Visualization tools for Monte Carlo simulation results."""

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Try to import CuPy for GPU acceleration, fallback to NumPy
try:
    import cupy as cp

    CUPY_AVAILABLE = True
except ImportError:
    cp = np  # Fallback to NumPy if CuPy not available
    CUPY_AVAILABLE = False


def plot_monte_carlo_results(
    results: dict,
    output_dir: Optional[Path] = None,
    show: bool = False,
) -> Path:
    """Create comprehensive visualization of Monte Carlo simulation results.

    Args:
        results: Monte Carlo results dictionary
        output_dir: Directory to save plots
        show: Whether to display plots interactively

    Returns:
        Path to saved plots directory
    """
    output_dir = output_dir or Path("results") / "monte_carlo_plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(
        f"Monte Carlo Simulation: {results['strategy']} on {results['symbol']}\n"
        f"Method: {results['method']}, N={results['n_simulations']}",
        fontsize=16,
        fontweight="bold",
    )

    # 1. Return Distribution (histogram)
    ax1 = plt.subplot(3, 3, 1)
    returns_pct = [r * 100 for r in results["all_returns"]]
    ax1.hist(returns_pct, bins=50, alpha=0.7, color="steelblue", edgecolor="black")
    ax1.axvline(
        results["mean_return"] * 100,
        color="red",
        linestyle="--",
        label=f"Mean: {results['mean_return'] * 100:.2f}%",
    )
    ax1.axvline(
        results["median_return"] * 100,
        color="green",
        linestyle="--",
        label=f"Median: {results['median_return'] * 100:.2f}%",
    )
    ax1.axvline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax1.set_xlabel("Return (%)")
    ax1.set_ylabel("Frequency")
    ax1.set_title("Return Distribution")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Return Distribution (box plot)
    ax2 = plt.subplot(3, 3, 2)
    ax2.boxplot(returns_pct, vert=True)
    ax2.axhline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax2.set_ylabel("Return (%)")
    ax2.set_title("Return Box Plot")
    ax2.grid(True, alpha=0.3)

    # 3. Percentile Analysis (GPU-accelerated if available)
    ax3 = plt.subplot(3, 3, 3)
    percentiles = range(1, 100)
    if CUPY_AVAILABLE:
        returns_pct_gpu = cp.asarray(returns_pct)
        percentile_values = [float(cp.percentile(returns_pct_gpu, p)) for p in percentiles]
    else:
        percentile_values = [np.percentile(returns_pct, p) for p in percentiles]
    ax3.plot(percentiles, percentile_values, color="steelblue", linewidth=2)
    ax3.axhline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax3.axhline(
        results["percentile_5"] * 100,
        color="red",
        linestyle="--",
        label=f"5th: {results['percentile_5'] * 100:.2f}%",
    )
    ax3.axhline(
        results["percentile_95"] * 100,
        color="green",
        linestyle="--",
        label=f"95th: {results['percentile_95'] * 100:.2f}%",
    )
    ax3.set_xlabel("Percentile")
    ax3.set_ylabel("Return (%)")
    ax3.set_title("Return Percentiles")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Final Value Distribution
    ax4 = plt.subplot(3, 3, 4)
    ax4.hist(
        results["all_final_values"],
        bins=50,
        alpha=0.7,
        color="darkgreen",
        edgecolor="black",
    )
    ax4.axvline(
        results["mean_final_value"],
        color="red",
        linestyle="--",
        label=f"Mean: ${results['mean_final_value']:,.0f}",
    )
    ax4.axvline(
        results["initial_capital"],
        color="black",
        linestyle="-",
        label=f"Initial: ${results['initial_capital']:,.0f}",
    )
    ax4.set_xlabel("Final Portfolio Value ($)")
    ax4.set_ylabel("Frequency")
    ax4.set_title("Final Value Distribution")
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # 5. Drawdown Distribution
    ax5 = plt.subplot(3, 3, 5)
    drawdowns_pct = [d * 100 for d in results["all_max_drawdowns"]]
    ax5.hist(drawdowns_pct, bins=50, alpha=0.7, color="darkred", edgecolor="black")
    ax5.axvline(
        results["mean_max_drawdown"] * 100,
        color="blue",
        linestyle="--",
        label=f"Mean: {results['mean_max_drawdown'] * 100:.2f}%",
    )
    ax5.axvline(
        results["worst_drawdown"] * 100,
        color="red",
        linestyle="--",
        label=f"Worst: {results['worst_drawdown'] * 100:.2f}%",
    )
    ax5.set_xlabel("Max Drawdown (%)")
    ax5.set_ylabel("Frequency")
    ax5.set_title("Drawdown Distribution")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 6. Cumulative Probability (GPU-accelerated if available)
    ax6 = plt.subplot(3, 3, 6)
    if CUPY_AVAILABLE:
        returns_pct_gpu = cp.asarray(returns_pct)
        sorted_returns_gpu = cp.sort(returns_pct_gpu)
        sorted_returns = cp.asnumpy(sorted_returns_gpu)  # Convert back to NumPy for plotting
        cumulative_prob_gpu = cp.arange(1, len(sorted_returns) + 1) / len(sorted_returns)
        cumulative_prob = cp.asnumpy(cumulative_prob_gpu)
    else:
        sorted_returns = np.sort(returns_pct)
        cumulative_prob = np.arange(1, len(sorted_returns) + 1) / len(sorted_returns)
    ax6.plot(sorted_returns, cumulative_prob * 100, color="steelblue", linewidth=2)
    ax6.axvline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax6.axhline(50, color="gray", linestyle="--", alpha=0.5)
    ax6.set_xlabel("Return (%)")
    ax6.set_ylabel("Cumulative Probability (%)")
    ax6.set_title("Cumulative Distribution Function")
    ax6.grid(True, alpha=0.3)

    # 7. Return vs Drawdown Scatter
    ax7 = plt.subplot(3, 3, 7)
    ax7.scatter(
        drawdowns_pct,
        returns_pct,
        alpha=0.5,
        color="purple",
        edgecolors="black",
        linewidth=0.5,
    )
    ax7.axhline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax7.axvline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax7.set_xlabel("Max Drawdown (%)")
    ax7.set_ylabel("Return (%)")
    ax7.set_title("Return vs Drawdown")
    ax7.grid(True, alpha=0.3)

    # 8. Statistics Summary
    ax8 = plt.subplot(3, 3, 8)
    ax8.axis("off")
    stats_text = f"""
    Return Statistics:
    Mean: {results['mean_return'] * 100:.2f}%
    Median: {results['median_return'] * 100:.2f}%
    Std Dev: {results['std_return'] * 100:.2f}%
    Min: {results['min_return'] * 100:.2f}%
    Max: {results['max_return'] * 100:.2f}%

    Risk Metrics:
    Prob(Profit): {results['probability_of_profit'] * 100:.2f}%
    Sharpe Ratio: {results['sharpe_ratio']:.2f}
    VaR (95%): {results['var_95'] * 100:.2f}%
    CVaR (95%): {results['cvar_95'] * 100:.2f}%

    Drawdown:
    Mean: {results['mean_max_drawdown'] * 100:.2f}%
    Worst: {results['worst_drawdown'] * 100:.2f}%
    """
    ax8.text(
        0.1,
        0.5,
        stats_text,
        fontsize=10,
        verticalalignment="center",
        fontfamily="monospace",
    )
    ax8.set_title("Summary Statistics")

    # 9. Confidence Intervals (GPU-accelerated if available)
    ax9 = plt.subplot(3, 3, 9)
    confidence_levels = [50, 75, 90, 95, 99]
    if CUPY_AVAILABLE:
        returns_pct_gpu = cp.asarray(returns_pct)
        lower_bounds = [
            float(cp.percentile(returns_pct_gpu, (100 - cl) / 2)) for cl in confidence_levels
        ]
        upper_bounds = [
            float(cp.percentile(returns_pct_gpu, 100 - (100 - cl) / 2)) for cl in confidence_levels
        ]
        y_pos_gpu = cp.arange(len(confidence_levels))
        y_pos = cp.asnumpy(y_pos_gpu)
    else:
        lower_bounds = [np.percentile(returns_pct, (100 - cl) / 2) for cl in confidence_levels]
        upper_bounds = [np.percentile(returns_pct, 100 - (100 - cl) / 2) for cl in confidence_levels]
        y_pos = np.arange(len(confidence_levels))
    ax9.barh(
        y_pos,
        [u - l for l, u in zip(lower_bounds, upper_bounds)],
        left=lower_bounds,
        color="steelblue",
        alpha=0.7,
    )
    ax9.axvline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax9.set_yticks(y_pos)
    ax9.set_yticklabels([f"{cl}%" for cl in confidence_levels])
    ax9.set_xlabel("Return (%)")
    ax9.set_ylabel("Confidence Level")
    ax9.set_title("Confidence Intervals")
    ax9.grid(True, alpha=0.3, axis="x")

    plt.tight_layout()

    # Save plot
    plot_file = output_dir / f"montecarlo_{results['strategy']}_{results['symbol']}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches="tight")
    print(f"Monte Carlo plot saved to: {plot_file}")

    if show:
        plt.show()
    else:
        plt.close()

    return output_dir


def plot_simulation_paths(
    results: dict,
    n_paths: int = 100,
    output_dir: Optional[Path] = None,
    show: bool = False,
) -> Path:
    """Plot individual simulation paths (if available).

    Args:
        results: Monte Carlo results dictionary
        n_paths: Number of random paths to display
        output_dir: Directory to save plots
        show: Whether to display plots interactively

    Returns:
        Path to saved plots directory
    """
    output_dir = output_dir or Path("results") / "monte_carlo_plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Check if portfolio history is available
    if "simulation_results" not in results or not results["simulation_results"]:
        print("No simulation portfolio histories available for path plotting")
        return output_dir

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle(
        f"Monte Carlo Simulation Paths: {results['strategy']} on {results['symbol']}",
        fontsize=14,
        fontweight="bold",
    )

    # Sample random simulations (GPU-accelerated if available)
    n_sims = min(n_paths, len(results["simulation_results"]))
    if CUPY_AVAILABLE:
        sampled_indices_gpu = cp.random.choice(
            len(results["simulation_results"]),
            size=n_sims,
            replace=False,
        )
        sampled_indices = cp.asnumpy(sampled_indices_gpu)
    else:
        sampled_indices = np.random.choice(
            len(results["simulation_results"]),
            size=n_sims,
            replace=False,
        )

    # Plot portfolio value paths
    for idx in sampled_indices:
        sim_result = results["simulation_results"][idx]
        if "portfolio_history" in sim_result and sim_result["portfolio_history"]:
            portfolio_df = pd.DataFrame(sim_result["portfolio_history"])
            ax1.plot(
                portfolio_df["portfolio_value"],
                alpha=0.3,
                linewidth=0.5,
                color="steelblue",
            )

    # Plot mean path
    ax1.axhline(
        results["mean_final_value"],
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean Final: ${results['mean_final_value']:,.0f}",
    )
    ax1.axhline(
        results["initial_capital"],
        color="black",
        linestyle="-",
        linewidth=2,
        label=f"Initial: ${results['initial_capital']:,.0f}",
    )
    ax1.set_ylabel("Portfolio Value ($)")
    ax1.set_xlabel("Time Steps")
    ax1.set_title(f"Portfolio Value Paths (n={n_sims})")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot return paths
    for idx in sampled_indices:
        sim_result = results["simulation_results"][idx]
        if "portfolio_history" in sim_result and sim_result["portfolio_history"]:
            portfolio_df = pd.DataFrame(sim_result["portfolio_history"])
            returns = (
                (portfolio_df["portfolio_value"] - results["initial_capital"])
                / results["initial_capital"]
                * 100
            )
            ax2.plot(returns, alpha=0.3, linewidth=0.5, color="darkgreen")

    ax2.axhline(0, color="black", linestyle="-", linewidth=1, alpha=0.5)
    ax2.axhline(
        results["mean_return"] * 100,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mean Return: {results['mean_return'] * 100:.2f}%",
    )
    ax2.set_ylabel("Return (%)")
    ax2.set_xlabel("Time Steps")
    ax2.set_title("Return Paths")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save plot
    plot_file = output_dir / f"montecarlo_paths_{results['strategy']}_{results['symbol']}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches="tight")
    print(f"Monte Carlo paths plot saved to: {plot_file}")

    if show:
        plt.show()
    else:
        plt.close()

    return output_dir
