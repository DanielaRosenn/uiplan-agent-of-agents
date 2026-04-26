"""MCP and direct router share the same decision path when patched identically."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server.tools.assistant_tools import call_assistant_tool
from uipath_claude.query.orchestration_context import build_orchestration_context
from uipath_claude.query.orchestration_types import (
    ApprovalLevel,
    OrchestrationDecision,
    RouteKind,
)
import uipath_claude.query.orchestration_router as orchestration_router


@pytest.mark.asyncio
async def test_mcp_route_matches_direct_route(tmp_path) -> None:
    fixed = OrchestrationDecision(
        route=RouteKind.PLAN,
        confidence=0.88,
        rationale="User wants a plan",
        approval_level=ApprovalLevel.CONFIRM_ROUTE,
        question=None,
        suggested_command=None,
        next_action=None,
        selected_skills=["uiplan"],
    )

    async def _fake(*_a: object, **_kw: object) -> OrchestrationDecision:
        return fixed

    with (
        patch.object(
            orchestration_router,
            "route_user_request",
            new=_fake,
        ),
        patch(
            "mcp_server.tools.assistant_tools.route_user_request",
            new=_fake,
        ),
    ):
        ctx = build_orchestration_context("build a feature", project_root=tmp_path)
        direct = await orchestration_router.route_user_request(ctx)
        mcp_out = await call_assistant_tool(
            "uipath_assistant_route",
            {"request": "build a feature", "project_root": str(tmp_path)},
        )

    assert mcp_out["status"] == "ok"
    assert mcp_out["decision"] == direct.to_dict()
    assert mcp_out["decision"] == fixed.to_dict()
