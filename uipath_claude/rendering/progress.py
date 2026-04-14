"""Progress reporting for terminal output."""
from contextlib import contextmanager
from typing import Generator

from rich.console import Console
from rich.status import Status


class ProgressReporter:
    """Progress reporter with spinner status and colored messages."""

    def __init__(self, console: Console | None = None):
        """
        Initialize progress reporter.

        Args:
            console: Rich console instance, creates new one if not provided
        """
        self.console = console or Console()

    @contextmanager
    def status(self, message: str, spinner: str = "dots") -> Generator[Status, None, None]:
        """
        Context manager for spinner status.

        Args:
            message: Status message to display
            spinner: Spinner style name

        Yields:
            Status object for updating message
        """
        with self.console.status(message, spinner=spinner) as status:
            yield status

    def analyzing(self) -> Status:
        """
        Return status for analyzing request.

        Returns:
            Status object with cyan analyzing message
        """
        return self.console.status("[cyan]Analyzing request...[/cyan]", spinner="dots")

    def selecting_skills(self) -> Status:
        """
        Return status for skill selection.

        Returns:
            Status object with cyan selecting message
        """
        return self.console.status("[cyan]Selecting skills...[/cyan]", spinner="dots")

    def generating(self, artifact_type: str = "workflow") -> Status:
        """
        Return status for generation.

        Args:
            artifact_type: Type of artifact being generated

        Returns:
            Status object with yellow generating message
        """
        return self.console.status(
            f"[yellow]Generating {artifact_type}...[/yellow]", spinner="dots"
        )

    def validating(self) -> Status:
        """
        Return status for validation.

        Returns:
            Status object with blue validating message
        """
        return self.console.status("[blue]Validating project...[/blue]", spinner="dots")

    def success(self, message: str) -> None:
        """
        Print success message with a green ASCII marker.

        Args:
            message: Success message to display
        """
        self.console.print(f"[green]+[/green] {message}")

    def error(self, message: str) -> None:
        """
        Print error message with a red ASCII marker.

        Args:
            message: Error message to display
        """
        self.console.print(f"[red]x[/red] {message}")

    def warning(self, message: str) -> None:
        """
        Print warning message with a yellow ASCII marker.

        Args:
            message: Warning message to display
        """
        self.console.print(f"[yellow]![/yellow] {message}")

    def info(self, message: str) -> None:
        """
        Print info message.

        Args:
            message: Info message to display
        """
        self.console.print(f"[dim]->[/dim] {message}")

    def file_written(self, path: str) -> None:
        """
        Print file written notification.

        Args:
            path: Path of the file that was written
        """
        self.console.print(f"  [green]+[/green] {path}")
