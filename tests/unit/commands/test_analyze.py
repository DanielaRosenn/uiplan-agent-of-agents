"""Test /analyze command."""
from unittest.mock import MagicMock, patch

from uipath_claude.commands.analyze import register_analyze_command
from uipath_claude.commands.registry import CommandRegistry


def test_analyze_command_invokes_cli():
    registry = CommandRegistry()
    register_analyze_command(registry)
    proc = MagicMock(returncode=0, stdout="clean", stderr="")
    with patch(
        "uipath_claude.commands.analyze.run_studio_package_analyze",
        return_value=proc,
    ) as mock_run:
        out = registry.execute("analyze", ".")
        mock_run.assert_called_once()
        assert "analyze" in out.lower()
        assert "clean" in out
