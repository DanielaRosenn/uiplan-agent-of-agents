"""Unit tests for docs/evaluations/run_evaluations.py parser and technical OR-tools."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _load_eval_module():
    path = _ROOT / "docs" / "evaluations" / "run_evaluations.py"
    spec = importlib.util.spec_from_file_location("eval_run", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def ev():
    return _load_eval_module()


def test_detect_mode_exit(ev):
    stdout = (
        "Chat session started.\n\n"
        "You: Goodbye!\n"
    )
    assert ev.OutputParser.detect_mode(stdout) == "exit"


def test_detect_mode_answering_then_goodbye_is_direct_response(ev):
    """Harness ends with Goodbye; must not override [ANSWERING] Q&A classification."""
    stdout = (
        "Chat session started.\n\n"
        "You: What is project.json?\n"
        "[ANSWERING]\n"
        "Assistant: project.json is the project manifest.\n"
        "You: Goodbye!\n"
    )
    assert ev.OutputParser.detect_mode(stdout) == "direct_response"


def test_mode_compatible_execution_vs_pte(ev):
    assert ev.TechnicalEvaluator._mode_compatible("execution", "planning_then_execution")


def test_extract_assistant_response_prefers_plan_over_short_preview(ev):
    stdout = (
        "[EXECUTING]\n"
        "┌──────────────────────────── Implementation Plan ─────────────────────────────┐\n"
        "│ ForEachRow and Excel row processing                                           │\n"
        "└──────────────────────────────────────────────────────────────────────────────┘\n"
        "  Preview: Short summary without the word Excel.\n"
        "You: Goodbye!\n"
    )
    text = ev.OutputParser.extract_assistant_response(stdout)
    assert "foreachrow" in text.lower() or "excel" in text.lower()


def test_tool_calls_required_any_of_passes_when_one_present(ev):
    evl = ev.TechnicalEvaluator(
        {
            "tool_calls": ["read_project_json", "write_file"],
            "mode": "planning_then_execution",
            "crashed": False,
            "files_written": [],
            "errors": [],
        },
        {
            "tool_calls_required_any_of": [
                "ensure_project_structure",
                "read_project_json",
            ],
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["passed"] is True


def test_tool_calls_required_any_of_ignored_when_not_list(ev):
    evl = ev.TechnicalEvaluator(
        {
            "tool_calls": ["list_directory"],
            "mode": "planning_then_execution",
            "crashed": False,
            "files_written": [],
            "errors": [],
        },
        {
            "tool_calls_required_any_of": "deploy_to_orchestrator",
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["passed"] is True


def test_tool_calls_required_any_of_fails_when_none_present(ev):
    evl = ev.TechnicalEvaluator(
        {
            "tool_calls": ["list_directory"],
            "mode": "planning_then_execution",
            "crashed": False,
            "files_written": [],
            "errors": [],
        },
        {
            "tool_calls_required_any_of": ["deploy_to_orchestrator", "read_project_json"],
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["passed"] is False
    assert any("need any of" in f for f in out["details"]["failed"])
