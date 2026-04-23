"""Status command implementation."""
from typing import Callable

from uipath_claude.commands.registry import CommandRegistry, register_command


def register_status_command(
    registry: CommandRegistry,
    get_status: Callable[[], dict[str, str | int | bool]],
) -> None:
    """Register the /status command."""

    @register_command(registry, name="status", description="Show session status")
    def status_command() -> str:
        """Show current session status."""
        status = get_status()
        return "\n".join(
            [
                "Session status:",
                f"- model: {status.get('model', 'unknown')}",
                f"- region: {status.get('region', 'unknown')}",
                f"- project_detected: {status.get('project_detected', False)}",
                f"- project_name: {status.get('project_name', 'n/a')}",
                f"- memory_loaded: {status.get('memory_loaded', False)}",
                f"- skill_count: {status.get('skill_count', 0)}",
                f"- tool_profile: {status.get('tool_profile', 'safe')}",
            ]
        )
