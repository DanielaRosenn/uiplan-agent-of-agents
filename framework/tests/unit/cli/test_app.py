"""Test CLI app."""
import asyncio
import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner
from uipath_claude.cli.app import (
    _UIPATH_CHAT_SYSTEM,
    _parse_numbered_questions_from_clarifier,
    _allow_project_file_generation,
    _is_file_generation_intent,
    _canonical_skill_name,
    _debug_skill_selection,
    _build_runtime_skill_context,
    _build_runtime_skill_context_for_selected,
    _get_model_response,
    _is_generated_chat_artifact_folder,
    _load_dotenv_from_cwd,
    _resolve_output_mode,
    _make_chat_session_id,
    _select_relevant_skills,
    app,
)


runner = CliRunner()


def test_load_dotenv_from_cwd_uipath_keys_override_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("UIPATH_DOTENV_TEST_KEY", raising=False)
    monkeypatch.delenv("UIPATH_QUOTED", raising=False)
    (tmp_path / ".env").write_text(
        'UIPATH_DOTENV_TEST_KEY=fromfile\nUIPATH_QUOTED="q"\n',
        encoding="utf-8",
    )
    _load_dotenv_from_cwd()
    assert os.environ["UIPATH_DOTENV_TEST_KEY"] == "fromfile"
    assert os.environ["UIPATH_QUOTED"] == "q"
    monkeypatch.setenv("UIPATH_DOTENV_TEST_KEY", "preset")
    _load_dotenv_from_cwd()
    assert os.environ["UIPATH_DOTENV_TEST_KEY"] == "fromfile"


def test_load_dotenv_from_cwd_non_uipath_does_not_override_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OTHER_DOTENV_KEY", "shell")
    (tmp_path / ".env").write_text("OTHER_DOTENV_KEY=file\n", encoding="utf-8")
    _load_dotenv_from_cwd()
    assert os.environ["OTHER_DOTENV_KEY"] == "shell"


@pytest.fixture(autouse=True)
def _skip_uipath_auth_prompt_in_cli_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """Most chat tests mock the graph only; real auth would block on Rich Prompt."""
    monkeypatch.setenv("UIPATH_SKIP_AUTH_CHECK", "1")
    # Default CLI approval is on; Rich tests run without a TTY so destructive tools
    # would always be denied. Opt out for automated CLI tests.
    monkeypatch.setenv("UIPATH_TOOL_APPROVAL", "0")


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


def test_cli_chat_auth_interactive_success_starts_repl(monkeypatch: pytest.MonkeyPatch):
    """Option 1 runs uipath auth; on success + verification, chat REPL starts."""
    monkeypatch.setenv("UIPATH_SKIP_AUTH_CHECK", "0")
    _n = {"i": 0}

    def _check_status():
        _n["i"] += 1
        if _n["i"] == 1:
            return (False, None, "not authenticated")
        return (True, "user@org", None)

    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch(
            "uipath_claude.utils.auth_check.check_uipath_cli_installed",
            return_value=True,
        ):
            with patch(
                "uipath_claude.utils.auth_check.check_uipath_auth_status",
                side_effect=_check_status,
            ):
                with patch(
                    "uipath_claude.utils.auth_check.prompt_for_authentication",
                    return_value="interactive_auth",
                ):
                    with patch(
                        "uipath_claude.utils.auth_check.resolve_uipath_auth_argv",
                        return_value=(["uipath", "auth", "--cloud", "--tenant", "x"], None),
                    ):
                        with patch(
                            "uipath_claude.utils.auth_check.run_uipath_interactive_auth",
                            return_value=0,
                        ):
                            result = runner.invoke(
                                app, ["chat", "--no-banner"], input="exit\n"
                            )
    assert result.exit_code == 0
    out = (result.stdout or "").lower()
    assert "chat session started" in out
    assert "authenticated" in out


