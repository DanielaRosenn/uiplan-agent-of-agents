"""Integration test for chat flow."""
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner
from uipath_claude.cli.app import app


runner = CliRunner()


@pytest.mark.integration
def test_chat_flow_with_no_banner():
    """Test chat command runs without banner."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch("uipath_claude.cli.app._get_model_response", new_callable=AsyncMock) as get_model_response:
            get_model_response.return_value = "Hi from model"
            result = runner.invoke(app, ["chat", "--no-banner"], input="hello\nexit\n")
    assert result.exit_code == 0
    assert "assistant: hi from model" in result.stdout.lower()


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
