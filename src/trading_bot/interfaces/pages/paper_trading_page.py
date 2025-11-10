"""Paper Trading page for the Trading Bot TUI."""

import asyncio
import logging
from datetime import datetime

from textual import work
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Input, Label, Select, Static

from trading_bot.broker.paper import PaperBroker
from trading_bot.interfaces.pages.base_page import BasePage

logger = logging.getLogger(__name__)

# Import availability flags from main module
try:
    from trading_bot.interfaces.tui import TALIB_AVAILABLE
except ImportError:
    TALIB_AVAILABLE = False


class PaperTradingPage(BasePage):
    """Paper Trading (simulated live trading) page."""

    def __init__(self, app):
        """Initialize paper trading page."""
        super().__init__(app)
        self.is_running = False
        self.paper_broker: PaperBroker | None = None

    def compose(self, body: Container) -> None:
        """Compose Paper Trading page widgets."""
        logger.info("Composing PaperTradingPage")

        body.mount(
            Vertical(
                Static("[bold cyan]Paper Trading[/bold cyan]", id="paper-title"),
                Static(
                    "[dim]Simulate live trading without risking real money[/dim]",
                    id="paper-subtitle",
                ),
                # Configuration Section
                Horizontal(
                    Vertical(
                        Label("Symbol:"),
                        Input(placeholder="BTC/USDT", id="paper-symbol"),
                        Static("[dim]Trading pair or stock symbol[/dim]", classes="field-hint"),
                    ),
                    Vertical(
                        Label("Strategy:"),
                        Select(
                            [
                                ("Simple MA Crossover", "ma_crossover"),
                                ("TA-Lib MA" + (" ✓" if TALIB_AVAILABLE else " (req TA-Lib)"), "talib_ma"),
                                ("TA-Lib MACD" + (" ✓" if TALIB_AVAILABLE else " (req TA-Lib)"), "talib_macd"),
                            ],
                            value="ma_crossover",
                            id="paper-strategy",
                            allow_blank=False,
                        ),
                    ),
                    Vertical(
                        Label("Initial Capital:"),
                        Input(value="10000", id="paper-capital"),
                        Static("[dim]Starting capital in USD[/dim]", classes="field-hint"),
                    ),
                    id="paper-config-row-1",
                ),
                Horizontal(
                    Vertical(
                        Label("Short MA Window:"),
                        Input(value="50", id="paper-short-window"),
                    ),
                    Vertical(
                        Label("Long MA Window:"),
                        Input(value="200", id="paper-long-window"),
                    ),
                    Vertical(
                        Label("Check Interval (seconds):"),
                        Input(value="60", id="paper-interval"),
                        Static("[dim]How often to check for signals[/dim]", classes="field-hint"),
                    ),
                    id="paper-config-row-2",
                ),
                # Action Buttons
                Horizontal(
                    Button("▶ Start Paper Trading", id="btn-start-paper", variant="success"),
                    Button("⏸ Stop Trading", id="btn-stop-paper", variant="error"),
                    Button("📊 View Account", id="btn-view-account", variant="primary"),
                    id="paper-actions",
                ),
                # Status and Logs
                Static("", id="paper-status"),
                ScrollableContainer(
                    Static("", id="paper-logs"),
                    id="paper-logs-scroll",
                ),
                # Account Information
                ScrollableContainer(
                    Static("", id="paper-account"),
                    id="paper-account-scroll",
                ),
                id="paper-page",
            )
        )
        logger.info("PaperTradingPage composition complete")

    @work
    async def handle_start_paper_trading(self) -> None:
        """Start paper trading."""
        if self.is_running:
            self.app.notify("Paper trading is already running", severity="warning")
            return

        logger.info("Starting paper trading")
        status_widget = self.app.query_one("#paper-status", Static)
        logs_widget = self.app.query_one("#paper-logs", Static)
        account_widget = self.app.query_one("#paper-account", Static)

        try:
            # Get configuration
            symbol_input = self.app.query_one("#paper-symbol", Input)
            strategy_select = self.app.query_one("#paper-strategy", Select)
            capital_input = self.app.query_one("#paper-capital", Input)
            short_window_input = self.app.query_one("#paper-short-window", Input)
            long_window_input = self.app.query_one("#paper-long-window", Input)
            interval_input = self.app.query_one("#paper-interval", Input)

            symbol = symbol_input.value.strip() if symbol_input.value else ""
            strategy_name = str(strategy_select.value) if strategy_select.value else "ma_crossover"

            # Parse inputs
            try:
                initial_capital = float(capital_input.value) if capital_input.value else 10000.0
                short_window = int(short_window_input.value) if short_window_input.value else 50
                long_window = int(long_window_input.value) if long_window_input.value else 200
                check_interval = int(interval_input.value) if interval_input.value else 60
            except ValueError as e:
                logger.error(f"Invalid input value: {e}")
                status_widget.update(f"[red]✗ Invalid input: {e}[/red]")
                return

            # Validate inputs
            if not symbol:
                status_widget.update("[red]✗ Symbol is required[/red]")
                return

            if initial_capital <= 0:
                status_widget.update("[red]✗ Initial capital must be positive[/red]")
                return

            if short_window >= long_window:
                status_widget.update("[red]✗ Short window must be less than long window[/red]")
                return

            status_widget.update("[yellow]⏳ Starting paper trading...[/yellow]")
            logs_widget.update(f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] Starting paper trading...\n")

            # Create strategy
            if strategy_name == "ma_crossover":
                from trading_bot.strategies.moving_average import MovingAverageCrossover

                strategy = MovingAverageCrossover(short_window=short_window, long_window=long_window)
            elif strategy_name == "talib_ma":
                try:
                    from trading_bot.strategies.ta_lib_strategy import TALibMovingAverageCrossover

                    strategy = TALibMovingAverageCrossover(short_period=short_window, long_period=long_window)
                except ImportError:
                    status_widget.update("[red]✗ TA-Lib is required for this strategy[/red]")
                    return
            elif strategy_name == "talib_macd":
                try:
                    from trading_bot.strategies.ta_lib_strategy import TALibMACDStrategy

                    strategy = TALibMACDStrategy()
                except ImportError:
                    status_widget.update("[red]✗ TA-Lib is required for this strategy[/red]")
                    return
            else:
                status_widget.update(f"[red]✗ Unknown strategy: {strategy_name}[/red]")
                return

            # Create paper broker
            self.paper_broker = PaperBroker(
                initial_capital=initial_capital,
                commission=0.001,
                slippage=0.0005,
            )
            self.bot.set_broker(self.paper_broker)

            status_widget.update(f"[green]▶[/green] Paper trading active for {symbol}")
            logs_widget.update(
                logs_widget.renderable + f"\n[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] Strategy: {strategy_name}\n"
            )
            logs_widget.update(
                logs_widget.renderable + f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] Initial Capital: ${initial_capital:,.2f}\n"
            )

            self.is_running = True

            # Update account display
            self._update_account_display(account_widget)

            # Start live trading loop (this will run in background)
            # Note: run_live is blocking, so we need to run it in executor
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.bot.run_live(strategy=strategy, symbol=symbol, check_interval=check_interval),
            )

        except Exception as e:
            logger.exception(f"Paper trading failed: {e}")
            status_widget.update(f"[red]✗ Error: {e!s}[/red]")
            logs_widget.update(
                logs_widget.renderable + f"\n[red]{datetime.now().strftime('%H:%M:%S')}[/red] Error: {e}\n"
            )
            self.is_running = False

    def handle_stop_paper_trading(self) -> None:
        """Stop paper trading."""
        logger.info("Stopping paper trading")
        status_widget = self.app.query_one("#paper-status", Static)
        logs_widget = self.app.query_one("#paper-logs", Static)

        if not self.is_running:
            self.app.notify("Paper trading is not running", severity="warning")
            return

        # Note: run_live doesn't have a stop mechanism, so we'll just update status
        # In a real implementation, you'd need to add a stop flag to the bot
        self.is_running = False
        status_widget.update("[yellow]⏸ Paper trading stopped[/yellow]")
        logs_widget.update(
            logs_widget.renderable + f"\n[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] Paper trading stopped\n"
        )
        self.app.notify("Paper trading stopped", severity="information")

    def handle_view_account(self) -> None:
        """View account status."""
        logger.info("View account requested")
        account_widget = self.app.query_one("#paper-account", Static)

        if not self.paper_broker:
            account_widget.update("[yellow]No active paper trading session[/yellow]")
            return

        self._update_account_display(account_widget)

    def _update_account_display(self, widget: Static) -> None:
        """Update account display widget.

        Args:
            widget: Static widget to update
        """
        if not self.paper_broker:
            widget.update("[yellow]No active paper trading session[/yellow]")
            return

        try:
            account = self.paper_broker.get_account()
            positions = self.paper_broker.get_positions()

            output = []
            output.append("[bold cyan]Account Status[/bold cyan]\n")
            output.append("═" * 60 + "\n\n")
            output.append(f"Cash: ${account['cash']:,.2f}\n")
            output.append(f"Equity: ${account['equity']:,.2f}\n")
            output.append(f"Positions: {len(positions)}\n\n")

            if positions:
                output.append("[bold]Positions[/bold]\n")
                output.append("─" * 60 + "\n")
                for pos in positions:
                    output.append(f"Symbol: {pos['symbol']}\n")
                    output.append(f"  Quantity: {pos['quantity']:.2f}\n")
                    output.append(f"  Market Value: ${pos['market_value']:,.2f}\n\n")
            else:
                output.append("[dim]No open positions[/dim]\n")

            widget.update("".join(output))

        except Exception as e:
            logger.exception(f"Error updating account display: {e}")
            widget.update(f"[red]Error displaying account: {e}[/red]")

