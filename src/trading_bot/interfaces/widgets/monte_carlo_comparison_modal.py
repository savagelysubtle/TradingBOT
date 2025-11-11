"""Monte Carlo comparison modal widget."""

import logging
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

logger = logging.getLogger(__name__)


class MonteCarloComparisonModal(ModalScreen[bool]):
    """Modal for comparing Monte Carlo simulation results."""

    DEFAULT_CSS = """
    MonteCarloComparisonModal {
        align: center middle;
    }

    MonteCarloComparisonModal > Vertical {
        width: 90%;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1;
    }

    .comparison-header {
        width: 100%;
        height: 3;
        text-align: center;
        border-bottom: solid $primary;
        margin-bottom: 1;
    }

    .comparison-content {
        width: 100%;
        height: 1fr;
    }

    .comparison-table {
        width: 100%;
        height: auto;
        border: solid $secondary;
        padding: 1;
        margin-bottom: 1;
    }

    .comparison-footer {
        width: 100%;
        height: 3;
        align: center middle;
    }
    """

    def __init__(self, results_list: list[dict]) -> None:
        """Initialize comparison modal.

        Args:
            results_list: List of Monte Carlo result dictionaries to compare
        """
        super().__init__()
        self.results_list = results_list
        logger.debug(f"MonteCarloComparisonModal initialized with {len(results_list)} results")

    def compose(self) -> ComposeResult:
        """Compose comparison modal."""
        yield Vertical(
            Static(
                "[bold cyan]Monte Carlo Results Comparison[/bold cyan]", classes="comparison-header"
            ),
            ScrollableContainer(
                Static("", id="comparison-content"),
                classes="comparison-content",
            ),
            Button("Close", variant="primary", classes="comparison-footer"),
        )

    def on_mount(self) -> None:
        """Mount and display comparison."""
        self._display_comparison()

    def _display_comparison(self) -> None:
        """Display comparison table of results."""
        content_widget = self.query_one("#comparison-content", Static)

        if not self.results_list:
            content_widget.update("[dim]No results to compare[/dim]")
            return

        # Build comparison table
        table_rows = []

        # Header row
        header = (
            "| Metric | "
            + " | ".join([f"Run {i + 1}" for i in range(len(self.results_list))])
            + " |"
        )
        table_rows.append(header)
        table_rows.append("|" + "-" * (len(header) - 2) + "|")

        # Get common metrics
        metrics = [
            ("Strategy", "strategy", "{}", False),
            ("Symbol", "symbol", "{}", False),
            ("Method", "method", "{}", False),
            ("Simulations", "n_simulations", "{}", False),
            ("Probability of Profit", "probability_of_profit", "{:.1%}", True),
            ("Mean Return", "mean_return", "{:+.2%}", True),
            ("Median Return", "median_return", "{:+.2%}", True),
            ("Std Deviation", "std_return", "{:.2%}", False),
            ("Sharpe Ratio", "sharpe_ratio", "{:.2f}", True),
            ("VaR (95%)", "var_95", "{:+.2%}", False),
            ("Mean Drawdown", "mean_max_drawdown", "{:.2%}", False),
            ("Worst Drawdown", "worst_drawdown", "{:.2%}", False),
            ("5th Percentile", "percentile_5", "{:+.2%}", True),
            ("95th Percentile", "percentile_95", "{:+.2%}", True),
        ]

        # Build each metric row
        for metric_name, key, format_str, higher_better in metrics:
            values = []
            for result in self.results_list:
                value = result.get(key, "N/A")
                if value != "N/A":
                    try:
                        formatted = format_str.format(value)
                        values.append((formatted, value))
                    except (ValueError, TypeError):
                        values.append((str(value), value))
                else:
                    values.append(("N/A", None))

            # Find best value for highlighting (if numeric and higher_better is set)
            best_idx = None
            if higher_better and all(v[1] is not None for v in values):
                try:
                    numeric_values = [v[1] for v in values]
                    best_value = max(numeric_values)
                    best_idx = numeric_values.index(best_value)
                except (ValueError, TypeError):
                    pass

            # Build row with highlighting
            row_values = []
            for idx, (formatted, _) in enumerate(values):
                if idx == best_idx:
                    row_values.append(f"[green bold]{formatted}[/green bold]")
                else:
                    row_values.append(formatted)

            row = f"| {metric_name} | " + " | ".join(row_values) + " |"
            table_rows.append(row)

        # Add summary insights
        table_rows.append("")
        table_rows.append("[bold]Summary Insights:[/bold]")
        table_rows.append("")

        # Best overall (by Sharpe ratio)
        sharpe_ratios = [r.get("sharpe_ratio", 0) for r in self.results_list]
        if sharpe_ratios:
            best_sharpe_idx = sharpe_ratios.index(max(sharpe_ratios))
            table_rows.append(
                f"• [green]Best Risk-Adjusted Returns:[/green] Run {best_sharpe_idx + 1} (Sharpe: {sharpe_ratios[best_sharpe_idx]:.2f})"
            )

        # Highest probability of profit
        prob_profits = [r.get("probability_of_profit", 0) for r in self.results_list]
        if prob_profits:
            best_prob_idx = prob_profits.index(max(prob_profits))
            table_rows.append(
                f"• [green]Highest Profit Probability:[/green] Run {best_prob_idx + 1} ({prob_profits[best_prob_idx]:.1%})"
            )

        # Lowest drawdown
        drawdowns = [r.get("worst_drawdown", float("inf")) for r in self.results_list]
        if drawdowns:
            best_dd_idx = drawdowns.index(min(drawdowns))
            table_rows.append(
                f"• [green]Lowest Drawdown:[/green] Run {best_dd_idx + 1} ({drawdowns[best_dd_idx]:.2%})"
            )

        # Highest return
        mean_returns = [r.get("mean_return", 0) for r in self.results_list]
        if mean_returns:
            best_return_idx = mean_returns.index(max(mean_returns))
            table_rows.append(
                f"• [green]Highest Mean Return:[/green] Run {best_return_idx + 1} ({mean_returns[best_return_idx]:+.2%})"
            )

        content_widget.update("\n".join(table_rows))

    def on_button_pressed(self) -> None:
        """Handle close button."""
        self.dismiss(True)
