"""Test CLI app."""
from unittest.mock import AsyncMock, patch

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


def test_cli_chat_command_starts_and_exits():
    """Test chat command starts and exits cleanly."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        result = runner.invoke(app, ["chat", "--no-banner"], input="exit\n")
    assert result.exit_code == 0
    assert "chat session started" in result.stdout.lower()
    assert "goodbye" in result.stdout.lower()


def test_cli_chat_slash_chat_message():
    """Test /chat command inside REPL gives friendly message."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        result = runner.invoke(app, ["chat", "--no-banner"], input="/chat\nexit\n")
    assert result.exit_code == 0
    assert "already in chat mode" in result.stdout.lower()


def test_cli_chat_llm_error_message():
    """Test model error path displays actionable guidance."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as get_model_response:
            get_model_response.side_effect = RuntimeError("model failed")
            result = runner.invoke(app, ["chat", "--no-banner"], input="hello\nexit\n")
    assert result.exit_code == 0
    assert "bedrock request failed" in result.stdout.lower()
