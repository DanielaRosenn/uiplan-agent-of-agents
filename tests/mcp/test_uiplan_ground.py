"""Tests for uipath_plan_ground."""
from __future__ import annotations

import pytest

from mcp_server.tools import plan_tools


@pytest.mark.asyncio
async def test_plan_ground_returns_pack(tmp_path):
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    out = await plan_tools.call_plan_tool(
        "uipath_plan_ground",
        {"project_root": str(tmp_path), "topic": "orchestrator queues and Action Center"},
    )
    assert out.get("status") == "ok"
    assert "matched_skills" in out
    assert "library_hits" in out
    assert "constitution" in out
    assert "candidate_project_template" in out
