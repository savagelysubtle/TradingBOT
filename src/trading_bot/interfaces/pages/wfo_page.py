"""Walk-Forward Optimization page for the Trading Bot TUI."""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from textual import work
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Input, Label, Select, Static

from trading_bot.backtesting.backtrader_engine import BacktraderEngine
from trading_bot.backtesting.engine import BacktestEngine
from trading_bot.backtesting.vectorbt_engine import VectorBTEngine
from trading_bot.backtesting.wfo_integration import WFOBacktestWrapper
from trading_bot.backtesting.wfo_report import print_wfo_report
from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.interfaces.pages.base_page import BasePage
from trading_bot.interfaces.widgets import WFOResultsWidget

logger = logging.getLogger(__name__)

# Import availability flags from main module
try:
    from trading_bot.interfaces.tui import TALIB_AVAILABLE
except ImportError:
    TALIB_AVAILABLE = False


class WFOPage(BasePage):
    """Walk-Forward Optimization page."""

    def compose(self, body: Container) -> None:
        """Compose WFO page widgets."""
        logger.info("Composing WFOPage")
        # Get recent backtest configurations for loading
        recent_runs = self.history.get_runs(limit=10)
        config_options = [("New Configuration", "__new__")]
        for run in recent_runs:
            label = f"{run.config.strategy_name} - {run.config.symbol} ({run.timestamp[:10]})"
            config_options.append((label, run.id))

        body.mount(
            Vertical(
                Static("[bold cyan]Walk-Forward Optimization[/bold cyan]", id="wfo-title"),
                Static(
                    "[dim]Test strategy robustness by optimizing on in-sample data and validating on out-of-sample data[/dim]",
                    id="wfo-subtitle",
                ),
                # Configuration Section
                Horizontal(
                    Vertical(
                        Label("Load Config:"),
                        Select(
                            config_options,
                            id="wfo-config-select",
                            allow_blank=False,
                        ),
                        Static(
                            "[dim]Load parameters from a previous backtest[/dim]",
                            classes="field-hint",
                        ),
                    ),
                    Vertical(
                        Label("Strategy:"),
                        Select(
                            [
                                ("TA-Lib MA" + (" ✓" if TALIB_AVAILABLE else " (req TA-Lib)"), "talib_ma"),
                                ("TA-Lib MACD" + (" ✓" if TALIB_AVAILABLE else " (req TA-Lib)"), "talib_macd"),
                            ],
                            value="talib_ma",  # Always set to first option, even if TA-Lib not available
                            id="wfo-strategy",
                            allow_blank=False,
                        ),
                        Static(
                            "[dim]Only strategies with parameter optimization support[/dim]",
                            classes="field-hint",
                        ),
                    ),
                    Vertical(
                        Label("Engine:"),
                        Select(
                            [
                                ("Backtrader", "backtrader"),
                                ("VectorBT", "vectorbt"),
                                ("Custom", "custom"),
                            ],
                            value="backtrader",
                            id="wfo-engine",
                            allow_blank=False,
                        ),
                    ),
                    id="wfo-config-row-1",
                ),
                Horizontal(
                    Vertical(
                        Label("Periods:"),
                        Input(value="5", id="wfo-periods"),
                        Static("[dim]Number of walk-forward periods (3-10)[/dim]", classes="field-hint"),
                    ),
                    Vertical(
                        Label("In-Sample %:"),
                        Input(value="70", id="wfo-in-sample"),
                        Static("[dim]Percentage for optimization (60-80%)[/dim]", classes="field-hint"),
                    ),
                    Vertical(
                        Label("Out-of-Sample %:"),
                        Input(value="30", id="wfo-out-sample"),
                        Static("[dim]Percentage for validation (20-40%)[/dim]", classes="field-hint"),
                    ),
                    Vertical(
                        Label("Optimize Metric:"),
                        Select(
                            [
                                ("Sharpe Ratio", "sharpe_ratio"),
                                ("Total Return", "total_return"),
                                ("Profit Factor", "profit_factor"),
                            ],
                            value="sharpe_ratio",
                            id="wfo-metric",
                            allow_blank=False,
                        ),
                    ),
                    id="wfo-config-row-2",
                ),
                # Data configuration
                Horizontal(
                    Vertical(
                        Label("Symbol:"),
                        Input(placeholder="BTC/USDT", id="wfo-symbol"),
                    ),
                    Vertical(
                        Label("Exchange:"),
                        Select(
                            [
                                ("Binance", "binance"),
                                ("Coinbase", "coinbase"),
                                ("Kraken", "kraken"),
                            ],
                            value="binance",
                            id="wfo-exchange",
                            allow_blank=False,
                        ),
                    ),
                    Vertical(
                        Label("Timeframe:"),
                        Select(
                            [
                                ("1m", "1m"),
                                ("5m", "5m"),
                                ("15m", "15m"),
                                ("1h", "1h"),
                                ("4h", "4h"),
                                ("1d", "1d"),
                                ("1w", "1w"),
                            ],
                            value="1d",
                            id="wfo-timeframe",
                            allow_blank=False,
                        ),
                    ),
                    Vertical(
                        Label("Limit:"),
                        Input(value="2000", id="wfo-limit"),
                        Static("[dim]Need 1000+ bars for WFO[/dim]", classes="field-hint"),
                    ),
                    id="wfo-data-row",
                ),
                # Action Buttons
                Horizontal(
                    Button("▶ Run WFO", id="btn-run-wfo", variant="success"),
                    Button("📊 View Report", id="btn-view-wfo-report", variant="primary"),
                    Button("💾 Export Results", id="btn-export-wfo"),
                    id="wfo-actions",
                ),
                # Progress and Status
                Static("", id="wfo-status"),
                Static("", id="wfo-progress-bar"),
                # Results Display
                ScrollableContainer(
                    Static("", id="wfo-results"),
                    id="wfo-results-scroll",
                ),
                id="wfo-page",
            )
        )
        logger.info("WFOPage composition complete")

    @work
    async def handle_run_wfo(self) -> None:
        """Run Walk-Forward Optimization."""
        logger.info("Starting Walk-Forward Optimization")
        status_widget = self.app.query_one("#wfo-status", Static)
        results_widget = self.app.query_one("#wfo-results", Static)
        progress_widget = self.app.query_one("#wfo-progress-bar", Static)

        try:
            # Get configuration
            config_select = self.app.query_one("#wfo-config-select", Select)
            strategy_select = self.app.query_one("#wfo-strategy", Select)
            engine_select = self.app.query_one("#wfo-engine", Select)
            periods_input = self.app.query_one("#wfo-periods", Input)
            in_sample_input = self.app.query_one("#wfo-in-sample", Input)
            out_sample_input = self.app.query_one("#wfo-out-sample", Input)
            metric_select = self.app.query_one("#wfo-metric", Select)
            symbol_input = self.app.query_one("#wfo-symbol", Input)
            exchange_select = self.app.query_one("#wfo-exchange", Select)
            timeframe_select = self.app.query_one("#wfo-timeframe", Select)
            limit_input = self.app.query_one("#wfo-limit", Input)

            selected_run_id = str(config_select.value) if config_select.value else "__new__"
            strategy_name = str(strategy_select.value) if strategy_select.value else "talib_ma"
            engine_name = str(engine_select.value) if engine_select.value else "backtrader"
            metric = str(metric_select.value) if metric_select.value else "sharpe_ratio"

            # Parse inputs
            try:
                periods = int(periods_input.value) if periods_input.value else 5
                in_sample_pct = float(in_sample_input.value) / 100.0 if in_sample_input.value else 0.70
                out_sample_pct = float(out_sample_input.value) / 100.0 if out_sample_input.value else 0.30
                limit = int(limit_input.value) if limit_input.value else 2000
            except ValueError as e:
                logger.error(f"Invalid input value: {e}")
                status_widget.update(f"[red]✗ Invalid input: {e}[/red]")
                return

            symbol = symbol_input.value.strip() if symbol_input.value else ""
            exchange = str(exchange_select.value) if exchange_select.value else "binance"
            timeframe = str(timeframe_select.value) if timeframe_select.value else "1d"

            # Validate inputs
            if not symbol:
                status_widget.update("[red]✗ Symbol is required[/red]")
                return

            if periods < 3 or periods > 10:
                status_widget.update("[red]✗ Periods must be between 3 and 10[/red]")
                return

            if in_sample_pct + out_sample_pct != 1.0:
                status_widget.update("[red]✗ In-sample and out-of-sample percentages must sum to 100%[/red]")
                return

            if limit < 1000:
                status_widget.update("[red]✗ Need at least 1000 bars for WFO[/red]")
                return

            # Check TA-Lib availability
            if strategy_name in ["talib_ma", "talib_macd"] and not TALIB_AVAILABLE:
                status_widget.update("[red]✗ TA-Lib is required for this strategy[/red]")
                return

            status_widget.update("[yellow]⏳ Preparing Walk-Forward Optimization...[/yellow]")
            progress_widget.update("[dim]Fetching data...[/dim]")

            # Load configuration or use defaults
            if selected_run_id == "__new__":
                config = self.backtest_config
            else:
                runs = self.history.get_runs(limit=100)
                run = next((r for r in runs if r.id == selected_run_id), None)
                if not run:
                    status_widget.update("[red]✗ Could not load configuration[/red]")
                    return
                config = run.config

            # Fetch data
            logger.debug(f"Fetching data: exchange={exchange}, symbol={symbol}, timeframe={timeframe}, limit={limit}")
            loop = asyncio.get_event_loop()
            fetcher = CCXTDataFetcher(exchange_id=exchange, sandbox=False, use_cache=False)
            data = await loop.run_in_executor(
                None,
                lambda: fetcher.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit,
                ),
            )
            logger.info(f"Data fetched: {len(data)} rows")

            if len(data) < 500:
                status_widget.update(
                    f"[red]✗ Insufficient data ({len(data)} bars). Need at least 500 bars for WFO.[/red]"
                )
                return

            progress_widget.update("[dim]Creating strategy...[/dim]")

            # Create strategy (use wizard page's method)
            if self.app.wizard_page:
                strategy = self.app.wizard_page.create_strategy(config)
                if not strategy:
                    status_widget.update("[red]✗ Failed to create strategy[/red]")
                    return
            else:
                # Fallback
                if strategy_name == "talib_ma":
                    from trading_bot.strategies.ta_lib_strategy import TALibMovingAverageCrossover

                    strategy = TALibMovingAverageCrossover(short_period=50, long_period=200)
                elif strategy_name == "talib_macd":
                    from trading_bot.strategies.ta_lib_strategy import TALibMACDStrategy

                    strategy = TALibMACDStrategy()
                else:
                    status_widget.update(f"[red]✗ Unknown strategy: {strategy_name}[/red]")
                    return

            # Check if strategy supports parameter optimization
            param_ranges = strategy.get_parameter_ranges()
            if not param_ranges:
                status_widget.update(
                    f"[red]✗ Strategy {strategy_name} does not support parameter optimization[/red]"
                )
                return

            progress_widget.update("[dim]Creating backtest engine...[/dim]")

            # Create backtest engine
            if engine_name == "backtrader":
                backtest_engine = BacktraderEngine(
                    initial_capital=self.config.initial_capital,
                    commission=self.config.commission or 0.001,
                )
            elif engine_name == "vectorbt":
                backtest_engine = VectorBTEngine(
                    initial_capital=self.config.initial_capital,
                    commission=self.config.commission or 0.001,
                    slippage=self.config.slippage or 0.0005,
                )
            else:
                backtest_engine = BacktestEngine(
                    initial_capital=self.config.initial_capital,
                    commission=self.config.commission or 0.001,
                    slippage=self.config.slippage or 0.0005,
                )

            # Create WFO wrapper
            wfo_wrapper = WFOBacktestWrapper(backtest_engine, strategy)

            status_widget.update(
                f"[green]▶[/green] Running Walk-Forward Optimization ({periods} periods)..."
            )
            progress_widget.update(f"[green]{'━' * 50}[/green] 0%")

            # Run WFO
            logger.info(
                f"Starting WFO: periods={periods}, in_sample={in_sample_pct:.0%}, out_sample={out_sample_pct:.0%}, metric={metric}"
            )
            # Unpack param_ranges dict as keyword arguments
            def run_wfo_sync():
                return wfo_wrapper.run_wfo(
                    data=data,
                    num_periods=periods,
                    in_sample_pct=in_sample_pct,
                    out_of_sample_pct=out_sample_pct,
                    metric=metric,
                    **param_ranges,
                )
            results = await loop.run_in_executor(None, run_wfo_sync)

            logger.info(f"WFO complete: WFE={results['overall']['wfe']:.2%}")

            progress_widget.update(f"[green]{'█' * 50}[/green] 100%")
            status_widget.update("[green]✓ Walk-Forward Optimization complete![/green]")

            # Display results
            WFOResultsWidget.display_results(results, results_widget)

            # Save results
            filename = f"wfo_{symbol.replace('/', '_')}_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            json_results = {
                "overall": {
                    "wfe": float(results["overall"]["wfe"]),
                    "status": results["overall"]["status"],
                    "avg_in_sample_return": float(results["overall"]["avg_in_sample_return"]),
                    "avg_out_of_sample_return": float(results["overall"]["avg_out_of_sample_return"]),
                    "num_periods": results["overall"]["num_periods"],
                    "avg_parameter_changes": float(results["overall"].get("avg_parameter_changes", 0)),
                },
                "in_sample_returns": [float(x) for x in results.get("in_sample_returns", [])],
                "out_of_sample_returns": [float(x) for x in results.get("out_of_sample_returns", [])],
                "periods": [
                    {
                        "in_sample_return": float(p.get("in_sample_return", 0)),
                        "out_of_sample_return": float(p.get("out_of_sample_return", 0)),
                        "optimal_params": p.get("optimal_params", {}),
                    }
                    for p in results.get("periods", [])
                ],
            }

            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            filepath = results_dir / filename

            with open(filepath, "w") as f:
                json.dump(json_results, f, indent=2)

            logger.info(f"WFO results saved to {filepath}")
            self.app.notify(f"Results saved to {filename}", severity="information")

        except Exception as e:
            logger.exception(f"WFO failed: {e}")
            status_widget.update(f"[red]✗ Error: {e!s}[/red]")

    def handle_view_report(self) -> None:
        """View detailed WFO report."""
        logger.info("View WFO report requested")
        # The results are already displayed in the results widget
        self.app.notify("Report displayed in results panel", severity="information")

    def handle_export(self) -> None:
        """Export WFO results."""
        logger.info("Export WFO results requested")
        self.app.notify("Export functionality coming soon", severity="information")

