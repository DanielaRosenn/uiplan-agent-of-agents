"""Chat path materializes UIPATH_FILE blocks from assistant text."""
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from uipath_claude.cli.app import app

runner = CliRunner()


@pytest.mark.integration
def test_chat_writes_file_when_assistant_emits_block(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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
    out_file = tmp_path / "generated" / "chat" / "Main.xaml"
    assert out_file.is_file()
    assert "WriteLine" in out_file.read_text(encoding="utf-8")
    assert "Wrote:" in result.stdout


@pytest.mark.integration
def test_chat_skips_materialize_when_disabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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
    assert not (tmp_path / "generated" / "chat" / "Main.xaml").exists()
