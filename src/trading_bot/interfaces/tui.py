"""Enhanced Text User Interface (TUI) for the trading bot - Sprint 1 UX Improvements."""

import importlib.util
import logging
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

# Suppress SyntaxWarnings from backtrader (invalid escape sequences in their code)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="backtrader")

if TYPE_CHECKING:
    from pandas import DataFrame  # type: ignore[attr-defined]
else:
    import pandas as pd

    DataFrame = pd.DataFrame  # type: ignore[assignment]

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.events import Key
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Select,
    Static,
    Tabs,
)

from trading_bot.bot import TradingBot
from trading_bot.config import (
    BacktestConfiguration,
    BacktestHistory,
    TradingConfig,
    load_config,
)
from trading_bot.interfaces.pages import (
    DashboardPage,
    HistoryPage,
    MonteCarloPage,
    PaperTradingPage,
    StrategiesPage,
    WFOPage,
    WizardPage,
)
from trading_bot.interfaces.widgets import StatusSidebar

# Initialize logger early for use in import checks
logger = logging.getLogger(__name__)

# Try to import TA-Lib strategies (optional)
TALIB_LIB_AVAILABLE = False
TALIB_AVAILABLE = False
try:
    import talib  # noqa: F401

    TALIB_LIB_AVAILABLE = True
    try:
        # Check if TA-Lib strategies are available using importlib
        spec = importlib.util.find_spec("trading_bot.strategies.ta_lib_strategy")
        if spec is not None and spec.loader is not None:
            # Try to actually import to verify it works
            importlib.util.module_from_spec(spec)
            TALIB_AVAILABLE = True
        else:
            TALIB_AVAILABLE = False
    except Exception as e:
        logger.debug(f"TA-Lib strategies import failed: {e}")
        TALIB_AVAILABLE = False
except ImportError as e:
    logger.debug(f"TA-Lib library import failed: {e}")
    TALIB_LIB_AVAILABLE = False

# Try to import advanced strategies (optional)
try:
    spec = importlib.util.find_spec("trading_bot.strategies.advanced_indicators")
    ADVANCED_AVAILABLE = spec is not None and spec.loader is not None
except Exception:
    ADVANCED_AVAILABLE = False

# Try to import ML strategies (optional)
try:
    spec = importlib.util.find_spec("trading_bot.strategies.ml_strategy")
    ML_AVAILABLE = spec is not None and spec.loader is not None
except Exception:
    ML_AVAILABLE = False


def get_python_version_string() -> str:
    """Get formatted Python version string for display.

    Returns:
        Formatted string like "Python 3.14 Free-Threading" or "Python 3.13.4"
    """
    version = sys.version_info
    version_str = f"Python {version.major}.{version.minor}"
    if version.micro > 0:
        version_str += f".{version.micro}"

    # Python 3.14+ has free-threading (no GIL)
    if version >= (3, 14):
        version_str += " Free-Threading"
    elif version >= (3, 13, 4):
        version_str += " (GPU Support Available)"

    return version_str


