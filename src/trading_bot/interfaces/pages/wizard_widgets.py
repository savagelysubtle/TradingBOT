"""Wizard page widgets for the Trading Bot TUI."""

import logging
from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Input, Label, Select, Static

from trading_bot.config import BacktestConfiguration

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class WizardProgressWidget(Static):
    """Widget for displaying wizard progress indicator."""

    def __init__(self, **kwargs):
        super().__init__("", id="wizard-progress", **kwargs)

    def update_progress(self, step: int, step_text: str) -> None:
        """Update progress indicator based on current step."""
        try:
            # Build progress bar visualization
            if step == 1:
                progress_bar = "[green]●[/green]━━━[dim]○[/dim]━━━[dim]○[/dim]"
            elif step == 2:
                progress_bar = "[green]●━━━●[/green]━━━[dim]○[/dim]"
            else:  # step == 3
                progress_bar = "[green]●━━━●━━━●[/green]"

            progress_text = f"{progress_bar}  [bold]Step {step} of 3:[/bold] {step_text}"
            self.update(progress_text)
        except Exception as e:
            logger.debug(f"Failed to update wizard progress: {e}")


class WizardDataConfigWidget(Container):
    """Widget for data configuration section."""

    def __init__(self, config: BacktestConfiguration, **kwargs):
        super().__init__(id="wizard-data-config", **kwargs)
        self.config = config

    def compose(self):
        """Compose data configuration widgets."""
        yield Static("[bold]📊 Step 1: Data Configuration[/bold]", classes="step-title")
        yield Static(
            "[dim]Select exchange, trading pair, timeframe, and data period[/dim]",
            classes="step-hint",
        )

        # Row 1: Exchange and Symbol
        yield Horizontal(
            Vertical(
                Label("Exchange:"),
                Select(
                    [
                        ("Binance", "binance"),
                        ("Coinbase", "coinbase"),
                        ("Kraken", "kraken"),
                    ],
                    value=self.config.exchange or "binance",
                    id="wizard-exchange",
                    allow_blank=False,
                    classes="wizard-select",
                ),
                Static("[dim]Choose crypto exchange[/dim]", classes="field-hint"),
            ),
            Vertical(
                Label("Symbol:"),
                Input(
                    placeholder="BTC/USDT",
                    value=self.config.symbol or "",
                    id="wizard-symbol",
                ),
                Static("[dim]Format: BASE/QUOTE (e.g., BTC/USDT)[/dim]", classes="field-hint"),
            ),
            classes="wizard-row",
        )

        # Row 2: Timeframe and Candles
        yield Horizontal(
            Vertical(
                Label("Timeframe:"),
                Select(
                    [
                        ("1 Minute", "1m"),
                        ("5 Minutes", "5m"),
                        ("15 Minutes", "15m"),
                        ("1 Hour", "1h"),
                        ("4 Hours", "4h"),
                        ("1 Day", "1d"),
                    ],
                    value=self.config.timeframe or "1d",
                    id="wizard-timeframe",
                    allow_blank=False,
                    classes="wizard-select",
                ),
                Static("[dim]Candle interval[/dim]", classes="field-hint"),
            ),
            Vertical(
                Label("Candles:"),
                Input(
                    value=str(self.config.limit) if self.config.limit else "1000",
                    id="wizard-limit",
                ),
                Static("[dim]Number of candles (50-5000 recommended)[/dim]", classes="field-hint"),
            ),
            classes="wizard-row",
        )

        # Date Range Section
        yield Static(
            "[bold]📅 Date Range (Optional - overrides candle count)[/bold]",
            classes="step-title",
        )
        yield Static(
            "[dim]Leave empty to use candle count, or specify dates for exact period[/dim]",
            classes="step-hint",
        )

        # Date Range Row
        yield Horizontal(
            Vertical(
                Label("Start Date (YYYY-MM-DD):"),
                Input(
                    placeholder="2020-01-01",
                    value=self.config.start_date or "",
                    id="wizard-start-date",
                ),
                Static("[dim]Optional start date[/dim]", classes="field-hint"),
            ),
            Vertical(
                Label("End Date (YYYY-MM-DD):"),
                Input(
                    placeholder="2024-01-01",
                    value=self.config.end_date or "",
                    id="wizard-end-date",
                ),
                Static("[dim]Optional end date[/dim]", classes="field-hint"),
            ),
            classes="wizard-row",
            id="wizard-date-range-row",
        )


