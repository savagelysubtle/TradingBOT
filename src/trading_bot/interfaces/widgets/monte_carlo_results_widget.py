"""Monte Carlo results display widget for the Trading Bot TUI."""

from rich.console import Console
from rich.table import Table
from textual.widgets import Static


class MonteCarloResultsWidget:
    """Widget for displaying Monte Carlo simulation results."""

    @staticmethod
    def display_results(results: dict, widget: Static) -> None:
        """Display Monte Carlo simulation results in a formatted table.

        Args:
            results: Dictionary containing Monte Carlo simulation results
            widget: Static widget to update with results
        """
        # Create results table
        results_table = Table(
            title="Monte Carlo Simulation Results", show_header=True, header_style="bold cyan"
        )
        results_table.add_column("Metric", style="bold", width=30)
        results_table.add_column("Value", justify="right", width=20)
        results_table.add_column("Interpretation", width=40)

        # Return Statistics
        mean_return = results["mean_return"] * 100
        median_return = results["median_return"] * 100
        std_return = results["std_return"] * 100
        p5 = results["percentile_5"] * 100
        p95 = results["percentile_95"] * 100

        results_table.add_row(
            "[bold]Return Statistics[/bold]",
            "",
            "",
        )
        results_table.add_row(
            "Mean Return",
            f"[green]{mean_return:.2f}%[/green]"
            if mean_return > 0
            else f"[red]{mean_return:.2f}%[/red]",
            "Average across all simulations",
        )
        results_table.add_row(
            "Median Return",
            f"[green]{median_return:.2f}%[/green]"
            if median_return > 0
            else f"[red]{median_return:.2f}%[/red]",
            "Middle value (50th percentile)",
        )
        results_table.add_row(
            "Std Deviation",
            f"{std_return:.2f}%",
            "Volatility of returns",
        )
        results_table.add_row(
            "5th Percentile",
            f"[red]{p5:.2f}%[/red]",
            "95% of outcomes are better",
        )
        results_table.add_row(
            "95th Percentile",
            f"[green]{p95:.2f}%[/green]",
            "Best-case scenario (5% chance)",
        )

        # Risk Metrics
        prob_profit = results["probability_of_profit"] * 100
        sharpe = results["sharpe_ratio"]
        var_95 = results["var_95"] * 100
        mean_dd = results["mean_max_drawdown"] * 100
        worst_dd = results["worst_drawdown"] * 100

        results_table.add_row("", "", "")
        results_table.add_row(
            "[bold]Risk Metrics[/bold]",
            "",
            "",
        )
        results_table.add_row(
            "Probability of Profit",
            f"[green]{prob_profit:.1f}%[/green]"
            if prob_profit >= 70
            else f"[yellow]{prob_profit:.1f}%[/yellow]"
            if prob_profit >= 50
            else f"[red]{prob_profit:.1f}%[/red]",
            "✓ High confidence"
            if prob_profit >= 70
            else "⚠ Moderate"
            if prob_profit >= 50
            else "✗ Low confidence",
        )
        results_table.add_row(
            "Sharpe Ratio",
            f"[green]{sharpe:.2f}[/green]"
            if sharpe >= 1.0
            else f"[yellow]{sharpe:.2f}[/yellow]"
            if sharpe >= 0.5
            else f"[red]{sharpe:.2f}[/red]",
            "✓ Good risk-adjusted"
            if sharpe >= 1.0
            else "⚠ Moderate"
            if sharpe >= 0.5
            else "✗ Poor risk-adjusted",
        )
        results_table.add_row(
            "Value at Risk (95%)",
            f"[red]{var_95:.2f}%[/red]",
            "95% confidence worst case",
        )
        results_table.add_row(
            "Mean Max Drawdown",
            f"{mean_dd:.2f}%",
            "Average worst drawdown",
        )
        results_table.add_row(
            "Worst Drawdown",
            f"[red]{worst_dd:.2f}%[/red]",
            "✓ Acceptable"
            if abs(worst_dd) <= 20
            else "⚠ Moderate"
            if abs(worst_dd) <= 30
            else "✗ High risk",
        )

        # Summary metrics
        results_table.add_row("", "", "")
        results_table.add_row(
            "[bold]Summary[/bold]",
            "",
            "",
        )
        results_table.add_row(
            "Simulations",
            f"{results['n_simulations']}",
            f"Method: {results['method']}",
        )
        results_table.add_row(
            "Strategy",
            results["strategy"],
            f"Symbol: {results['symbol']}",
        )

        # Render table
        console = Console()
        with console.capture() as capture:
            console.print(results_table)

        widget.update(capture.get())
