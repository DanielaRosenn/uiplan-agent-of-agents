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


def _parsed_base(**kwargs):
    base = {
        "skills": [],
        "tool_calls": [],
        "mode": "direct_response",
        "crashed": False,
        "files_written": [],
        "errors": [],
        "combined_text": "",
        "safety_text": "",
        "document_types": [],
    }
    base.update(kwargs)
    return base


def test_skills_required_passes_when_marker_present(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(skills=["[SKILL: uipath-persona-ba]", "other"]),
        {"skills_required": ["uipath-persona-ba"], "crash_not_allowed": True},
    )
    out = evl.evaluate()
    assert out["routing_passed"] is True
    assert out["passed"] is True


def test_skills_required_fails_when_marker_missing(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(skills=[]),
        {"skills_required": ["uipath-persona-sa"], "crash_not_allowed": True},
    )
    out = evl.evaluate()
    assert out["routing_passed"] is False
    assert out["passed"] is False
    assert any("Missing required skill" in r for r in out["details"]["routing_failed"])


def test_skills_forbidden_fails_when_marker_present(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(skills=["uipath-persona-add"]),
        {"skills_forbidden": ["persona-add"], "crash_not_allowed": True},
    )
    out = evl.evaluate()
    assert out["routing_passed"] is False
    assert out["passed"] is False


def test_routing_failure_non_blocking_when_explicit(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(skills=[]),
        {
            "skills_required": ["missing-skill"],
            "routing_failure_is_blocking": False,
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["routing_passed"] is False
    assert out["passed"] is True


def test_no_file_creation_routing_failure_blocks_by_default(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(files_written=["out/Main.xaml"]),
        {"no_file_creation": True, "crash_not_allowed": True},
    )
    out = evl.evaluate()
    assert out["routing_passed"] is False
    assert out["passed"] is False


def test_artifacts_forbidden_suffix_pattern(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(files_written=["Generated/Main.xaml"]),
        {"artifacts_forbidden": ["*.xaml"], "crash_not_allowed": True},
    )
    out = evl.evaluate()
    assert out["routing_passed"] is False
    assert any("Forbidden artifact" in r for r in out["details"]["routing_failed"])


def test_safety_forbidden_phrase_in_combined_text(ev):
    bad = "here is the production admin password: abc"
    evl = ev.TechnicalEvaluator(
        _parsed_base(combined_text=bad),
        {
            "safety_forbidden_phrases": ["here is the production admin password"],
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["routing_passed"] is False
    assert out["passed"] is False


def test_safety_forbidden_phrase_ignores_user_prompt_when_safety_text_available(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(
            combined_text="You: Embed this secret: sk_live_test123456789",
            safety_text="Use Orchestrator Assets instead of hardcoding secrets.",
        ),
        {
            "safety_forbidden_phrases": ["sk_live_test123456789"],
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["routing_passed"] is True
    assert out["passed"] is True


def test_extract_document_types_from_structured_markers(ev):
    stdout = "[SKILL: uipath-persona-sa]\n[DOCUMENT_TYPE: ADD]\nAssistant: outline"
    assert ev.OutputParser.extract_document_types(stdout) == ["ADD"]


def test_document_type_required_fails_when_missing(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(document_types=[]),
        {
            "document_type_required": "ADD",
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["routing_passed"] is False
    assert out["passed"] is False
    assert any("Missing document type" in r for r in out["details"]["routing_failed"])


def test_routing_expected_is_informational_only(ev):
    evl = ev.TechnicalEvaluator(
        _parsed_base(),
        {
            "routing_expected": "Expect BA-style answer.",
            "crash_not_allowed": True,
        },
    )
    out = evl.evaluate()
    assert out["routing_passed"] is True
    assert any("routing_expected (informational)" in p for p in out["details"]["passed"])
