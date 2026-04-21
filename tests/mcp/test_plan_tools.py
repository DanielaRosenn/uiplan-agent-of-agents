"""Tests for uipath_plan_build MCP tool."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.tools import plan_tools
from uipath_claude.query.agentic_executor import AgenticResult
from uipath_claude.skills.submodule_guard import GuardResult


class TestGetPlanTools:
    def test_exposes_single_tool(self):
        tools = plan_tools.get_plan_tools()
        assert len(tools) == 1
        assert tools[0].name == "uipath_plan_build"
        schema = tools[0].inputSchema
        assert "user_request" in schema["properties"]
        assert schema["required"] == ["user_request"]


class TestCallPlanTool:
    @pytest.mark.asyncio
    async def test_rejects_unknown_tool(self):
        with pytest.raises(ValueError):
            await plan_tools.call_plan_tool("nope", {"user_request": "x"})

    @pytest.mark.asyncio
    async def test_rejects_empty_request(self):
        with pytest.raises(ValueError):
            await plan_tools.call_plan_tool("uipath_plan_build", {"user_request": ""})

    @pytest.mark.asyncio
    async def test_blocks_when_guard_fails(self):
        failed = GuardResult(ok=False, errors=["bad submodule"])
        planner = AsyncMock()

        with patch.object(plan_tools, "verify_guard", return_value=failed), \
             patch.object(plan_tools, "run_planner_agent_with_discovery", planner):
            out = await plan_tools.call_plan_tool(
                "uipath_plan_build", {"user_request": "build"}
            )

        assert out["status"] == "blocked"
        assert out["reason"] == "submodule_guard_failed"
        assert out["plan"] is None
        planner.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_runs_planner_when_guard_ok(self):
        ok = GuardResult(ok=True, checked=["skills/"])
        planner = AsyncMock(
            return_value=AgenticResult(success=True, final_response="PLAN")
        )

        with patch.object(plan_tools, "verify_guard", return_value=ok), \
             patch.object(plan_tools, "run_planner_agent_with_discovery", planner):
            out = await plan_tools.call_plan_tool(
                "uipath_plan_build",
                {"user_request": "build", "force_rediscover": True},
            )

        assert out["status"] == "ok"
        assert out["guard"]["ok"] is True
        assert out["plan"]["final_response"] == "PLAN"
        planner.assert_awaited_once()
        _, kwargs = planner.call_args
        assert kwargs["force_rediscover"] is True

    @pytest.mark.asyncio
    async def test_bypass_guard_skips_check(self):
        verifier = patch.object(plan_tools, "verify_guard").start()
        try:
            planner = AsyncMock(
                return_value=AgenticResult(success=True, final_response="P")
            )
            with patch.object(
                plan_tools, "run_planner_agent_with_discovery", planner
            ):
                out = await plan_tools.call_plan_tool(
                    "uipath_plan_build",
                    {"user_request": "build", "bypass_guard": True},
                )

            assert out["status"] == "ok"
            assert out["guard"] is None
            verifier.assert_not_called()
        finally:
            patch.stopall()
