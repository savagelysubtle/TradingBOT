"""History actions modal widget for the Trading Bot TUI."""

import subprocess
from pathlib import Path

from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from trading_bot.config import BacktestRun


class HistoryActionsModal(ModalScreen):
    """Modal screen for history row actions."""

    def __init__(self, parent_app, run_data: BacktestRun):
        """Initialize modal with run data.

        Args:
            parent_app: Reference to main TUI app
            run_data: BacktestRun instance
        """
        super().__init__()
        self.parent_app = parent_app
        self.run = run_data

    def compose(self):
        """Compose modal widgets."""
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
            id="history-actions-dialog",
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
