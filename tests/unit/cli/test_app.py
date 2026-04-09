"""Test CLI app."""
from typer.testing import CliRunner
from uipath_claude.cli.app import app


runner = CliRunner()


def test_cli_chat_command():
    """Test chat command exists."""
    result = runner.invoke(app, ["chat", "--help"])
    assert result.exit_code == 0
    assert "chat" in result.stdout.lower()


def test_cli_start_project_command():
    """Test start-project command exists."""
    result = runner.invoke(app, ["start-project", "--help"])
    assert result.exit_code == 0
    assert "start-project" in result.stdout.lower()
