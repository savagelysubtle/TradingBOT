"""Wizard page for the Trading Bot TUI."""

import asyncio
import contextlib
import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Input, Select, Static

from trading_bot.bot import TradingBot
from trading_bot.config import BacktestConfiguration, BacktestRun
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.interfaces.pages.base_page import BasePage
from trading_bot.interfaces.pages.wizard_logic import WizardLogic
from trading_bot.interfaces.pages.wizard_widgets import (
    WizardActionWidget,
    WizardDataConfigWidget,
    WizardProgressWidget,
    WizardResultsWidget,
    WizardStrategyConfigWidget,
)
from trading_bot.interfaces.widgets import (
    EnhancedProgressBar,
    RunHistorySidebar,
    StatusSidebar,
    StrategyParametersPanel,
    ValidationPanel,
)
from trading_bot.strategies.strategy_registry import _strategy_registry
from trading_bot.utils.visualization import plot_backtest_results, plot_simple_results

if TYPE_CHECKING:
    pass  # type: ignore[attr-defined]

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


class WizardPage(BasePage):
    """Wizard page for backtest configuration."""

    def __init__(self, app):
        super().__init__(app)
        self.logic = WizardLogic(self)

    def compose(self, body: Container) -> None:
        """Compose wizard widgets."""
        logger.info("Composing WizardPage")
        # Ensure body is empty
        if body.children:
            logger.debug(f"Removing {len(body.children)} existing children from body")
            for child in list(body.children):
                child.remove()

        body.mount(
            Horizontal(
                # Current Setup sidebar (left)
                Container(id="wizard-sidebar-container"),
                # Main configuration area (center)
                ScrollableContainer(
                    Vertical(
                        Static("[bold cyan]Backtest Wizard[/bold cyan]", id="wizard-title"),
                        Static(
                            "[dim]Configure your backtest in 3 steps, then run[/dim]",
                            id="wizard-hint",
                        ),
                        # Visual Progress Indicator
                        WizardProgressWidget(),
                        # Step 1: Data Configuration
                        WizardDataConfigWidget(self.backtest_config),
                        # Step 2: Strategy Selection
                        WizardStrategyConfigWidget(
                            self.backtest_config, self._get_available_strategies()
                        ),
                        # Validation panel
                        ValidationPanel(id="wizard-validation-panel"),
                        # Step 3: Run & Results
                        WizardActionWidget(),
                        # Results display
                        WizardResultsWidget(),
                        id="wizard-main",
                    ),
                    id="wizard-scroll",
                ),
                # History sidebar (right)
                Container(id="wizard-history-container"),
                id="wizard-container",
            ),
        )

        # Mount sidebars
        logger.debug("Mounting sidebars")
        # Current Setup sidebar (left)
        sidebar_container = self.app.query_one("#wizard-sidebar-container")
        self.app.sidebar = StatusSidebar(self.backtest_config, id="wizard-sidebar")
        sidebar_container.mount(self.app.sidebar)
        logger.debug("Status sidebar mounted")

        # History sidebar (right)
        history_container = self.app.query_one("#wizard-history-container")
        self.app.history_sidebar = RunHistorySidebar(self.history, id="wizard-history-sidebar")
        history_container.mount(self.app.history_sidebar)
        logger.debug("History sidebar mounted")

        # Ensure Select widgets display current values after mounting
        # Use call_after_refresh to ensure widgets are fully rendered
        logger.debug("Scheduling select value sync")
        self.app.call_after_refresh(self._sync_select_values)

        # Mount initial parameters panel
        logger.debug(
            f"Mounting parameters panel for strategy: {self.backtest_config.strategy_name}"
        )
        self._update_parameters_panel(self.backtest_config.strategy_name)
        logger.info("WizardPage composition complete")

    def _sync_select_values(self) -> None:
        """Sync Select widget values with current configuration.

        Sets defaults if config values are missing, and syncs widget values
        to ensure they display correctly. This prevents overwriting user selections.
        """
        logger.debug("Syncing select widget values with configuration")
        try:
            # Set exchange - ensure default if missing, then sync widget
            exchange_select = self.app.query_one("#wizard-exchange")
            exchange_value = self.backtest_config.exchange or "binance"
            if not self.backtest_config.exchange:
                self.backtest_config.update(exchange=exchange_value)

            current_value = exchange_select.value
            is_blank = (
                current_value == Select.BLANK
                or current_value is None
                or current_value == ""
                or str(current_value) != exchange_value
            )
            if is_blank:
                exchange_select.value = exchange_value
                exchange_select.refresh()
                logger.debug(f"Set exchange Select to: {exchange_value}")

            # Set timeframe - ensure default if missing, then sync widget
            timeframe_select = self.app.query_one("#wizard-timeframe")
            timeframe_value = self.backtest_config.timeframe or "1d"
            if not self.backtest_config.timeframe:
                self.backtest_config.update(timeframe=timeframe_value)

            current_value = timeframe_select.value
            is_blank = (
                current_value == Select.BLANK
                or current_value is None
                or current_value == ""
                or str(current_value) != timeframe_value
            )
            if is_blank:
                timeframe_select.value = timeframe_value
                timeframe_select.refresh()
                logger.debug(f"Set timeframe Select to: {timeframe_value}")

            # Set strategy - sync if config has value and widget doesn't match
            strategy_select = self.app.query_one("#wizard-strategy")
            if self.backtest_config.strategy_name:
                current_value = strategy_select.value
                is_blank = (
                    current_value == Select.BLANK
                    or current_value is None
                    or current_value == ""
                    or current_value != self.backtest_config.strategy_name
                )
                if is_blank:
                    strategy_select.value = self.backtest_config.strategy_name
                    strategy_select.refresh()

            # Set engine - ensure default if missing, then sync widget
            engine_select = self.app.query_one("#wizard-engine")
            engine_value = self.backtest_config.engine or "custom"
            if not self.backtest_config.engine:
                self.backtest_config.update(engine=engine_value)

            current_value = engine_select.value
            is_blank = (
                current_value == Select.BLANK
                or current_value is None
                or current_value == ""
                or str(current_value) != engine_value
            )
            if is_blank:
                engine_select.value = engine_value
                engine_select.refresh()
                logger.debug(f"Set engine Select to: {engine_value}")
            logger.debug("Select values synced successfully")
        except Exception as e:
            logger.exception(f"Failed to sync select values: {e}")

    def _get_available_strategies(self) -> list:
        """Get list of available strategies for dropdown.

        Returns:
            List of tuples (display_name, internal_name) from registry
        """
        return _strategy_registry.get_strategies_list()

    def _update_parameters_panel(self, strategy_name: str) -> None:
        """Update the parameters panel for the selected strategy."""
        logger.debug(f"Updating parameters panel for strategy: {strategy_name}")
        # Defer to after refresh to ensure any pending operations complete
        # The _mount_params_panel method will check if panel exists and update in place
        self.app.call_after_refresh(self._mount_params_panel, strategy_name)

    def _mount_params_panel(self, strategy_name: str) -> None:
        """Mount or update the parameters panel (called after cleanup completes)."""
        logger.debug(f"Mounting/updating parameters panel for strategy: {strategy_name}")
        try:
            container = self.app.query_one("#wizard-params-container")
            # Check if panel already exists - if so, update it instead of removing/remounting
            existing_panel = None
            try:
                existing_panel = container.query_one("#wizard-params", StrategyParametersPanel)
                logger.debug("Found existing parameters panel, updating in place")
            except Exception:
                # No existing panel found, will create new one
                logger.debug("No existing parameters panel found, will create new one")
                pass

            if existing_panel:
                # Update existing panel instead of removing/remounting (avoids duplicate ID issues)
                existing_panel.update_strategy(strategy_name)
                logger.info(f"Parameters panel updated for strategy: {strategy_name}")
            else:
                # Remove any remaining children first (safety measure)
                if container.children:
                    for child in list(container.children):
                        with contextlib.suppress(Exception):
                            child.remove()
                    container.remove_children()
                # Mount new panel
                params_panel = StrategyParametersPanel(strategy_name, id="wizard-params")
                container.mount(params_panel)
                logger.info(f"Parameters panel mounted for strategy: {strategy_name}")
        except Exception as e:
            logger.exception(f"Failed to mount/update params panel: {e}")

    def _update_wizard_progress(self) -> None:
        """Update wizard progress indicator based on filled fields."""
        try:
            # Determine current step based on completed fields
            step = 1
            step_text = "Data Configuration"

            # Check if Step 1 is complete (all data fields filled)
            if (
                self.backtest_config.symbol
                and "/" in self.backtest_config.symbol
                and self.backtest_config.limit >= 50
            ):
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
            progress_widget = self.app.query_one("#wizard-progress")
            progress_widget.update(progress_text)
        except Exception as e:
            logger.debug(f"Failed to update wizard progress: {e}")

    # Event handler methods (called from tui.py)

    def handle_strategy_changed(self, strategy_name: str) -> None:
        """Handle strategy selection change."""
        logger.info(f"Strategy changed to: {strategy_name}")
        self.backtest_config.update(strategy_name=strategy_name)
        # Note: Select widget already has the correct value from user's selection
        # No need to set it again - this was causing the value to disappear
        self._update_parameters_panel(strategy_name)

        # Update validation in real-time
        self.logic.validate_config()

        if self.app.sidebar:
            self.app.sidebar.update_display()
        self.logic.update_wizard_progress()
        logger.debug("Strategy change handled successfully")

    def handle_select_changed(self, widget_id: str, value: str) -> None:
        """Handle select widget change (exchange, timeframe, engine)."""
        logger.debug(f"Select widget changed: {widget_id} = {value}")
        if "exchange" in widget_id:
            logger.info(f"Exchange changed to: {value}")
            self.backtest_config.update(exchange=value)
        elif "timeframe" in widget_id:
            logger.info(f"Timeframe changed to: {value}")
            self.backtest_config.update(timeframe=value)
        elif "engine" in widget_id:
            logger.info(f"Engine changed to: {value}")
            self.backtest_config.update(engine=value)
        # Note: Select widget already has the correct value from user's selection
        # No need to set it again - this was causing the value to disappear

        # Update validation in real-time
        self.logic.validate_config()

        if self.app.sidebar:
            self.app.sidebar.update_display()
        self.logic.update_wizard_progress()
        logger.debug("Select change handled successfully")

    def handle_input_changed(self, widget_id: str, value: str, input_widget: Input) -> None:
        """Handle input changes with validation hints."""
        logger.debug(f"Input changed: {widget_id} = '{value}'")
        if "symbol" in widget_id:
            logger.debug(f"Symbol input changed: {value}")
            self.backtest_config.update(symbol=value)
            # Validate symbol format
            try:
                parent = input_widget.parent
                if parent:
                    hints = parent.query(".field-hint")
                    if hints:
                        hint = hints.first(Static)
                        if "/" in value and len(value.split("/")) == 2:
                            base, quote = value.split("/")
                            if base and quote:
                                hint.update("[green]✓[/green] [dim]Valid format[/dim]")
                            else:
                                hint.update(
                                    "[yellow]⚠[/yellow] [dim]Format: BASE/QUOTE (e.g., BTC/USDT)[/dim]"
                                )
                        elif value:
                            hint.update("[yellow]⚠[/yellow] [dim]Missing '/' separator[/dim]")
                        else:
                            hint.update("[dim]Format: BASE/QUOTE (e.g., BTC/USDT)[/dim]")
            except Exception as e:
                logger.exception(f"Failed to update symbol hint: {e}")

        elif "limit" in widget_id:
            # Validate candles number
            logger.debug(f"Limit input changed: {value}")
            try:
                parent = input_widget.parent
                if parent:
                    hints = parent.query(".field-hint")
                    if hints:
                        hint = hints.first(Static)
                        if value:
                            try:
                                limit_val = int(value)
                                self.backtest_config.update(limit=limit_val)
                                if 50 <= limit_val <= 1000:
                                    hint.update(
                                        "[green]✓[/green] [dim]Good range for backtesting[/dim]"
                                    )
                                elif limit_val < 50:
                                    hint.update(
                                        "[yellow]⚠[/yellow] [dim]Too few candles (50+ recommended)[/dim]"
                                    )
                                elif 1000 < limit_val <= 5000:
                                    hint.update(
                                        f"[yellow]⚠[/yellow] [dim]Large dataset (~{limit_val / 365:.1f} years for daily)[/dim]"
                                    )
                                elif limit_val > 5000:
                                    hint.update(
                                        f"[yellow]⚠[/yellow] [dim]Very large dataset (~{limit_val / 365:.1f} years for daily). Use date range instead.[/dim]"
                                    )
                            except ValueError:
                                hint.update("[red]✗[/red] [dim]Must be a number[/dim]")
                        else:
                            hint.update("[dim]Number of candles (or use date range below)[/dim]")
            except Exception as e:
                logger.exception(f"Failed to update limit hint: {e}")

        elif "start-date" in widget_id or "end-date" in widget_id:
            # Validate date format
            logger.debug(f"Date input changed: {widget_id} = {value}")
            if value:
                try:
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
                            parent = input_widget.parent
                            if parent:
                                hints = parent.query(".field-hint")
                                if hints:
                                    hint = hints.first(Static)
                                    hint.update(
                                        f"[green]✓[/green] [dim]~{estimated_candles:,} candles ({days} days)[/dim]"
                                    )
                        except Exception:
                            pass
                except ValueError:
                    parent = input_widget.parent
                    if parent:
                        hints = parent.query(".field-hint")
                        if hints:
                            hint = hints.first(Static)
                            hint.update(
                                "[red]✗[/red] [dim]Invalid date format (use YYYY-MM-DD)[/dim]"
                            )

        # Update validation in real-time
        self.logic.validate_config()

        if self.app.sidebar:
            self.app.sidebar.update_display()
        self.logic.update_wizard_progress()
        logger.debug("Input change handled successfully")

    async def handle_run_backtest(self) -> None:
        """Handle run backtest from wizard."""
        logger.info("Starting backtest from wizard")
        results_display = self.app.query_one("#wizard-results")
        progress_container = self.app.query_one("#wizard-progress-container")

        # Clear any existing progress widgets
        progress_container.remove_children()

        # Remove any existing progress bar with this ID to avoid duplicate ID error
        try:
            existing_bar = self.app.query_one("#wizard-progress-bar")
            existing_bar.remove()
        except Exception:
            # Widget doesn't exist, which is fine
            pass

        try:
            # Update config from inputs
            logger.debug("Syncing configuration from wizard inputs")
            self.logic.sync_config_from_inputs()

            # Validate configuration
            logger.debug("Validating backtest configuration")
            validation_errors = self.logic.validate_config()

            if validation_errors:
                logger.warning(f"Configuration validation failed: {validation_errors}")
                error_msg = "[red]✗ Validation Failed:[/red]\n"
                for error in validation_errors:
                    error_msg += f"  • {error}\n"
                error_msg += "\n[dim]Please fix the issues above and try again[/dim]"
                results_display.update(error_msg)
                return
            logger.debug("Configuration validation passed")

            # Show enhanced progress bar
            stages = [
                "Creating strategy",
                "Fetching market data",
                "Generating signals",
                "Running backtest",
                "Calculating metrics",
            ]
            progress_bar = EnhancedProgressBar(stages=stages, id="wizard-progress-bar")
            progress_container.mount(progress_bar)
            progress_bar.set_stage(0)  # Start with first stage

            # Set up cancellation handling
            cancelled = False

            def cancel_callback():
                nonlocal cancelled
                cancelled = True
                logger.info("Backtest cancelled by user")
                results_display.update("[yellow]⚠ Backtest cancelled by user[/yellow]")

            progress_bar.set_cancel_callback(cancel_callback)

            # Get strategy parameters
            try:
                logger.debug("Getting strategy parameters from panel")
                params_panel = self.app.query_one("#wizard-params")
                params = params_panel.get_parameters()
                logger.debug(f"Strategy parameters: {params}")
                self.backtest_config.update(strategy_params=params)

                # Validate MA periods
                param_errors = self.logic.validate_strategy_params(params)
                if param_errors:
                    logger.warning(f"Strategy parameter validation errors: {param_errors}")
                validation_errors.extend(param_errors)
            except Exception as e:
                logger.exception(f"Failed to get parameters: {e}")

            if validation_errors:
                error_msg = "[red]✗ Validation Failed:[/red]\n"
                for error in validation_errors:
                    error_msg += f"  • {error}\n"
                error_msg += "\n[dim]Please fix the issues above and try again[/dim]"
                results_display.update(error_msg)
                return

            # Update bot config
            if not self.app.config:
                results_display.update("[red]✗ Configuration not loaded[/red]")
                return

            self.app.config.data_provider = "ccxt"
            self.app.config.exchange_id = self.backtest_config.exchange
            self.app.config.backtest_engine = self.backtest_config.engine
            self.app.bot = TradingBot(self.app.config)

            # Create strategy
            logger.info(f"Creating strategy: {self.backtest_config.strategy_name}")
            progress_bar.set_stage(0)  # Creating strategy
            progress_bar.set_progress(10.0)  # 10% complete
            strategy = self.logic.create_strategy(self.backtest_config)
            if strategy is None:
                logger.error("Strategy creation returned None")
                results_display.update("[red]✗ Failed to create strategy[/red]")
                progress_bar.error("Strategy creation failed")
                return
            logger.info(f"Strategy created successfully: {strategy.name}")

            # Run backtest
            loop = asyncio.get_event_loop()

            # Fetch data
            progress_bar.set_stage(1)  # Fetching market data
            progress_bar.set_progress(25.0)  # 25% complete
            # Initialize fetch_kwargs before try block so it's available in exception handler
            fetch_kwargs: dict = {}
            try:
                # Determine fetch parameters first
                fetch_kwargs = self.logic.prepare_fetch_kwargs()
                logger.info(f"Fetching data: {fetch_kwargs}")

                # Validate fetch parameters before creating fetcher
                if not fetch_kwargs.get("symbol") or "/" not in str(fetch_kwargs["symbol"]):
                    raise ValueError(
                        f"Invalid symbol format: {fetch_kwargs.get('symbol')}. "
                        f"Expected format: BASE/QUOTE (e.g., BTC/USDT)"
                    )

                if not fetch_kwargs.get("timeframe"):
                    raise ValueError("Timeframe is required")

                fetcher = CCXTDataFetcher(
                    exchange_id=self.backtest_config.exchange, sandbox=False, use_cache=False
                )

                # Extract parameters
                symbol_param = str(fetch_kwargs["symbol"])
                timeframe_param = str(fetch_kwargs["timeframe"])
                limit_param = int(fetch_kwargs.get("limit", 1000))
                start_date_param = fetch_kwargs.get("start_date")
                end_date_param = fetch_kwargs.get("end_date")

                # Validate limit
                if limit_param <= 0:
                    raise ValueError(f"Invalid limit: {limit_param}. Must be greater than 0")

                def fetch_data():
                    try:
                        result = fetcher.fetch_ohlcv(
                            symbol=symbol_param,
                            timeframe=timeframe_param,
                            start_date=start_date_param
                            if isinstance(start_date_param, str)
                            else None,
                            end_date=end_date_param if isinstance(end_date_param, str) else None,
                            limit=limit_param,
                        )
                        return result
                    except Exception as fetch_error:
                        logger.error(f"CCXT fetch error: {fetch_error}")
                        raise

                data = await loop.run_in_executor(None, fetch_data)

                # Check for empty or None data with detailed diagnostics
                if data is None:
                    raise ValueError(
                        f"Data fetcher returned None for {symbol_param} on {self.backtest_config.exchange}. "
                        f"This usually means:\n"
                        f"  • Symbol doesn't exist on this exchange\n"
                        f"  • Exchange API returned an error\n"
                        f"  • Network connection issue"
                    )

                if data.empty:
                    # Provide helpful diagnostics for empty data
                    diagnostics = []
                    if start_date_param and end_date_param:
                        diagnostics.append(
                            f"  • Date range: {start_date_param} to {end_date_param} may have no data"
                        )
                    diagnostics.append(
                        f"  • Symbol {symbol_param} may not be available on {self.backtest_config.exchange}"
                    )
                    diagnostics.append(f"  • Timeframe {timeframe_param} may not be supported")
                    diagnostics.append("  • Try a different symbol or exchange")

                    raise ValueError(
                        f"No data returned for {symbol_param} on {self.backtest_config.exchange}\n\n"
                        f"Possible reasons:\n" + "\n".join(diagnostics)
                    )

                # Validate data has required columns
                required_columns = ["open", "high", "low", "close", "volume"]
                missing_columns = [col for col in required_columns if col not in data.columns]
                if missing_columns:
                    raise ValueError(
                        f"Data missing required columns: {missing_columns}. "
                        f"Available columns: {list(data.columns)}"
                    )

                logger.info(f"Data fetched successfully: {len(data)} rows")
                progress_bar.set_stage(2)  # Generating signals
                progress_bar.set_progress(50.0)  # 50% complete
            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                logger.error(f"Failed to fetch data: {e}\n{error_details}")
                progress_bar.error("Data fetch failed")

                # Build detailed error message
                error_msg_parts = [
                    "[red]✗ Failed to Fetch Data[/red]",
                    "",
                    f"[bold]Error:[/bold] {e!s}",
                    "",
                    "[bold]Configuration:[/bold]",
                    f"  • Exchange: {self.backtest_config.exchange}",
                    f"  • Symbol: {self.backtest_config.symbol}",
                    f"  • Timeframe: {self.backtest_config.timeframe}",
                    f"  • Limit: {fetch_kwargs.get('limit', 'N/A')}",
                ]

                if fetch_kwargs.get("start_date"):
                    error_msg_parts.append(f"  • Start Date: {fetch_kwargs.get('start_date')}")
                if fetch_kwargs.get("end_date"):
                    error_msg_parts.append(f"  • End Date: {fetch_kwargs.get('end_date')}")

                error_msg_parts.extend(
                    [
                        "",
                        "[bold]Troubleshooting:[/bold]",
                        "  • Verify symbol exists on exchange (e.g., BTC/USDT on Binance)",
                        "  • Check timeframe is supported (1m, 5m, 15m, 1h, 4h, 1d)",
                        "  • Try increasing candle count or using date range",
                        "  • Check internet connection",
                        "",
                        "[dim]Full error details logged to logs/trading_bot.log[/dim]",
                    ]
                )

                error_msg = "\n".join(error_msg_parts)
                results_display.update(error_msg)
                return

            # Generate signals
            progress_bar.set_stage(2)  # Generating signals
            try:
                logger.info(
                    f"Generating signals with strategy: {self.backtest_config.strategy_name}"
                )
                signals = await loop.run_in_executor(
                    None,
                    lambda: strategy.generate_signals(data),
                )

                if signals is None or signals.empty:
                    raise ValueError("Strategy generated no signals")

                logger.info(f"Signals generated successfully: {len(signals)} rows")
                progress_bar.set_stage(3)  # Running backtest
                progress_bar.set_progress(75.0)  # 75% complete
            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                logger.error(f"Failed to generate signals: {e}\n{error_details}")
                progress_bar.error("Signal generation failed")
                error_msg = (
                    f"[red]✗ Failed to Generate Signals[/red]\n\n"
                    f"[bold]Error:[/bold] {e!s}\n\n"
                    f"[bold]Details:[/bold]\n"
                    f"  • Strategy: {self.backtest_config.strategy_name}\n"
                    f"  • Parameters: {self.backtest_config.strategy_params}\n"
                    f"  • Data rows: {len(data) if data is not None else 0}\n\n"
                    f"[dim]Check logs/trading_bot.log for full details[/dim]"
                )
                results_display.update(error_msg)
                return

            # Run backtest
            if not self.app.bot:
                results_display.update("[red]✗ Bot not initialized[/red]")
                progress_bar.error("Bot not initialized")
                return

            bot = self.app.bot
            use_backtrader = self.backtest_config.engine == "backtrader"

            # Prepare backtest arguments (include fetched data to avoid re-fetching)
            backtest_kwargs = self.logic.prepare_backtest_kwargs(
                strategy, use_backtrader, data=data
            )

            progress_bar.set_stage(3)  # Running backtest
            progress_bar.set_progress(80.0)  # 80% complete
            try:
                logger.info(f"Running backtest with engine: {self.backtest_config.engine}")
                logger.info(f"Backtest kwargs: {backtest_kwargs}")
                results = await loop.run_in_executor(
                    None,
                    lambda: bot.backtest(**backtest_kwargs),
                )

                if results is None:
                    raise ValueError("Backtest returned no results")

                logger.info(
                    f"Backtest completed successfully: {results.get('total_trades', 0)} trades"
                )
                progress_bar.set_stage(4)  # Calculating metrics
                progress_bar.set_progress(95.0)  # 95% complete
                # Small delay to show final stage, then complete
                await asyncio.sleep(0.1)
                progress_bar.complete("Backtest completed successfully!")
            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                logger.error(f"Failed to run backtest: {e}\n{error_details}")
                progress_bar.error("Backtest execution failed")
                error_msg = (
                    f"[red]✗ Backtest Execution Failed[/red]\n\n"
                    f"[bold]Error:[/bold] {e!s}\n\n"
                    f"[bold]Details:[/bold]\n"
                    f"  • Engine: {self.backtest_config.engine}\n"
                    f"  • Strategy: {self.backtest_config.strategy_name}\n"
                    f"  • Symbol: {self.backtest_config.symbol}\n"
                    f"  • Timeframe: {self.backtest_config.timeframe}\n"
                    f"  • Limit: {backtest_kwargs.get('limit', 'N/A')}\n\n"
                    f"[dim]Check logs/trading_bot.log for full stack trace[/dim]"
                )
                results_display.update(error_msg)
                return

            # Store results
            self.app.backtest_results = results
            self.app.backtest_data = data
            self.app.backtest_signals = signals

            # Save to history
            logger.debug("Saving backtest run to history")
            run = BacktestRun(
                id=str(uuid.uuid4()),
                timestamp=datetime.now().isoformat(),
                config=self.backtest_config,
                results=results,
            )
            self.history.add_run(run)
            logger.info(f"Backtest run saved to history: {run.id}")

            # Refresh history sidebar
            if hasattr(self.app, "history_sidebar") and self.app.history_sidebar:
                self.app.history_sidebar.refresh_runs()

            # Display results
            results_widget = self.app.query_one("#wizard-results-section")
            results_widget.display_results(results)

            # Warn if no trades
            if results.get("total_trades", 0) == 0:
                self.app.notify(
                    "⚠ No trades generated! This usually means:\n"
                    "• MA periods are too long for the data (try shorter periods like 10/30)\n"
                    "• Not enough data (increase candles or use longer timeframe)\n"
                    "• No crossovers occurred in the selected period",
                    severity="warning",
                )

            self.app.notify("✓ Backtest completed!", severity="information")

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            logger.error(f"Unexpected error in backtest: {e}\n{error_details}")

            error_msg = (
                f"[red]✗ Unexpected Error[/red]\n\n"
                f"[bold]Error:[/bold] {e!s}\n\n"
                f"[bold]Error Type:[/bold] {type(e).__name__}\n\n"
                f"[dim]Full error details logged to logs/trading_bot.log[/dim]\n"
                f"[dim]Please check the log file for complete stack trace[/dim]"
            )
            results_display.update(error_msg)

            with contextlib.suppress(Exception):
                progress_bar.error("Unexpected error occurred")

    def handle_save_template(self) -> None:
        """Save current configuration as template."""
        logger.info("Saving configuration as template")
        self.sync_config_from_inputs()

        if not self.backtest_config.name:
            self.backtest_config.name = self.backtest_config.get_display_name()
            logger.debug(f"Generated template name: {self.backtest_config.name}")

        self.history.save_template(self.backtest_config)
        logger.info(f"Template saved: {self.backtest_config.name}")
        self.app.notify(f"✓ Template '{self.backtest_config.name}' saved!", severity="information")

    def handle_reset(self) -> None:
        """Reset configuration to defaults."""
        logger.info("Resetting wizard configuration to defaults")
        self.backtest_config = BacktestConfiguration()
        if self.app.current_tab == "Wizard":
            body = self.app.query_one("#app-body", Container)
            body.remove_children()
            self.app.call_after_refresh(self.app.show_wizard)
        logger.info("Configuration reset complete")
        self.app.notify("Configuration reset", severity="information")

    async def handle_generate_charts(self) -> None:
        """Generate visualization charts."""
        logger.info("Generating backtest visualization charts")
        if not self.app.backtest_results:
            logger.warning("No backtest results available for chart generation")
            self.app.notify("Run backtest first", severity="warning")
            return

        try:
            loop = asyncio.get_event_loop()

            if not self.app.config:
                logger.error("App config not available")
                return

            results = self.app.backtest_results
            data = self.app.backtest_data
            signals = self.app.backtest_signals
            results_dir = self.app.config.results_dir
            logger.debug(
                f"Chart generation: data={'available' if data is not None else 'None'}, signals={'available' if signals is not None else 'None'}"
            )

            if data is not None and signals is not None:
                logger.debug("Generating comprehensive backtest charts")
                plot_file = await loop.run_in_executor(
                    None,
                    lambda: plot_backtest_results(results, data, signals, output_dir=results_dir),
                )
            else:
                logger.debug("Generating simple backtest charts")
                plot_file = await loop.run_in_executor(
                    None,
                    lambda: plot_simple_results(results, output_dir=results_dir),
                )

            logger.info(f"Charts saved to {plot_file}")
            self.app.notify(f"✓ Charts saved to {plot_file}", severity="information")

        except Exception as e:
            logger.exception(f"Chart generation failed: {e}")
            self.app.notify(f"✗ Chart generation failed: {e}", severity="error")

    # Helper methods

    def sync_config_from_inputs(self) -> None:
        """Synchronize backtest_config from wizard input widgets."""
        logger.debug("Syncing configuration from wizard inputs")
        try:
            limit_value = self.app.query_one("#wizard-limit").value
            limit = int(limit_value) if limit_value else 365

            start_date_value = self.app.query_one("#wizard-start-date").value
            end_date_value = self.app.query_one("#wizard-end-date").value

            exchange_value = str(self.app.query_one("#wizard-exchange").value)
            symbol_value = self.app.query_one("#wizard-symbol").value
            timeframe_value = str(self.app.query_one("#wizard-timeframe").value)
            strategy_value = str(self.app.query_one("#wizard-strategy").value)
            engine_value = str(self.app.query_one("#wizard-engine").value)

            logger.debug(
                f"Syncing config: exchange={exchange_value}, symbol={symbol_value}, timeframe={timeframe_value}, strategy={strategy_value}, engine={engine_value}, limit={limit}"
            )

            self.backtest_config.update(
                exchange=exchange_value,
                symbol=symbol_value,
                timeframe=timeframe_value,
                limit=limit,
                start_date=start_date_value if start_date_value else None,
                end_date=end_date_value if end_date_value else None,
                strategy_name=strategy_value,
                engine=engine_value,
            )
            logger.debug("Configuration synced successfully")
        except Exception as e:
            logger.exception(f"Failed to sync config: {e}")
