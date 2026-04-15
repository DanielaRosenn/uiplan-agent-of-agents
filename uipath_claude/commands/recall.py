"""Recall command implementation."""
from io import StringIO
from typing import Callable

from rich.console import Console
from rich.table import Table

from uipath_claude.commands.registry import CommandRegistry, register_command
from uipath_claude.query.session_search import search_session_history


def register_recall_command(
    registry: CommandRegistry,
    get_history: Callable[[], list[dict[str, str]]],
) -> None:
    """Register the /recall command."""

    @register_command(
        registry,
        name="recall",
        description="Search recent session history",
    )
    def recall_command(*query_parts: str) -> str:
        """Search for matching messages in the current session."""
        query = " ".join(query_parts).strip()
        if not query:
            return "Usage: /recall <query>"

        matches = search_session_history(get_history(), query)
        if not matches:
            return f"No matches found for: {query}"

        table = Table(title=f"Matches for '{query}'")
        table.add_column("#", style="dim", width=4)
        table.add_column("Role", style="cyan", width=12)
        table.add_column("Content", style="white")

        for idx, match in enumerate(matches, start=1):
            role = match.get("role", "unknown")
            content = match.get("content", "")
            if len(content) > 80:
                content = content[:77] + "..."
            table.add_row(str(idx), role, content)

        string_io = StringIO()
        console = Console(file=string_io, force_terminal=True)
        console.print(table)
        return string_io.getvalue()
