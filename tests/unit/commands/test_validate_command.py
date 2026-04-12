"""Approval-gate tests for /validate command."""
from unittest.mock import MagicMock, patch

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.validate import register_validate_command


def test_validate_command_blocks_without_approval():
    registry = CommandRegistry()
    register_validate_command(registry)

    with patch(
        "uipath_claude.commands.validate.check_cli_approval",
        return_value=(False, "approval required"),
    ), patch(
        "uipath_claude.commands.validate.run_studio_package_analyze"
    ) as mock_analyze, patch(
        "uipath_claude.commands.validate.run_studio_package_pack"
    ) as mock_pack, patch(
        "uipath_claude.commands.validate.run_integration_service_connector_check"
    ) as mock_integration:
        out = registry.execute("validate", ".")
        assert out == "approval required"
        mock_analyze.assert_not_called()
        mock_pack.assert_not_called()
        mock_integration.assert_not_called()


def test_validate_command_runs_when_approved():
    registry = CommandRegistry()
    register_validate_command(registry)
    ok = MagicMock(returncode=0, stdout="ok", stderr="")

    with patch(
        "uipath_claude.commands.validate.check_cli_approval",
        return_value=(True, ""),
    ), patch(
        "uipath_claude.commands.validate.run_studio_package_analyze",
        return_value=ok,
    ) as mock_analyze, patch(
        "uipath_claude.commands.validate.run_studio_package_pack",
        return_value=ok,
    ) as mock_pack, patch(
        "uipath_claude.commands.validate.run_integration_service_connector_check",
        return_value="integration: smoke",
    ) as mock_integration:
        out = registry.execute("validate", ".")
        mock_analyze.assert_called_once()
        mock_pack.assert_called_once()
        mock_integration.assert_called_once()
        assert "analyze" in out.lower()
        assert "pack" in out.lower()
        assert "integration" in out.lower()
