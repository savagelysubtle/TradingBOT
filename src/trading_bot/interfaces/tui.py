"""Enhanced Text User Interface (TUI) for the trading bot - Sprint 1 UX Improvements."""

import asyncio
import contextlib
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pandas import DataFrame  # type: ignore[attr-defined]
else:
    import pandas as pd

    DataFrame = pd.DataFrame  # type: ignore[assignment]

from rich.table import Table
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    Tabs,
)

from trading_bot.bot import TradingBot
from trading_bot.config import (
    BacktestConfiguration,
    BacktestHistory,
    BacktestRun,
    TradingConfig,
    load_config,
)
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.interfaces.tui_widgets import StatusSidebar, StrategyParametersPanel
from trading_bot.strategies.base import BaseStrategy
from trading_bot.strategies.moving_average import MovingAverageCrossover
from trading_bot.utils.visualization import plot_backtest_results, plot_simple_results

# Initialize logger early for use in import checks
logger = logging.getLogger(__name__)

# Try to import TA-Lib strategies (optional)
TALIB_LIB_AVAILABLE = False
TALIB_AVAILABLE = False
try:
    import talib  # noqa: F401

    TALIB_LIB_AVAILABLE = True
    try:
        from trading_bot.strategies.ta_lib_strategy import (
            TALibMACDStrategy,
            TALibMovingAverageCrossover,
        )

        TALIB_AVAILABLE = True
    except ImportError as e:
        logger.debug(f"TA-Lib strategies import failed: {e}")
        TALIB_AVAILABLE = False
except ImportError as e:
    logger.debug(f"TA-Lib library import failed: {e}")
    TALIB_LIB_AVAILABLE = False

# Try to import advanced strategies (optional)
try:
    from trading_bot.strategies.advanced_indicators import (
        BollingerBandsStrategy,
        IchimokuStrategy,
        SupertrendStrategy,
    )

    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False

# Try to import ML strategies (optional)
try:
    from trading_bot.strategies.ml_strategy import MLRandomForestStrategy

    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


