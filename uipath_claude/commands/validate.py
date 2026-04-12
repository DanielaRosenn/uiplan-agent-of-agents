"""Validate UiPath project: uip rpa get-errors + optional pack."""
from uipath_claude.commands.registry import CommandRegistry, register_command
from uipath_claude.tools.uipath.approval import check_cli_approval
from uipath_claude.tools.uipath.cli_runner import (
    format_cli_result,
    run_uip_rpa_get_errors,
    run_studio_package_pack,
)
from uipath_claude.tools.uipath.integration_service import (
    run_integration_service_connector_check,
)


def register_validate_command(registry: CommandRegistry) -> None:
    """Register /validate: uip rpa get-errors validation."""

    @register_command(
        registry,
        name="validate",
        description="Validate UiPath project with uip rpa get-errors",
    )
    def validate_command(project_path: str = ".") -> str:
        """Validate project using uip CLI with approval guard."""
        allowed, message = check_cli_approval()
        if not allowed:
            return message

        result = run_uip_rpa_get_errors(project_path)
        
        lines = ["UiPath Project Validation"]
        lines.append("=" * 40)
        
        if result["success"]:
            lines.append("Status: PASSED - No errors found")
        else:
            lines.append(f"Status: FAILED - {len(result['errors'])} error(s)")
            lines.append("")
            lines.append("Errors:")
            for error in result["errors"]:
                lines.append(f"  - {error}")
        
        return "\n".join(lines)
