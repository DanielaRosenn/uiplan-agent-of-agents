"""Integration test for chat flow."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner
from uipath_claude.cli.app import app


runner = CliRunner()


@pytest.fixture(autouse=True)
def _integration_chat_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Match unit CLI tests: skip auth prompts (would consume stdin) and skip planner."""
    monkeypatch.setenv("UIPATH_SKIP_AUTH_CHECK", "1")
    monkeypatch.setenv("UIPATH_PLAN_MODE", "0")
    # Tests mock ``_get_model_response``; agentic mode bypasses it and calls Bedrock directly.
    monkeypatch.setenv("UIPATH_AGENTIC_MODE", "0")


@pytest.mark.integration
def test_chat_flow_with_no_banner():
    """Test chat command runs without banner."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as get_model_response:
            get_model_response.return_value = "Hi from model"
            result = runner.invoke(app, ["chat", "--no-banner"], input="hello\nexit\n")
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "you:" in output
    assert "goodbye" in output or "what would you like to do next" in output


@pytest.mark.integration
def test_chat_flow_no_stream_flag_keeps_buffered_output():
    """Test --no-stream uses buffered assistant print path."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch(
            "uipath_claude.cli.app._get_model_response", new_callable=AsyncMock
        ) as get_model_response:
            get_model_response.return_value = "Buffered reply"
            result = runner.invoke(
                app, ["chat", "--no-banner", "--no-stream"], input="hello\nexit\n"
            )
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "you:" in output
    assert "goodbye" in output or "what would you like to do next" in output


@pytest.mark.integration
def test_chat_flow_detects_project(tmp_path, monkeypatch):
    """Test chat flow detects UiPath project."""
    # Create fake project
    project_json = tmp_path / "project.json"
    project_json.write_text('{"name": "TestProject", "projectType": "Process"}')
    
    monkeypatch.chdir(tmp_path)
    
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        result = runner.invoke(app, ["chat", "--no-banner"], input="exit\n")
    assert result.exit_code == 0
    assert "detected uipath project: testproject" in result.stdout.lower()


@pytest.mark.integration
def test_chat_flow_skills_command_lists_discovered(tmp_path, monkeypatch):
    """Test /skills command lists discovered local skills."""
    skill_dir = tmp_path / ".uipath-claude" / "skills" / "sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: sample-skill
description: sample
triggers: ["sample"]
---
"""
    )
    monkeypatch.chdir(tmp_path)
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        result = runner.invoke(app, ["chat", "--no-banner"], input="/skills\nexit\n")
    assert result.exit_code == 0
    assert "sample-skill" in result.stdout


@pytest.mark.integration
def test_chat_flow_bootstrap_command_executes(tmp_path, monkeypatch):
    """Test /bootstrap command renders bootstrap stages."""
    monkeypatch.chdir(tmp_path)
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch("uipath_claude.cli.app.run_bootstrap_flow", new_callable=AsyncMock) as run_bootstrap:
            run_bootstrap.return_value = {
                "pdd": "pdd",
                "sdd": "sdd",
                "code": "code",
                "validation": "ok",
                "paths": {"pdd": "/tmp/pdd.md"},
            }
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="/bootstrap build invoice automation\nexit\n",
            )
    assert result.exit_code == 0
    assert "bootstrap complete" in result.stdout.lower()
    assert "qa:" in result.stdout.lower()
    assert "artifacts written" in result.stdout.lower()


@pytest.mark.integration
def test_chat_flow_skill_invocation(tmp_path, monkeypatch):
    """Test explicit /skill invocation executes selected skill."""
    skill_dir = tmp_path / ".uipath-claude" / "skills" / "sample-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: sample-skill
description: sample
triggers: ["sample"]
---

# Sample Skill
"""
    )
    monkeypatch.chdir(tmp_path)
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        result = runner.invoke(
            app,
            ["chat", "--no-banner"],
            input="/skill sample-skill test query\nexit\n",
        )
    assert result.exit_code == 0
    assert "skill: sample-skill" in result.stdout.lower()


@pytest.mark.integration
def test_chat_warns_when_running_in_generated_chat_artifact(tmp_path, monkeypatch):
    """Chat should warn when cwd is a generated chat artifact folder."""
    artifact_dir = tmp_path / "generated" / "chat" / "artifact-1"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "project.json").write_text('{"name":"artifact"}')
    monkeypatch.chdir(artifact_dir)

    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        result = runner.invoke(app, ["chat", "--no-banner"], input="exit\n")

    assert result.exit_code == 0
    assert "generated chat artifact folder" in result.stdout.lower()


@pytest.mark.integration
def test_chat_confirm_build_prompt_cancel(tmp_path, monkeypatch):
    """UIPATH_CONFIRM_BUILD shows prompt and skips invoke when user declines."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_CONFIRM_BUILD", "1")
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": []}
        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            result = runner.invoke(
                app,
                ["chat", "--no-banner"],
                input="create an rpa workflow for outlook\nn\nexit\n",
            )
    assert result.exit_code == 0
    output = result.stdout.lower()
    assert "you:" in output
    assert "goodbye" in output or "what would you like to do next" in output
    mock_graph.ainvoke.assert_called()
