"""Integration tests that keep skill-picking output artifacts."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from uipath_claude.cli.app import app

runner = CliRunner()


@pytest.mark.integration
def test_chat_asks_for_clarification_on_ambiguous_prompt(monkeypatch):
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(repo_root)
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "pytest-clarification-gate")

    with patch("uipath_claude.cli.app._create_engine") as eng:
        eng.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as gmr:
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="help me with this\nexit\n",
            )

    assert result.exit_code == 0
    assert "could you clarify the automation goal" in result.stdout.lower()
    gmr.assert_not_called()


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
    assert gmr.await_count >= 1


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

    required_templates = [
        repo_root / "templates" / "dispatcher" / "project.json",
        repo_root / "templates" / "dispatcher" / "project.uiproj",
        repo_root / "templates" / "dispatcher" / "Main.xaml",
        repo_root / "templates" / "performer" / "project.json",
        repo_root / "templates" / "performer" / "project.uiproj",
        repo_root / "templates" / "performer" / "Main.xaml",
        repo_root / "templates" / "long-running" / "project.json",
        repo_root / "templates" / "long-running" / "project.uiproj",
        repo_root / "templates" / "long-running" / "Main.xaml",
        repo_root / "templates" / "long-running" / "Main-Queue.xaml",
    ]
    missing_templates = [path for path in required_templates if not path.exists()]
    if missing_templates:
        missing = ", ".join(str(path.relative_to(repo_root)) for path in missing_templates)
        pytest.skip(f"Template fixtures unavailable in this test context: {missing}")

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

    assert "generating files, one moment" in result.stdout.lower()
    assert "wrote:" in result.stdout.lower()
