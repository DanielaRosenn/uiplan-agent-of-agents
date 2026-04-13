"""Approval-gate tests for /validate command."""
from unittest.mock import patch

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.validate import register_validate_command


def test_validate_command_blocks_without_approval():
    registry = CommandRegistry()
    register_validate_command(registry)

    with patch(
        "uipath_claude.commands.validate.check_cli_approval",
        return_value=(False, "approval required"),
    ), patch(
        "uipath_claude.commands.validate.run_uip_rpa_get_errors"
    ) as mock_get_errors:
        out = registry.execute("validate", ".")
        assert out == "approval required"
        mock_get_errors.assert_not_called()


def test_validate_command_runs_when_approved():
    registry = CommandRegistry()
    register_validate_command(registry)

    with patch(
        "uipath_claude.commands.validate.check_cli_approval",
        return_value=(True, ""),
    ), patch(
        "uipath_claude.commands.validate.run_uip_rpa_get_errors",
        return_value={"success": True, "errors": []},
    ) as mock_get_errors:
        out = registry.execute("validate", ".")
        mock_get_errors.assert_called_once()
        assert "passed" in out.lower()


def test_validate_command_reports_studio_diagnostics_unavailable_and_warnings():
    registry = CommandRegistry()
    register_validate_command(registry)

    with patch(
        "uipath_claude.commands.validate.check_cli_approval",
        return_value=(True, ""),
    ), patch(
        "uipath_claude.commands.validate.run_uip_rpa_get_errors",
        return_value={
            "success": True,
            "errors": [],
            "warnings": ["Package restore could not be confirmed."],
            "diagnostics_ran": False,
        },
    ):
        out = registry.execute("validate", ".")

    assert "studio diagnostics unavailable" in out.lower()
    assert "warnings:" in out.lower()
    assert "package restore could not be confirmed." in out.lower()


def test_validate_command_renders_failed_status_and_errors():
    registry = CommandRegistry()
    register_validate_command(registry)

    with patch(
        "uipath_claude.commands.validate.check_cli_approval",
        return_value=(True, ""),
    ), patch(
        "uipath_claude.commands.validate.run_uip_rpa_get_errors",
        return_value={
            "success": False,
            "errors": ["Main.xaml: Unknown activity", "project.json missing dependency"],
            "warnings": [],
            "diagnostics_ran": True,
        },
    ):
        out = registry.execute("validate", ".")

    assert "status: failed - 2 error(s)" in out.lower()
    assert "errors:" in out.lower()
    assert "main.xaml: unknown activity" in out.lower()
    assert "project.json missing dependency" in out.lower()
