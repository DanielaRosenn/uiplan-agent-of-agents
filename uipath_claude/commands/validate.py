"""Validate UiPath project via `uip rpa get-errors`."""
from uipath_claude.commands.registry import CommandRegistry, register_command
from uipath_claude.tools.uipath.approval import check_cli_approval
from uipath_claude.tools.uipath.cli_runner import run_uip_rpa_get_errors


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
        warnings = result.get("warnings", [])
        if not isinstance(warnings, list):
            warnings = [str(warnings)]
        diagnostics_ran = bool(result.get("diagnostics_ran", True))

        lines = ["UiPath Project Validation"]
        lines.append("=" * 40)

        if result["success"] and diagnostics_ran:
            lines.append("Status: PASSED - No errors found")
        elif result["success"]:
            lines.append("Status: PASSED WITH WARNINGS - Diagnostics incomplete")
        else:
            lines.append(f"Status: FAILED - {len(result['errors'])} error(s)")
            lines.append("")
            lines.append("Errors:")
            for error in result["errors"]:
                lines.append(f"  - {error}")

        if not diagnostics_ran:
            lines.append("")
            lines.append(
                "Note: Studio diagnostics unavailable; file-level diagnostics could not run."
            )

        if warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)
