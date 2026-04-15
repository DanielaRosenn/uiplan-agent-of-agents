"""Plan command implementation."""
from typing import Callable

from uipath_claude.commands.registry import CommandRegistry, register_command


def register_plan_command(
    registry: CommandRegistry,
    run_planner: Callable[[str], str],
) -> None:
    """Register the /plan command.

    Args:
        registry: Command registry
        run_planner: Function that generates a plan from a description
    """

    @register_command(
        registry,
        name="plan",
        description="Generate implementation plan without executing",
    )
    def plan_command(*description_parts: str) -> str:
        """Generate a plan for the given description."""
        description = " ".join(description_parts).strip()
        if not description:
            return "Usage: /plan <description>\n\nGenerates an implementation plan without executing it."

        try:
            plan = run_planner(description)
        except Exception as exc:
            return f"Plan generation failed: {exc}"
        return f"{plan}\n\n[Type 'y' to execute this plan, or continue chatting]"
