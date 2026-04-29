"""Tests for the uipath_intent_* MCP tools."""
from __future__ import annotations

import asyncio

import pytest

from mcp_server.tools.intent_tools import (
    call_intent_tool,
    classify,
    get_intent_tools,
)


def test_tool_registered():
    names = {t.name for t in get_intent_tools()}
    assert "uipath_intent_classify" in names


def test_tool_description_meets_min_length():
    tools = get_intent_tools()
    for tool in tools:
        assert len(tool.description) >= 60
        assert "uipath" in tool.description.lower()


def test_build_request_routes_to_planner():
    payload = classify("Create a UiPath coded agent that summarises emails.")
    assert payload["intent"] == "build"
    assert payload["recommended_next_tool"] == "uipath_plan_build"
    # BUILD should not pre-pick a persona; planner owns that decision.
    assert payload["persona"] is None


def test_question_routes_to_answer_with_persona():
    payload = classify("How does REFramework handle retries?")
    assert payload["intent"] == "question"
    assert payload["recommended_next_tool"] == "uipath_answer"
    assert payload["persona"] == "sa"
    assert payload["persona_reason"] == "question_default"


def test_documentation_intent_defaults_to_sa_persona():
    payload = classify("Create a SDD for the RPC approval agent.")
    assert payload["intent"] == "documentation"
    assert payload["recommended_next_tool"] == "uipath_answer"
    assert payload["persona"] == "sa"
    assert payload.get("document_type") is None


def test_ambiguous_stays_ambiguous():
    payload = classify("help")
    assert payload["intent"] == "ambiguous"
    assert payload["recommended_next_tool"] == "uipath_intent_classify"


def test_library_hints_extracted():
    payload = classify("Explain when to use Action Center for HITL in Maestro.")
    hints = set(payload["library_hints"])
    assert "action center" in hints
    assert "hitl" in hints
    assert "maestro" in hints


def test_keyword_maps_to_specific_persona():
    payload = classify("What validation strategy should I use for this agent?")
    assert payload["intent"] == "question"
    assert payload["persona"] == "qa"
    assert payload["persona_reason"] == "quality/testing keyword"


def test_call_intent_tool_echoes_project_root():
    payload = asyncio.run(
        call_intent_tool(
            "uipath_intent_classify",
            {"text": "Build an email agent", "project_root": "/tmp/my-agent"},
        )
    )
    assert payload["intent"] == "build"
    assert payload["project_root"] == "/tmp/my-agent"


def test_call_intent_tool_rejects_unknown_name():
    with pytest.raises(ValueError):
        asyncio.run(call_intent_tool("uipath_intent_other", {"text": "hi"}))


def test_call_intent_tool_rejects_non_string_text():
    with pytest.raises(TypeError):
        asyncio.run(call_intent_tool("uipath_intent_classify", {"text": 42}))