def test_cli_chat_auth_interactive_missing_tenant_exits(monkeypatch: pytest.MonkeyPatch):
    """Option 1 without UIPATH_TENANT_NAME exits with error."""
    monkeypatch.setenv("UIPATH_SKIP_AUTH_CHECK", "0")
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch(
            "uipath_claude.utils.auth_check.check_uipath_cli_installed",
            return_value=True,
        ):
            with patch(
                "uipath_claude.utils.auth_check.check_uipath_auth_status",
                return_value=(False, None, "not authenticated"),
            ):
                with patch(
                    "uipath_claude.utils.auth_check.prompt_for_authentication",
                    return_value="interactive_auth",
                ):
                    with patch(
                        "uipath_claude.utils.auth_check.resolve_uipath_auth_argv",
                        return_value=(None, "Set UIPATH_TENANT_NAME"),
                    ):
                        result = runner.invoke(app, ["chat", "--no-banner"], input="")
    assert result.exit_code == 1
    assert "uipath_tenant_name" in (result.stdout or "").lower()


def test_cli_chat_auth_skip_starts_repl(monkeypatch: pytest.MonkeyPatch):
    """Option 2 continues without Orchestrator auth."""
    monkeypatch.setenv("UIPATH_SKIP_AUTH_CHECK", "0")
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        with patch(
            "uipath_claude.utils.auth_check.check_uipath_cli_installed",
            return_value=True,
        ):
            with patch(
                "uipath_claude.utils.auth_check.check_uipath_auth_status",
                return_value=(False, None, "not authenticated"),
            ):
                with patch(
                    "uipath_claude.utils.auth_check.prompt_for_authentication",
                    return_value="skip_auth",
                ):
                    result = runner.invoke(app, ["chat", "--no-banner"], input="exit\n")
    assert result.exit_code == 0
    out = (result.stdout or "").lower()
    assert "chat session started" in out
    assert "continuing without authentication" in out


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
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("model failed"))
        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            # BUILD + --no-plan reaches the chat graph; vague one-word prompts route to clarifier.
            result = runner.invoke(
                app,
                ["chat", "--no-banner", "--no-plan"],
                input="Create a minimal workflow that logs once in Main.xaml.\nexit\n",
            )
    assert result.exit_code == 0
    assert "bedrock request failed" in result.stdout.lower()


def test_cli_chat_question_uses_simple_llm_answer_not_graph():
    """QUESTION intent uses simple_llm_answer and does not invoke the chat graph."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock()

        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.simple_llm_answer",
                new=AsyncMock(
                    return_value="project.json holds metadata; Main.xaml is the entry."
                ),
            ):
                result = runner.invoke(
                    app,
                    ["chat", "--no-banner", "--no-plan", "--no-stream"],
                    input="What is project.json?\nexit\n",
                )
    assert result.exit_code == 0
    assert "project.json" in result.stdout.lower()
    assert "[ANSWERING]" in result.stdout
    mock_graph.ainvoke.assert_not_awaited()


def test_cli_chat_ambiguous_invokes_graph():
    """AMBIGUOUS intent still goes through the chat graph."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()

        async def _ainvoke(state):
            msg = "Which email provider do you use?"
            return {
                "messages": list(state.get("messages") or [])
                + [{"role": "assistant", "content": msg}],
                "assistant_response": msg,
                "pending_question": None,
            }

        mock_graph.ainvoke = AsyncMock(side_effect=_ainvoke)
        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            result = runner.invoke(
                app,
                ["chat", "--no-banner", "--no-plan"],
                input="Automate my email.\nexit\n",
            )
    assert result.exit_code == 0
    assert "which email provider" in result.stdout.lower()
    mock_graph.ainvoke.assert_awaited()


