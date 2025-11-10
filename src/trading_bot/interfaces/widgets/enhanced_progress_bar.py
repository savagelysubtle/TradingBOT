"""Enhanced progress bar with stages and cancellation."""

import logging
from typing import Callable

from textual import on
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Button, ProgressBar, Static

logger = logging.getLogger(__name__)


class EnhancedProgressBar(Vertical):
    """Progress bar with stage tracking and cancel button."""

    DEFAULT_CSS = """
    EnhancedProgressBar {
        height: auto;
        min-height: 8;
        width: 100%;
        padding: 1;
        margin: 1 0;
        background: $surface;
        border: solid $primary;
    }

    EnhancedProgressBar .stage-label {
        text-align: center;
        margin-bottom: 1;
        height: auto;
        min-height: 1;
    }

    EnhancedProgressBar #progress-bar {
        height: 2;
        width: 100%;
        margin: 1 0;
    }

    EnhancedProgressBar .percentage {
        text-align: center;
        margin-top: 1;
        height: auto;
        min-height: 1;
        color: $text-muted;
    }

    EnhancedProgressBar .cancel-button {
        margin-top: 1;
        align: center middle;
        height: 3;
    }
    """

    progress = reactive(0.0)
    stage = reactive("")
    total_stages = reactive(1)
    current_stage = reactive(1)
    can_cancel = reactive(True)

    def __init__(
        self,
        stages: list[str] | None = None,
        can_cancel: bool = True,
        **kwargs
    ):
        """Initialize enhanced progress bar.

        Args:
            stages: List of stage names (e.g., ["Fetching data", "Processing", "Complete"])
            can_cancel: Whether to show cancel button
            **kwargs: Additional arguments passed to Vertical widget
        """
        super().__init__(**kwargs)
        self.stages = stages or ["Processing"]
        self.total_stages = len(self.stages)
        self.can_cancel = can_cancel
        self._cancel_callback: Callable[[], None] | None = None

        logger.debug(f"EnhancedProgressBar initialized with {self.total_stages} stages: {self.stages}")

    def compose(self):
        """Compose progress widgets."""
        yield Static(
            f"Stage {self.current_stage}/{self.total_stages}: {self.stage}",
            classes="stage-label",
            id="stage-label"
        )
        yield ProgressBar(total=100.0, show_eta=False, id="progress-bar")
        yield Static(f"{self.progress:.0f}%", classes="percentage", id="percentage-label")

        if self.can_cancel:
            yield Button("Cancel", variant="error", classes="cancel-button", id="btn-cancel-progress")

    def on_mount(self) -> None:
        """Initialize progress bar when mounted."""
        # Update display with current values
        self._sync_display()

    def _sync_display(self) -> None:
        """Sync display with current reactive values."""
        try:
            if not self.is_mounted:
                return
            # Update stage label
            label = self.query_one("#stage-label", Static)
            label.update(f"Stage {self.current_stage}/{self.total_stages}: {self.stage}")
            # Update progress bar
            bar = self.query_one("#progress-bar", ProgressBar)
            bar.update(progress=self.progress)
            # Update percentage
            percent = self.query_one("#percentage-label", Static)
            percent.update(f"{self.progress:.0f}%")
        except Exception as e:
            logger.debug(f"Display sync deferred: {e}")

    def watch_progress(self, progress: float) -> None:
        """Update progress bar when progress changes."""
        try:
            # Only update if widgets are mounted
            if not self.is_mounted:
                return
            bar = self.query_one("#progress-bar", ProgressBar)
            bar.update(progress=progress)

            percent = self.query_one("#percentage-label", Static)
            percent.update(f"{progress:.0f}%")

            logger.debug(f"Progress updated to {progress:.1f}%")
        except Exception as e:
            # Widgets not mounted yet, will update on mount
            logger.debug(f"Progress update deferred (widgets not mounted): {e}")

    def watch_stage(self, stage: str) -> None:
        """Update stage label when stage changes."""
        try:
            # Only update if widgets are mounted
            if not self.is_mounted:
                return
            label = self.query_one("#stage-label", Static)
            label.update(f"Stage {self.current_stage}/{self.total_stages}: {stage}")
            logger.debug(f"Stage updated to: {stage}")
        except Exception as e:
            # Widgets not mounted yet, will update on mount
            logger.debug(f"Stage update deferred (widgets not mounted): {e}")

    def set_stage(self, stage_index: int) -> None:
        """Set current stage by index and update progress.

        Args:
            stage_index: Zero-based index of stage to set
        """
        if 0 <= stage_index < len(self.stages):
            self.current_stage = stage_index + 1
            self.stage = self.stages[stage_index]
            # Calculate progress based on stage
            if self.total_stages > 0:
                stage_progress = (stage_index / self.total_stages) * 100.0
                self.progress = stage_progress
            logger.debug(f"Set stage to index {stage_index}: {self.stage} ({self.progress:.1f}%)")
        else:
            logger.warning(f"Invalid stage index: {stage_index} (max: {len(self.stages) - 1})")

    def set_progress(self, progress: float) -> None:
        """Set progress value (0-100).

        Args:
            progress: Progress value between 0 and 100
        """
        self.progress = max(0.0, min(100.0, progress))

    def advance_stage(self) -> None:
        """Advance to next stage."""
        next_stage = self.current_stage
        if next_stage <= self.total_stages:
            self.set_stage(next_stage - 1)  # set_stage expects 0-based index

    def set_cancel_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for cancel button.

        Args:
            callback: Function to call when cancel is pressed
        """
        self._cancel_callback = callback
        logger.debug("Cancel callback set")

    def complete(self, message: str = "Complete!") -> None:
        """Mark progress as complete.

        Args:
            message: Final message to display
        """
        self.progress = 100.0
        self.stage = message

        # Hide cancel button
        try:
            cancel_btn = self.query_one("#btn-cancel-progress", Button)
            cancel_btn.display = False
        except Exception:
            pass

        logger.debug("Progress marked as complete")

    def error(self, message: str = "Error occurred") -> None:
        """Mark progress as having an error.

        Args:
            message: Error message to display
        """
        self.stage = f"Error: {message}"

        # Update styling to show error
        try:
            label = self.query_one("#stage-label", Static)
            label.styles.border = ("solid", "$error")
            label.update(f"[red]{self.stage}[/red]")
        except Exception:
            pass

        logger.debug(f"Progress marked with error: {message}")

    @on(Button.Pressed, "#btn-cancel-progress")
    def handle_cancel(self) -> None:
        """Handle cancel button press."""
        logger.info("Cancel button pressed")
        if self._cancel_callback:
            try:
                self._cancel_callback()
                self.stage = "Cancelling..."
            except Exception as e:
                logger.exception(f"Cancel callback failed: {e}")
        else:
            logger.warning("Cancel pressed but no callback set")
