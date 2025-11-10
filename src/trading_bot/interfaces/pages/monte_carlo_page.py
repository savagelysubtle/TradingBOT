"""Monte Carlo page for the Trading Bot TUI."""

import asyncio
import logging
import subprocess
from pathlib import Path

from textual import work
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Input, Label, Select, Static

from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.interfaces.pages.base_page import BasePage
from trading_bot.interfaces.widgets import MonteCarloResultsWidget

logger = logging.getLogger(__name__)


class MonteCarloPage(BasePage):
    """Monte Carlo simulation page."""

    def compose(self, body: Container) -> None:
        """Compose Monte Carlo page widgets."""
        logger.info("Composing MonteCarloPage")
        # Get recent backtest configurations for loading
        logger.debug("Loading recent backtest configurations")
        recent_runs = self.history.get_runs(limit=10)
        config_options = [("New Configuration", "__new__")]
        for run in recent_runs:
            label = f"{run.config.strategy_name} - {run.config.symbol} ({run.timestamp[:10]})"
            config_options.append((label, run.id))
        logger.debug(f"Loaded {len(recent_runs)} recent configurations for Monte Carlo")

        body.mount(
            ScrollableContainer(
                Vertical(
                    Static("[bold cyan]Monte Carlo Simulation[/bold cyan]", id="mc-title"),
                    Static(
                        "[dim]Run thousands of simulations to assess strategy robustness and risk[/dim]",
                        classes="step-hint",
                    ),
                    # Configuration Section
                    Static("[bold]⚙️ Configuration[/bold]", classes="step-title"),
                    Static(
                        "[dim]Select backtest configuration and simulation parameters[/dim]",
                        classes="step-hint",
                    ),
                    Horizontal(
                        Vertical(
                            Label("Load Config:"),
                            Select(
                                config_options,
                                value=config_options[0][1] if config_options else None,
                                id="mc-config-select",
                                allow_blank=False,
                            ),
                            Static(
                                "[dim]Load parameters from a previous backtest[/dim]",
                                classes="field-hint",
                            ),
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
                            Static(
                                "[dim]Bootstrap = resample data, Shuffle = randomize order, Randomize = add noise[/dim]",
                                classes="field-hint",
                            ),
                        ),
                        Vertical(
                            Label("Simulations:"),
                            Input(value="1000", id="mc-sims"),
                            Static(
                                "[dim]More simulations = better statistics (100-5000)[/dim]",
                                classes="field-hint",
                            ),
                        ),
                        Vertical(
                            Label("Seed (optional):"),
                            Input(value="", id="mc-seed"),
                            Static("[dim]For reproducible results[/dim]", classes="field-hint"),
                        ),
                        classes="wizard-row",
                        id="mc-config-row",
                    ),
                    # Action Buttons
                    Static("[bold]▶ Run Simulation[/bold]", classes="step-title"),
                    Horizontal(
                        Button("▶ Run Monte Carlo", id="btn-run-mc", variant="success"),
                        Button(
                            "📊 View Visualizations", id="btn-view-mc-charts", variant="primary"
                        ),
                        Button("💾 Export Results", id="btn-export-mc"),
                        id="mc-actions",
                    ),
                    # Progress and Status
                    Static("", id="mc-status"),
                    Static("", id="mc-progress-bar"),
                    # Results Display
                    Static("[bold]📊 Results[/bold]", classes="step-title"),
                    ScrollableContainer(
                        Static("", id="mc-results"),
                        id="mc-results-scroll",
                    ),
                    id="monte-carlo",
                ),
                id="mc-scroll",
            )
        )
        logger.info("MonteCarloPage composition complete")

    # Event handler methods (called from tui.py)

    @work
    async def handle_run_monte_carlo(self) -> None:
        """Run Monte Carlo simulation."""
        logger.info("Starting Monte Carlo simulation")
        status_widget = self.app.query_one("#mc-status", Static)
        results_widget = self.app.query_one("#mc-results", Static)
        progress_widget = self.app.query_one("#mc-progress-bar", Static)

        try:
            # Get configuration
            logger.debug("Reading Monte Carlo configuration from UI")
            config_select = self.app.query_one("#mc-config-select", Select)
            method_select = self.app.query_one("#mc-method", Select)
            sims_input = self.app.query_one("#mc-sims", Input)
            seed_input = self.app.query_one("#mc-seed", Input)

            selected_run_id = str(config_select.value) if config_select.value else "__new__"
            method = str(method_select.value) if method_select.value else "bootstrap"
            logger.debug(f"Configuration: run_id={selected_run_id}, method={method}")

            try:
                n_sims = int(sims_input.value) if sims_input.value else 1000
                logger.debug(f"Number of simulations: {n_sims}")
            except ValueError:
                logger.error(f"Invalid number of simulations: {sims_input.value}")
                status_widget.update("[red]✗ Invalid number of simulations[/red]")
                return

            seed = None
            if seed_input.value:
                try:
                    seed = int(seed_input.value)
                    logger.debug(f"Random seed: {seed}")
                except ValueError:
                    logger.error(f"Invalid seed value: {seed_input.value}")
                    status_widget.update("[red]✗ Seed must be a number[/red]")
                    return

            # Validate simulations
            if n_sims < 100:
                logger.warning(f"Low number of simulations: {n_sims} (recommended: 100+)")
                status_widget.update(
                    "[yellow]⚠ Warning: Less than 100 simulations may not be statistically significant[/yellow]"
                )
            elif n_sims > 5000:
                logger.warning(f"High number of simulations: {n_sims} (may take a long time)")
                status_widget.update(
                    "[yellow]⚠ Warning: More than 5000 simulations may take a long time[/yellow]"
                )

            # Load configuration
            if selected_run_id == "__new__":
                # Use wizard configuration
                logger.debug("Using wizard configuration for Monte Carlo")
                config = self.backtest_config
            else:
                # Load from history
                logger.debug(f"Loading configuration from history: {selected_run_id}")
                runs = self.history.get_runs(limit=100)
                run = next((r for r in runs if r.id == selected_run_id), None)
                if not run:
                    logger.error(f"Could not find run with ID: {selected_run_id}")
                    status_widget.update("[red]✗ Could not load configuration[/red]")
                    return
                config = run.config
                logger.info(f"Loaded configuration from history: {run.config.get_display_name()}")

            logger.info(
                f"Preparing Monte Carlo simulation: {config.symbol}, method={method}, n_sims={n_sims}"
            )
            status_widget.update("[yellow]⏳ Preparing Monte Carlo simulation...[/yellow]")
            progress_widget.update("[dim]Fetching data...[/dim]")

            # Fetch data
            logger.debug(
                f"Fetching data: exchange={config.exchange}, symbol={config.symbol}, timeframe={config.timeframe}, limit={config.limit}"
            )
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
            logger.info(f"Data fetched: {len(data)} rows")

            progress_widget.update("[dim]Creating strategy...[/dim]")
            logger.debug(f"Creating strategy: {config.strategy_name}")

            # Create strategy (use wizard page's method)
            if self.app.wizard_page:
                strategy = self.app.wizard_page.create_strategy(config)
                if strategy:
                    logger.info(f"Strategy created: {strategy.name}")
                else:
                    logger.error("Failed to create strategy")
            else:
                # Fallback if wizard page not initialized
                logger.error("Wizard page not initialized")
                status_widget.update("[red]✗ Wizard page not initialized[/red]")
                return
            if not strategy:
                logger.error("Strategy creation returned None")
                status_widget.update("[red]✗ Failed to create strategy[/red]")
                return

            # Create Monte Carlo engine
            logger.debug(f"Creating MonteCarloEngine: n_sims={n_sims}, seed={seed}")
            from trading_bot.backtesting.monte_carlo_engine import MonteCarloEngine

            mc_engine = MonteCarloEngine(
                initial_capital=10000.0,
                commission=0.001,
                slippage=0.0005,
                n_simulations=n_sims,
                random_seed=seed,
            )
            logger.info(f"MonteCarloEngine created: {n_sims} simulations, method={method}")

            status_widget.update(
                f"[green]▶[/green] Running {n_sims} {method} simulations on {config.symbol}..."
            )
            progress_widget.update(f"[green]{'━' * 50}[/green] 0%")

            # Run simulation (this will take time)
            logger.info(f"Starting Monte Carlo simulation: {n_sims} simulations, method={method}")
            results = await loop.run_in_executor(
                None,
                lambda: mc_engine.run(strategy, data, config.symbol, method=method),
            )
            logger.info(
                f"Monte Carlo simulation complete: probability_of_profit={results.get('probability_of_profit', 0):.2%}"
            )

            progress_widget.update(f"[green]{'█' * 50}[/green] 100%")
            status_widget.update("[green]✓ Monte Carlo simulation complete![/green]")

            # Display results using widget
            logger.debug("Displaying Monte Carlo results")
            MonteCarloResultsWidget.display_results(results, results_widget)

            # Save results
            logger.debug("Saving Monte Carlo results")
            result_dir = mc_engine.save_results(results)
            logger.info(f"Monte Carlo results saved to {result_dir}")
            self.app.notify(f"Results saved to {result_dir}", severity="information")

        except Exception as e:
            logger.exception(f"Monte Carlo simulation failed: {e}")
            status_widget.update(f"[red]✗ Error: {e!s}[/red]")

    def handle_view_charts(self) -> None:
        """Open the most recent Monte Carlo visualization."""
        logger.info("Opening Monte Carlo visualization")
        # Find the most recent Monte Carlo results directory
        results_dir = Path("results")
        if not results_dir.exists():
            logger.warning(f"Results directory does not exist: {results_dir}")
            self.app.notify("No Monte Carlo results found", severity="warning")
            return

        # Find most recent MC result
        logger.debug(f"Searching for Monte Carlo results in {results_dir}")
        mc_dirs = sorted(
            [d for d in results_dir.iterdir() if d.is_dir() and "monte_carlo" in d.name.lower()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        logger.debug(f"Found {len(mc_dirs)} Monte Carlo result directories")

        if not mc_dirs:
            logger.warning("No Monte Carlo results found")
            self.app.notify("No Monte Carlo results found", severity="warning")
            return

        # Open the comprehensive chart
        chart_file = mc_dirs[0] / "monte_carlo_comprehensive.png"
        logger.debug(f"Looking for chart file: {chart_file}")
        if chart_file.exists():
            try:
                logger.info(f"Opening chart: {chart_file}")
                subprocess.run(["start", str(chart_file)], shell=True, check=False)
                self.app.notify(f"Opened {chart_file.name}", severity="information")
                logger.info(f"Chart opened successfully: {chart_file.name}")
            except Exception as e:
                logger.exception(f"Failed to open chart: {e}")
                self.app.notify(f"Could not open chart: {e}", severity="error")
        else:
            logger.warning(f"Chart file not found: {chart_file}")
            self.app.notify("Chart file not found", severity="warning")

    def handle_export(self) -> None:
        """Export Monte Carlo results."""
        logger.info("Export Monte Carlo results requested")
        self.app.notify("Export functionality coming soon", severity="information")
