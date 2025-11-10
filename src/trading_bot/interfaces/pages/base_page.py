"""Base page class for TUI pages."""

import logging
from abc import ABC, abstractmethod

from textual.containers import Container

logger = logging.getLogger(__name__)


class BasePage(ABC):
    """Abstract base class for TUI pages."""

    def __init__(self, app):
        """Initialize page with reference to main app."""
        logger.debug(f"Initializing {self.__class__.__name__}")
        self.app = app
        self.bot = app.bot
        self.config = app.config
        self.backtest_config = app.backtest_config
        self.history = app.history
        logger.info(f"{self.__class__.__name__} initialized")

    @abstractmethod
    def compose(self, body: Container) -> None:
        """Compose and mount the page widgets to the body container.

        Args:
            body: The container to mount widgets into
        """
        pass

    def on_mount(self) -> None:
        """Called when page is mounted. Override if needed."""
        logger.debug(f"{self.__class__.__name__} mounted")

    def on_unmount(self) -> None:
        """Called when page is unmounted. Override if needed."""
        logger.debug(f"{self.__class__.__name__} unmounted")