class WizardStrategyConfigWidget(Container):
    """Widget for strategy configuration section."""

    def __init__(self, config: BacktestConfiguration, available_strategies: list, **kwargs):
        super().__init__(id="wizard-strategy-config", **kwargs)
        self.config = config
        self.available_strategies = available_strategies

    def compose(self):
        """Compose strategy configuration widgets."""
        yield Static("[bold]🎯 Step 2: Strategy Selection[/bold]", classes="step-title")
        yield Static(
            "[dim]Choose strategy algorithm and backtesting engine[/dim]",
            classes="step-hint",
        )

        yield Horizontal(
            Vertical(
                Label("Strategy:"),
                Select(
                    self.available_strategies,
                    value=self.config.strategy_name,
                    id="wizard-strategy",
                    allow_blank=False,
                    classes="wizard-select",
                ),
                Static("[dim]Trading algorithm to test[/dim]", classes="field-hint"),
            ),
            Vertical(
                Label("Engine:"),
                Select(
                    [
                        ("Custom (Default)", "custom"),
                        ("Backtrader", "backtrader"),
                        ("VectorBT (Fast)", "vectorbt"),
                    ],
                    value=self.config.engine or "custom",
                    id="wizard-engine",
                    allow_blank=False,
                    classes="wizard-select",
                ),
                Static("[dim]VectorBT is 10-100x faster[/dim]", classes="field-hint"),
            ),
            classes="wizard-row",
        )

        # Dynamic parameters panel container
        yield Container(id="wizard-params-container")


class WizardActionWidget(Container):
    """Widget for action buttons."""

    def __init__(self, **kwargs):
        super().__init__(id="wizard-actions", **kwargs)

    def compose(self):
        """Compose action buttons."""
        yield Static("[bold]▶ Step 3: Run & View Results[/bold]", classes="step-title")
        yield Static(
            "[dim]Execute backtest and analyze performance metrics[/dim]",
            classes="step-hint",
        )

        yield Horizontal(
            Button("▶ Run Backtest", id="wizard-run", variant="success"),
            Button("📊 Generate Charts", id="wizard-charts", variant="primary"),
            Button("💾 Save as Template", id="wizard-save-template"),
            Button("🔄 Reset", id="wizard-reset"),
            classes="wizard-button-row",
        )


