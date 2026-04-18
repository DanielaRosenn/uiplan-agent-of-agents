"""CLI command: ``/library-harvest`` — enqueue library proposals from upstream."""
from __future__ import annotations

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.library.harvest import harvest_upstream_skills


def register_library_harvest_command(registry: CommandRegistry) -> None:
    """Register the ``/library-harvest`` command."""

    def handle_harvest(*args: str) -> str:
        result = harvest_upstream_skills()
        return (
            "Harvest complete: "
            + result.summary()
            + "\nReview with /library-proposals (approve/reject)."
        )

    registry.register(
        "library-harvest",
        "Enqueue library proposals from UiPath/skills SKILL.md files",
        handle_harvest,
    )
