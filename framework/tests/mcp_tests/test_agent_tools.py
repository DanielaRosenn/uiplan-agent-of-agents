"""MCP agent tools: dispatch with fakes (no Bedrock / no real bootstrap)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

import mcp_server.tools.agent_tools as ag
from mcp_server.tools.agent_tools import call_agent_tool, get_agent_tools


def test_agent_tool_registry():
    names = {t.name for t in get_agent_tools()}
    assert len(names) == 6


@pytest.mark.asyncio
async def test_unknown_raises():
    with pytest.raises(ValueError, match="Unknown agent tool"):
        await call_agent_tool("uipath_agent_nope", {})


@pytest.mark.asyncio
async def test_bootstrap_delegates(monkeypatch, tmp_path):
    async def fake_flow(req: str, output_root: Path):
        return {
            "paths": {"pdd": str(output_root / "pdd.md")},
            "pdd": "pdd " * 500,
            "sdd": "sdd " * 500,
            "code": "code " * 500,
            "validation": "val " * 500,
        }

    monkeypatch.setattr(ag, "run_bootstrap_flow", fake_flow)
    out = await call_agent_tool(
        "uipath_agent_bootstrap",
        {"user_request": "build invoice bot", "output_dir": str(tmp_path)},
    )
    assert "paths" in out
    assert "pdd_preview" in out
    assert len(out["pdd_preview"]) <= 2000


@pytest.mark.asyncio
async def test_plan_delegates(monkeypatch):
    @dataclass
    class _Res:
        success: bool
        final_response: str
        iterations: int
        tool_calls_made: list
        error: str | None

    async def fake_planner(*a, **k):
        return _Res(
            success=True,
            final_response="done",
            iterations=1,
            tool_calls_made=[],
            error=None,
        )

    monkeypatch.setattr(ag, "run_planner_agent", fake_planner)
    out = await call_agent_tool(
        "uipath_agent_plan",
        {"user_request": "add logging", "project_context": {"k": 1}},
    )
    assert out["success"] is True
    assert out["final_response"] == "done"


@pytest.mark.asyncio
async def test_execute_delegates(monkeypatch):
    @dataclass
    class _Exec:
        success: bool
        final_response: str
        iterations: int
        tool_calls_made: list
        files_written: list
        validation_status: str | None
        error: str | None

    class _Ex:
        async def execute(self, **kwargs):
            return _Exec(
                success=True,
                final_response="ok",
                iterations=2,
                tool_calls_made=["a"],
                files_written=[],
                validation_status=None,
                error=None,
            )

    monkeypatch.setattr(ag, "AgenticExecutor", lambda **kw: _Ex())
    monkeypatch.setattr(ag, "get_skill_execution_tools", lambda: [])

    class _Reg:
        def get_skill(self, name):
            return {"name": name, "path": "/x", "origin": "test"}

    import mcp_server.tools.skill_tools as sk

    monkeypatch.setattr(sk, "_get_registry", lambda: _Reg())
    monkeypatch.setattr(ag, "load_skill_content", lambda sk: "# skill")

    out = await call_agent_tool(
        "uipath_agent_execute",
        {"task": "run tests", "skill_name": "uipath-rpa", "max_iterations": 5},
    )
    assert out["success"] is True
    assert out["iterations"] == 2


@pytest.mark.asyncio
async def test_ba_delegates(monkeypatch):
    monkeypatch.setattr(
        "uipath_claude.query.engine_factory.create_conversation_engine_from_env",
        lambda: MagicMock(),
    )
    monkeypatch.setattr(
        "uipath_claude.query.agent_invoke.invoke_agent_llm",
        AsyncMock(return_value="# PDD\n\nBody"),
    )
    ba_inst = MagicMock()
    ba_inst.get_system_prompt.return_value = "sys"
    monkeypatch.setattr("uipath_claude.agents.ba.BAAgent", lambda: ba_inst)

    out = await call_agent_tool(
        "uipath_agent_ba",
        {"requirements": "need a queue consumer"},
    )
    assert "# PDD" in out["pdd"]


@pytest.mark.asyncio
async def test_sa_delegates(monkeypatch):
    monkeypatch.setattr(
        "uipath_claude.query.engine_factory.create_conversation_engine_from_env",
        lambda: MagicMock(),
    )
    monkeypatch.setattr(
        "uipath_claude.query.agent_invoke.invoke_agent_llm",
        AsyncMock(return_value="# SDD\n\nDesign"),
    )
    sa_inst = MagicMock()
    sa_inst.get_system_prompt.return_value = "sys"
    monkeypatch.setattr("uipath_claude.agents.sa.SAAgent", lambda: sa_inst)

    out = await call_agent_tool(
        "uipath_agent_sa",
        {"pdd": "# PDD\n\nMinimal"},
    )
    assert "# SDD" in out["sdd"]


@pytest.mark.asyncio
async def test_classify_intent_requires_input():
    with pytest.raises(KeyError):
        await call_agent_tool("uipath_agent_classify_intent", {})
