"""CLI command: ``/scan-upstream-skills`` — diff the UiPath/skills submodule.

Prints new or removed skills and tool packs since the last scan. Persists
the new snapshot so the next call only surfaces further changes.
"""
from __future__ import annotations

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.skills.upstream_scan import format_diff, scan_upstream


def register_scan_upstream_skills_command(registry: CommandRegistry) -> None:
    """Register the ``/scan-upstream-skills`` command."""

    def handle_scan(*args: str) -> str:
        persist = not (args and args[0] in ("--dry-run", "-n"))
        diff = scan_upstream(persist=persist)
        return format_diff(diff)

    registry.register(
        "scan-upstream-skills",
        "Show new/removed skills in the UiPath/skills submodule since last scan",
        handle_scan,
    )
