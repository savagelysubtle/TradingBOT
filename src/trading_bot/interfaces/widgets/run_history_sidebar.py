"""Run history sidebar widget for displaying recent backtest runs."""

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Static

from trading_bot.config import BacktestHistory, BacktestRun


class RunHistorySidebar(ScrollableContainer):
    """Sidebar showing recent backtest run history."""

    DEFAULT_CSS = """
    RunHistorySidebar {
        width: 35%;
        min-width: 30;
        max-width: 50;
        height: 100%;
        background: $boost;
        border: panel $primary;
        padding: 1;
    }

    RunHistorySidebar Vertical {
        height: auto;
        width: 100%;
    }

    RunHistorySidebar .section-title {
        background: $primary;
        color: $text;
        padding: 0 1;
        margin: 1 0;
    }

    RunHistorySidebar .run-item {
        padding: 0 1;
        margin: 1 0;
        border-left: solid $primary;
    }

    RunHistorySidebar .run-header {
        color: $text;
        margin-bottom: 1;
    }

    RunHistorySidebar .run-metric {
        color: $text-muted;
    }

    RunHistorySidebar .run-metric-value {
        color: $success;
    }

    RunHistorySidebar .run-metric-negative {
        color: $error;
    }

    RunHistorySidebar .no-runs {
        color: $text-muted;
        padding: 1;
        text-align: center;
    }
    """

    def __init__(self, history: BacktestHistory, **kwargs):
        """Initialize sidebar with history."""
        super().__init__(**kwargs)
        self.history = history
        self.max_runs = 10  # Show last 10 runs

    def compose(self) -> ComposeResult:
        """Compose sidebar widgets."""
        with Vertical():
            yield Static("[bold cyan]Recent Runs[/bold cyan]", classes="section-title")
            yield Static("", id="history-runs-list", classes="config-item")

    def on_mount(self) -> None:
        """Update display on mount."""
        self.update_display()

    def update_display(self) -> None:
        """Update sidebar display with recent runs."""
        runs_list = self.query_one("#history-runs-list", Static)
        runs = self.history.get_runs(limit=self.max_runs)

        if not runs:
            runs_list.update("[dim]No backtest runs yet[/dim]\n[dim]Run a backtest to see history[/dim]")
            return

        # Build runs display
        runs_text = ""
        for i, run in enumerate(runs):
            # Format timestamp
            try:
                # Handle ISO format with or without timezone
                timestamp_str = run.timestamp.replace("Z", "+00:00")
                if "T" in timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.split(".")[0])
                else:
                    timestamp = datetime.fromisoformat(timestamp_str)
                time_str = timestamp.strftime("%m/%d %H:%M")
            except Exception:
                # Fallback: use first 16 chars or full string
                time_str = run.timestamp[:16] if len(run.timestamp) > 16 else run.timestamp

            # Get key metrics
            results = run.results
            return_pct = results.get("total_return_pct", 0.0)
            total_trades = results.get("total_trades", 0)
            win_rate = results.get("win_rate_pct", 0.0)
            sharpe = results.get("sharpe_ratio", 0.0)

            # Format return color
            return_color = "run-metric-value" if return_pct >= 0 else "run-metric-negative"
            return_sign = "+" if return_pct >= 0 else ""

            # Build run item
            runs_text += (
                f"[bold]{time_str}[/bold]  "
                f"[dim]{run.config.strategy_name}[/dim]\n"
                f"  {run.config.symbol}  [dim]{run.config.timeframe}[/dim]\n"
                f"  Return: [{return_color}]{return_sign}{return_pct:.2f}%[/{return_color}]  "
                f"[dim]Trades: {total_trades}[/dim]\n"
                f"  [dim]Win Rate: {win_rate:.1f}%[/dim]"
            )

            if sharpe > 0:
                sharpe_color = "run-metric-value" if sharpe >= 1.0 else "run-metric"
                runs_text += f"  [dim]Sharpe: [{sharpe_color}]{sharpe:.2f}[/{sharpe_color}][/dim]"

            runs_text += "\n\n"

        runs_list.update(runs_text.rstrip())

    def refresh_runs(self) -> None:
        """Refresh the runs display."""
        self.update_display()

