"""Strategies page for the Trading Bot TUI."""

import logging

from textual.containers import Container, Vertical
from textual.widgets import DataTable, Static

from trading_bot.interfaces.pages.base_page import BasePage

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


class StrategiesPage(BasePage):
    """Strategies page showing available trading strategies."""

    def compose(self, body: Container) -> None:
        """Compose strategies page widgets."""
        logger.info("Composing StrategiesPage")
        talib_status_text = (
            "[green]✓ TA-Lib Status: Available[/green]"
            if TALIB_AVAILABLE
            else "[red]✗ TA-Lib Status: Not detected[/red]"
        )
        logger.debug(f"TA-Lib available: {TALIB_AVAILABLE}, Advanced: {ADVANCED_AVAILABLE}, ML: {ML_AVAILABLE}")
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
        logger.info("StrategiesPage composition complete")

    def _populate_strategies_table(self) -> None:
        """Populate strategies table."""
        logger.debug("Populating strategies table")
        table = self.app.query_one("#strategies-table", DataTable)
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
        logger.info(f"Strategies table populated with {len(strategies_info)} strategies")

