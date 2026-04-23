"""Analyze command implementation."""
from uipath_claude.commands.registry import CommandRegistry, register_command
from uipath_claude.tools.uipath.approval import check_cli_approval
from uipath_claude.tools.uipath.cli_runner import (
    format_cli_result,
    run_studio_package_analyze,
)


def register_analyze_command(registry: CommandRegistry) -> None:
    """Register the /analyze command."""

    @register_command(
        registry,
        name="analyze",
        description="Run uipath studio package analyze on a project",
    )
    def analyze_command(project_path: str = ".") -> str:
        """Analyze a UiPath project via official CLI."""
        allowed, message = check_cli_approval()
        if not allowed:
            return message

        proc = run_studio_package_analyze(project_path)
        return format_cli_result("uipath studio package analyze", proc)