class WizardResultsWidget(Container):
    """Widget for displaying backtest results."""

    def __init__(self, **kwargs):
        super().__init__(id="wizard-results-section", **kwargs)

    def compose(self):
        """Compose results display widgets."""
        yield Static("[bold]📈 Results[/bold]", classes="step-title")
        yield Container(id="wizard-progress-container")  # For spinner or progress bar

        yield ScrollableContainer(
            Static(
                "[dim]Run a backtest to see results here...[/dim]",
                id="wizard-results",
            ),
            id="wizard-results-scroll",
        )

    def display_results(self, results: dict) -> None:
        """Display backtest results in formatted table."""
        logger.info("Displaying backtest results")
        results_table = Table(show_header=False, box=None, padding=(0, 1))
        results_table.add_column(style="cyan", width=22)
        results_table.add_column(width=25)

        return_pct = results["total_return_pct"]
        return_color = "green" if return_pct > 0 else "red"
        return_icon = "📈" if return_pct > 0 else "📉"

        results_table.add_row("🎯 [bold]Strategy[/bold]", results["strategy"])
        results_table.add_row("💹 [bold]Symbol[/bold]", results["symbol"])
        results_table.add_row(
            "💰 [bold]Initial Capital[/bold]", f"${results['initial_capital']:,.2f}"
        )
        results_table.add_row("💵 [bold]Final Value[/bold]", f"${results['final_value']:,.2f}")
        results_table.add_row("", "")
        results_table.add_row(
            f"{return_icon} [bold]Total Return[/bold]",
            f"[{return_color}]{results['total_return_pct']:.2f}%[/{return_color}]",
        )
        results_table.add_row(
            "📊 [bold]Buy & Hold[/bold]", f"{results['buy_hold_return_pct']:.2f}%"
        )
        results_table.add_row("", "")
        results_table.add_row("🔄 [bold]Total Trades[/bold]", str(results["total_trades"]))
        results_table.add_row("🎯 [bold]Win Rate[/bold]", f"{results['win_rate_pct']:.2f}%")
        results_table.add_row(
            "⚠️  [bold]Max Drawdown[/bold]", f"[red]{results['max_drawdown_pct']:.2f}%[/red]"
        )

        if "sharpe_ratio" in results:
            sharpe = results["sharpe_ratio"]
            sharpe_color = "green" if sharpe >= 1.0 else "yellow" if sharpe >= 0.5 else "red"
            results_table.add_row(
                "📉 [bold]Sharpe Ratio[/bold]", f"[{sharpe_color}]{sharpe:.2f}[/{sharpe_color}]"
            )

        # Add Kelly Criterion metrics if available
        if "kelly_metrics" in results:
            kelly_data = results["kelly_metrics"]
            results_table.add_row("", "")
            results_table.add_row("🎲 [bold]Kelly Criterion[/bold]", "")
            results_table.add_row("  Win Rate", f"{kelly_data['win_rate']:.1%}")
            results_table.add_row("  R:R Ratio", f"{kelly_data['reward_risk_ratio']:.2f}")
            results_table.add_row("", "")

            from trading_bot.risk.kelly_criterion import KellyMetrics, validate_kelly_parameters

            full_kelly = kelly_data["full_kelly"]
            half_kelly = kelly_data["half_kelly"]
            quarter_kelly = kelly_data["quarter_kelly"]

            full_color = "red" if full_kelly > 0.3 else "yellow" if full_kelly > 0.15 else "green"
            results_table.add_row(
                "  [bold]Full Kelly[/bold]", f"[{full_color}]{full_kelly:.1%}[/{full_color}]"
            )
            results_table.add_row(
                "  [bold]Half Kelly ⭐[/bold]", f"[yellow]{half_kelly:.1%}[/yellow]"
            )
            results_table.add_row(
                "  [bold]Quarter Kelly[/bold]", f"[green]{quarter_kelly:.1%}[/green]"
            )

            kelly_metrics_obj = KellyMetrics(
                win_rate=kelly_data["win_rate"],
                avg_win_pct=kelly_data["avg_win_pct"],
                avg_loss_pct=kelly_data["avg_loss_pct"],
                total_trades=kelly_data["total_trades"],
                reward_risk_ratio=kelly_data["reward_risk_ratio"],
            )
            warnings = validate_kelly_parameters(kelly_metrics_obj, 0.5)
            if warnings:
                results_table.add_row("", "")
                results_table.add_row("⚠️  [bold yellow]Warnings[/bold yellow]", "")
                for warning in warnings:
                    results_table.add_row(f"  {warning}", "")

        # Add portfolio performance sparkline if available
        if results.get("portfolio_history"):
            portfolio_values = [entry["portfolio_value"] for entry in results["portfolio_history"]]
            if len(portfolio_values) > 1:
                # Calculate percentage returns from initial value
                initial_value = portfolio_values[0]
                returns_pct = [(v - initial_value) / initial_value * 100 for v in portfolio_values]

                # Create a simple progress bar representation
                final_return = returns_pct[-1]
                if final_return >= 0:
                    bar_color = "green"
                    bar_char = "█"
                else:
                    bar_color = "red"
                    bar_char = "░"

                progress_bar = f"[{bar_color}]{bar_char * 20}[/{bar_color}]"

                results_table.add_row("", "")
                results_table.add_row("📈 [bold]Portfolio Performance[/bold]", progress_bar)
                results_table.add_row(
                    "",
                    f"[dim]Final return: {final_return:.1f}% over {len(portfolio_values)} periods[/dim]",
                )

        console = Console()
        with console.capture() as capture:
            console.print(results_table)

        results_widget = self.query_one("#wizard-results")
        results_widget.update(capture.get())
        logger.info("Backtest results displayed successfully")
