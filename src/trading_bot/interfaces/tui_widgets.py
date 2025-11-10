"""Custom widgets for the Trading Bot TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Input, Static

from trading_bot.config import BacktestConfiguration


class StatusSidebar(Container):
    """Persistent sidebar showing current configuration state."""

    DEFAULT_CSS = """
    StatusSidebar {
        width: 30;
        background: $boost;
        border: solid $primary;
        padding: 1;
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


class StrategyParametersPanel(Vertical):
    """Dynamic panel for strategy-specific parameters."""

    DEFAULT_CSS = """
    StrategyParametersPanel {
        height: auto;
        padding: 1;
    }

    StrategyParametersPanel Label {
        margin: 1 0 0 0;
    }

    StrategyParametersPanel Input {
        width: 30;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, strategy_name: str = "ma_crossover", **kwargs):
        """Initialize parameters panel."""
        super().__init__(**kwargs)
        self.strategy_name = strategy_name

    def compose(self) -> ComposeResult:
        """Compose parameter widgets based on strategy."""
        from textual.widgets import Input, Label

        yield Static("[bold]Strategy Parameters[/bold]")

        if self.strategy_name == "ma_crossover":
            yield Label("Short MA Period:")
            yield Input(placeholder="50", value="50", id="param-short-ma")
            yield Static("[dim]Recommended: 10-20 for hourly, 50 for daily[/dim]", id="param-short-hint")
            yield Label("Long MA Period:")
            yield Input(placeholder="200", value="200", id="param-long-ma")
            yield Static("[dim]Recommended: 30-50 for hourly, 200 for daily[/dim]", id="param-long-hint")
            yield Label("Use RSI Filter:")
            from textual.widgets import Checkbox

            yield Checkbox("Enable RSI filter", id="param-use-rsi")

        elif self.strategy_name in ["talib_ma", "talib_macd"]:
            if self.strategy_name == "talib_ma":
                yield Label("Short Period:")
                yield Input(placeholder="50", value="50", id="param-short-period")
                yield Static("[dim]Recommended: 10-20 for hourly, 50 for daily[/dim]", id="param-short-hint")
                yield Label("Long Period:")
                yield Input(placeholder="200", value="200", id="param-long-period")
                yield Static("[dim]Recommended: 30-50 for hourly, 200 for daily[/dim]", id="param-long-hint")
            else:  # MACD
                yield Label("Fast Period:")
                yield Input(placeholder="12", value="12", id="param-fast-period")
                yield Label("Slow Period:")
                yield Input(placeholder="26", value="26", id="param-slow-period")
                yield Label("Signal Period:")
                yield Input(placeholder="9", value="9", id="param-signal-period")

        elif self.strategy_name == "supertrend":
            yield Label("ATR Period:")
            yield Input(placeholder="10", value="10", id="param-period")
            yield Label("Multiplier:")
            yield Input(placeholder="3.0", value="3.0", id="param-multiplier")

        elif self.strategy_name == "bollinger":
            yield Label("Period:")
            yield Input(placeholder="20", value="20", id="param-period")
            yield Label("Standard Deviation:")
            yield Input(placeholder="2.0", value="2.0", id="param-std-dev")

        elif self.strategy_name == "ichimoku":
            yield Label("Tenkan Period:")
            yield Input(placeholder="9", value="9", id="param-tenkan")
            yield Label("Kijun Period:")
            yield Input(placeholder="26", value="26", id="param-kijun")
            yield Label("Senkou B Period:")
            yield Input(placeholder="52", value="52", id="param-senkou")

        elif self.strategy_name == "ml_randomforest":
            yield Label("Lookback Period:")
            yield Input(placeholder="50", value="50", id="param-lookback")
            yield Label("Min Trade Interval:")
            yield Input(placeholder="5", value="5", id="param-min-interval")

    def get_parameters(self) -> dict:
        """Extract parameter values from inputs."""
        params = {}

        if self.strategy_name == "ma_crossover":
            try:
                params["short_window"] = int(self.query_one("#param-short-ma", Input).value)
                params["long_window"] = int(self.query_one("#param-long-ma", Input).value)
                params["use_rsi"] = self.query_one("#param-use-rsi").value
            except Exception:
                params = {"short_window": 50, "long_window": 200, "use_rsi": False}

        elif self.strategy_name == "talib_ma":
            try:
                params["short_period"] = int(self.query_one("#param-short-period", Input).value)
                params["long_period"] = int(self.query_one("#param-long-period", Input).value)
            except Exception:
                params = {"short_period": 50, "long_period": 200}

        elif self.strategy_name == "talib_macd":
            try:
                params["fast_period"] = int(self.query_one("#param-fast-period", Input).value)
                params["slow_period"] = int(self.query_one("#param-slow-period", Input).value)
                params["signal_period"] = int(self.query_one("#param-signal-period", Input).value)
            except Exception:
                params = {"fast_period": 12, "slow_period": 26, "signal_period": 9}

        elif self.strategy_name == "supertrend":
            try:
                params["period"] = int(self.query_one("#param-period", Input).value)
                params["multiplier"] = float(self.query_one("#param-multiplier", Input).value)
            except Exception:
                params = {"period": 10, "multiplier": 3.0}

        elif self.strategy_name == "bollinger":
            try:
                params["period"] = int(self.query_one("#param-period", Input).value)
                params["std_dev"] = float(self.query_one("#param-std-dev", Input).value)
            except Exception:
                params = {"period": 20, "std_dev": 2.0}

        elif self.strategy_name == "ichimoku":
            try:
                params["tenkan_period"] = int(self.query_one("#param-tenkan", Input).value)
                params["kijun_period"] = int(self.query_one("#param-kijun", Input).value)
                params["senkou_b_period"] = int(self.query_one("#param-senkou", Input).value)
            except Exception:
                params = {"tenkan_period": 9, "kijun_period": 26, "senkou_b_period": 52}

        elif self.strategy_name == "ml_randomforest":
            try:
                params["lookback"] = int(self.query_one("#param-lookback", Input).value)
                params["min_trade_interval"] = int(
                    self.query_one("#param-min-interval", Input).value
                )
            except Exception:
                params = {"lookback": 50, "min_trade_interval": 5}

        return params

    def update_strategy(self, strategy_name: str) -> None:
        """Update panel for new strategy."""
        self.strategy_name = strategy_name
        # Remove all children and recompose
        self.remove_children()
        self.mount_all(self.compose())