def test_cli_chat_auto_approve_plan_passes_approved_plan_in_runtime_extra():
    """After plan approval, runtime_extra must include the plan for execute.py to merge."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        captured: list[dict[str, Any]] = []

        async def _ainvoke(state):
            captured.append(dict(state))
            msgs = list(state.get("messages") or [])
            return {
                "messages": msgs + [{"role": "assistant", "content": "ok"}],
                "assistant_response": "ok",
                "pending_question": None,
            }

        mock_graph.ainvoke = AsyncMock(side_effect=_ainvoke)
        mock_plan_result = MagicMock()
        mock_plan_result.final_response = (
            "Step 1: Call ensure_project_structure\nStep 2: Add Main.xaml"
        )

        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.run_planner_agent",
                new=AsyncMock(return_value=mock_plan_result),
            ):
                result = runner.invoke(
                    app,
                    ["chat", "--no-banner", "--auto-approve-plan"],
                    input="Create Hello World workflow\nexit\n",
                )

    assert result.exit_code == 0
    assert captured, "expected graph invoke after plan approval"
    extra = str(captured[0].get("runtime_extra") or "")
    assert "Approved Implementation Plan" in extra
    assert "ensure_project_structure" in extra


def test_cli_chat_clarification_loop_progresses():
    """Multi-turn chat invokes the graph each turn; planner mocked when plan mode runs."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        n = {"i": 0}

        async def _ainvoke(state):
            n["i"] += 1
            text = f"assistant turn {n['i']}"
            return {
                "messages": list(state.get("messages") or [])
                + [{"role": "assistant", "content": text}],
                "assistant_response": text,
                "pending_question": None,
            }

        mock_graph.ainvoke = AsyncMock(side_effect=_ainvoke)
        mock_plan_result = MagicMock()
        mock_plan_result.final_response = "# Plan\n- Step 1: Create project\n- Step 2: Add workflow"

        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.run_planner_agent",
                new=AsyncMock(return_value=mock_plan_result),
            ):
                result = runner.invoke(
                    app,
                    ["chat", "--no-banner"],
                    input="Automate my email.\nOutlook\nRead emails\ny\nexit\n",
                )

    assert result.exit_code == 0
    assert mock_graph.ainvoke.await_count >= 1