class TradingBotTUI(App):
    """Enhanced TUI application for the trading bot with improved UX."""

    CSS_PATH = str(Path(__file__).parent / "tui.css")
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

        # Page instances (initialized in on_mount)
        self.dashboard_page: DashboardPage | None = None
        self.history_page: HistoryPage | None = None
        self.strategies_page: StrategiesPage | None = None
        self.wizard_page: WizardPage | None = None
        self.monte_carlo_page: MonteCarloPage | None = None
        self.wfo_page: WFOPage | None = None
        self.paper_trading_page: PaperTradingPage | None = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Tabs(
            "Dashboard",
            "Wizard",  # New unified workflow
            "Monte Carlo",  # Monte Carlo simulations
            "WFO",  # Walk-Forward Optimization
            "Paper Trading",  # Simulated live trading
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

        # Initialize page instances
        self.dashboard_page = DashboardPage(self)
        self.history_page = HistoryPage(self)
        self.strategies_page = StrategiesPage(self)
        self.wizard_page = WizardPage(self)
        self.monte_carlo_page = MonteCarloPage(self)
        self.wfo_page = WFOPage(self)
        self.paper_trading_page = PaperTradingPage(self)

        self.show_dashboard()

    @on(Key, "ctrl+c")
    def handle_ctrl_c(self) -> None:
        """Handle Ctrl+C to cancel current operation."""
        # If we're in the Monte Carlo tab and there's an active simulation
        if self.current_tab == "Monte Carlo" and hasattr(self.monte_carlo_page, '_cancel_requested'):
            if not self.monte_carlo_page._cancel_requested:
                self.monte_carlo_page._handle_cancel()
                self.notify("Cancelling Monte Carlo simulation...", severity="warning")
            else:
                self.notify("Simulation is already being cancelled", severity="information")

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        """Handle tab switching."""
        tab_label = str(event.tab.label) if hasattr(event.tab, "label") else ""
        if self.current_tab == tab_label:
            return

        self.current_tab = tab_label
        body = self.query_one("#app-body", Container)
        body.remove_children()

        if "Dashboard" in tab_label or not tab_label:
            assert self.dashboard_page is not None
            body = self.query_one("#app-body", Container)
            self.dashboard_page.compose(body)
        elif "Wizard" in tab_label:
            assert self.wizard_page is not None
            body = self.query_one("#app-body", Container)
            self.wizard_page.compose(body)
        elif "History" in tab_label:
            assert self.history_page is not None
            body = self.query_one("#app-body", Container)
            self.history_page.compose(body)
        elif "Strategies" in tab_label:
            assert self.strategies_page is not None
            body = self.query_one("#app-body", Container)
            self.strategies_page.compose(body)
        elif "Monte Carlo" in tab_label:
            assert self.monte_carlo_page is not None
            body = self.query_one("#app-body", Container)
            self.monte_carlo_page.compose(body)
        elif "WFO" in tab_label:
            assert self.wfo_page is not None
            body = self.query_one("#app-body", Container)
            self.wfo_page.compose(body)
        elif "Paper Trading" in tab_label:
            assert self.paper_trading_page is not None
            body = self.query_one("#app-body", Container)
            self.paper_trading_page.compose(body)

    def show_dashboard(self) -> None:
        """Show enhanced dashboard with recent runs and templates."""
        assert self.dashboard_page is not None
        body = self.query_one("#app-body", Container)
        self.dashboard_page.compose(body)

    def show_wizard(self) -> None:
        """Show unified workflow wizard - Single-tab backtest configuration."""
        assert self.wizard_page is not None
        body = self.query_one("#app-body", Container)
        self.wizard_page.compose(body)

    def show_monte_carlo(self) -> None:
        """Show Monte Carlo simulation tab."""
        assert self.monte_carlo_page is not None
        body = self.query_one("#app-body", Container)
        self.monte_carlo_page.compose(body)

    def show_history(self) -> None:
        """Show backtest history with comparison capabilities."""
        assert self.history_page is not None
        body = self.query_one("#app-body", Container)
        self.history_page.compose(body)

    def show_strategies(self) -> None:
        """Show strategies information."""
        assert self.strategies_page is not None
        body = self.query_one("#app-body", Container)
        self.strategies_page.compose(body)

    def show_wfo(self) -> None:
        """Show Walk-Forward Optimization tab."""
        assert self.wfo_page is not None
        body = self.query_one("#app-body", Container)
        self.wfo_page.compose(body)

    def show_paper_trading(self) -> None:
        """Show Paper Trading tab."""
        assert self.paper_trading_page is not None
        body = self.query_one("#app-body", Container)
        self.paper_trading_page.compose(body)

    # Helper methods

    def _get_available_strategies(self) -> list:
        """Get list of available strategies for dropdown - delegates to wizard page."""
        if self.wizard_page:
            return self.wizard_page._get_available_strategies()
        # Fallback if wizard page not initialized
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
        """Update the parameters panel for the selected strategy - delegates to wizard page."""
        if self.wizard_page:
            self.wizard_page._update_parameters_panel(strategy_name)

    def _mount_params_panel(self, strategy_name: str) -> None:
        """Mount the parameters panel - delegates to wizard page."""
        if self.wizard_page:
            self.wizard_page._mount_params_panel(strategy_name)

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
        """Navigate to wizard - delegates to dashboard page."""
        if self.dashboard_page:
            self.dashboard_page.handle_new_backtest()

    @on(Button.Pressed, "#btn-run-last")
    def on_run_last(self) -> None:
        """Run last configuration - delegates to dashboard page."""
        if self.dashboard_page:
            self.dashboard_page.handle_run_last()

    @on(Button.Pressed, "#btn-browse-templates")
    @on(Button.Pressed, "#btn-view-history")
    def on_view_history(self) -> None:
        """Navigate to history - delegates to dashboard page."""
        if self.dashboard_page:
            self.dashboard_page.handle_view_history()

    @on(Button.Pressed, "#btn-refresh-dash")
    def on_refresh_dashboard(self) -> None:
        """Refresh dashboard - delegates to dashboard page."""
        if self.dashboard_page:
            self.dashboard_page.handle_refresh()

    @on(Button.Pressed, "#btn-refresh-history")
    def on_refresh_history(self) -> None:
        """Refresh history - delegates to history page."""
        if self.history_page:
            self.history_page.handle_refresh()

    @on(Button.Pressed, "#btn-run-mc")
    @work
    async def on_run_monte_carlo(self) -> None:
        """Run Monte Carlo simulation - delegates to Monte Carlo page."""
        if self.monte_carlo_page:
            await self.monte_carlo_page.handle_run_monte_carlo()

    @on(Button.Pressed, "#btn-view-mc-charts")
    def on_view_mc_charts(self) -> None:
        """View Monte Carlo charts - delegates to Monte Carlo page."""
        if self.monte_carlo_page:
            self.monte_carlo_page.handle_view_charts()

    @on(Button.Pressed, "#btn-export-mc")
    def on_export_mc(self) -> None:
        """Export Monte Carlo results - delegates to Monte Carlo page."""
        if self.monte_carlo_page:
            self.monte_carlo_page.handle_export()

    @on(Button.Pressed, "#btn-stop-mc")
    def on_stop_mc(self) -> None:
        """Stop Monte Carlo simulation - delegates to Monte Carlo page."""
        if self.monte_carlo_page:
            self.monte_carlo_page.handle_stop_monte_carlo()

    @on(Button.Pressed, "#btn-compare-mc")
    def on_compare_mc(self) -> None:
        """Compare Monte Carlo results - delegates to Monte Carlo page."""
        if self.monte_carlo_page:
            self.monte_carlo_page.handle_compare_monte_carlo()

    @on(Button.Pressed, "#btn-run-wfo")
    def on_run_wfo(self) -> None:
        """Run Walk-Forward Optimization - delegates to WFO page."""
        if self.wfo_page:
            self.wfo_page.handle_run_wfo()

    @on(Button.Pressed, "#btn-view-wfo-report")
    def on_view_wfo_report(self) -> None:
        """View WFO report - delegates to WFO page."""
        if self.wfo_page:
            self.wfo_page.handle_view_report()

    @on(Button.Pressed, "#btn-export-wfo")
    def on_export_wfo(self) -> None:
        """Export WFO results - delegates to WFO page."""
        if self.wfo_page:
            self.wfo_page.handle_export()

    @on(Button.Pressed, "#btn-start-paper")
    def on_start_paper_trading(self) -> None:
        """Start paper trading - delegates to Paper Trading page."""
        if self.paper_trading_page:
            self.paper_trading_page.handle_start_paper_trading()

    @on(Button.Pressed, "#btn-stop-paper")
    def on_stop_paper_trading(self) -> None:
        """Stop paper trading - delegates to Paper Trading page."""
        if self.paper_trading_page:
            self.paper_trading_page.handle_stop_paper_trading()

    @on(Button.Pressed, "#btn-view-account")
    def on_view_account(self) -> None:
        """View account status - delegates to Paper Trading page."""
        if self.paper_trading_page:
            self.paper_trading_page.handle_view_account()

    @on(Input.Changed, "#history-search")
    def on_history_search(self, event: Input.Changed) -> None:
        """Filter history table - delegates to history page."""
        if self.history_page:
            self.history_page.handle_search(event.value.lower())

    @on(Button.Pressed, "#btn-clear-search")
    def on_clear_search(self) -> None:
        """Clear search - delegates to history page."""
        if self.history_page:
            self.history_page.handle_clear_search()

    @on(DataTable.RowSelected, "#history-table")
    def on_history_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle history row selection - delegates to history page."""
        if self.history_page:
            self.history_page.handle_row_selected(event.cursor_row)

    @on(Select.Changed, "#wizard-strategy")
    def on_strategy_changed(self, event: Select.Changed) -> None:
        """Handle strategy selection change - delegates to wizard page."""
        if event.value and self.wizard_page:
            strategy_name = str(event.value)
            self.wizard_page.handle_strategy_changed(strategy_name)

    @on(Select.Changed, "#wizard-exchange")
    @on(Select.Changed, "#wizard-timeframe")
    @on(Select.Changed, "#wizard-engine")
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select widget change - delegates to wizard page."""
        if event.value and self.wizard_page:
            widget_id = str(event.select.id) if hasattr(event.select, "id") else ""
            value = str(event.value)
            self.wizard_page.handle_select_changed(widget_id, value)

    @on(Input.Changed, "#wizard-symbol")
    @on(Input.Changed, "#wizard-limit")
    @on(Input.Changed, "#wizard-start-date")
    @on(Input.Changed, "#wizard-end-date")
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes - delegates to wizard page."""
        if self.wizard_page:
            widget_id = str(event.input.id) if hasattr(event.input, "id") else ""
            value = event.value
            self.wizard_page.handle_input_changed(widget_id, value, event.input)

    @on(Button.Pressed, "#wizard-run")
    @on(Button.Pressed, "#sidebar-run")
    @work
    async def on_run_wizard_backtest(self) -> None:
        """Handle run backtest - delegates to wizard page."""
        if self.wizard_page:
            await self.wizard_page.handle_run_backtest()

    @on(Button.Pressed, "#wizard-save-template")
    @on(Button.Pressed, "#sidebar-save")
    def on_save_template(self) -> None:
        """Save template - delegates to wizard page."""
        if self.wizard_page:
            self.wizard_page.handle_save_template()

    @on(Button.Pressed, "#wizard-reset")
    @on(Button.Pressed, "#sidebar-reset")
    def on_reset(self) -> None:
        """Reset configuration - delegates to wizard page."""
        if self.wizard_page:
            self.wizard_page.handle_reset()

    @on(Button.Pressed, "#wizard-charts")
    @work
    async def on_generate_wizard_charts(self) -> None:
        """Generate charts - delegates to wizard page."""
        if self.wizard_page:
            await self.wizard_page.handle_generate_charts()

    def _switch_to_tab(self, tab_name: str) -> None:
        """Switch to a different tab."""
        self.current_tab = tab_name
        body = self.query_one("#app-body", Container)
        # Explicitly remove all children to avoid duplicate IDs
        for child in list(body.children):
            child.remove()
        body.remove_children()

        if tab_name == "Dashboard":
            self.show_dashboard()
        elif tab_name == "Wizard":
            self.show_wizard()
        elif tab_name == "Monte Carlo":
            assert self.monte_carlo_page is not None
            body = self.query_one("#app-body", Container)
            self.monte_carlo_page.compose(body)
        elif tab_name == "History":
            self.show_history()
        elif tab_name == "Strategies":
            self.show_strategies()
        elif tab_name == "WFO":
            self.show_wfo()
        elif tab_name == "Paper Trading":
            self.show_paper_trading()

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
        if self.current_tab == "Dashboard" and self.dashboard_page:
            self.dashboard_page.handle_refresh()
        elif self.current_tab == "History" and self.history_page:
            self.history_page.handle_refresh()

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
            from textual.containers import Vertical
            from textual.screen import ModalScreen

            class HelpScreen(ModalScreen):
                """Modal screen for help dialog."""

                def compose(self):
                    yield Vertical(
                        Static(help_text),
                        Button("Close", variant="primary", id="close-help"),
                        id="help-dialog",
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
