"""Tests for LLM orchestration router (no Bedrock)."""
from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from uipath_claude.query.orchestration_context import build_orchestration_context
from uipath_claude.query.orchestration_router import (
    decision_from_parsed,
    parse_orchestration_json,
    route_user_request,
)
from uipath_claude.query.orchestration_types import ApprovalLevel, OrchestrationContext, RouteKind


def test_decision_from_parsed_valid_json() -> None:
    data = {
        "route": "answer",
        "confidence": 0.9,
        "rationale": "Informational only.",
        "approval_level": "none",
        "question": None,
    }
    d = decision_from_parsed(data)
    assert d.route == RouteKind.ANSWER
    assert d.confidence == 0.9
    assert d.approval_level == ApprovalLevel.NONE


def test_malformed_json_falls_back_to_clarify() -> None:
    d = decision_from_parsed(None)
    assert d.route == RouteKind.CLARIFY
    assert d.question


def test_low_confidence_non_answer_becomes_clarify() -> None:
    data = {
        "route": "execute",
        "confidence": 0.2,
        "rationale": "unsure",
        "approval_level": "none",
        "question": None,
    }
    d = decision_from_parsed(data)
    assert d.route == RouteKind.CLARIFY
    assert d.question


def test_low_confidence_answer_kept() -> None:
    data = {
        "route": "answer",
        "confidence": 0.2,
        "rationale": "best guess",
        "approval_level": "none",
        "question": None,
    }
    d = decision_from_parsed(data)
    assert d.route == RouteKind.ANSWER


def test_allowed_routes_clamp() -> None:
    data = {
        "route": "execute",
        "confidence": 0.99,
        "rationale": "x",
        "approval_level": "none",
        "question": None,
    }
    d = decision_from_parsed(
        data, allowed_routes={RouteKind.ANSWER, RouteKind.CLARIFY}
    )
    assert d.route == RouteKind.CLARIFY


@pytest.mark.asyncio
async def test_route_user_request_uses_invoke_model() -> None:
    ctx = OrchestrationContext(
        user_request="hi",
        project_root="/tmp",
        tool_profile="all",
    )

    async def _fake_invoke(_messages: object) -> AIMessage:
        body = (
            '{"route": "clarify", "confidence": 0.8, "rationale": "need more", '
            '"approval_level": "none", "question": "Which project?"}'
        )
        return AIMessage(content=body)

    d = await route_user_request(ctx, invoke_model=_fake_invoke)
    assert d.route == RouteKind.CLARIFY
    assert "Which project" in (d.question or "")


def test_parse_orchestration_json_raw() -> None:
    text = (
        '{"route": "answer", "confidence": 1, "rationale": "ok", '
        '"approval_level": "none", "question": null}'
    )
    p = parse_orchestration_json(text)
    assert p and p.get("route") == "answer"
