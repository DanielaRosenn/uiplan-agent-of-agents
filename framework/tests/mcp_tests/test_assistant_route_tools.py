"""MCP uipath_assistant_* tools."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server.tools.assistant_tools import call_assistant_tool
from uipath_claude.query.orchestration_types import (
    ApprovalLevel,
    OrchestrationDecision,
    RouteKind,
)
import uipath_claude.query.orchestration_router as orchestration_router


@pytest.mark.asyncio
async def test_assistant_context_read_only_includes_grounding(tmp_path) -> None:
    with patch(
        "uipath_claude.query.orchestration_context.build_grounding_pack",
        return_value={
            "status": "ok",
            "topic": "queues",
            "source_documents": [
                {"path": "docs/x.md", "name": "x", "kind": "other", "excerpt": "abc"}
            ],
        },
    ):
        out = await call_assistant_tool(
            "uipath_assistant_context",
            {"request": "read docs/x.md", "project_root": str(tmp_path)},
        )
    assert out["status"] == "ok"
    ctx = out["context"]
    g = ctx.get("grounding_pack") or {}
    sdocs = g.get("source_documents") or []
    assert sdocs and sdocs[0].get("path") == "docs/x.md"


@pytest.mark.asyncio
async def test_assistant_route_returns_decision(tmp_path) -> None:
    want = OrchestrationDecision(
        route=RouteKind.ANSWER,
        confidence=0.95,
        rationale="Q&A",
        approval_level=ApprovalLevel.NONE,
    )

    async def _fake(*_a: object, **_kw: object) -> OrchestrationDecision:
        return want

    with patch.object(orchestration_router, "route_user_request", new=_fake), patch(
        "mcp_server.tools.assistant_tools.route_user_request",
        new=_fake,
    ), patch(
        "uipath_claude.query.orchestration_context.build_grounding_pack",
        return_value={"status": "ok", "topic": "q"},
    ):
        out = await call_assistant_tool(
            "uipath_assistant_route",
            {"request": "can we use uiplan?", "project_root": str(tmp_path)},
        )
    assert out["status"] == "ok"
    assert out["decision"] == want.to_dict()
    assert out["decision"]["route"] == "answer"
    assert out["decision"]["confidence"] >= 0.9
