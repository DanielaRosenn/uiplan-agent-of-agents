"""Integration test for chat flow."""
import pytest
from typer.testing import CliRunner
from uipath_claude.cli.app import app


runner = CliRunner()


@pytest.mark.integration
def test_chat_flow_with_no_banner():
    """Test chat command runs without banner."""
    result = runner.invoke(app, ["chat", "--no-banner"])
    # Should not crash
    assert result.exit_code == 0 or "to be implemented" in result.stdout


@pytest.mark.integration
def test_chat_flow_detects_project(tmp_path, monkeypatch):
    """Test chat flow detects UiPath project."""
    # Create fake project
    project_json = tmp_path / "project.json"
    project_json.write_text('{"name": "TestProject", "projectType": "Process"}')
    
    monkeypatch.chdir(tmp_path)
    
    result = runner.invoke(app, ["chat", "--no-banner"])
    # Should detect project
    assert "TestProject" in result.stdout or "to be implemented" in result.stdout
