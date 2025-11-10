"""Panel for displaying validation results."""

import logging
from textual.containers import Vertical
from textual.widgets import Static

from trading_bot.utils.validation import ValidationResult

logger = logging.getLogger(__name__)


class ValidationPanel(Vertical):
    """Display validation results in a formatted panel."""

    DEFAULT_CSS = """
    ValidationPanel {
        height: auto;
        max-height: 20;
        padding: 1;
        background: $surface;
        border: solid $primary;
        overflow-y: auto;
    }

    ValidationPanel.has-errors {
        border: solid $error;
    }

    ValidationPanel.has-warnings {
        border: solid $warning;
    }

    ValidationPanel.all-valid {
        border: solid $success;
    }
    """

    def __init__(self, **kwargs):
        """Initialize validation panel."""
        super().__init__(**kwargs)
        self.results: list[ValidationResult] = []
        logger.debug("ValidationPanel initialized")

    def compose(self):
        """Compose panel widgets."""
        yield Static("", id="validation-content")

    def update_results(self, results: list[ValidationResult]) -> None:
        """Update displayed validation results.

        Args:
            results: List of validation results to display
        """
        logger.debug(f"Updating validation results: {len(results)} results")
        self.results = results

        # Categorize results
        errors = [r for r in results if not r.is_valid and r.severity == "error"]
        warnings = [r for r in results if not r.is_valid and r.severity == "warning"]
        info = [r for r in results if r.is_valid]

        # Build display text
        lines = []

        if errors:
            lines.append("[bold red]❌ Issues Found:[/bold red]\n")
            for result in errors:
                lines.append(result.to_rich_text())
                lines.append("")
        elif warnings:
            lines.append("[bold yellow]⚠️  Warnings:[/bold yellow]\n")
            for result in warnings:
                lines.append(result.to_rich_text())
                lines.append("")

        if info and not (errors or warnings):
            lines.append("[bold green]✅ All Validations Passed:[/bold green]\n")
            for result in info:
                lines.append(f"[green]✓[/green] {result.field}: {result.message}")
            lines.append("")

        # Update styling based on severity
        if errors:
            self.remove_class("has-warnings", "all-valid")
            self.add_class("has-errors")
            logger.debug("Panel styled with error state")
        elif warnings:
            self.remove_class("has-errors", "all-valid")
            self.add_class("has-warnings")
            logger.debug("Panel styled with warning state")
        else:
            self.remove_class("has-errors", "has-warnings")
            self.add_class("all-valid")
            logger.debug("Panel styled with valid state")

        # Update content
        content = self.query_one("#validation-content", Static)
        content.update("\n".join(lines))
        logger.debug("Validation results displayed")

    def has_errors(self) -> bool:
        """Check if there are any errors.

        Returns:
            True if any validation results are errors
        """
        return any(not r.is_valid and r.severity == "error" for r in self.results)

    def has_warnings(self) -> bool:
        """Check if there are any warnings.

        Returns:
            True if any validation results are warnings
        """
        return any(not r.is_valid and r.severity == "warning" for r in self.results)

    def is_valid(self) -> bool:
        """Check if all validations pass.

        Returns:
            True if no errors or warnings
        """
        return not self.has_errors() and not self.has_warnings()

    def clear(self) -> None:
        """Clear all validation results."""
        logger.debug("Clearing validation results")
        self.results = []
        content = self.query_one("#validation-content", Static)
        content.update("")
        self.remove_class("has-errors", "has-warnings", "all-valid")
