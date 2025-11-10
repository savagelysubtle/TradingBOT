"""Status sidebar widget for displaying current configuration state."""

from textual.app import ComposeResult
from textual.containers import ScrollableContainer, Vertical
from textual.widgets import Button, Static

from trading_bot.config import BacktestConfiguration


class StatusSidebar(ScrollableContainer):
    """Persistent sidebar showing current configuration state."""

    DEFAULT_CSS = """
    StatusSidebar {
        width: 40%;
        min-width: 40;
        max-width: 65;
        height: 100%;
        background: $boost;
        border: panel $primary;
        padding: 1;
    }

    StatusSidebar Vertical {
        height: auto;
        width: 100%;
    }

    StatusSidebar .section-title {
        background: $primary;
        color: $text;
        padding: 0 1;
        margin: 1 0;
    }

    StatusSidebar .config-item {
        padding: 0 1;
        color: $text-muted;
    }

    StatusSidebar .config-value {
        color: $success;
    }

    StatusSidebar .not-configured {
        color: $warning;
    }

    StatusSidebar Button {
        width: 100%;
        margin: 1 0;
    }
    """

    def __init__(self, config: BacktestConfiguration, **kwargs):
        """Initialize sidebar with configuration."""
        super().__init__(**kwargs)
        self.config = config

    def compose(self) -> ComposeResult:
        """Compose sidebar widgets."""
        with Vertical():
            yield Static("[bold cyan]Current Setup[/bold cyan]", classes="section-title")
            yield Static("", id="sidebar-data-info", classes="config-item")
            yield Static("", id="sidebar-strategy-info", classes="config-item")
            yield Static("", id="sidebar-engine-info", classes="config-item")
            yield Static("", id="sidebar-status", classes="config-item")
            yield Vertical(
                Button("▶ Run Backtest", id="sidebar-run", variant="success"),
                Button("💾 Save Template", id="sidebar-save", variant="primary"),
                Button("📂 Load Template", id="sidebar-load"),
                Button("🔄 Reset", id="sidebar-reset"),
            )

    def on_mount(self) -> None:
        """Update display on mount."""
        self.update_display()

    def update_display(self) -> None:
        """Update sidebar display with current config."""
        # Data section
        data_info = self.query_one("#sidebar-data-info", Static)
        data_text = (
            f"[bold]📊 Data[/bold]\n"
            f"  Exchange: [config-value]{self.config.exchange}[/config-value]\n"
            f"  Symbol: [config-value]{self.config.symbol}[/config-value]\n"
            f"  Timeframe: [config-value]{self.config.timeframe}[/config-value]\n"
        )
        if self.config.start_date and self.config.end_date:
            data_text += (
                f"  Date Range: [config-value]{self.config.start_date}[/config-value] to "
                f"[config-value]{self.config.end_date}[/config-value]\n"
            )
        else:
            data_text += f"  Candles: [config-value]{self.config.limit}[/config-value]\n"
        data_info.update(data_text)

        # Strategy section
        strategy_info = self.query_one("#sidebar-strategy-info", Static)
        params_str = ", ".join(f"{k}={v}" for k, v in self.config.strategy_params.items())
        strategy_info.update(
            f"[bold]🎯 Strategy[/bold]\n"
            f"  Name: [config-value]{self.config.strategy_name}[/config-value]\n"
            f"  Params: [dim]{params_str}[/dim]"
        )

        # Engine section
        engine_info = self.query_one("#sidebar-engine-info", Static)
        engine_info.update(
            f"[bold]⚙️ Engine[/bold]\n  Type: [config-value]{self.config.engine}[/config-value]"
        )

        # Status section
        status = self.query_one("#sidebar-status", Static)
        if self.config.is_complete():
            status.update("[green]✓ Ready to run[/green]")
        else:
            status.update("[yellow]⚠ Configuration incomplete[/yellow]")

