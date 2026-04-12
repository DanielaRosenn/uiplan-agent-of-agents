"""Validate UiPath project: studio analyze/pack + integration-service smoke."""
from uipath_claude.commands.registry import CommandRegistry, register_command
from uipath_claude.tools.uipath.cli_runner import (
    format_cli_result,
    run_studio_package_analyze,
    run_studio_package_pack,
)
from uipath_claude.tools.uipath.integration_service import (
    run_integration_service_connector_check,
)


def register_validate_command(registry: CommandRegistry) -> None:
    """Register /validate: analyze, pack, and integration connector check."""

    @register_command(
        registry,
        name="validate",
        description="Run studio package analyze/pack and integration connector smoke",
    )
    def validate_command(project_path: str = ".") -> str:
        """Analyze and pack project; run Integration Service CLI smoke."""
        analyze_proc = run_studio_package_analyze(project_path)
        pack_proc = run_studio_package_pack(project_path)
        lines = [
            format_cli_result("analyze", analyze_proc),
            "",
            format_cli_result("pack", pack_proc),
            "",
            "Integration Service (connector smoke):",
            run_integration_service_connector_check(),
        ]
        return "\n".join(lines)
