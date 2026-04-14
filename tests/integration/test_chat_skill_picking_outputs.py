"""Integration tests that keep skill-picking output artifacts."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from uipath_claude.cli.app import app

runner = CliRunner()


@pytest.mark.integration
def test_chat_skill_picking_creates_persistent_output_artifact(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    output_root = repo_root / "generated" / "test-runs" / "skill-picking"
    output_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(output_root))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "pytest-rpa-skill-picking")
    monkeypatch.setenv("UIPATH_CHAT_DEBUG_SKILLS", "1")

    fake_reply = """<<<UIPATH_FILE path="Main.xaml">>>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"><Sequence /></Activity>
<<<END_UIPATH_FILE>>>"""

    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="build an outlook workflow that logs first 5 emails\nexit\n",
            )

    assert result.exit_code == 0
    artifact_file = output_root / "pytest-rpa-skill-picking" / "Main.xaml"
    assert artifact_file.exists()
    assert "skill selection" in result.stdout.lower()
    assert "uipath-rpa" in result.stdout.lower()


@pytest.mark.integration
def test_chat_outlook_last_30_days_subjects_materializes_main(tmp_path, monkeypatch):
    """Chat + skill pick for Outlook scope; assistant reply mocked as Main.xaml scaffold."""
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)
    out_root = tmp_path / "chat-outlook-30d-out"
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(out_root))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "chat-outlook-30d")
    monkeypatch.setenv("UIPATH_CHAT_DEBUG_SKILLS", "1")

    fake_reply = """<<<UIPATH_FILE path="Main.xaml">>>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities"
 xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Sequence DisplayName="Outlook subjects last 30 days">
    <!-- Intended: Get Outlook Mail Messages with filter for last 30 days, then For Each + WriteLine subject -->
    <WriteLine Text="[Stub] Would print each mail.Subject for messages in the last 30 days" />
  </Sequence>
</Activity>
<<<END_UIPATH_FILE>>>"""

    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input=(
                    "Create a UiPath automation project that reads Outlook emails and prints "
                    "to the screen the last subjects from the last 30 days\nexit\n"
                ),
            )

    assert result.exit_code == 0
    assert "uipath-rpa" in result.stdout.lower()
    assert "skill selection" in result.stdout.lower()
    out_file = out_root / "chat-outlook-30d" / "Main.xaml"
    assert out_file.is_file()
    text = out_file.read_text(encoding="utf-8")
    assert "WriteLine" in text
    assert "30 days" in text.lower()


def _file_block(rel_path: str, body: str) -> str:
    return (
        f'<<<UIPATH_FILE path="{rel_path}">>>\n'
        f"{body.rstrip()}\n"
        "<<<END_UIPATH_FILE>>>"
    )


@pytest.mark.integration
def test_chat_generates_dispatcher_performer_long_running_projects(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    output_root = repo_root / "generated" / "test-runs" / "chat-project-bundles"
    output_root.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_DIR", str(output_root))
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "pytest-project-bundles")
    monkeypatch.setenv("UIPATH_CHAT_DEBUG_SKILLS", "1")
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_MODE", "quiet")

    dispatcher_project = (repo_root / "templates" / "dispatcher" / "project.json").read_text(encoding="utf-8")
    dispatcher_uiproj = (repo_root / "templates" / "dispatcher" / "project.uiproj").read_text(encoding="utf-8")
    dispatcher_main = (repo_root / "templates" / "dispatcher" / "Main.xaml").read_text(encoding="utf-8")

    performer_project = (repo_root / "templates" / "performer" / "project.json").read_text(encoding="utf-8")
    performer_uiproj = (repo_root / "templates" / "performer" / "project.uiproj").read_text(encoding="utf-8")
    performer_main = (repo_root / "templates" / "performer" / "Main.xaml").read_text(encoding="utf-8")

    long_running_project = (repo_root / "templates" / "long-running" / "project.json").read_text(
        encoding="utf-8"
    )
    long_running_uiproj = (repo_root / "templates" / "long-running" / "project.uiproj").read_text(
        encoding="utf-8"
    )
    long_running_main = (repo_root / "templates" / "long-running" / "Main.xaml").read_text(encoding="utf-8")
    long_running_queue = (repo_root / "templates" / "long-running" / "Main-Queue.xaml").read_text(
        encoding="utf-8"
    )

    fake_reply = "\n\n".join(
        [
            _file_block("dispatcher/project.json", dispatcher_project),
            _file_block("dispatcher/project.uiproj", dispatcher_uiproj),
            _file_block("dispatcher/Main.xaml", dispatcher_main),
            _file_block("performer/project.json", performer_project),
            _file_block("performer/project.uiproj", performer_uiproj),
            _file_block("performer/Main.xaml", performer_main),
            _file_block("long-running/project.json", long_running_project),
            _file_block("long-running/project.uiproj", long_running_uiproj),
            _file_block("long-running/Main.xaml", long_running_main),
            _file_block("long-running/Main-Queue.xaml", long_running_queue),
        ]
    )

    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            gmr.return_value = fake_reply
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="create project scaffolds for dispatcher performer and long-running templates\nexit\n",
            )

    assert result.exit_code == 0
    root = output_root / "pytest-project-bundles"

    assert (root / "dispatcher" / "project.json").exists()
    assert (root / "dispatcher" / "project.uiproj").exists()
    assert (root / "dispatcher" / "Main.xaml").exists()

    assert (root / "performer" / "project.json").exists()
    assert (root / "performer" / "project.uiproj").exists()
    assert (root / "performer" / "Main.xaml").exists()

    assert (root / "long-running" / "project.json").exists()
    assert (root / "long-running" / "project.uiproj").exists()
    assert (root / "long-running" / "Main.xaml").exists()
    assert (root / "long-running" / "Main-Queue.xaml").exists()

    assert "wrote:" in result.stdout.lower()
