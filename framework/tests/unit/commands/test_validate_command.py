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
