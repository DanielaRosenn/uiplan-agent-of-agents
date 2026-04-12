"""Test /validate command."""
from unittest.mock import MagicMock, patch

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.validate import register_validate_command


def test_validate_command_runs_analyze_pack_and_integration():
    registry = CommandRegistry()
    register_validate_command(registry)
    ok = MagicMock(returncode=0, stdout="ok", stderr="")

    with patch(
        "uipath_claude.commands.validate.run_studio_package_analyze",
        return_value=ok,
    ) as mock_a, patch(
        "uipath_claude.commands.validate.run_studio_package_pack",
        return_value=ok,
    ) as mock_p, patch(
        "uipath_claude.commands.validate.run_integration_service_connector_check",
        return_value="integration: smoke",
    ):
        out = registry.execute("validate", ".")
        mock_a.assert_called_once()
        mock_p.assert_called_once()
        assert "analyze" in out.lower()
        assert "pack" in out.lower()
        assert "integration" in out.lower()
