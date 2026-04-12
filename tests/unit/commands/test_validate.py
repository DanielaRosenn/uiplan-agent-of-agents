"""Test /validate command."""
from unittest.mock import patch

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.validate import register_validate_command


def test_validate_command_runs_get_errors():
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
        mock_get_errors.assert_called_once_with(".")
        assert "passed" in out.lower()
        assert "validation" in out.lower()


def test_validate_command_shows_errors():
    registry = CommandRegistry()
    register_validate_command(registry)

    with patch(
        "uipath_claude.commands.validate.check_cli_approval",
        return_value=(True, ""),
    ), patch(
        "uipath_claude.commands.validate.run_uip_rpa_get_errors",
        return_value={"success": False, "errors": ["Error 1", "Error 2"]},
    ):
        out = registry.execute("validate", ".")
        assert "failed" in out.lower()
        assert "2 error" in out.lower()
        assert "Error 1" in out
        assert "Error 2" in out
