"""Progress reporting for terminal output."""
from contextlib import contextmanager
from typing import Generator
import os

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.status import Status
from rich.text import Text


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


class AgenticProgressReporter:
    """Progress reporter for agentic execution with human-readable debug output."""

    def __init__(self, console: Console | None = None):
        """
        Initialize agentic progress reporter.

        Args:
            console: Rich console instance, creates new one if not provided
        """
        self.console = console or Console()
        self.verbose = os.environ.get("UIPATH_DEBUG_VERBOSE", "0").lower() in ("1", "true", "yes")
        self.raw = os.environ.get("UIPATH_DEBUG_RAW", "0").lower() in ("1", "true", "yes")

    def iteration_start(self, n: int, max_iter: int) -> None:
        """
        Show iteration header with progress bar.

        Args:
            n: Current iteration number
            max_iter: Maximum iterations
        """
        progress_pct = (n / max_iter) * 100
        bar_width = 10
        filled = int((n / max_iter) * bar_width)
        bar = "=" * filled + ">" + " " * (bar_width - filled - 1)
        
        panel = Panel(
            f"Iteration {n} of {max_iter}                              [{bar}]",
            border_style="cyan",
            padding=(0, 1),
        )
        self.console.print(panel)
        self.console.print()

    def tool_call(self, name: str, args: dict) -> None:
        """
        Show tool being called with icon.

        Args:
            name: Tool name
            args: Tool arguments
        """
        self.console.print(f"  [cyan][tool][/cyan] {name}")
        
        # Show key arguments
        if self.verbose or self.raw:
            import json
            args_str = json.dumps(args, indent=2)
            if not self.verbose and len(args_str) > 200:
                args_str = args_str[:200] + "..."
            self.console.print(f"         [dim]{args_str}[/dim]")
        else:
            # Show summary
            if "file_path" in args:
                self.console.print(f"         -> {args['file_path']}")
            elif "package_id" in args:
                self.console.print(f"         -> {args['package_id']}")
            elif "query" in args:
                query = args["query"]
                if len(query) > 50:
                    query = query[:50] + "..."
                self.console.print(f"         -> {query}")

    def tool_result(self, name: str, success: bool, result: str) -> None:
        """
        Show result with status icon.

        Args:
            name: Tool name
            success: Whether tool succeeded
            result: Tool result message
        """
        if success:
            icon = "[green][ok][/green]"
        else:
            icon = "[red][err][/red]"
        
        # Truncate result if not verbose
        display_result = result
        if not self.verbose and not self.raw and len(result) > 300:
            display_result = result[:300] + "..."
        
        # Extract key info from result
        lines = display_result.split("\n")
        if len(lines) > 5 and not self.verbose:
            # Show first few lines
            display_result = "\n".join(lines[:3])
            if "error" in result.lower() or "failed" in result.lower():
                # For errors, show more context
                display_result = "\n".join(lines[:5])
        
        self.console.print(f"  {icon}   {display_result}")
        self.console.print()

    def validation_status(self, errors: int, warnings: int, files: int = 1) -> None:
        """
        Show validation summary box.

        Args:
            errors: Number of errors
            warnings: Number of warnings
            files: Number of files validated
        """
        status_text = f"Errors: {errors}    Warnings: {warnings}    Files: {files}"
        
        if errors > 0:
            style = "red"
        elif warnings > 0:
            style = "yellow"
        else:
            style = "green"
        
        panel = Panel(
            status_text,
            title="Validation Summary",
            border_style=style,
            padding=(0, 1),
        )
        self.console.print(panel)
        self.console.print()