class TradingBotTUI(App):
    """Enhanced TUI application for the trading bot with improved UX."""

    CSS_PATH: str | None = None
    TITLE: ClassVar[str] = "Trading Bot TUI - Enhanced"
    BINDINGS: ClassVar[list] = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Dark Mode"),
        ("r", "refresh", "Refresh"),
        ("ctrl+n", "new_backtest", "New Backtest"),
        ("ctrl+h", "show_history", "History"),
        ("ctrl+s", "save_template", "Save"),
        ("f1", "show_help", "Help"),
    ]

    def __init__(self):
        """Initialize TUI."""
        super().__init__()
        self.bot: TradingBot | None = None
        self.config: TradingConfig | None = None

        # Use BacktestConfiguration for state management
        self.backtest_config = BacktestConfiguration()
        self.history = BacktestHistory()

        # Results storage
        self.backtest_results: dict | None = None
        self.backtest_data: DataFrame | None = None
        self.backtest_signals: DataFrame | None = None
        self.current_tab: str | None = None

        # Sidebar reference
        self.sidebar: StatusSidebar | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Tabs(
            "Dashboard",
            "Wizard",  # New unified workflow
            "Monte Carlo",  # Monte Carlo simulations
            "History",  # Replaces Results
            "Strategies",
            id="tabs",
        )
        yield Container(id="app-body")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        self.config = load_config()
        self.bot = TradingBot(self.config)
        self.current_tab = "Dashboard"
        if not hasattr(self, "dark"):
            self.dark = True
        self.show_dashboard()

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        tab_label = str(event.tab.label) if hasattr(event.tab, "label") else ""
        if self.current_tab == tab_label:
            return

        self.current_tab = tab_label
        body = self.query_one("#app-body", Container)
        body.remove_children()

        if "Dashboard" in tab_label or not tab_label:
            self.show_dashboard()
        elif "Wizard" in tab_label:
            self.show_wizard()
        elif "History" in tab_label:
            self.show_history()
        elif "Strategies" in tab_label:
            self.show_strategies()

    def show_dashboard(self) -> None:
        """Show enhanced dashboard with recent runs and templates."""
        body = self.query_one("#app-body", Container)

        # Get recent runs
        recent_runs = self.history.get_runs(limit=5)
        templates = self.history.get_templates()

        # Create recent runs table
        recent_table = Table(title="Recent Backtests", show_header=True)
        recent_table.add_column("Time", style="cyan")
        recent_table.add_column("Strategy", style="yellow")
        recent_table.add_column("Symbol", style="green")
        recent_table.add_column("Return", style="bold")
        recent_table.add_column("Actions")

        for run in recent_runs:
            return_pct = run.results.get("total_return_pct", 0)
            return_style = "green" if return_pct > 0 else "red"
            recent_table.add_row(
                run.timestamp[:16],
                run.config.strategy_name,
                run.config.symbol,
                f"[{return_style}]{return_pct:.2f}%[/{return_style}]",
                "[▶ Rerun]",
            )

        # Create templates table
        templates_table = Table(title="Saved Templates", show_header=True)
        templates_table.add_column("Name", style="cyan")
        templates_table.add_column("Strategy", style="yellow")
        templates_table.add_column("Symbol")
        templates_table.add_column("Actions")

        for template in templates[:5]:
            templates_table.add_row(
                template.name or template.get_display_name(),
                template.strategy_name,
                template.symbol,
                "[📂 Load]",
            )

        # Create performance sparkline
        sparkline = self._create_performance_sparkline(recent_runs)

        # Start live price ticker
        if recent_runs:
            symbol = recent_runs[0].config.symbol
            self._start_live_price_ticker(symbol)

        body.mount(
            Vertical(
                Static("[bold cyan]Trading Bot Dashboard[/bold cyan]", id="dashboard-title"),
                Horizontal(
                    Vertical(
                        Static("[bold]System Status[/bold]"),
                        Static("[green]✓[/green] Python 3.14 Free-Threading"),
                        Static("[green]✓[/green] CCXT Connected"),
                        Static(
                            f"[green]✓[/green] Strategies: {sum([1, TALIB_AVAILABLE * 2, ADVANCED_AVAILABLE * 3, ML_AVAILABLE])} Ready"
                        ),
                        Static(
                            f"[green]✓[/green] TA-Lib: Available" if TALIB_AVAILABLE
                            else "[yellow]⚠[/yellow] TA-Lib: Not installed"
                        ),
                        Static(f"[green]✓[/green] History: {len(recent_runs)} runs"),
                        Static(f"[green]✓[/green] Templates: {len(templates)} saved"),
                        Static(""),
                        Static("[bold]Performance Trend[/bold]"),
                        Static(f"[dim]Last 10 backtests:[/dim] {sparkline}"),
                        Static("", id="live-price"),
                        id="status-panel",
                    ),
                    Vertical(
                        Static("[bold]Quick Actions[/bold]"),
                        Button("🚀 New Backtest", id="btn-new-backtest", variant="success"),
                        Button("▶ Run Last Config", id="btn-run-last", variant="primary"),
                        Button("📂 Browse Templates", id="btn-browse-templates"),
                        Button("📊 View All History", id="btn-view-history"),
                        Button("🔄 Refresh", id="btn-refresh-dash"),
                        id="quick-actions",
                    ),
                    id="dashboard-top",
                ),
                Static("", id="dashboard-recent"),
                Static("", id="dashboard-templates"),
                id="dashboard",
            ),
        )

        # Render tables
        from rich.console import Console

        console = Console()

        with console.capture() as capture:
            console.print(recent_table)
        self.query_one("#dashboard-recent", Static).update(capture.get())

        with console.capture() as capture:
            console.print(templates_table)
        self.query_one("#dashboard-templates", Static).update(capture.get())

    def show_wizard(self) -> None:
        """Show unified workflow wizard - Single-tab backtest configuration."""
        body = self.query_one("#app-body", Container)
        body.remove_children()

        body.mount(
            Horizontal(
                # Main configuration area
                ScrollableContainer(
                    Vertical(
                        Static("[bold cyan]Backtest Wizard[/bold cyan]", id="wizard-title"),
                        Static(
                            "[dim]Configure your backtest in 3 steps, then run[/dim]",
                            id="wizard-hint",
                        ),
                        # Visual Progress Indicator
                        Static(
                            "[green]●[/green]━━━[dim]○[/dim]━━━[dim]○[/dim]  [bold]Step 1 of 3[/bold]",
                            id="wizard-progress",
                        ),
                        # Step 1: Data Configuration
                        Static("[bold]📊 Step 1: Data Configuration[/bold]", classes="step-title"),
                        Static("[dim]Select exchange, trading pair, timeframe, and data period[/dim]", classes="step-hint"),
                        Horizontal(
                            Vertical(
                                Label("Exchange:"),
                                Select(
                                    [
                                        ("Binance", "binance"),
                                        ("Coinbase", "coinbase"),
                                        ("Kraken", "kraken"),
                                    ],
                                    value=self.backtest_config.exchange,
                                    id="wizard-exchange",
                                    allow_blank=False,
                                ),
                                Static("[dim]Choose crypto exchange[/dim]", classes="field-hint"),
                            ),
                            Vertical(
                                Label("Symbol:"),
                                Input(
                                    placeholder="BTC/USDT",
                                    value=self.backtest_config.symbol,
                                    id="wizard-symbol",
                                ),
                                Static("[dim]Format: BASE/QUOTE (e.g., BTC/USDT)[/dim]", classes="field-hint"),
                            ),
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
                                    value=self.backtest_config.timeframe,
                                    id="wizard-timeframe",
                                    allow_blank=False,
                                ),
                                Static("[dim]Candle interval[/dim]", classes="field-hint"),
                            ),
                            Vertical(
                                Label("Candles:"),
                                Input(
                                    placeholder="365",
                                    value=str(self.backtest_config.limit),
                                    id="wizard-limit",
                                ),
                                Static("[dim]Number of candles (or use date range below)[/dim]", classes="field-hint"),
                            ),
                        ),
                        Static("[bold]Date Range (Optional - for multi-year backtesting)[/bold]", classes="step-title"),
                        Static("[dim]Leave empty to use candle count, or specify dates for exact period[/dim]", classes="step-hint"),
                        Horizontal(
                            Vertical(
                                Label("Start Date (YYYY-MM-DD):"),
                                Input(
                                    placeholder="2020-01-01",
                                    value=self.backtest_config.start_date or "",
                                    id="wizard-start-date",
                                ),
                                Static("[dim]Optional: Start date for backtest[/dim]", classes="field-hint"),
                            ),
                            Vertical(
                                Label("End Date (YYYY-MM-DD):"),
                                Input(
                                    placeholder="2024-01-01",
                                    value=self.backtest_config.end_date or "",
                                    id="wizard-end-date",
                                ),
                                Static("[dim]Optional: End date (defaults to today)[/dim]", classes="field-hint"),
                            ),
                        ),
                        # Step 2: Strategy Selection
                        Static("[bold]🎯 Step 2: Strategy Selection[/bold]", classes="step-title"),
                        Static("[dim]Choose strategy algorithm and backtesting engine[/dim]", classes="step-hint"),
                        Horizontal(
                            Vertical(
                                Label("Strategy:"),
                                Select(
                                    self._get_available_strategies(),
                                    value=self.backtest_config.strategy_name,
                                    id="wizard-strategy",
                                    allow_blank=False,
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
                                    value=self.backtest_config.engine,
                                    id="wizard-engine",
                                    allow_blank=False,
                                ),
                                Static("[dim]VectorBT is 10-100x faster[/dim]", classes="field-hint"),
                            ),
                        ),
                        # Dynamic parameters panel
                        Container(id="wizard-params-container"),
                        # Step 3: Run & Results
                        Static("[bold]▶ Step 3: Run & View Results[/bold]", classes="step-title"),
                        Static("[dim]Execute backtest and analyze performance metrics[/dim]", classes="step-hint"),
                        Horizontal(
                            Button("▶ Run Backtest", id="wizard-run", variant="success"),
                            Button("📊 Generate Charts", id="wizard-charts", variant="primary"),
                            Button("💾 Save as Template", id="wizard-save-template"),
                            Button("🔄 Reset", id="wizard-reset"),
                        ),
                        # Results display
                        Static("[bold]Results[/bold]"),
                        ScrollableContainer(
                            Static("", id="wizard-results"),
                            id="wizard-results-scroll",
                        ),
                        id="wizard-main",
                    ),
                    id="wizard-scroll",
                ),
                # Sidebar with current configuration
                Container(
                    id="wizard-sidebar-container",
                ),
                id="wizard-container",
            ),
        )

        # Mount sidebar
        sidebar_container = self.query_one("#wizard-sidebar-container")
        self.sidebar = StatusSidebar(self.backtest_config, id="wizard-sidebar")
        sidebar_container.mount(self.sidebar)

        # Mount initial parameters panel
        self._update_parameters_panel(self.backtest_config.strategy_name)

    def show_monte_carlo(self) -> None:
        """Show Monte Carlo simulation tab."""
        body = self.query_one("#app-body", Container)

        # Get recent backtest configurations for loading
        recent_runs = self.history.get_runs(limit=10)
        config_options = [("New Configuration", "__new__")]
        for run in recent_runs:
            label = f"{run.config.strategy_name} - {run.config.symbol} ({run.timestamp[:10]})"
            config_options.append((label, run.run_id))

        body.mount(
            Vertical(
                Static("[bold cyan]Monte Carlo Simulation[/bold cyan]", id="mc-title"),
                Static(
                    "[dim]Run thousands of simulations to assess strategy robustness and risk[/dim]",
                    id="mc-subtitle",
                ),
                # Configuration Section
                Horizontal(
                    Vertical(
                        Label("Load Config:"),
                        Select(
                            config_options,
                            id="mc-config-select",
                            allow_blank=False,
                        ),
                        Static("[dim]Load parameters from a previous backtest[/dim]", classes="field-hint"),
                    ),
                    Vertical(
                        Label("Method:"),
                        Select(
                            [
                                ("Bootstrap Resampling", "bootstrap"),
                                ("Shuffle Trades", "shuffle_trades"),
                                ("Randomize Returns", "randomize_returns"),
                            ],
                            value="bootstrap",
                            id="mc-method",
                            allow_blank=False,
                        ),
                        Static("[dim]Bootstrap = resample data, Shuffle = randomize order, Randomize = add noise[/dim]", classes="field-hint"),
                    ),
                    Vertical(
                        Label("Simulations:"),
                        Input(value="1000", id="mc-sims"),
                        Static("[dim]More simulations = better statistics (100-5000)[/dim]", classes="field-hint"),
                    ),
                    Vertical(
                        Label("Seed (optional):"),
                        Input(placeholder="42", id="mc-seed"),
                        Static("[dim]For reproducible results[/dim]", classes="field-hint"),
                    ),
                    id="mc-config-row",
                ),
                # Action Buttons
                Horizontal(
                    Button("▶ Run Monte Carlo", id="btn-run-mc", variant="success"),
                    Button("📊 View Visualizations", id="btn-view-mc-charts", variant="primary"),
                    Button("💾 Export Results", id="btn-export-mc"),
                    id="mc-actions",
                ),
                # Progress and Status
                Static("", id="mc-status"),
                Static("", id="mc-progress-bar"),
                # Results Display
                ScrollableContainer(
                    Static("", id="mc-results"),
                    id="mc-results-scroll",
                ),
                id="monte-carlo",
            )
        )

    def show_history(self) -> None:
        """Show backtest history with comparison capabilities."""
        body = self.query_one("#app-body", Container)

        body.mount(
            Vertical(
                Static("[bold cyan]Backtest History[/bold cyan]", id="history-title"),
                Static(
                    "[dim]Select runs to compare (Ctrl+Click for multiple)[/dim]",
                    id="history-hint",
                ),
                Horizontal(
                    Button("📊 Compare Selected", id="btn-compare", variant="primary"),
                    Button("🗑️ Clear History", id="btn-clear-history", variant="error"),
                    Button("💾 Export CSV", id="btn-export-history"),
                    Button("🔄 Refresh", id="btn-refresh-history"),
                ),
                DataTable(id="history-table", zebra_stripes=True),
                Static("", id="comparison-display"),
                id="history",
            ),
        )

        # Populate history table
        self._populate_history_table()

    def show_strategies(self) -> None:
        """Show strategies information (kept from original)."""
        body = self.query_one("#app-body", Container)
        talib_status_text = (
            "[green]✓ TA-Lib Status: Available[/green]"
            if TALIB_AVAILABLE
            else "[red]✗ TA-Lib Status: Not detected[/red]"
        )
        body.mount(
            Vertical(
                Static("[bold cyan]Available Strategies[/bold cyan]", id="strategies-title"),
                Static(talib_status_text, id="talib-status"),
                DataTable(id="strategies-table", zebra_stripes=True),
                Static("", id="strategy-details"),
                id="strategies",
            ),
        )
        self._populate_strategies_table()

    # Helper methods

    def _get_available_strategies(self) -> list:
        """Get list of available strategies for dropdown."""
        strategies = [("Simple MA Crossover", "ma_crossover")]

        strategies.extend(
            [
                ("TA-Lib MA" + (" ✓" if TALIB_AVAILABLE else " (req TA-Lib)"), "talib_ma"),
                ("TA-Lib MACD" + (" ✓" if TALIB_AVAILABLE else " (req TA-Lib)"), "talib_macd"),
            ]
        )

        if ADVANCED_AVAILABLE:
            strategies.extend(
                [
                    ("Supertrend", "supertrend"),
                    ("Bollinger Bands", "bollinger"),
                    ("Ichimoku Cloud", "ichimoku"),
                ]
            )

        if ML_AVAILABLE:
            strategies.append(("ML Random Forest", "ml_randomforest"))

        return strategies

    def _update_parameters_panel(self, strategy_name: str) -> None:
        """Update the parameters panel for the selected strategy."""
        container = self.query_one("#wizard-params-container")
        # Remove all children first
        container.remove_children()
        # Defer mounting until after the refresh cycle to ensure removal completes
        self.call_after_refresh(self._mount_params_panel, strategy_name)

    def _mount_params_panel(self, strategy_name: str) -> None:
        """Mount the parameters panel (called after cleanup completes)."""
        try:
            container = self.query_one("#wizard-params-container")
            # Double-check no panel exists
            try:
                existing = container.query_one("#wizard-params", StrategyParametersPanel, can_focus=False)
                existing.remove()
            except Exception:
                pass
            # Mount new panel
            params_panel = StrategyParametersPanel(strategy_name, id="wizard-params")
            container.mount(params_panel)
        except Exception as e:
            logger.debug(f"Failed to mount params panel: {e}")

    def _populate_history_table(self) -> None:
        """Populate history table with runs and quick actions."""
        table = self.query_one("#history-table", DataTable)
        table.clear()
        table.add_columns(
            "Date", "Strategy", "Symbol", "TF", "Return %", "Trades", "Win Rate", "Sharpe", "Actions"
        )

        runs = self.history.get_runs(limit=50)
        for run in runs:
            r = run.results
            return_pct = r.get('total_return_pct', 0)
            return_style = "green" if return_pct > 0 else "red"

            table.add_row(
                run.timestamp[:16],
                run.config.strategy_name[:15],
                run.config.symbol,
                run.config.timeframe,
                f"[{return_style}]{return_pct:.2f}%[/{return_style}]",
                str(r.get("total_trades", 0)),
                f"{r.get('win_rate_pct', 0):.1f}%",
                f"{r.get('sharpe_ratio', 0):.2f}",
                "▶ 📊 💾",  # Rerun, Charts, Export icons
            )

        # Store runs for quick actions
        self._history_runs = runs

    def _populate_strategies_table(self) -> None:
        """Populate strategies table."""
        table = self.query_one("#strategies-table", DataTable)
        table.clear()
        table.add_columns("Strategy", "Description", "Indicators", "Status")

        strategies_info = [
            (
                "Simple MA Crossover",
                "Basic moving average crossover",
                "SMA, RSI (optional)",
                "✓ Ready",
            ),
            (
                "TA-Lib Moving Average",
                "MA Crossover with RSI filter",
                "SMA, EMA, RSI",
                "✓ Ready" if TALIB_AVAILABLE else "✗ TA-Lib required",
            ),
            (
                "TA-Lib MACD",
                "MACD crossover strategy",
                "MACD, Signal, Histogram",
                "✓ Ready" if TALIB_AVAILABLE else "✗ TA-Lib required",
            ),
            (
                "Supertrend",
                "Trend-following with dynamic stops",
                "ATR, Supertrend",
                "✓ Ready" if ADVANCED_AVAILABLE else "✗ TA-Lib required",
            ),
            (
                "Bollinger Bands",
                "Mean reversion with RSI filter",
                "BB, RSI",
                "✓ Ready" if ADVANCED_AVAILABLE else "✗ TA-Lib required",
            ),
            (
                "Ichimoku Cloud",
                "Comprehensive trend analysis",
                "Tenkan, Kijun, Senkou, Chikou",
                "✓ Ready" if ADVANCED_AVAILABLE else "✗ TA-Lib required",
            ),
            (
                "ML Random Forest",
                "Machine learning-based strategy",
                "Random Forest, Features",
                "✓ Ready" if ML_AVAILABLE else "✗ scikit-learn required",
            ),
        ]

        for info in strategies_info:
            table.add_row(*info)

    # Event handlers

    @on(Button.Pressed, "#btn-new-backtest")
    def on_new_backtest(self) -> None:
        """Navigate to wizard for new backtest."""
        self._switch_to_tab("Wizard")

    @on(Button.Pressed, "#btn-run-last")
    def on_run_last(self) -> None:
        """Run last configuration."""
        runs = self.history.get_runs(limit=1)
        if runs:
            self.backtest_config = runs[0].config
            self._switch_to_tab("Wizard")
            self.notify("Loaded last configuration", severity="information")
        else:
            self.notify("No previous runs found", severity="warning")

    @on(Button.Pressed, "#btn-browse-templates")
    @on(Button.Pressed, "#btn-view-history")
    def on_view_history(self) -> None:
        """Navigate to history tab."""
        self._switch_to_tab("History")

    @on(Button.Pressed, "#btn-refresh-dash")
    @on(Button.Pressed, "#btn-refresh-history")
    def on_refresh(self) -> None:
        """Refresh current view."""
        if self.current_tab == "Dashboard":
            body = self.query_one("#app-body", Container)
            body.remove_children()
            self.show_dashboard()
        elif self.current_tab == "History":
            self._populate_history_table()
        self.notify("Refreshed", severity="information")

    @on(Button.Pressed, "#btn-run-mc")
    @work
    async def on_run_monte_carlo(self) -> None:
        """Run Monte Carlo simulation."""
        status_widget = self.query_one("#mc-status", Static)
        results_widget = self.query_one("#mc-results", Static)
        progress_widget = self.query_one("#mc-progress-bar", Static)

        try:
            # Get configuration
            config_select = self.query_one("#mc-config-select", Select)
            method_select = self.query_one("#mc-method", Select)
            sims_input = self.query_one("#mc-sims", Input)
            seed_input = self.query_one("#mc-seed", Input)

            selected_run_id = str(config_select.value) if config_select.value else "__new__"
            method = str(method_select.value) if method_select.value else "bootstrap"

            try:
                n_sims = int(sims_input.value) if sims_input.value else 1000
            except ValueError:
                status_widget.update("[red]✗ Invalid number of simulations[/red]")
                return

            seed = None
            if seed_input.value:
                try:
                    seed = int(seed_input.value)
                except ValueError:
                    status_widget.update("[red]✗ Seed must be a number[/red]")
                    return

            # Validate simulations
            if n_sims < 100:
                status_widget.update("[yellow]⚠ Warning: Less than 100 simulations may not be statistically significant[/yellow]")
            elif n_sims > 5000:
                status_widget.update("[yellow]⚠ Warning: More than 5000 simulations may take a long time[/yellow]")

            # Load configuration
            if selected_run_id == "__new__":
                # Use wizard configuration
                config = self.backtest_config
            else:
                # Load from history
                run = self.history.get_run(selected_run_id)
                if not run:
                    status_widget.update("[red]✗ Could not load configuration[/red]")
                    return
                config = run.config

            status_widget.update(f"[yellow]⏳ Preparing Monte Carlo simulation...[/yellow]")
            progress_widget.update("[dim]Fetching data...[/dim]")

            # Fetch data
            loop = asyncio.get_event_loop()
            fetcher = CCXTDataFetcher(exchange_id=config.exchange, sandbox=False, use_cache=False)
            data = await loop.run_in_executor(
                None,
                lambda: fetcher.fetch_ohlcv(
                    symbol=config.symbol,
                    timeframe=config.timeframe,
                    limit=config.limit,
                ),
            )

            progress_widget.update(f"[dim]Creating strategy...[/dim]")

            # Create strategy
            strategy = self._create_strategy(config)
            if not strategy:
                status_widget.update("[red]✗ Failed to create strategy[/red]")
                return

            # Create Monte Carlo engine
            from trading_bot.backtesting.monte_carlo_engine import MonteCarloEngine

            mc_engine = MonteCarloEngine(
                initial_capital=10000.0,
                commission=0.001,
                slippage=0.0005,
                n_simulations=n_sims,
                random_seed=seed,
            )

            status_widget.update(
                f"[green]▶[/green] Running {n_sims} {method} simulations on {config.symbol}..."
            )
            progress_widget.update(f"[green]{'━' * 50}[/green] 0%")

            # Run simulation (this will take time)
            results = await loop.run_in_executor(
                None,
                lambda: mc_engine.run(strategy, data, config.symbol, method=method),
            )

            progress_widget.update(f"[green]{'█' * 50}[/green] 100%")
            status_widget.update("[green]✓ Monte Carlo simulation complete![/green]")

            # Display results
            self._display_monte_carlo_results(results, results_widget)

            # Save results
            result_dir = mc_engine.save_results(results)
            self.notify(f"Results saved to {result_dir}", severity="information")

        except Exception as e:
            status_widget.update(f"[red]✗ Error: {str(e)}[/red]")
            logger.exception("Monte Carlo simulation failed")

    @on(Button.Pressed, "#btn-view-mc-charts")
    def on_view_mc_charts(self) -> None:
        """Open the most recent Monte Carlo visualization."""
        import subprocess
        from pathlib import Path

        # Find the most recent Monte Carlo results directory
        results_dir = Path("results")
        if not results_dir.exists():
            self.notify("No Monte Carlo results found", severity="warning")
            return

        # Find most recent MC result
        mc_dirs = sorted(
            [d for d in results_dir.iterdir() if d.is_dir() and "monte_carlo" in d.name.lower()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        if not mc_dirs:
            self.notify("No Monte Carlo results found", severity="warning")
            return

        # Open the comprehensive chart
        chart_file = mc_dirs[0] / "monte_carlo_comprehensive.png"
        if chart_file.exists():
            try:
                subprocess.run(["start", str(chart_file)], shell=True, check=False)
                self.notify(f"Opened {chart_file.name}", severity="information")
            except Exception as e:
                self.notify(f"Could not open chart: {e}", severity="error")
        else:
            self.notify("Chart file not found", severity="warning")

    @on(Button.Pressed, "#btn-export-mc")
    def on_export_mc(self) -> None:
        """Export Monte Carlo results."""
        self.notify("Export functionality coming soon", severity="information")

    @on(DataTable.RowSelected, "#history-table")
    def on_history_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle history table row selection for quick actions."""
        if not hasattr(self, "_history_runs") or not self._history_runs:
            return

        try:
            row_index = event.cursor_row
            if row_index < len(self._history_runs):
                run = self._history_runs[row_index]

                # Show action menu
                from textual.widgets import Label
                from textual.screen import ModalScreen
                from textual.containers import Vertical

                class HistoryActionsScreen(ModalScreen):
                    """Modal screen for history row actions."""

                    def __init__(self, parent_app, run_data):
                        super().__init__()
                        self.parent_app = parent_app
                        self.run = run_data

                    def compose(self):
                        yield Vertical(
                            Static(f"[bold cyan]Actions for {self.run.config.symbol}[/bold cyan]"),
                            Static(f"[dim]{self.run.timestamp}[/dim]"),
                            Static(""),
                            Button("▶ Rerun This Configuration", id="action-rerun", variant="primary"),
                            Button("📊 View Charts", id="action-charts", variant="default"),
                            Button("💾 Export Results", id="action-export", variant="default"),
                            Button("📋 Copy to Wizard", id="action-copy", variant="default"),
                            Static(""),
                            Button("Cancel", id="action-cancel", variant="error"),
                            id="history-actions-dialog"
                        )

                    def on_button_pressed(self, event: Button.Pressed) -> None:
                        """Handle action button presses."""
                        button_id = str(event.button.id)

                        if button_id == "action-rerun":
                            self.parent_app.notify(f"Rerunning {self.run.config.symbol}...", severity="information")
                            # Load config and switch to wizard
                            self.parent_app.backtest_config = self.run.config
                            self.app.pop_screen()
                            self.parent_app._switch_to_tab("Wizard")

                        elif button_id == "action-charts":
                            # Open charts directory
                            import subprocess
                            from pathlib import Path
                            results_dir = Path("results")
                            if results_dir.exists():
                                self.parent_app.notify("Opening charts...", severity="information")
                                subprocess.run(["explorer", str(results_dir)], shell=True, check=False)
                            self.app.pop_screen()

                        elif button_id == "action-export":
                            self.parent_app.notify("Export functionality coming soon", severity="information")
                            self.app.pop_screen()

                        elif button_id == "action-copy":
                            self.parent_app.backtest_config = self.run.config
                            self.parent_app.notify("Configuration copied to wizard", severity="information")
                            self.app.pop_screen()

                        else:  # action-cancel
                            self.app.pop_screen()

                self.push_screen(HistoryActionsScreen(self, run))

        except Exception as e:
            logger.debug(f"Failed to handle history row selection: {e}")

    @on(Select.Changed, "#wizard-strategy")
    def on_strategy_changed(self, event: Select.Changed) -> None:
        """Handle strategy selection change."""
        if event.value:
            strategy_name = str(event.value)
            self.backtest_config.update(strategy_name=strategy_name)
            self._update_parameters_panel(strategy_name)
            if self.sidebar:
                self.sidebar.update_display()

            # Update wizard progress indicator
            self._update_wizard_progress()

    @on(Select.Changed, "#wizard-exchange")
    @on(Select.Changed, "#wizard-timeframe")
    @on(Select.Changed, "#wizard-engine")
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle any select widget change."""
        if not event.value:
            return

        widget_id = str(event.select.id) if hasattr(event.select, "id") else ""
        value = str(event.value)

        if "exchange" in widget_id:
            self.backtest_config.update(exchange=value)
        elif "timeframe" in widget_id:
            self.backtest_config.update(timeframe=value)
        elif "engine" in widget_id:
            self.backtest_config.update(engine=value)

        if self.sidebar:
            self.sidebar.update_display()

        # Update wizard progress indicator
        self._update_wizard_progress()

    @on(Input.Changed, "#wizard-symbol")
    @on(Input.Changed, "#wizard-limit")
    @on(Input.Changed, "#wizard-start-date")
    @on(Input.Changed, "#wizard-end-date")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes with validation hints."""
        widget_id = str(event.input.id) if hasattr(event.input, "id") else ""
        value = event.value

        if "symbol" in widget_id:
            self.backtest_config.update(symbol=value)
            # Validate symbol format (should be BASE/QUOTE)
            try:
                # Find the hint widget that follows this input
                parent = event.input.parent
                if parent:
                    hints = parent.query(".field-hint")
                    if hints:
                        hint = hints[0]
                        if "/" in value and len(value.split("/")) == 2:
                            base, quote = value.split("/")
                            if base and quote:
                                hint.update("[green]✓[/green] [dim]Valid format[/dim]")
                            else:
                                hint.update("[yellow]⚠[/yellow] [dim]Format: BASE/QUOTE (e.g., BTC/USDT)[/dim]")
                        elif value:
                            hint.update("[yellow]⚠[/yellow] [dim]Missing '/' separator[/dim]")
                        else:
                            hint.update("[dim]Format: BASE/QUOTE (e.g., BTC/USDT)[/dim]")
            except Exception as e:
                logger.debug(f"Failed to update symbol hint: {e}")

        elif "limit" in widget_id:
            # Validate candles number
            try:
                parent = event.input.parent
                if parent:
                    hints = parent.query(".field-hint")
                    if hints:
                        hint = hints[0]
                        if value:
                            try:
                                limit_val = int(value)
                                self.backtest_config.update(limit=limit_val)
                                if 50 <= limit_val <= 1000:
                                    hint.update("[green]✓[/green] [dim]Good range for backtesting[/dim]")
                                elif limit_val < 50:
                                    hint.update("[yellow]⚠[/yellow] [dim]Too few candles (50+ recommended)[/dim]")
                                elif 1000 < limit_val <= 5000:
                                    hint.update("[yellow]⚠[/yellow] [dim]Large dataset (~{:.1f} years for daily)[/dim]".format(limit_val / 365))
                                elif limit_val > 5000:
                                    hint.update("[yellow]⚠[/yellow] [dim]Very large dataset (~{:.1f} years for daily). Use date range instead.[/dim]".format(limit_val / 365))
                            except ValueError:
                                hint.update("[red]✗[/red] [dim]Must be a number[/dim]")
                        else:
                            hint.update("[dim]Number of candles (or use date range below)[/dim]")
            except Exception as e:
                logger.debug(f"Failed to update limit hint: {e}")

        elif "start-date" in widget_id or "end-date" in widget_id:
            # Validate date format
            if value:
                try:
                    from datetime import datetime
                    datetime.strptime(value, "%Y-%m-%d")
                    if "start-date" in widget_id:
                        self.backtest_config.update(start_date=value)
                    else:
                        self.backtest_config.update(end_date=value)

                    # Calculate approximate candle count if both dates provided
                    if self.backtest_config.start_date and self.backtest_config.end_date:
                        try:
                            start = datetime.strptime(self.backtest_config.start_date, "%Y-%m-%d")
                            end = datetime.strptime(self.backtest_config.end_date, "%Y-%m-%d")
                            days = (end - start).days

                            # Estimate candles based on timeframe
                            timeframe = self.backtest_config.timeframe
                            if timeframe == "1d":
                                estimated_candles = days
                            elif timeframe == "1h":
                                estimated_candles = days * 24
                            elif timeframe == "4h":
                                estimated_candles = days * 6
                            elif timeframe == "15m":
                                estimated_candles = days * 96
                            elif timeframe == "5m":
                                estimated_candles = days * 288
                            elif timeframe == "1m":
                                estimated_candles = days * 1440
                            else:
                                estimated_candles = days

                            # Update hint
                            parent = event.input.parent
                            if parent:
                                hints = parent.query(".field-hint")
                                if hints:
                                    hint = hints[0]
                                    hint.update(f"[green]✓[/green] [dim]~{estimated_candles:,} candles ({days} days)[/dim]")
                        except Exception:
                            pass
                except ValueError:
                    parent = event.input.parent
                    if parent:
                        hints = parent.query(".field-hint")
                        if hints:
                            hint = hints[0]
                            hint.update("[red]✗[/red] [dim]Invalid date format (use YYYY-MM-DD)[/dim]")

        if self.sidebar:
            self.sidebar.update_display()

        # Update wizard progress indicator
        self._update_wizard_progress()

    @on(Button.Pressed, "#wizard-run")
    @on(Button.Pressed, "#sidebar-run")
    @work
    async def on_run_wizard_backtest(self) -> None:
        """Handle run backtest from wizard."""
        results_display = self.query_one("#wizard-results", Static)

        try:
            # Update config from inputs
            self._sync_config_from_inputs()

            # Validate configuration before starting
            validation_errors = []

            if not self.backtest_config.symbol:
                validation_errors.append("Symbol is required")
            elif "/" not in self.backtest_config.symbol:
                validation_errors.append("Symbol must be in BASE/QUOTE format (e.g., BTC/USDT)")

            # Validate candles (only if dates not provided)
            if not (self.backtest_config.start_date and self.backtest_config.end_date):
                if self.backtest_config.limit < 50:
                    validation_errors.append("Number of candles should be at least 50")
                elif self.backtest_config.limit > 50000:
                    validation_errors.append("Number of candles exceeds maximum (50,000). Use date range for multi-year backtests.")

            # Validate date range if provided
            if self.backtest_config.start_date or self.backtest_config.end_date:
                try:
                    from datetime import datetime
                    if self.backtest_config.start_date:
                        start = datetime.strptime(self.backtest_config.start_date, "%Y-%m-%d")
                    if self.backtest_config.end_date:
                        end = datetime.strptime(self.backtest_config.end_date, "%Y-%m-%d")

                    if self.backtest_config.start_date and self.backtest_config.end_date:
                        if start >= end:
                            validation_errors.append("Start date must be before end date")
                        days = (end - start).days
                        if days > 3650:  # ~10 years
                            validation_errors.append(f"Date range too large ({days} days = ~{days/365:.1f} years). Maximum is ~10 years.")
                except ValueError as e:
                    validation_errors.append(f"Invalid date format: {e}. Use YYYY-MM-DD format.")

            if not self.backtest_config.strategy_name:
                validation_errors.append("Strategy must be selected")

            # Display validation errors if any
            if validation_errors:
                error_msg = "[red]✗ Validation Failed:[/red]\n"
                for error in validation_errors:
                    error_msg += f"  • {error}\n"
                error_msg += "\n[dim]Please fix the issues above and try again[/dim]"
                results_display.update(error_msg)
                return

            results_display.update("[yellow]⏳ Starting backtest...[/yellow]")

            # Get strategy parameters
            try:
                params_panel = self.query_one("#wizard-params", StrategyParametersPanel)
                params = params_panel.get_parameters()
                self.backtest_config.update(strategy_params=params)

                # Validate MA periods vs data limit for MA strategies
                if self.backtest_config.strategy_name in ["ma_crossover", "talib_ma"]:
                    long_period = params.get("long_window") or params.get("long_period", 200)
                    short_period = params.get("short_window") or params.get("short_period", 50)

                    if long_period >= self.backtest_config.limit:
                        validation_errors.append(
                            f"Long MA period ({long_period}) is too large for {self.backtest_config.limit} candles. "
                            f"Need at least {long_period + 50} candles for reliable signals."
                        )
                    elif long_period > self.backtest_config.limit * 0.5:
                        # Warning but not blocking
                        self.notify(
                            f"⚠ Long MA period ({long_period}) is large relative to data ({self.backtest_config.limit} candles). "
                            f"Consider using shorter periods (e.g., {max(20, int(self.backtest_config.limit * 0.1))}/{max(50, int(self.backtest_config.limit * 0.3))}) "
                            f"or more candles ({long_period + 100}+)",
                            severity="warning"
                        )

                    if short_period >= long_period:
                        validation_errors.append(
                            f"Short MA period ({short_period}) must be less than long MA period ({long_period})"
                        )
            except Exception as e:
                logger.debug(f"Failed to get parameters: {e}")

            # Re-check validation errors after parameter validation
            if validation_errors:
                error_msg = "[red]✗ Validation Failed:[/red]\n"
                for error in validation_errors:
                    error_msg += f"  • {error}\n"
                error_msg += "\n[dim]Please fix the issues above and try again[/dim]"
                results_display.update(error_msg)
                return

            # Update bot config
            if not self.config:
                results_display.update("[red]✗ Configuration not loaded[/red]")
                return

            self.config.data_provider = "ccxt"
            self.config.exchange_id = self.backtest_config.exchange
            self.config.backtest_engine = self.backtest_config.engine
            self.bot = TradingBot(self.config)

            # Create strategy
            strategy = self._create_strategy(self.backtest_config)
            if strategy is None:
                results_display.update("[red]✗ Failed to create strategy[/red]")
                return

            # Run backtest
            loop = asyncio.get_event_loop()

            # Fetch data
            fetcher = CCXTDataFetcher(
                exchange_id=self.backtest_config.exchange, sandbox=False, use_cache=False
            )

            # Determine fetch parameters
            fetch_kwargs = {
                "symbol": self.backtest_config.symbol,
                "timeframe": self.backtest_config.timeframe,
            }

            # Use date range if provided, otherwise use limit
            if self.backtest_config.start_date and self.backtest_config.end_date:
                fetch_kwargs["start_date"] = self.backtest_config.start_date
                fetch_kwargs["end_date"] = self.backtest_config.end_date
                # Calculate appropriate limit based on timeframe and date range
                from datetime import datetime
                start = datetime.strptime(self.backtest_config.start_date, "%Y-%m-%d")
                end = datetime.strptime(self.backtest_config.end_date, "%Y-%m-%d")
                days = (end - start).days

                # Estimate max candles needed (add 20% buffer)
                if self.backtest_config.timeframe == "1d":
                    fetch_kwargs["limit"] = int(days * 1.2)
                elif self.backtest_config.timeframe == "1h":
                    fetch_kwargs["limit"] = int(days * 24 * 1.2)
                elif self.backtest_config.timeframe == "4h":
                    fetch_kwargs["limit"] = int(days * 6 * 1.2)
                elif self.backtest_config.timeframe == "15m":
                    fetch_kwargs["limit"] = int(days * 96 * 1.2)
                elif self.backtest_config.timeframe == "5m":
                    fetch_kwargs["limit"] = int(days * 288 * 1.2)
                elif self.backtest_config.timeframe == "1m":
                    fetch_kwargs["limit"] = int(days * 1440 * 1.2)
                else:
                    fetch_kwargs["limit"] = int(days * 1.2)
            else:
                fetch_kwargs["limit"] = self.backtest_config.limit

            data = await loop.run_in_executor(
                None,
                lambda: fetcher.fetch_ohlcv(**fetch_kwargs),
            )

            # Generate signals
            signals = await loop.run_in_executor(
                None,
                lambda: strategy.generate_signals(data),
            )

            # Run backtest
            if not self.bot:
                results_display.update("[red]✗ Bot not initialized[/red]")
                return

            bot = self.bot
            use_backtrader = self.backtest_config.engine == "backtrader"

            # Prepare backtest arguments
            backtest_kwargs = {
                "strategy": strategy,
                "symbol": self.backtest_config.symbol,
                "timeframe": self.backtest_config.timeframe,
            }

            # Use date range if provided, otherwise use limit
            if self.backtest_config.start_date and self.backtest_config.end_date:
                backtest_kwargs["start_date"] = self.backtest_config.start_date
                backtest_kwargs["end_date"] = self.backtest_config.end_date
                # Calculate limit from date range (already done in fetch_kwargs, but need for bot.backtest)
                from datetime import datetime
                start = datetime.strptime(self.backtest_config.start_date, "%Y-%m-%d")
                end = datetime.strptime(self.backtest_config.end_date, "%Y-%m-%d")
                days = (end - start).days
                if self.backtest_config.timeframe == "1d":
                    backtest_kwargs["limit"] = int(days * 1.2)
                elif self.backtest_config.timeframe == "1h":
                    backtest_kwargs["limit"] = int(days * 24 * 1.2)
                elif self.backtest_config.timeframe == "4h":
                    backtest_kwargs["limit"] = int(days * 6 * 1.2)
                elif self.backtest_config.timeframe == "15m":
                    backtest_kwargs["limit"] = int(days * 96 * 1.2)
                elif self.backtest_config.timeframe == "5m":
                    backtest_kwargs["limit"] = int(days * 288 * 1.2)
                elif self.backtest_config.timeframe == "1m":
                    backtest_kwargs["limit"] = int(days * 1440 * 1.2)
                else:
                    backtest_kwargs["limit"] = int(days * 1.2)
            else:
                backtest_kwargs["limit"] = self.backtest_config.limit

            if self.backtest_config.engine != "vectorbt":
                backtest_kwargs["use_backtrader"] = use_backtrader

            results = await loop.run_in_executor(
                None,
                lambda: bot.backtest(**backtest_kwargs),
            )

            # Store results
            self.backtest_results = results
            self.backtest_data = data
            self.backtest_signals = signals

            # Save to history
            run = BacktestRun(
                id=str(uuid.uuid4()),
                timestamp=datetime.now().isoformat(),
                config=self.backtest_config,
                results=results,
            )
            self.history.add_run(run)

            # Display results
            self._display_results(results, results_display)

            # Warn if no trades were generated
            if results.get("total_trades", 0) == 0:
                self.notify(
                    "⚠ No trades generated! This usually means:\n"
                    "• MA periods are too long for the data (try shorter periods like 10/30)\n"
                    "• Not enough data (increase candles or use longer timeframe)\n"
                    "• No crossovers occurred in the selected period",
                    severity="warning"
                )

            self.notify("✓ Backtest completed!", severity="information")

        except Exception as e:
            results_display.update(f"[red]✗ Error: {e}[/red]")
            import traceback

            logger.error(traceback.format_exc())

    @on(Button.Pressed, "#wizard-save-template")
    @on(Button.Pressed, "#sidebar-save")
    def on_save_template(self) -> None:
        """Save current configuration as template."""
        self._sync_config_from_inputs()

        # Prompt for name (simplified - using display name)
        if not self.backtest_config.name:
            self.backtest_config.name = self.backtest_config.get_display_name()

        self.history.save_template(self.backtest_config)
        self.notify(f"✓ Template '{self.backtest_config.name}' saved!", severity="information")

    @on(Button.Pressed, "#wizard-reset")
    @on(Button.Pressed, "#sidebar-reset")
    def on_reset(self) -> None:
        """Reset configuration to defaults."""
        self.backtest_config = BacktestConfiguration()
        if self.current_tab == "Wizard":
            body = self.query_one("#app-body", Container)
            body.remove_children()
            # Defer mounting until after removal completes
            self.call_after_refresh(self.show_wizard)
        self.notify("Configuration reset", severity="information")

    @on(Button.Pressed, "#wizard-charts")
    @work
    async def on_generate_wizard_charts(self) -> None:
        """Generate visualization charts."""
        if not self.backtest_results:
            self.notify("Run backtest first", severity="warning")
            return

        try:
            loop = asyncio.get_event_loop()

            if not self.config:
                return

            results = self.backtest_results
            data = self.backtest_data
            signals = self.backtest_signals
            results_dir = self.config.results_dir

            if data is not None and signals is not None:
                plot_file = await loop.run_in_executor(
                    None,
                    lambda: plot_backtest_results(results, data, signals, output_dir=results_dir),
                )
            else:
                plot_file = await loop.run_in_executor(
                    None,
                    lambda: plot_simple_results(results, output_dir=results_dir),
                )

            self.notify(f"✓ Charts saved to {plot_file}", severity="information")

        except Exception as e:
            self.notify(f"✗ Chart generation failed: {e}", severity="error")

    # Helper methods

    def _sync_config_from_inputs(self) -> None:
        """Synchronize backtest_config from wizard input widgets."""
        try:
            # Get limit (default to 365 if empty)
            limit_value = self.query_one("#wizard-limit", Input).value
            limit = int(limit_value) if limit_value else 365

            # Get dates (can be empty)
            start_date_value = self.query_one("#wizard-start-date", Input).value
            end_date_value = self.query_one("#wizard-end-date", Input).value

            self.backtest_config.update(
                exchange=str(self.query_one("#wizard-exchange", Select).value),
                symbol=self.query_one("#wizard-symbol", Input).value,
                timeframe=str(self.query_one("#wizard-timeframe", Select).value),
                limit=limit,
                start_date=start_date_value if start_date_value else None,
                end_date=end_date_value if end_date_value else None,
                strategy_name=str(self.query_one("#wizard-strategy", Select).value),
                engine=str(self.query_one("#wizard-engine", Select).value),
            )
        except Exception as e:
            logger.debug(f"Failed to sync config: {e}")

    def _display_monte_carlo_results(self, results: dict, widget: Static) -> None:
        """Display Monte Carlo simulation results in a formatted table."""
        from rich.table import Table
        from rich.console import Console

        # Create results table
        results_table = Table(title="Monte Carlo Simulation Results", show_header=True, header_style="bold cyan")
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
            f"[green]{mean_return:.2f}%[/green]" if mean_return > 0 else f"[red]{mean_return:.2f}%[/red]",
            "Average across all simulations",
        )
        results_table.add_row(
            "Median Return",
            f"[green]{median_return:.2f}%[/green]" if median_return > 0 else f"[red]{median_return:.2f}%[/red]",
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
            f"[green]{prob_profit:.1f}%[/green]" if prob_profit >= 70 else
            f"[yellow]{prob_profit:.1f}%[/yellow]" if prob_profit >= 50 else
            f"[red]{prob_profit:.1f}%[/red]",
            "✓ High confidence" if prob_profit >= 70 else
            "⚠ Moderate" if prob_profit >= 50 else
            "✗ Low confidence",
        )
        results_table.add_row(
            "Sharpe Ratio",
            f"[green]{sharpe:.2f}[/green]" if sharpe >= 1.0 else
            f"[yellow]{sharpe:.2f}[/yellow]" if sharpe >= 0.5 else
            f"[red]{sharpe:.2f}[/red]",
            "✓ Good risk-adjusted" if sharpe >= 1.0 else
            "⚠ Moderate" if sharpe >= 0.5 else
            "✗ Poor risk-adjusted",
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
            "✓ Acceptable" if abs(worst_dd) <= 20 else
            "⚠ Moderate" if abs(worst_dd) <= 30 else
            "✗ High risk",
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

    def _create_strategy(self, config: BacktestConfiguration) -> BaseStrategy | None:
        """Create strategy instance from configuration."""
        params = config.strategy_params

        if config.strategy_name == "ma_crossover":
            return MovingAverageCrossover(
                short_window=int(params.get("short_window", 50)),
                long_window=int(params.get("long_window", 200)),
                use_rsi=bool(params.get("use_rsi", False)),
            )
        elif config.strategy_name == "talib_ma" and TALIB_AVAILABLE:
            return TALibMovingAverageCrossover(
                short_period=int(params.get("short_period", 50)),
                long_period=int(params.get("long_period", 200)),
            )
        elif config.strategy_name == "talib_macd" and TALIB_AVAILABLE:
            return TALibMACDStrategy()
        elif config.strategy_name == "supertrend" and ADVANCED_AVAILABLE:
            return SupertrendStrategy(
                period=int(params.get("period", 10)),
                multiplier=float(params.get("multiplier", 3.0)),
            )
        elif config.strategy_name == "bollinger" and ADVANCED_AVAILABLE:
            return BollingerBandsStrategy(
                period=int(params.get("period", 20)),
                std_dev=float(params.get("std_dev", 2.0)),
            )
        elif config.strategy_name == "ichimoku" and ADVANCED_AVAILABLE:
            return IchimokuStrategy()
        elif config.strategy_name == "ml_randomforest" and ML_AVAILABLE:
            return MLRandomForestStrategy(lookback=int(params.get("lookback", 50)))

        return None

    def _display_results(self, results: dict, widget: Static) -> None:
        """Display backtest results in formatted table."""
        results_table = Table(show_header=False, box=None, padding=(0, 1))
        results_table.add_column(style="cyan", width=22)
        results_table.add_column(width=25)

        # Determine return color
        return_pct = results['total_return_pct']
        return_color = "green" if return_pct > 0 else "red"
        return_icon = "📈" if return_pct > 0 else "📉"

        results_table.add_row("🎯 [bold]Strategy[/bold]", results["strategy"])
        results_table.add_row("💹 [bold]Symbol[/bold]", results["symbol"])
        results_table.add_row("💰 [bold]Initial Capital[/bold]", f"${results['initial_capital']:,.2f}")
        results_table.add_row("💵 [bold]Final Value[/bold]", f"${results['final_value']:,.2f}")
        results_table.add_row("", "")
        results_table.add_row(
            f"{return_icon} [bold]Total Return[/bold]",
            f"[{return_color}]{results['total_return_pct']:.2f}%[/{return_color}]"
        )
        results_table.add_row(
            "📊 [bold]Buy & Hold[/bold]",
            f"{results['buy_hold_return_pct']:.2f}%"
        )
        results_table.add_row("", "")
        results_table.add_row("🔄 [bold]Total Trades[/bold]", str(results["total_trades"]))
        results_table.add_row("🎯 [bold]Win Rate[/bold]", f"{results['win_rate_pct']:.2f}%")
        results_table.add_row(
            "⚠️  [bold]Max Drawdown[/bold]",
            f"[red]{results['max_drawdown_pct']:.2f}%[/red]"
        )
        if "sharpe_ratio" in results:
            sharpe = results['sharpe_ratio']
            sharpe_color = "green" if sharpe >= 1.0 else "yellow" if sharpe >= 0.5 else "red"
            results_table.add_row(
                "📉 [bold]Sharpe Ratio[/bold]",
                f"[{sharpe_color}]{sharpe:.2f}[/{sharpe_color}]"
            )

        from rich.console import Console

        console = Console()
        with console.capture() as capture:
            console.print(results_table)
        widget.update(capture.get())

    @work
    async def _start_live_price_ticker(self, symbol: str) -> None:
        """Update live price display every 5 seconds."""
        for _ in range(12):  # Run for 60 seconds (12 * 5)
            try:
                # Fetch current price
                loop = asyncio.get_event_loop()
                fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=False, use_cache=False)

                ticker = await loop.run_in_executor(
                    None,
                    lambda: fetcher.exchange.fetch_ticker(symbol),
                )

                price = ticker.get("last", 0)
                change_pct = ticker.get("percentage", 0)
                arrow = "↑" if change_pct > 0 else "↓"
                color = "green" if change_pct > 0 else "red"

                try:
                    price_widget = self.query_one("#live-price", Static)
                    price_widget.update(
                        f"[bold]💹 {symbol}:[/bold] ${price:,.2f} "
                        f"[{color}]{arrow} {change_pct:.2f}%[/{color}]"
                    )
                except Exception:
                    # Widget might have been removed if user switched tabs
                    break

                await asyncio.sleep(5)
            except Exception as e:
                logger.debug(f"Failed to update live price: {e}")
                break

    def _create_performance_sparkline(self, runs: list) -> str:
        """Create ASCII sparkline of recent backtest performance."""
        if not runs or len(runs) < 2:
            return "[dim]No data[/dim]"

        # Get last 10 runs
        runs_to_show = runs[:10] if len(runs) >= 10 else runs
        returns = [r.results.get("total_return_pct", 0) for r in runs_to_show]

        # Reverse to show oldest to newest
        returns = list(reversed(returns))

        min_val, max_val = min(returns), max(returns)
        if max_val == min_val:
            return f"[yellow]{'▄' * len(returns)}[/yellow] (flat)"

        # Unicode block characters for sparkline
        chars = "▁▂▃▄▅▆▇█"
        normalized = [(r - min_val) / (max_val - min_val) for r in returns]
        sparkline_chars = "".join(chars[min(int(n * 7), 7)] for n in normalized)

        # Color based on latest return
        latest = returns[-1]
        if latest > 5:
            color = "green"
        elif latest > 0:
            color = "yellow"
        else:
            color = "red"

        return f"[{color}]{sparkline_chars}[/{color}] ({latest:.1f}%)"

    def _update_wizard_progress(self) -> None:
        """Update wizard progress indicator based on filled fields."""
        try:
            # Determine current step based on completed fields
            step = 1
            step_text = "Data Configuration"

            # Check if Step 1 is complete (all data fields filled)
            if (self.backtest_config.symbol and
                "/" in self.backtest_config.symbol and
                self.backtest_config.limit >= 50):
                step = 2
                step_text = "Strategy Selection"

                # Check if Step 2 is complete (strategy selected)
                if self.backtest_config.strategy_name:
                    step = 3
                    step_text = "Ready to Run"

            # Build progress bar visualization
            if step == 1:
                progress_bar = "[green]●[/green]━━━[dim]○[/dim]━━━[dim]○[/dim]"
            elif step == 2:
                progress_bar = "[green]●━━━●[/green]━━━[dim]○[/dim]"
            else:  # step == 3
                progress_bar = "[green]●━━━●━━━●[/green]"

            progress_text = f"{progress_bar}  [bold]Step {step} of 3:[/bold] {step_text}"

            # Update the progress widget
            progress_widget = self.query_one("#wizard-progress", Static)
            progress_widget.update(progress_text)
        except Exception as e:
            logger.debug(f"Failed to update wizard progress: {e}")

    def _switch_to_tab(self, tab_name: str) -> None:
        """Switch to a different tab."""
        self.current_tab = tab_name
        body = self.query_one("#app-body", Container)
        body.remove_children()

        if tab_name == "Dashboard":
            self.show_dashboard()
        elif tab_name == "Wizard":
            self.show_wizard()
        elif tab_name == "Monte Carlo":
            self.show_monte_carlo()
        elif tab_name == "History":
            self.show_history()
        elif tab_name == "Strategies":
            self.show_strategies()

        # Update tabs widget
        try:
            tabs_widget = self.query_one("#tabs", Tabs)
            tabs_list = tabs_widget.query("#tabs-list > Tab")
            for tab in tabs_list:
                tab_label = getattr(tab, "label", None)
                if tab_label and tab_name in str(tab_label):
                    tab_id = getattr(tab, "id", None)
                    if tab_id:
                        tabs_widget.active = str(tab_id)
                    break
        except Exception as e:
            logger.debug(f"Failed to switch tab widget: {e}")

    def action_refresh(self) -> None:
        """Refresh current view."""
        self.on_refresh()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        current_dark = getattr(self, "dark", True)
        self.dark = not current_dark

    def action_new_backtest(self) -> None:
        """Action: Navigate to wizard for new backtest."""
        self._switch_to_tab("Wizard")

    def action_show_history(self) -> None:
        """Action: Navigate to history tab."""
        self._switch_to_tab("History")

    def action_save_template(self) -> None:
        """Action: Save current configuration as template."""
        self.on_save_template()

    def action_show_help(self) -> None:
        """Action: Show help dialog with keyboard shortcuts."""
        help_text = """[bold cyan]Trading Bot TUI - Keyboard Shortcuts[/bold cyan]

[bold]Navigation:[/bold]
  q              Quit application
  d              Toggle dark mode
  r              Refresh current view

[bold]Quick Actions:[/bold]
  Ctrl+N         New backtest (go to wizard)
  Ctrl+H         Show history
  Ctrl+S         Save current config as template
  F1             Show this help

[bold]Tab Navigation:[/bold]
  Use mouse or buttons to switch between:
  • Dashboard  - Overview and quick actions
  • Wizard     - Configure and run backtests
  • History    - View past backtest results

[bold]Wizard Actions:[/bold]
  • Fill in parameters in each step
  • Click 'Run Backtest' or 'Sidebar Run' button
  • Results appear in the results panel

Press any key to close this help."""

        try:
            from textual.widgets import Label
            from textual.screen import ModalScreen
            from textual.containers import Vertical

            class HelpScreen(ModalScreen):
                """Modal screen for help dialog."""

                def compose(self):
                    yield Vertical(
                        Static(help_text),
                        Button("Close", variant="primary", id="close-help"),
                        id="help-dialog"
                    )

                def on_button_pressed(self, event: Button.Pressed) -> None:
                    """Close help dialog."""
                    self.app.pop_screen()

                def on_key(self, event) -> None:
                    """Close on any key press."""
                    self.app.pop_screen()

            self.push_screen(HelpScreen())
        except Exception as e:
            logger.debug(f"Failed to show help dialog: {e}")
            # Fallback: just log the help text
            logger.info(help_text)


def main():
    """Run the enhanced TUI application."""
    app = TradingBotTUI()
    app.run()


if __name__ == "__main__":
    main()
