"""Widget for displaying Walk-Forward Optimization results."""

import logging
from typing import Any

from rich.console import Console
from rich.table import Table
from textual.widgets import Static

logger = logging.getLogger(__name__)
console = Console()


class WFOResultsWidget:
    """Widget for displaying WFO results."""

    @staticmethod
    def display_results(results: dict[str, Any], widget: Static) -> None:
        """Display WFO results in a formatted way.

        Args:
            results: WFO results dictionary
            widget: Static widget to update with results
        """
        try:
            overall = results.get("overall", {})
            periods = results.get("periods", [])

            # Build results text
            output = []

            # Overall metrics
            wfe = overall.get("wfe", 0.0)
            status = overall.get("status", "Unknown")
            num_periods = overall.get("num_periods", 0)

            wfe_color = "green" if wfe >= 0.60 else "yellow" if wfe >= 0.50 else "red"

            output.append("[bold cyan]Walk-Forward Optimization Results[/bold cyan]\n")
            output.append("═" * 60 + "\n\n")

            # Overall metrics table
            output.append("[bold]Overall Metrics[/bold]\n")
            output.append(f"Walk Forward Efficiency (WFE): [{wfe_color}]{wfe:.1%}[/{wfe_color}]\n")
            output.append(f"Status: {status}\n")
            output.append(f"Number of Periods: {num_periods}\n\n")

            # Performance metrics
            avg_is_return = overall.get("avg_in_sample_return", 0.0)
            avg_oos_return = overall.get("avg_out_of_sample_return", 0.0)
            degradation = 1 - wfe if wfe > 0 else 0.0

            output.append("[bold]Performance[/bold]\n")
            output.append(f"Avg In-Sample Return: {avg_is_return:+.2%}\n")
            output.append(f"Avg Out-of-Sample Return: {avg_oos_return:+.2%}\n")
            output.append(f"Performance Degradation: {degradation:.1%}\n\n")

            # Parameter stability
            avg_param_changes = overall.get("avg_parameter_changes", 0.0)
            output.append("[bold]Parameter Stability[/bold]\n")
            output.append(f"Avg Parameter Changes: {avg_param_changes:.1f} changes/period\n")
            output.append("[dim](Higher = less stable parameters)[/dim]\n\n")

            # Period-by-period breakdown
            if periods:
                output.append("[bold]Period-by-Period Breakdown[/bold]\n")
                output.append("─" * 60 + "\n")
                for i, period in enumerate(periods, 1):
                    is_ret = period.get("in_sample_return", 0.0)
                    oos_ret = period.get("out_of_sample_return", 0.0)
                    params = period.get("optimal_params", {})
                    params_str = ", ".join([f"{k}={v}" for k, v in params.items()])

                    output.append(f"Period {i}:\n")
                    output.append(f"  In-Sample: {is_ret:+.2%}\n")
                    output.append(f"  Out-of-Sample: {oos_ret:+.2%}\n")
                    if params_str:
                        output.append(f"  Optimal Params: {params_str}\n")
                    output.append("\n")

            # Interpretation
            output.append("[bold]Interpretation[/bold]\n")
            if wfe >= 0.60:
                output.append("[green]✓ Strategy appears robust - not significantly overfitted[/green]\n")
            elif wfe >= 0.50:
                output.append("[yellow]△ Strategy may be slightly overfitted - proceed with caution[/yellow]\n")
            else:
                output.append("[red]✗ Strategy likely overfitted - consider simplifying or using different parameters[/red]\n")

            widget.update("".join(output))

        except Exception as e:
            logger.exception(f"Error displaying WFO results: {e}")
            widget.update(f"[red]Error displaying results: {e}[/red]")

