"""Tests for AgenticProgressReporter."""
from io import StringIO

import pytest
from rich.console import Console

from uipath_claude.rendering.progress import AgenticProgressReporter


@pytest.fixture
def string_console() -> tuple[AgenticProgressReporter, StringIO]:
    buf = StringIO()
    console = Console(file=buf, force_terminal=True, width=120)
    return AgenticProgressReporter(console), buf


def test_should_show_full_tool_body_failure_always(string_console):
    rep, _ = string_console
    assert rep.should_show_full_tool_body(False) is True


def test_should_show_full_tool_body_success_verbose_by_default(string_console):
    rep, _ = string_console
    assert rep.should_show_full_tool_body(True) is True


def test_should_show_full_tool_body_success_quiet_when_verbose_off(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("UIPATH_DEBUG_VERBOSE", "0")
    monkeypatch.setenv("UIPATH_DEBUG_RAW", "0")
    monkeypatch.setenv("UIPATH_AGENTIC_FULL_TOOL_OUTPUT", "0")
    buf = StringIO()
    rep = AgenticProgressReporter(Console(file=buf, force_terminal=True, width=120))
    assert rep.should_show_full_tool_body(True) is False


def test_skills_in_context_prints_names(string_console):
    rep, buf = string_console
    rep.skills_in_context(["uipath-rpa", "uipath-planner"], "uipath-rpa")
    out = buf.getvalue()
    assert "Skills in context" in out
    assert "uipath-rpa" in out
    assert "uipath-planner" in out


def test_session_banner_prints_root(string_console):
    rep, buf = string_console
    rep.session_banner("C:\\tmp\\session-abc")
    out = buf.getvalue()
    assert "Artifact root" in out
    assert "session-abc" in out


def test_complete_shows_iterations_and_tool_counts(string_console):
    rep, buf = string_console
    rep.complete(
        ["Main.xaml"],
        2,
        tool_success_count=2,
        tool_failure_count=1,
        artifact_root="C:\\out\\sess",
    )
    out = buf.getvalue()
    assert "Agent finished after 2 iteration" in out
    assert "2 ok" in out
    assert "1 reported errors" in out or "reported errors" in out
    assert "Main.xaml" in out


def test_iteration_start_shows_fraction_and_dot_padding(string_console):
    rep, buf = string_console
    rep.iteration_start(3, 25)
    out = buf.getvalue()
    assert "Step 3/25" in out
    assert "\u00b7" in out
    assert "==>" in out


def test_model_finished_first_iteration_no_tools_empty(string_console):
    rep, buf = string_console
    rep.model_finished_without_tools(
        iteration=1,
        had_tool_calls_before=False,
        final_text="",
    )
    out = buf.getvalue()
    assert "No action taken" in out
    assert "Finishing" not in out


def test_model_finished_first_iteration_no_tools_with_text(string_console):
    rep, buf = string_console
    rep.model_finished_without_tools(
        iteration=1,
        had_tool_calls_before=False,
        final_text="hello",
    )
    out = buf.getvalue()
    assert "Responding (no tools used)" in out
    assert "Finishing" not in out


def test_model_finished_after_tools_shows_finishing_line(string_console):
    rep, buf = string_console
    rep.model_finished_without_tools(
        iteration=2,
        had_tool_calls_before=True,
        final_text="Done explaining the workflow.",
    )
    out = buf.getvalue()
    assert "Finishing (no more tool calls this turn)" in out
    assert "Preview:" in out
    assert "Done explaining the workflow" in out