def test_cli_chat_question_streaming_callback():
    """QUESTION path calls simple_llm_answer with streaming enabled from CLI default."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock()

        captured: dict[str, Any] = {}

        async def _simple_answer(**kwargs):
            captured["stream"] = kwargs.get("stream")
            captured["on_delta"] = kwargs.get("on_delta")
            cb = kwargs.get("on_delta")
            if cb:
                cb("project.json contains metadata")
            return ""

        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.simple_llm_answer",
                new=AsyncMock(side_effect=_simple_answer),
            ):
                result = runner.invoke(
                    app,
                    ["chat", "--no-banner"],
                    input="What is project.json?\nexit\n",
                )

    assert result.exit_code == 0
    assert "project.json" in result.stdout.lower()
    mock_graph.ainvoke.assert_not_awaited()
    assert captured.get("stream") is True
    assert callable(captured.get("on_delta"))


def test_cli_chat_slash_command_output_added_to_history():
    """Slash command output should be appended to history so the next QA turn sees it."""
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock()

        captured: dict[str, Any] = {}

        async def _simple_answer(**kwargs):
            captured["history"] = list(kwargs.get("history") or [])
            captured["user_input"] = kwargs.get("user_input")
            return "ok"

        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.simple_llm_answer",
                new=AsyncMock(side_effect=_simple_answer),
            ):
                result = runner.invoke(
                    app,
                    ["chat", "--no-banner", "--no-stream"],
                    input="/status\nwhat did /status just say?\nexit\n",
                )

    assert result.exit_code == 0
    history = captured.get("history") or []
    assert any(m.get("role") == "user" and m.get("content") == "/status" for m in history), (
        f"Expected /status user turn in history, got: {history}"
    )
    assistant_logs = [
        m for m in history
        if m.get("role") == "assistant" and "[command output: /status]" in (m.get("content") or "")
    ]
    assert assistant_logs, f"Expected slash output in history, got: {history}"


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
    assert _canonical_skill_name(selected[0]["name"]) == "uipath-rpa"


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


def test_make_chat_session_id_uses_env_override(monkeypatch):
    """Configured chat session ID should be sanitized and reused."""
    monkeypatch.setenv("UIPATH_CHAT_SESSION_ID", "trace id/alpha")
    assert _make_chat_session_id() == "trace-id-alpha"


def test_make_chat_session_id_has_timestamp_prefix(monkeypatch):
    """Generated session IDs should include a timestamp-based prefix."""
    monkeypatch.delenv("UIPATH_CHAT_SESSION_ID", raising=False)
    value = _make_chat_session_id()
    assert len(value) >= 24
    assert value[8] == "-"


def test_allow_project_file_generation_requires_explicit_request():
    """Project file writes should require explicit wording."""
    assert not _allow_project_file_generation("build an outlook workflow")
    assert _allow_project_file_generation("create a new project with project.json")


def test_is_file_generation_intent_false_for_questions_about_project_files():
    """QUESTION prompts mention ``project`` but must not trigger stream-suppression."""
    assert not _is_file_generation_intent("What is project.json?")
    assert _is_file_generation_intent("Add a new workflow file Main.xaml")


def test_debug_skill_selection_returns_sorted_scores():
    skills = [
        {"name": "x", "description": "none", "triggers": []},
        {"name": "uipath-rpa-workflows", "description": "UiPath Outlook email workflow", "triggers": []},
    ]
    traces = _debug_skill_selection("create outlook workflow", skills)
    assert traces
    assert "uipath-rpa" in traces[0]


def test_resolve_output_mode_defaults_to_auto(monkeypatch):
    monkeypatch.delenv("UIPATH_CHAT_OUTPUT_MODE", raising=False)
    assert _resolve_output_mode() == "auto"


def test_resolve_output_mode_respects_full(monkeypatch):
    monkeypatch.setenv("UIPATH_CHAT_OUTPUT_MODE", "full")
    assert _resolve_output_mode() == "full"


def test_generated_chat_artifact_folder_detection(tmp_path):
    artifact_path = tmp_path / "generated" / "chat" / "abc"
    artifact_path.mkdir(parents=True)
    assert _is_generated_chat_artifact_folder(artifact_path)


def test_build_runtime_skill_context_for_selected_includes_insights(
    tmp_path, monkeypatch
):
    """Learned-from-usage block is appended when insights summary exists."""
    monkeypatch.chdir(tmp_path)
    skill_file = tmp_path / "uipath-rpa" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\nname: uipath-rpa\ndescription: RPA\n---\n# Body\nHello skill\n",
        encoding="utf-8",
    )
    selected = [{"name": "uipath-rpa", "path": str(skill_file)}]
    with patch("uipath_claude.cli.app.get_execution_hooks") as mock_get_hooks:
        hooks = MagicMock()
        hooks.get_insights_summary.return_value = "## Learned from usage\n- Gotcha: test"
        mock_get_hooks.return_value = hooks
        out = _build_runtime_skill_context_for_selected("create workflow", selected)
    assert "Learned from Usage" in out
    assert "Gotcha: test" in out
    hooks.get_insights_summary.assert_called_once_with("uipath-rpa", max_tokens=150)


def test_uipath_chat_system_instructs_executor_on_approved_plans() -> None:
    """Regression: executor must treat Approved Implementation Plan as actionable."""
    assert "Approved Implementation Plan" in _UIPATH_CHAT_SYSTEM
    assert "ensure_project_structure" in _UIPATH_CHAT_SYSTEM
    assert "write_file" in _UIPATH_CHAT_SYSTEM or "UIPATH_FILE" in _UIPATH_CHAT_SYSTEM


def test_parse_numbered_questions_from_clarifier() -> None:
    text = "Intro line\n1. First question here?\n2) Second one\n"
    qs = _parse_numbered_questions_from_clarifier(text)
    assert qs == ["First question here?", "Second one"]


def test_plan_approval_shows_hint_line(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich default hides [y/n/edit]; we print an explicit hint before Prompt.ask."""
    monkeypatch.setenv("UIPATH_PLAN_POST_QUESTIONS", "0")
    monkeypatch.setenv("UIPATH_FORCE_INTERACTIVE", "1")
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        captured: list[dict[str, Any]] = []

        async def _ainvoke(state):
            captured.append(dict(state))
            return {
                "messages": list(state.get("messages") or [])
                + [{"role": "assistant", "content": "done"}],
                "assistant_response": "done",
                "pending_question": None,
            }

        mock_graph.ainvoke = AsyncMock(side_effect=_ainvoke)
        mock_plan = MagicMock()
        mock_plan.final_response = "# Plan\n- Step 1"
        ask_answers = iter(
            [
                "Create a minimal workflow in Main.xaml",
                "y",
                "exit",
            ]
        )

        def _fake_prompt_ask(prompt, *args, **kwargs):
            return next(ask_answers)

        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
                with patch(
                    "uipath_claude.cli.app.run_planner_agent",
                    new=AsyncMock(return_value=mock_plan),
                ):
                    with patch(
                        "uipath_claude.cli.app.Prompt.ask",
                        side_effect=_fake_prompt_ask,
                    ):
                        result = runner.invoke(
                            app,
                            ["chat", "--no-banner", "--no-stream"],
                            input="",
                        )
    assert result.exit_code == 0
    out = result.stdout or ""
    assert "type 'y' to approve" in out.lower()
    assert "edit" in out.lower()
    assert captured
    extra = str(captured[0].get("runtime_extra") or "")
    assert "Approved Implementation Plan" in extra


