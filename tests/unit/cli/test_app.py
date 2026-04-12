"""Test CLI app."""
from unittest.mock import AsyncMock, patch
import asyncio

from typer.testing import CliRunner
from uipath_claude.cli.app import (
    _build_runtime_skill_context,
    _get_model_response,
    _select_relevant_skills,
    app,
)


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


def test_select_relevant_skills_prefers_rpa_workflow():
    """Workflow prompts should prioritize the RPA workflow skill."""
    skills = [
        {"name": "pdd-creation", "description": "Process docs", "triggers": []},
        {
            "name": "uipath-rpa-workflows",
            "description": "Generate and edit UiPath workflow xaml",
            "triggers": ["xaml workflows", "email automation"],
        },
        {"name": "uipath-coded-workflows", "description": "C# coded workflows", "triggers": []},
    ]
    selected = _select_relevant_skills(
        "Build a UiPath workflow that reads Outlook email subjects",
        skills,
    )
    assert selected
    assert selected[0]["name"] == "uipath-rpa-workflows"


def test_build_runtime_skill_context_includes_selected_skill_content():
    """Runtime guidance should include selected skill content."""
    skills = [
        {
            "name": "uipath-rpa-workflows",
            "description": "Generate and edit UiPath workflow xaml",
            "triggers": ["xaml workflows"],
            "path": "/tmp/skill.md",
        }
    ]
    with patch("uipath_claude.cli.app.load_skill_content") as load_skill:
        load_skill.return_value = "# RPA Workflow Skill\nDo not edit project.json manually."
        context = _build_runtime_skill_context("create an xaml workflow", skills)
    assert "Skill: uipath-rpa-workflows" in context
    assert "Do not edit project.json manually." in context


def test_get_model_response_includes_runtime_context_in_system_message():
    """System prompt should include runtime guidance context."""

    class FakeEngine:
        def __init__(self):
            self.messages = None
            self.system_prompt = None

        async def run(self, messages, tools, system_prompt):
            self.messages = messages
            self.system_prompt = system_prompt
            return "ok"

    engine = FakeEngine()
    result = asyncio.run(
        _get_model_response(
            engine,
            [{"role": "user", "content": "hello"}],
            memory="saved memory",
            runtime_context="use rpa skill",
            stream=False,
        )
    )
    assert result == "ok"
    assert "Runtime guidance:\nuse rpa skill" in engine.messages[0]["content"]
    assert "saved memory" in engine.system_prompt
