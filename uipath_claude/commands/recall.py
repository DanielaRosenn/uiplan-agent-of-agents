"""Recall command implementation."""
from typing import Callable

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

        lines = ["Recent matches:"]
        for match in matches:
            role = match.get("role", "unknown")
            content = match.get("content", "")
            lines.append(f"- [{role}] {content}")
        return "\n".join(lines)