def test_plan_approval_edit_then_feedback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Typing edit opens a feedback prompt; feedback is merged into the next planner turn."""
    monkeypatch.setenv("UIPATH_PLAN_POST_QUESTIONS", "0")
    monkeypatch.setenv("UIPATH_FORCE_INTERACTIVE", "1")
    planner_calls: list[str] = []

    async def _planner(user_input, **kwargs):
        planner_calls.append(user_input)
        m = MagicMock()
        m.final_response = "# Plan v\n- step"
        return m

    ask_answers = iter(
        [
            "Build invoice workflow",
            "edit",
            "Add validation step",
            "y",
            "exit",
        ]
    )

    def _fake_prompt_ask(prompt, *args, **kwargs):
        return next(ask_answers)

    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "messages": [],
                "assistant_response": "ok",
                "pending_question": None,
            }
        )
        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.run_planner_agent",
                new=_planner,
            ):
                with patch(
                    "uipath_claude.cli.app.Prompt.ask",
                    side_effect=_fake_prompt_ask,
                ):
                    result = runner.invoke(
                        app,
                        ["chat", "--no-banner", "--no-stream"],
                        input="",
                    )
    assert result.exit_code == 0
    assert len(planner_calls) >= 2
    assert "Feedback on plan: Add validation step" in planner_calls[1]


def test_plan_post_questions_flag_merges_answers_into_runtime_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("UIPATH_PLAN_POST_QUESTIONS", "1")
    monkeypatch.setenv("UIPATH_FORCE_INTERACTIVE", "1")
    with patch("uipath_claude.cli.app._create_engine") as create_engine:
        create_engine.return_value = object()
        mock_graph = MagicMock()
        captured: list[dict[str, Any]] = []

        async def _ainvoke(state):
            captured.append(dict(state))
            return {
                "messages": list(state.get("messages") or [])
                + [{"role": "assistant", "content": "done"}],
                "assistant_response": "done",
                "pending_question": None,
            }

        mock_graph.ainvoke = AsyncMock(side_effect=_ainvoke)
        mock_plan = MagicMock()
        mock_plan.final_response = "# Plan\n- Step 1"
        ask_answers = iter(
            [
                "Create Hello World workflow",
                "y",
                "north",
                "2026",
                "exit",
            ]
        )

        def _fake_prompt_ask(prompt, *args, **kwargs):
            return next(ask_answers)

        with patch("uipath_claude.cli.app.compile_chat_graph", return_value=mock_graph):
            with patch(
                "uipath_claude.cli.app.run_planner_agent",
                new=AsyncMock(return_value=mock_plan),
            ):
                with patch(
                    "uipath_claude.query.clarifier.run_clarifier_agent",
                    new=AsyncMock(
                        return_value="1. Which region?\n2. Go-live date?\n"
                    ),
                ):
                    with patch(
                        "uipath_claude.cli.app.Prompt.ask",
                        side_effect=_fake_prompt_ask,
                    ):
                        result = runner.invoke(
                            app,
                            ["chat", "--no-banner", "--no-stream"],
                            input="",
                        )
    assert result.exit_code == 0
    extra = str(captured[0].get("runtime_extra") or "")
    assert "Q: Which region?" in extra
    assert "A: north" in extra
    assert "Q: Go-live date?" in extra
    assert "A: 2026" in extra
