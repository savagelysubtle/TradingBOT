"""Monte Carlo page for the Trading Bot TUI."""

import asyncio
import logging
import subprocess
from pathlib import Path

import numpy as np
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Input, Label, Select, Static

try:
    from scipy import stats as scipy_stats

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from trading_bot.data.ccxt_fetcher import CCXTDataFetcher
from trading_bot.interfaces.pages.base_page import BasePage
from trading_bot.interfaces.widgets import EnhancedProgressBar, MonteCarloResultsWidget

logger = logging.getLogger(__name__)


class MonteCarloPage(BasePage):
    """Monte Carlo simulation page."""

    def __init__(self, app):
        """Initialize Monte Carlo page."""
        super().__init__(app)
        self._progress_bar: EnhancedProgressBar | None = None
        self._cancel_requested = False
        self._current_task = None
        self._recent_results: list[dict] = []  # Store recent results for comparison

    def compose(self, body: Container) -> None:
        """Compose Monte Carlo page widgets with improved workspace allocation."""
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
            Vertical(
                # Header Section
                Vertical(
                    Static("[bold cyan]🎲 Monte Carlo Simulation[/bold cyan]", id="mc-title"),
                    Static(
                        "[dim]Run thousands of simulations to assess strategy robustness, risk, and probability of success[/dim]",
                        classes="step-hint",
                    ),
                    id="mc-header",
                ),
                # Main Working Area - Split into two columns
                Horizontal(
                    # Left Column - Configuration & Controls (1/3 width) - SCROLLABLE
                    Vertical(
                        ScrollableContainer(
                            Vertical(
                                Static("[bold]⚙️ Configuration[/bold]", classes="step-title"),
                                Static(
                                    "[dim]Select backtest configuration and simulation parameters[/dim]",
                                    classes="step-hint",
                                ),
                                # Configuration Parameters - needs Vertical for Select to render
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
                                # Simulation Parameters
                                Static("[bold]Simulation Parameters[/bold]", classes="step-title"),
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
                                    "[dim]Bootstrap = resample data[/dim]",
                                    classes="field-hint",
                                ),
                                Label("Simulations:"),
                                Input(value="1000", id="mc-sims"),
                                Static(
                                    "[dim]100-5000 recommended[/dim]",
                                    classes="field-hint",
                                ),
                                Label("Seed (optional):"),
                                Input(value="", id="mc-seed"),
                                Static(
                                    "[dim]For reproducibility[/dim]",
                                    classes="field-hint",
                                ),
                                # Action Buttons
                                Static("[bold]▶ Actions[/bold]", classes="step-title"),
                                Static(
                                    "[dim]Configure parameters above, then click Run[/dim]",
                                    classes="field-hint",
                                ),
                                Button(
                                    "▶ Run Simulation",
                                    id="btn-run-mc",
                                    variant="success",
                                    classes="run-button",
                                ),
                                Horizontal(
                                    Button("⏹️ Stop", id="btn-stop-mc", variant="error"),
                                    Button(
                                        "📊 View Charts",
                                        id="btn-view-mc-charts",
                                        variant="primary",
                                    ),
                                    id="mc-control-buttons",
                                ),
                                Horizontal(
                                    Button("💾 Export", id="btn-export-mc"),
                                    Button("🔄 Compare", id="btn-compare-mc"),
                                    id="mc-analysis-buttons",
                                ),
                                # Progress Section
                                Static("[bold]📈 Progress[/bold]", classes="step-title"),
                                Static("", id="mc-status"),
                                Container(
                                    id="mc-progress-container",
                                    classes="progress-container",
                                ),
                                # Quick Metrics Summary
                                Static("[bold]📊 Quick Metrics[/bold]", classes="step-title"),
                                Static("", id="mc-quick-metrics"),
                                classes="mc-scroll-content",
                            ),
                        ),
                        id="mc-left-panel",
                        classes="mc-left-panel",
                    ),
                    # Right Column - Results & Analysis (2/3 width)
                    Vertical(
                        # Results Header
                        Horizontal(
                            Static("[bold]📊 Results & Analysis[/bold]", classes="step-title"),
                            Static("", id="mc-results-summary"),
                            id="mc-results-header",
                        ),
                        # Main Results Display
                        ScrollableContainer(
                            Vertical(
                                # Summary Cards
                                Horizontal(
                                    Vertical(
                                        Static(
                                            "[bold]Return Statistics[/bold]",
                                            classes="metric-group-title",
                                        ),
                                        Static("", id="mc-return-stats"),
                                        classes="metric-card",
                                        id="mc-return-card",
                                    ),
                                    Vertical(
                                        Static(
                                            "[bold]Risk Metrics[/bold]",
                                            classes="metric-group-title",
                                        ),
                                        Static("", id="mc-risk-metrics"),
                                        classes="metric-card",
                                        id="mc-risk-card",
                                    ),
                                    Vertical(
                                        Static(
                                            "[bold]Probability Analysis[/bold]",
                                            classes="metric-group-title",
                                        ),
                                        Static("", id="mc-probability-analysis"),
                                        classes="metric-card",
                                        id="mc-probability-card",
                                    ),
                                    id="mc-summary-cards",
                                ),
                                # Detailed Results Table
                                Vertical(
                                    Static(
                                        "[bold]Detailed Results Table[/bold]", classes="sub-title"
                                    ),
                                    ScrollableContainer(
                                        Static("", id="mc-detailed-results"),
                                        id="mc-detailed-results-scroll",
                                        classes="results-table-container",
                                    ),
                                    id="mc-detailed-section",
                                ),
                                # Distribution Analysis
                                Vertical(
                                    Static(
                                        "[bold]Return Distribution Analysis[/bold]",
                                        classes="sub-title",
                                    ),
                                    Static("", id="mc-distribution-analysis"),
                                    id="mc-distribution-section",
                                ),
                                # Recommendations
                                Vertical(
                                    Static(
                                        "[bold]🤖 AI Recommendations[/bold]", classes="sub-title"
                                    ),
                                    Static("", id="mc-recommendations"),
                                    id="mc-recommendations-section",
                                ),
                                id="mc-results-content",
                            ),
                            id="mc-main-results",
                            classes="mc-main-results",
                        ),
                        id="mc-right-panel",
                        classes="mc-right-panel",
                    ),
                    id="mc-main-workspace",
                    classes="mc-main-workspace",
                ),
                id="monte-carlo",
                classes="monte-carlo-page",
            )
        )
        logger.info("MonteCarloPage composition complete with improved workspace")

    def _clear_results(self) -> None:
        """Clear all result widgets."""
        widgets_to_clear = [
            "#mc-quick-metrics",
            "#mc-return-stats",
            "#mc-risk-metrics",
            "#mc-probability-analysis",
            "#mc-detailed-results",
            "#mc-distribution-analysis",
            "#mc-recommendations",
            "#mc-results-summary",
        ]

        for widget_id in widgets_to_clear:
            try:
                widget = self.app.query_one(widget_id, Static)
                widget.update("")
            except Exception:
                pass  # Widget might not exist yet

    def _create_progress_bar(self) -> None:
        """Create and mount the enhanced progress bar."""
        try:
            # Remove existing progress bar if any
            if self._progress_bar:
                self._progress_bar.remove()

            # Create new progress bar with stages
            self._progress_bar = EnhancedProgressBar(
                stages=[
                    "Preparing simulation",
                    "Fetching market data",
                    "Running simulations",
                    "Aggregating results",
                    "Complete",
                ],
                can_cancel=True,
                id="mc-progress-bar",
            )

            # Set cancel callback
            self._progress_bar.set_cancel_callback(self._handle_cancel)

            # Mount to progress container
            container = self.app.query_one("#mc-progress-container", Container)
            container.mount(self._progress_bar)

            logger.debug("Enhanced progress bar created and mounted")

        except Exception as e:
            logger.exception(f"Failed to create progress bar: {e}")

    def _handle_cancel(self) -> None:
        """Handle cancellation request."""
        logger.info("Monte Carlo simulation cancellation requested")
        self._cancel_requested = True
        self.app.notify("Cancelling simulation...", severity="warning")

        # Update progress bar to show cancellation
        if self._progress_bar:
            self._progress_bar.stage = "Cancelling simulation..."
            try:
                # Disable cancel button during cancellation
                cancel_btn = self._progress_bar.query_one("#btn-cancel-progress", Button)
                cancel_btn.disabled = True
                cancel_btn.label = "Cancelling..."
            except Exception:
                pass

    def _update_progress(
        self, completed: int, total: int, stage: int = 2, eta_seconds: float | None = None
    ) -> None:
        """Update progress display with completion percentage and ETA.

        Args:
            completed: Number of simulations completed
            total: Total number of simulations
            stage: Current stage index (default 2 for simulation stage)
            eta_seconds: Estimated time remaining in seconds
        """
        if not self._progress_bar or not self._progress_bar.is_mounted:
            return

        # Calculate progress within current stage
        # Stage 0: Preparing (0-20%)
        # Stage 1: Fetching (20-25%)
        # Stage 2: Simulating (25-95%) - increased range for better visibility
        # Stage 3: Aggregating (95-98%)
        # Stage 4: Complete (98-100%)

        if stage == 0:  # Preparing
            self._progress_bar.set_stage(0)
            self._progress_bar.set_progress(10.0)
        elif stage == 1:  # Fetching
            self._progress_bar.set_stage(1)
            self._progress_bar.set_progress(22.5)
        elif stage == 2:  # Simulating
            self._progress_bar.set_stage(2)
            # Allocate more progress range to simulation stage (25-95% instead of 25-90%)
            sim_progress = (completed / total) * 70.0  # 70% of bar for simulation
            self._progress_bar.set_progress(25.0 + sim_progress)

            # Update ETA in stage label
            if eta_seconds:
                minutes = int(eta_seconds // 60)
                seconds = int(eta_seconds % 60)
                eta_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
                # Update the stage text to include ETA and simulation count
                stage_text = f"Running simulations ({completed}/{total}) - ETA: {eta_str}"
                self._progress_bar.stage = stage_text
        elif stage == 3:  # Aggregating
            self._progress_bar.set_stage(3)
            self._progress_bar.set_progress(96.0)
        elif stage == 4:  # Complete
            self._progress_bar.set_stage(4)
            self._progress_bar.set_progress(100.0)
            self._progress_bar.complete("Monte Carlo simulation complete!")

    # Event handler methods (called from tui.py)

    async def handle_run_monte_carlo(self) -> None:
        """Run Monte Carlo simulation with enhanced progress tracking."""
        logger.info("Starting Monte Carlo simulation - Use Cancel button or press Ctrl+C to stop")
        status_widget = self.app.query_one("#mc-status", Static)

        # Reset cancellation flag
        self._cancel_requested = False

        # Validate configuration first
        try:
            config_select = self.app.query_one("#mc-config-select", Select)
            selected_run_id = str(config_select.value) if config_select.value else "__new__"

            if selected_run_id == "__new__":
                # Check if wizard configuration is valid
                if not self.backtest_config.symbol or not self.backtest_config.strategy_name:
                    status_widget.update(
                        "[red]✗ Please configure backtest parameters in the Wizard tab first[/red]"
                    )
                    self.app.notify(
                        "Configure backtest parameters in Wizard tab before running Monte Carlo",
                        severity="error",
                    )
                    return
        except Exception as e:
            logger.exception(f"Configuration validation failed: {e}")
            status_widget.update("[red]✗ Configuration error[/red]")
            return

        # Clear previous results
        self._clear_results()

        # Create enhanced progress bar
        self._create_progress_bar()

        # Show initial feedback
        status_widget.update("[green]✓ Starting Monte Carlo simulation...[/green]")
        self.app.notify("Monte Carlo simulation starting...", severity="information")

        try:
            # Stage 0: Preparing
            self._update_progress(0, 1, stage=0)
            status_widget.update("[yellow]⏳ Preparing Monte Carlo simulation...[/yellow]")

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
                if self._progress_bar:
                    self._progress_bar.error("Invalid number of simulations")
                return

            seed = None
            if seed_input.value:
                try:
                    seed = int(seed_input.value)
                    logger.debug(f"Random seed: {seed}")
                except ValueError:
                    logger.error(f"Invalid seed value: {seed_input.value}")
                    status_widget.update("[red]✗ Seed must be a number[/red]")
                    if self._progress_bar:
                        self._progress_bar.error("Seed must be a number")
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
                    if self._progress_bar:
                        self._progress_bar.error("Could not load configuration")
                    return
                config = run.config
                logger.info(f"Loaded configuration from history: {run.config.get_display_name()}")

            logger.info(
                f"Preparing Monte Carlo simulation: {config.symbol}, method={method}, n_sims={n_sims}"
            )

            # Stage 1: Fetching data
            self._update_progress(0, n_sims, stage=1)
            status_widget.update("[yellow]⏳ Fetching market data...[/yellow]")

            # Fetch data
            logger.debug(
                f"Fetching data: exchange={config.exchange}, symbol={config.symbol}, timeframe={config.timeframe}, limit={config.limit}"
            )
            fetcher = CCXTDataFetcher(exchange_id=config.exchange, sandbox=False, use_cache=False)
            data = await asyncio.to_thread(
                fetcher.fetch_ohlcv,
                symbol=config.symbol,
                timeframe=config.timeframe,
                limit=config.limit,
            )
            logger.info(f"Data fetched: {len(data)} rows")

            # Check cancellation
            if self._cancel_requested:
                status_widget.update("[yellow]⏹️ Simulation cancelled[/yellow]")
                if self._progress_bar:
                    self._progress_bar.error("Cancelled by user")
                return

            # Create strategy
            logger.debug(f"Creating strategy: {config.strategy_name}")
            if self.app.wizard_page and self.app.wizard_page.logic:
                strategy = self.app.wizard_page.logic.create_strategy(config)
                if strategy:
                    logger.info(f"Strategy created: {strategy.name}")
                else:
                    logger.error("Failed to create strategy")
                    status_widget.update("[red]✗ Failed to create strategy[/red]")
                    if self._progress_bar:
                        self._progress_bar.error("Failed to create strategy")
                    return
            else:
                # Fallback if wizard page not initialized
                logger.error("Wizard page not initialized")
                status_widget.update("[red]✗ Wizard page not initialized[/red]")
                if self._progress_bar:
                    self._progress_bar.error("Wizard page not initialized")
                return

            # Check cancellation
            if self._cancel_requested:
                status_widget.update("[yellow]⏹️ Simulation cancelled[/yellow]")
                if self._progress_bar:
                    self._progress_bar.error("Cancelled by user")
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

            # Stage 2: Running simulations
            self._update_progress(0, n_sims, stage=2)
            status_widget.update(
                f"[green]▶[/green] Running {n_sims} {method} simulations on {config.symbol}..."
            )

            # Run simulation with progress callback
            logger.info(f"Starting Monte Carlo simulation: {n_sims} simulations, method={method}")

            # Create a progress callback for real-time updates
            import time

            start_time = time.time()
            last_update_time = start_time

            def progress_callback(completed: int) -> None:
                """Update progress during simulation."""
                nonlocal last_update_time

                # Update more frequently for better tracking
                # Every 5 simulations, every 0.2 seconds, or every 1% progress increment
                current_time = time.time()
                progress_percent = (completed / n_sims) * 100
                last_progress_percent = ((completed - 1) / n_sims) * 100 if completed > 0 else 0

                # Update if significant progress made or time elapsed
                if (completed % 5 == 0 or
                    (current_time - last_update_time) >= 0.2 or
                    int(progress_percent) > int(last_progress_percent)):

                    elapsed = current_time - start_time
                    if completed > 0:
                        rate = completed / elapsed
                        remaining = (n_sims - completed) / rate if rate > 0 else 0
                        self._update_progress(completed, n_sims, stage=2, eta_seconds=remaining)
                    else:
                        # Initial progress update
                        self._update_progress(completed, n_sims, stage=2, eta_seconds=None)
                    last_update_time = current_time

                # Check for cancellation
                if self._cancel_requested:
                    raise KeyboardInterrupt("Simulation cancelled by user")

            try:
                results = await asyncio.to_thread(
                    mc_engine.run,
                    strategy,
                    data,
                    config.symbol,
                    method=method,
                    progress_callback=progress_callback,
                )
            except KeyboardInterrupt:
                status_widget.update("[yellow]⏹️ Simulation cancelled by user[/yellow]")
                if self._progress_bar:
                    self._progress_bar.stage = "Simulation cancelled"
                    self._progress_bar.progress = 0.0
                    try:
                        # Re-enable cancel button for future use
                        cancel_btn = self._progress_bar.query_one("#btn-cancel-progress", Button)
                        cancel_btn.disabled = False
                        cancel_btn.label = "Cancel"
                    except Exception:
                        pass
                logger.info("Simulation cancelled by user")
                return

            logger.info(
                f"Monte Carlo simulation complete: probability_of_profit={results.get('probability_of_profit', 0):.2%}"
            )

            # Check cancellation one last time
            if self._cancel_requested:
                status_widget.update("[yellow]⏹️ Simulation cancelled[/yellow]")
                if self._progress_bar:
                    self._progress_bar.stage = "Simulation cancelled"
                    self._progress_bar.progress = 0.0
                    try:
                        # Re-enable cancel button for future use
                        cancel_btn = self._progress_bar.query_one("#btn-cancel-progress", Button)
                        cancel_btn.disabled = False
                        cancel_btn.label = "Cancel"
                    except Exception:
                        pass
                return

            # Stage 3: Aggregating results
            self._update_progress(n_sims, n_sims, stage=3)
            status_widget.update("[yellow]⏳ Aggregating results...[/yellow]")

            # Display results using enhanced widget layout
            logger.debug("Displaying Monte Carlo results with enhanced layout")
            self._display_enhanced_results(results)

            # Stage 4: Complete
            self._update_progress(n_sims, n_sims, stage=4)
            status_widget.update("[green]✓ Monte Carlo simulation complete![/green]")

            # Store results for comparison (keep last 5)
            self._recent_results.append(results)
            if len(self._recent_results) > 5:
                self._recent_results.pop(0)
            logger.debug(f"Stored results for comparison (total: {len(self._recent_results)})")

            # Save results
            logger.debug("Saving Monte Carlo results")
            result_dir = mc_engine.save_results(results)
            logger.info(f"Monte Carlo results saved to {result_dir}")
            self.app.notify(f"Results saved to {result_dir}", severity="information")

        except Exception as e:
            logger.exception(f"Monte Carlo simulation failed: {e}")
            status_widget.update(f"[red]✗ Error: {e!s}[/red]")
            if self._progress_bar:
                self._progress_bar.error(f"Error: {e!s}")

    def _display_enhanced_results(self, results: dict) -> None:
        """Display Monte Carlo results using the enhanced workspace layout."""
        # Update results summary header
        summary_widget = self.app.query_one("#mc-results-summary", Static)
        prob_profit = results["probability_of_profit"] * 100
        summary_text = f"[bold]{results['n_simulations']} simulations • {prob_profit:.1f}% profit probability[/bold]"
        summary_widget.update(summary_text)

        # Quick metrics for left panel
        self._display_quick_metrics(results)

        # Return statistics card
        self._display_return_stats(results)

        # Risk metrics card
        self._display_risk_metrics(results)

        # Probability analysis card
        self._display_probability_analysis(results)

        # Detailed results table
        self._display_detailed_results(results)

        # Distribution analysis
        self._display_distribution_analysis(results)

        # AI recommendations
        self._display_recommendations(results)

    def _display_quick_metrics(self, results: dict) -> None:
        """Display quick metrics summary in the left panel."""
        widget = self.app.query_one("#mc-quick-metrics", Static)

        prob_profit = results["probability_of_profit"] * 100
        sharpe = results["sharpe_ratio"]
        max_dd = results["worst_drawdown"] * 100
        mean_return = results["mean_return"] * 100

        metrics_text = f"""
[dim]Strategy:[/dim] {results.get("strategy", "Unknown")}
[dim]Symbol:[/dim] {results.get("symbol", "Unknown")}
[dim]Simulations:[/dim] {results.get("n_simulations", 0)}

[bold green]Profit Probability: {prob_profit:.1f}%[/bold green]
[dim]Mean Return:[/dim] {mean_return:+.2f}%
[dim]Sharpe Ratio:[/dim] {sharpe:.2f}
[dim]Max Drawdown:[/dim] {max_dd:.2f}%

[dim]Method:[/dim] {results.get("method", "Unknown")}
"""
        widget.update(metrics_text)

    def _display_return_stats(self, results: dict) -> None:
        """Display return statistics in the return stats card."""
        widget = self.app.query_one("#mc-return-stats", Static)

        mean_return = results["mean_return"] * 100
        median_return = results["median_return"] * 100
        std_return = results["std_return"] * 100
        p5 = results["percentile_5"] * 100
        p95 = results["percentile_95"] * 100

        stats_text = f"""
[dim]Mean Return:[/dim] {mean_return:+.2f}%
[dim]Median Return:[/dim] {median_return:+.2f}%
[dim]Std Deviation:[/dim] {std_return:.2f}%

[dim]5th Percentile:[/dim] {p5:+.2f}%
[dim]95th Percentile:[/dim] {p95:+.2f}%

[dim]Best Case:[/dim] {p95:+.2f}%
[dim]Worst Case:[/dim] {p5:+.2f}%
"""
        widget.update(stats_text)

    def _display_risk_metrics(self, results: dict) -> None:
        """Display risk metrics in the risk metrics card."""
        widget = self.app.query_one("#mc-risk-metrics", Static)

        sharpe = results["sharpe_ratio"]
        var_95 = results["var_95"] * 100
        mean_dd = results["mean_max_drawdown"] * 100
        worst_dd = results["worst_drawdown"] * 100

        risk_text = f"""
[dim]Sharpe Ratio:[/dim] {sharpe:.2f}
[dim]VaR (95%):[/dim] {var_95:+.2f}%

[dim]Mean Max DD:[/dim] {mean_dd:.2f}%
[dim]Worst Max DD:[/dim] {worst_dd:.2f}%

[dim]Risk-Adjusted:[/dim] {"✓ Good" if sharpe >= 1.0 else "⚠ Moderate" if sharpe >= 0.5 else "✗ Poor"}
"""
        widget.update(risk_text)

    def _display_probability_analysis(self, results: dict) -> None:
        """Display probability analysis in the probability card."""
        widget = self.app.query_one("#mc-probability-analysis", Static)

        prob_profit = results["probability_of_profit"] * 100

        # Calculate additional probabilities
        positive_returns = sum(1 for r in results.get("all_returns", []) if r > 0)
        total_sims = len(results.get("all_returns", []))
        prob_positive = (positive_returns / total_sims * 100) if total_sims > 0 else 0

        # Sharpe distribution analysis
        sharpes = results.get("sharpe_distribution", [])
        prob_good_sharpe = (
            sum(1 for s in sharpes if s >= 1.0) / len(sharpes) * 100 if sharpes else 0
        )

        prob_text = f"""
[dim]Profit Probability:[/dim] {prob_profit:.1f}%
[dim]Positive Return %:[/dim] {prob_positive:.1f}%

[dim]Good Sharpe (≥1.0):[/dim] {prob_good_sharpe:.1f}%

[dim]Confidence Level:[/dim] {"High" if prob_profit >= 70 else "Medium" if prob_profit >= 50 else "Low"}
"""
        widget.update(prob_text)

    def _display_detailed_results(self, results: dict) -> None:
        """Display detailed results table."""
        widget = self.app.query_one("#mc-detailed-results", Static)
        MonteCarloResultsWidget.display_results(results, widget)

    def _display_distribution_analysis(self, results: dict) -> None:
        """Display return distribution analysis."""
        widget = self.app.query_one("#mc-distribution-analysis", Static)

        # Analyze return distribution
        all_returns = results.get("all_returns", [])
        if not all_returns:
            widget.update("[dim]No return data available for distribution analysis[/dim]")
            return

        returns_array = np.array(all_returns)

        # Calculate skewness and kurtosis
        if SCIPY_AVAILABLE:
            skewness = float(scipy_stats.skew(returns_array))
            kurtosis = float(scipy_stats.kurtosis(returns_array))
        else:
            # Fallback to simple calculations without scipy
            mean = np.mean(returns_array)
            std = np.std(returns_array)
            n = len(returns_array)
            # Simple skewness estimation
            skewness = float(np.sum(((returns_array - mean) / std) ** 3) / n) if std > 0 else 0.0
            # Simple excess kurtosis estimation
            kurtosis = (
                float(np.sum(((returns_array - mean) / std) ** 4) / n - 3.0) if std > 0 else 0.0
            )

        # Categorize distribution
        if abs(skewness) < 0.5 and abs(kurtosis) < 0.5:
            distribution_type = "Normal-like"
        elif skewness > 1:
            distribution_type = "Right-skewed (positive bias)"
        elif skewness < -1:
            distribution_type = "Left-skewed (negative bias)"
        else:
            distribution_type = "Moderately skewed"

        if kurtosis > 1:
            distribution_type += " with fat tails (high risk)"
        elif kurtosis < -1:
            distribution_type += " with thin tails (low risk)"

        analysis_text = f"""
[dim]Return Distribution Analysis[/dim]

[dim]Sample Size:[/dim] {len(all_returns)} simulations
[dim]Distribution Type:[/dim] {distribution_type}

[dim]Skewness:[/dim] {skewness:.2f}
[dim]Kurtosis:[/dim] {kurtosis:.2f}

[dim]Interpretation:[/dim]
• {"Positive skew indicates potential for large gains" if skewness > 0.5 else "Negative skew suggests risk of large losses" if skewness < -0.5 else "Relatively symmetric returns"}
• {"Fat tails indicate higher probability of extreme events" if kurtosis > 1 else "Thin tails suggest more predictable outcomes" if kurtosis < -1 else "Normal tail behavior"}
"""
        widget.update(analysis_text)

    def _display_recommendations(self, results: dict) -> None:
        """Display AI-powered recommendations based on results."""
        widget = self.app.query_one("#mc-recommendations", Static)

        prob_profit = results["probability_of_profit"] * 100
        sharpe = results["sharpe_ratio"]
        max_dd = results["worst_drawdown"] * 100

        recommendations = []

        # Profit probability assessment
        if prob_profit >= 70:
            recommendations.append(
                "✅ [green]High probability of profit - Strategy shows strong potential[/green]"
            )
        elif prob_profit >= 50:
            recommendations.append(
                "⚠️ [yellow]Moderate profit probability - Consider optimization[/yellow]"
            )
        else:
            recommendations.append(
                "❌ [red]Low profit probability - Strategy needs significant improvement[/red]"
            )

        # Risk assessment
        if sharpe >= 1.5:
            recommendations.append("✅ [green]Excellent risk-adjusted returns[/green]")
        elif sharpe >= 1.0:
            recommendations.append("✅ [green]Good risk-adjusted returns[/green]")
        elif sharpe >= 0.5:
            recommendations.append("⚠️ [yellow]Moderate risk-adjusted returns[/yellow]")
        else:
            recommendations.append("❌ [red]Poor risk-adjusted returns - High risk[/red]")

        # Drawdown assessment
        if max_dd <= 10:
            recommendations.append("✅ [green]Acceptable maximum drawdown[/green]")
        elif max_dd <= 20:
            recommendations.append("⚠️ [yellow]Moderate drawdown - Monitor closely[/yellow]")
        else:
            recommendations.append(
                "❌ [red]High drawdown risk - Implement stricter risk controls[/red]"
            )

        # Specific recommendations
        if prob_profit < 50:
            recommendations.append(
                "💡 [blue]Consider: Reducing position sizes, tightening stops, or changing market conditions[/blue]"
            )

        if sharpe < 0.5:
            recommendations.append(
                "💡 [blue]Consider: Adding trend filters, improving entry timing, or diversifying signals[/blue]"
            )

        if max_dd > 20:
            recommendations.append(
                "💡 [blue]Consider: Implementing maximum drawdown limits, reducing leverage, or adding exit rules[/blue]"
            )

        rec_text = "\n".join(recommendations)
        widget.update(rec_text)

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

    def handle_stop_monte_carlo(self) -> None:
        """Stop Monte Carlo simulation."""
        logger.info("Stop Monte Carlo simulation requested")
        if not self._cancel_requested:
            self._cancel_requested = True
            status_widget = self.app.query_one("#mc-status", Static)
            status_widget.update("[yellow]⏹️ Cancelling simulation...[/yellow]")
            self.app.notify("Cancelling simulation - this may take a moment...", severity="warning")
            if self._progress_bar:
                self._progress_bar.stage = "Cancelling simulation..."
        else:
            self.app.notify("Cancel already requested", severity="information")

    def handle_compare_monte_carlo(self) -> None:
        """Compare Monte Carlo results."""
        logger.info("Compare Monte Carlo results requested")

        if len(self._recent_results) < 2:
            self.app.notify(
                f"Need at least 2 results to compare (have {len(self._recent_results)})",
                severity="warning",
            )
            return

        logger.debug(f"Comparing {len(self._recent_results)} Monte Carlo results")

        # Import and show comparison modal
        from trading_bot.interfaces.widgets import MonteCarloComparisonModal

        def show_comparison(accepted: bool) -> None:
            """Callback after modal closes."""
            if accepted:
                logger.debug("Comparison modal closed")

        self.app.push_screen(MonteCarloComparisonModal(self._recent_results), show_comparison)
