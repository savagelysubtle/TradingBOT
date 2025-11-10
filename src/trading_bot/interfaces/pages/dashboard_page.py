"""Dashboard page for the Trading Bot TUI."""

import asyncio
import logging
import sys

from rich.console import Console
from rich.table import Table
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Static

from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.interfaces.pages.base_page import BasePage
from trading_bot.interfaces.widgets import LoadBarWidget

logger = logging.getLogger(__name__)

# Import availability flags from main module
try:
    from trading_bot.interfaces.tui import (
        ADVANCED_AVAILABLE,
        ML_AVAILABLE,
        TALIB_AVAILABLE,
    )
except ImportError:
    # Fallback if not available
    TALIB_AVAILABLE = False
    ADVANCED_AVAILABLE = False
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


class DashboardPage(BasePage):
    """Dashboard page showing recent runs, templates, and quick actions."""

    def compose(self, body: Container) -> None:
        """Compose dashboard widgets."""
        logger.info("Composing DashboardPage")
        # Get recent runs
        logger.debug("Fetching recent runs and templates")
        recent_runs = self.history.get_runs(limit=5)
        templates = self.history.get_templates()
        logger.debug(f"Loaded {len(recent_runs)} recent runs and {len(templates)} templates")

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
            logger.debug(f"Starting live price ticker for {symbol}")
            # Create task on event loop since DashboardPage is not a DOMNode
            loop = asyncio.get_event_loop()
            self._price_ticker_task = loop.create_task(self._start_live_price_ticker(symbol))
            logger.info(f"Live price ticker started for {symbol}")
        else:
            logger.debug("No recent runs found, skipping live price ticker")

        body.mount(
            Vertical(
                Static("[bold cyan]Trading Bot Dashboard[/bold cyan]", id="dashboard-title"),
                Horizontal(
                    Vertical(
                        Static("[bold]System Status[/bold]"),
                        Static(f"[green]✓[/green] {get_python_version_string()}"),
                        Static("[green]✓[/green] CCXT Connected"),
                        Static(
                            f"[green]✓[/green] Strategies: {sum([1, TALIB_AVAILABLE * 2, ADVANCED_AVAILABLE * 3, ML_AVAILABLE])} Ready"
                        ),
                        Static(
                            "[green]✓[/green] TA-Lib: Available"
                            if TALIB_AVAILABLE
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
        logger.debug("Rendering dashboard tables")
        console = Console()

        with console.capture() as capture:
            console.print(recent_table)
        self.app.query_one("#dashboard-recent", Static).update(capture.get())
        logger.debug("Recent runs table rendered")

        with console.capture() as capture:
            console.print(templates_table)
        self.app.query_one("#dashboard-templates", Static).update(capture.get())
        logger.debug("Templates table rendered")
        logger.info("DashboardPage composition complete")

    def _create_performance_sparkline(self, runs: list) -> str:
        """Create ASCII sparkline of recent backtest performance."""
        logger.debug(f"Creating performance sparkline from {len(runs)} runs")
        if not runs or len(runs) < 2:
            logger.debug("Insufficient runs for sparkline")
            return "[dim]No data[/dim]"

        # Get last 10 runs
        runs_to_show = runs[:10] if len(runs) >= 10 else runs
        returns = [r.results.get("total_return_pct", 0) for r in runs_to_show]

        # Reverse to show oldest to newest
        returns = list(reversed(returns))
        logger.debug(f"Sparkline created from {len(returns)} returns: {returns[:3]}...")

        return LoadBarWidget.generate_sparkline(returns)

    async def _start_live_price_ticker(self, symbol: str) -> None:
        """Update live price display every 5 seconds."""
        logger.info(f"Starting live price ticker for {symbol}")
        # Create fetcher outside loop to avoid binding issues
        price_fetcher = CCXTDataFetcher(exchange_id="binance", sandbox=False, use_cache=False)
        logger.debug("Price fetcher created for live ticker")

        for iteration in range(12):  # Run for 60 seconds (12 * 5)
            try:
                logger.debug(f"Fetching price update #{iteration + 1}/12 for {symbol}")
                # Fetch current price
                loop = asyncio.get_event_loop()

                def fetch_ticker():
                    return price_fetcher.exchange.fetch_ticker(symbol)

                ticker = await loop.run_in_executor(None, fetch_ticker)

                price = ticker.get("last", 0)
                change_pct = ticker.get("percentage", 0)
                arrow = "↑" if change_pct > 0 else "↓"
                color = "green" if change_pct > 0 else "red"
                logger.debug(f"Price update #{iteration + 1}: ${price:,.2f} ({change_pct:.2f}%)")

                try:
                    price_widget = self.app.query_one("#live-price", Static)
                    price_widget.update(
                        f"[bold]💹 {symbol}:[/bold] ${price:,.2f} "
                        f"[{color}]{arrow} {change_pct:.2f}%[/{color}]"
                    )
                    logger.debug("Price widget updated successfully")
                except Exception as e:
                    # Widget might have been removed if user switched tabs
                    logger.debug(f"Price widget not found (user may have switched tabs): {e}")
                    break

                await asyncio.sleep(5)
            except Exception as e:
                logger.warning(f"Failed to update live price (iteration {iteration + 1}): {e}")
                break

        logger.info(f"Live price ticker stopped for {symbol}")

    # Event handler methods (called from tui.py)

    def handle_new_backtest(self) -> None:
        """Navigate to wizard for new backtest."""
        logger.info("Navigating to wizard for new backtest")
        self.app._switch_to_tab("Wizard")

    def handle_run_last(self) -> None:
        """Run last configuration."""
        logger.info("Loading last configuration")
        runs = self.history.get_runs(limit=1)
        if runs:
            logger.debug(f"Found last run: {runs[0].id} - {runs[0].config.get_display_name()}")
            self.backtest_config = runs[0].config
            self.app._switch_to_tab("Wizard")
            self.app.notify("Loaded last configuration", severity="information")
            logger.info("Last configuration loaded successfully")
        else:
            logger.warning("No previous runs found")
            self.app.notify("No previous runs found", severity="warning")

    def handle_view_history(self) -> None:
        """Navigate to history tab."""
        logger.info("Navigating to history tab")
        self.app._switch_to_tab("History")

    def handle_refresh(self) -> None:
        """Refresh dashboard view."""
        logger.info("Refreshing dashboard")
        body = self.app.query_one("#app-body", Container)
        body.remove_children()
        self.compose(body)
        self.app.notify("Refreshed", severity="information")
        logger.info("Dashboard refreshed")
