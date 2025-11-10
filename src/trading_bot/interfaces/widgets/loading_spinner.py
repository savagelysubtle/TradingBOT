"""Loading spinner widget with customizable messages."""

import logging
from textual.widgets import Static
from textual.reactive import reactive

logger = logging.getLogger(__name__)


class LoadingSpinner(Static):
    """Animated loading spinner with status message."""

    DEFAULT_CSS = """
    LoadingSpinner {
        height: 5;
        width: 100%;
        content-align: center middle;
        background: $boost;
        border: solid $primary;
    }
    """

    message = reactive("Loading...")
    is_active = reactive(True)

    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Loading...", **kwargs):
        """Initialize loading spinner.

        Args:
            message: Initial status message to display
            **kwargs: Additional arguments passed to Static widget
        """
        super().__init__(**kwargs)
        self.message = message
        self.frame_index = 0

    def on_mount(self) -> None:
        """Start animation when widget is mounted."""
        logger.debug("LoadingSpinner mounted, starting animation")
        self.set_interval(0.1, self.animate)

    def animate(self) -> None:
        """Update spinner animation frame."""
        if not self.is_active:
            return

        frame = self.SPINNER_FRAMES[self.frame_index]
        self.update(f"[cyan]{frame}[/cyan] {self.message}")
        self.frame_index = (self.frame_index + 1) % len(self.SPINNER_FRAMES)

    def set_message(self, message: str) -> None:
        """Update the spinner message.

        Args:
            message: New message to display
        """
        self.message = message
        logger.debug(f"LoadingSpinner message updated: {message}")

    def stop(self, success_message: str | None = None) -> None:
        """Stop spinner and show result.

        Args:
            success_message: Optional success message to display
        """
        logger.debug(f"LoadingSpinner stopped with message: {success_message}")
        self.is_active = False
        if success_message:
            self.update(f"[green]✓[/green] {success_message}")
        else:
            self.update("")

    def start(self, message: str = "Loading...") -> None:
        """Restart spinner with new message.

        Args:
            message: Message to display
        """
        logger.debug(f"LoadingSpinner restarted with message: {message}")
        self.message = message
        self.is_active = True
        self.frame_index = 0
