"""Input router for chat session."""

from typing import Any

from uipath_claude.cli.utils import parse_slash_command


def route_user_input(user_input: str) -> tuple[str, dict[str, Any]]:
    """Route raw user input into command, skill invocation, or llm message."""
    if user_input.startswith("/skill "):
        parts = user_input.split(maxsplit=2)
        if len(parts) < 3:
            return "skill_usage", {}
        return "skill", {"skill_name": parts[1], "query": parts[2]}

    command, args = parse_slash_command(user_input)
    if command:
        return "command", {"command": command, "args": args}

    return "llm", {"text": user_input}

