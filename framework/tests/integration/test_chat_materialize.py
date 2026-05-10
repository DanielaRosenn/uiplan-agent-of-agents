"""Chat path materializes UIPATH_FILE blocks from assistant text."""
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from uipath_claude.cli.app import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _integration_chat_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UIPATH_SKIP_AUTH_CHECK", "1")
    monkeypatch.setenv("UIPATH_PLAN_MODE", "0")
    monkeypatch.setenv("UIPATH_AGENTIC_MODE", "0")


@pytest.mark.integration
def test_chat_writes_file_when_assistant_emits_block(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "chat-abc123")
    fake_reply = """Here is your workflow.
<<<UIPATH_FILE path="Main.xaml">>>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><Sequence><WriteLine Text="Ok"/></Sequence></Activity>
<<<END_UIPATH_FILE>>>
"""
    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="create Main.xaml\nexit\n",
            )
    assert result.exit_code == 0
    out_file = tmp_path / "generated" / "chat" / "chat-abc123" / "Main.xaml"
    assert out_file.is_file()
    assert "WriteLine" in out_file.read_text(encoding="utf-8")
    assert "Wrote:" in result.stdout
    assert "chat-abc123" in result.stdout
    assert "WriteLine Text=\"Ok\"" not in result.stdout


@pytest.mark.integration
def test_chat_skips_materialize_when_disabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "chat-disabled")
    monkeypatch.setenv("UIPATH_CHAT_MATERIALIZE", "0")
    fake_reply = """<<<UIPATH_FILE path="Main.xaml">>>
<x/>
<<<END_UIPATH_FILE>>>
"""
    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="go\nexit\n",
            )
    assert result.exit_code == 0
    assert "Wrote:" not in result.stdout
    assert not any((tmp_path / "generated" / "chat").rglob("Main.xaml"))


@pytest.mark.integration
def test_chat_blocks_project_json_unless_explicit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "chat-no-project")
    fake_reply = """<<<UIPATH_FILE path="project.json">>>
{"name":"wrong"}
<<<END_UIPATH_FILE>>>
<<<UIPATH_FILE path="Main.xaml">>>
<Activity />
<<<END_UIPATH_FILE>>>
"""
    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="build a workflow for outlook emails\nexit\n",
            )
    assert result.exit_code == 0
    root = tmp_path / "generated" / "chat" / "chat-no-project"
    assert not (root / "Main.xaml").exists()
    assert not (root / "project.json").exists()
    assert "/uiplan-spec" in result.stdout.lower()
