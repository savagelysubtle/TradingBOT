"""History page for the Trading Bot TUI."""

import logging

from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Static

from trading_bot.interfaces.pages.base_page import BasePage
from trading_bot.interfaces.widgets import HistoryActionsModal

logger = logging.getLogger(__name__)


class HistoryPage(BasePage):
    """History page showing backtest history with comparison capabilities."""

    def __init__(self, app):
        """Initialize history page."""
        super().__init__(app)
        self._history_runs = []
        logger.debug("HistoryPage initialized")

    def compose(self, body: Container) -> None:
        """Compose history page widgets."""
        logger.info("Composing HistoryPage")
        body.mount(
            Vertical(
                Static("[bold cyan]Backtest History[/bold cyan]", id="history-title"),
                Static(
                    "[dim]Search and click rows for quick actions[/dim]",
                    id="history-hint",
                ),
                Horizontal(
                    Input(
                        placeholder="🔍 Search by symbol, strategy, or date...",
                        id="history-search",
                    ),
                    Button("🗑️ Clear", id="btn-clear-search"),
                ),
                Horizontal(
                    Button("📊 Compare Selected", id="btn-compare", variant="primary"),
                    Button("💾 Export CSV", id="btn-export-history"),
                    Button("🔄 Refresh", id="btn-refresh-history"),
                ),
                DataTable(id="history-table", zebra_stripes=True),
                Static("", id="comparison-display"),
                id="history",
            ),
        )

        # Populate history table
        logger.debug("Populating history table")
        self._populate_history_table()
        logger.info("HistoryPage composition complete")

    def _populate_history_table(self) -> None:
        """Populate history table with runs and quick actions."""
        logger.debug("Populating history table")
        table = self.app.query_one("#history-table", DataTable)
        table.clear()
        table.add_columns(
            "Date",
            "Strategy",
            "Symbol",
            "TF",
            "Return %",
            "Trades",
            "Win Rate",
            "Sharpe",
            "Actions",
        )

        runs = self.history.get_runs(limit=50)
        logger.debug(f"Adding {len(runs)} runs to history table")
        for run in runs:
            r = run.results
            return_pct = r.get("total_return_pct", 0)
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
        logger.info(f"History table populated with {len(runs)} runs")

    # Event handler methods (called from tui.py)

    def handle_search(self, search_term: str) -> None:
        """Filter history table by search term."""
        logger.info(f"Searching history with term: '{search_term}'")
        table = self.app.query_one("#history-table", DataTable)
        table.clear()
        table.add_columns(
            "Date",
            "Strategy",
            "Symbol",
            "TF",
            "Return %",
            "Trades",
            "Win Rate",
            "Sharpe",
            "Actions",
        )

        runs = self.history.get_runs(limit=100)
        filtered_runs = []
        logger.debug(f"Filtering {len(runs)} runs with search term: '{search_term}'")

        for run in runs:
            # Filter by strategy name, symbol, or date
            if (
                search_term in run.config.strategy_name.lower()
                or search_term in run.config.symbol.lower()
                or search_term in run.timestamp.lower()
            ):
                r = run.results
                return_pct = r.get("total_return_pct", 0)
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
                    "▶ 📊 💾",
                )
                filtered_runs.append(run)

        # Update stored runs for quick actions
        self._history_runs = filtered_runs
        logger.info(f"Search complete: {len(filtered_runs)} runs match '{search_term}'")

    def handle_clear_search(self) -> None:
        """Clear search and show all results."""
        logger.info("Clearing search filter")
        try:
            search_input = self.app.query_one("#history-search", Input)
            search_input.value = ""
            self._populate_history_table()
            logger.info("Search cleared, showing all results")
        except Exception as e:
            logger.exception(f"Failed to clear search: {e}")

    def handle_row_selected(self, row_index: int) -> None:
        """Handle history table row selection for quick actions."""
        logger.debug(f"Row selected: index={row_index}, total_runs={len(self._history_runs)}")
        if not self._history_runs or row_index >= len(self._history_runs):
            logger.warning(f"Invalid row index: {row_index} (max: {len(self._history_runs) - 1})")
            return

        try:
            run = self._history_runs[row_index]
            logger.info(
                f"Opening actions modal for run: {run.id} - {run.config.get_display_name()}"
            )
            # Use the modal widget
            modal = HistoryActionsModal(self.app, run)
            self.app.push_screen(modal)
            logger.debug("Actions modal opened")
        except Exception as e:
            logger.exception(f"Failed to handle history row selection: {e}")

    def handle_refresh(self) -> None:
        """Refresh history table."""
        logger.info("Refreshing history table")
        self._populate_history_table()
        self.app.notify("Refreshed", severity="information")
        logger.info("History table refreshed")
