"""Strategy parameters panel widget for dynamic parameter input."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Checkbox, Input, Static


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
            yield Static(
                "[dim]Recommended: 10-20 for hourly, 50 for daily[/dim]", id="param-short-hint"
            )
            yield Label("Long MA Period:")
            yield Input(placeholder="200", value="200", id="param-long-ma")
            yield Static(
                "[dim]Recommended: 30-50 for hourly, 200 for daily[/dim]", id="param-long-hint"
            )
            yield Label("Use RSI Filter:")
            yield Checkbox("Enable RSI filter", id="param-use-rsi")

        elif self.strategy_name in ["talib_ma", "talib_macd"]:
            if self.strategy_name == "talib_ma":
                yield Label("Short Period:")
                yield Input(placeholder="50", value="50", id="param-short-period")
                yield Static(
                    "[dim]Recommended: 10-20 for hourly, 50 for daily[/dim]", id="param-short-hint"
                )
                yield Label("Long Period:")
                yield Input(placeholder="200", value="200", id="param-long-period")
                yield Static(
                    "[dim]Recommended: 30-50 for hourly, 200 for daily[/dim]", id="param-long-hint"
                )
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

        elif self.strategy_name == "stop_hunt":
            yield Label("Support Lookback:")
            yield Input(placeholder="20", value="20", id="param-support-lookback")
            yield Static(
                "[dim]Periods to look back for support/resistance levels[/dim]",
                id="param-support-lookback-hint",
            )
            yield Label("Cluster Min Factors:")
            yield Input(placeholder="3", value="3", id="param-cluster-min-factors")
            yield Static(
                "[dim]Minimum converging factors for stop cluster[/dim]",
                id="param-cluster-hint",
            )
            yield Label("Entry Distance %:")
            yield Input(placeholder="0.5", value="0.5", id="param-entry-distance-pct")
            yield Static(
                "[dim]Percentage distance from cluster to enter[/dim]",
                id="param-entry-distance-hint",
            )
            yield Label("Volume Spike Multiplier:")
            yield Input(placeholder="2.0", value="2.0", id="param-volume-spike-multiplier")
            yield Static(
                "[dim]Volume spike threshold multiplier[/dim]",
                id="param-volume-spike-hint",
            )

    def get_parameters(self) -> dict:
        """Extract parameter values from inputs."""
        params = {}

        if self.strategy_name == "ma_crossover":
            try:
                params["short_window"] = int(self.query_one("#param-short-ma", Input).value)
                params["long_window"] = int(self.query_one("#param-long-ma", Input).value)
                params["use_rsi"] = self.query_one("#param-use-rsi", Checkbox).value
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

        elif self.strategy_name == "stop_hunt":
            try:
                params["support_lookback"] = int(
                    self.query_one("#param-support-lookback", Input).value
                )
                params["cluster_min_factors"] = int(
                    self.query_one("#param-cluster-min-factors", Input).value
                )
                params["entry_distance_pct"] = float(
                    self.query_one("#param-entry-distance-pct", Input).value
                )
                params["volume_spike_multiplier"] = float(
                    self.query_one("#param-volume-spike-multiplier", Input).value
                )
            except Exception:
                params = {
                    "support_lookback": 20,
                    "cluster_min_factors": 3,
                    "entry_distance_pct": 0.5,
                    "volume_spike_multiplier": 2.0,
                }

        return params

    def update_strategy(self, strategy_name: str) -> None:
        """Update panel for new strategy."""
        self.strategy_name = strategy_name
        # Remove all children and recompose
        self.remove_children()
        # Convert generator to list for mount_all
        widgets = list(self.compose())
        self.mount_all(widgets)
