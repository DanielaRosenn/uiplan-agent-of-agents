"""Restore troubleshooting command implementation."""

from uipath_claude.commands.registry import CommandRegistry, register_command


def register_repair_restore_command(registry: CommandRegistry) -> None:
    """Register the /repair-restore command."""

    @register_command(
        registry,
        name="repair-restore",
        description="Show steps for UiPath NuGet restore lock/permission errors",
    )
    def repair_restore_command() -> str:
        """Render deterministic restore troubleshooting guidance."""
        return "\n".join(
            [
                "Restore repair checklist:",
                "1) Close UiPath Studio and all UiPath Robot/Assistant processes.",
                "2) Close editors/terminals that may lock .nuget package files.",
                "3) Remove the failing package folder from %USERPROFILE%/.nuget/packages.",
                "   Example: %USERPROFILE%/.nuget/packages/uipath.system.activities/26.2.0",
                "4) Reopen Studio and restore/open the project again.",
                "5) If still failing, run Studio as Administrator and retry once.",
                "",
                "Tip: use the exact DLL/package name in the error to identify the package folder.",
            ]
        )
