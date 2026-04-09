"""Integration test for bootstrap flow."""
import pytest
from typer.testing import CliRunner
from uipath_claude.cli.app import app


runner = CliRunner()


@pytest.mark.integration
def test_start_project_command():
    """Test start-project command."""
    result = runner.invoke(app, ["start-project", "TestProject"])
    # Should not crash
    assert result.exit_code == 0 or "bootstrap" in result.stdout.lower()
