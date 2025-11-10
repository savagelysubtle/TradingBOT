"""Load bar widget for displaying animated loading progress."""

import logging
from textual.widgets import Static
from textual.reactive import reactive

logger = logging.getLogger(__name__)


class LoadBarWidget(Static):
    """Animated loading bar widget with progress indication."""

    DEFAULT_CSS = """
    LoadBarWidget {
        height: 5;
        min-height: 5;
        width: 100%;
        content-align: center middle;
        background: $boost;
        border: solid $primary;
        padding: 1;
        margin: 1 0;
    }
    """

    progress = reactive(0.0)  # 0.0 to 100.0
    message = reactive("Loading...")
    show_percentage = reactive(True)

    def __init__(
        self,
        progress: float = 0.0,
        message: str = "Loading...",
        show_percentage: bool = True,
        **kwargs
    ):
        """Initialize loading bar widget.

        Args:
            progress: Initial progress value (0-100)
            message: Loading message to display
            show_percentage: Whether to show percentage in the message
            **kwargs: Additional arguments passed to Static widget
        """
        super().__init__(**kwargs)
        self.progress = max(0.0, min(100.0, progress))
        self.message = message
        self.show_percentage = show_percentage

    def on_mount(self) -> None:
        """Initialize display when widget is mounted."""
        logger.debug("LoadBarWidget mounted")
        self._update_display()

    def watch_progress(self, old_progress: float, new_progress: float) -> None:
        """Update display when progress changes."""
        self._update_display()

    def watch_message(self, old_message: str, new_message: str) -> None:
        """Update display when message changes."""
        self._update_display()

    def _update_display(self) -> None:
        """Update the widget display with current progress."""
        try:
            # Create progress bar visualization - wider bar for better visibility
            bar_width = 40  # Wider progress bar in characters
            filled_chars = int((self.progress / 100.0) * bar_width)
            empty_chars = bar_width - filled_chars

            # Use thicker block characters for better visibility
            progress_bar = f"[bold green]{'█' * filled_chars}[/bold green][dim]{'░' * empty_chars}[/dim]"

            # Format message with percentage if requested
            display_message = self.message
            if self.show_percentage:
                display_message = f"{self.message} [bold]{self.progress:.0f}%[/bold]"

            # Combine progress bar and message with proper spacing
            display = f"\n{progress_bar}\n{display_message}\n"

            self.update(display)
            logger.debug(f"LoadBarWidget updated: {self.progress:.1f}% - {self.message}")

        except Exception as e:
            logger.exception(f"Failed to update LoadBarWidget display: {e}")

    def set_progress(self, progress: float, message: str | None = None) -> None:
        """Set progress value and optionally update message.

        Args:
            progress: Progress value (0-100)
            message: Optional new message
        """
        self.progress = max(0.0, min(100.0, progress))
        if message is not None:
            self.message = message

    def increment_progress(self, amount: float = 1.0, message: str | None = None) -> None:
        """Increment progress by specified amount.

        Args:
            amount: Amount to increment (default: 1.0)
            message: Optional new message
        """
        self.set_progress(self.progress + amount, message)

    def complete(self, message: str = "Complete!") -> None:
        """Mark progress as complete.

        Args:
            message: Completion message
        """
        self.set_progress(100.0, message)

    def reset(self, message: str = "Loading...") -> None:
        """Reset progress to 0.

        Args:
            message: Reset message
        """
        self.set_progress(0.0, message)

    # Static method for sparkline generation (legacy compatibility)
    @staticmethod
    def generate_sparkline(values: list[float]) -> str:
        """Generate sparkline string from values (legacy method).

        Args:
            values: List of numeric values to visualize.

        Returns:
            Formatted string with sparkline visualization.
        """
        if not values or len(values) < 2:
            return "[dim]No data[/dim]"

        returns = list(values)
        min_val, max_val = min(returns), max(returns)
        if max_val == min_val:
            return f"[yellow]{'▄' * len(returns)}[/yellow] (flat)"

        # Unicode block characters for sparkline
        chars = "▁▂▃▄▅▆▇█"
        normalized = [(r - min_val) / (max_val - min_val) for r in returns]
        sparkline_chars = "".join(chars[min(int(n * 7), 7)] for n in normalized)

        # Color based on latest return
        latest = returns[-1]
        if latest > 5:
            color = "green"
        elif latest > 0:
            color = "yellow"
        else:
            color = "red"

        return f"[{color}]{sparkline_chars}[/{color}] ({latest:.1f}%)"

