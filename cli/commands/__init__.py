"""Slash command registry and execution."""

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class SlashCommand:
    """Represents a registered slash command."""

    name: str
    description: str
    handler: Callable[..., Any]
    aliases: list[str] | None = None


COMMANDS: dict[str, SlashCommand] = {}


def register_command(
    name: str,
    description: str,
    aliases: list[str] | None = None,
):
    """Decorator to register a slash command."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cmd = SlashCommand(
            name=name,
            description=description,
            handler=func,
            aliases=aliases,
        )
        COMMANDS[name] = cmd
        if aliases:
            for alias in aliases:
                COMMANDS[alias] = cmd
        return func

    return decorator


def parse_slash_command(text: str) -> Optional[dict]:
    """
    Parse text for slash command.

    Args:
        text: User input text

    Returns:
        Dict with 'command' and 'args' if slash command, None otherwise
    """
    text = text.strip()
    if not text.startswith("/"):
        return None

    parts = text[1:].split(maxsplit=1)
    if not parts:
        return None

    return {
        "command": parts[0].lower(),
        "args": parts[1] if len(parts) > 1 else "",
    }


def execute_command(command: str, args: str, context: dict) -> str:
    """
    Execute a slash command.

    Args:
        command: Command name
        args: Command arguments
        context: Execution context (session info, etc.)

    Returns:
        Command output string
    """
    if command not in COMMANDS:
        return f"Unknown command: /{command}. Type /help for available commands."

    cmd = COMMANDS[command]
    try:
        return cmd.handler(args, context)
    except Exception as e:
        return f"Error executing /{command}: {e}"


# Import commands to register them
from cli.commands import help as _help
from cli.commands import status as _status
from cli.commands import skills as _skills
from cli.commands import analyze as _analyze
