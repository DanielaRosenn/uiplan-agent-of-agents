"""Tests for the optional UIPATH_PLAN_GATE opt-in gate."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.tools import plan_tools
from mcp_server.tools.plan_tools import require_accepted_plan


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_tools, "_regen_plan_index", lambda r: {"skipped": True})
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    return tmp_path


class TestRequireAcceptedPlan:
    def test_gate_disabled_returns_allowed(self, repo, monkeypatch):
        monkeypatch.delenv("UIPATH_PLAN_GATE", raising=False)
        verdict = require_accepted_plan(str(repo))
        assert verdict["allowed"] is True
        assert verdict["enforced"] is False

    def test_gate_blocks_when_no_accepted_plan(self, repo, monkeypatch):
        monkeypatch.setenv("UIPATH_PLAN_GATE", "1")
        verdict = require_accepted_plan(str(repo))
        assert verdict["allowed"] is False
        assert verdict["reason"] == "no_accepted_plan"

    @pytest.mark.asyncio
    async def test_gate_unblocks_after_accept(self, repo, monkeypatch):
        monkeypatch.setenv("UIPATH_PLAN_GATE", "1")
        new_out = await plan_tools.call_plan_tool(
            "uipath_plan_new",
            {"project_root": str(repo), "title": "Gate Test", "intent": "Just a test"},
        )
        slug = new_out["slug"]
        await plan_tools.call_plan_tool(
            "uipath_plan_accept",
            {
                "project_root": str(repo),
                "slug": slug,
                "actor": "ci",
                "project_dir": str(repo),
            },
        )
        verdict = require_accepted_plan(str(repo))
        assert verdict["allowed"] is True
        assert verdict["enforced"] is True
        assert Path(verdict["plan"]).is_file()

    @pytest.mark.asyncio
    async def test_gate_rejects_plan_bound_to_other_project(self, repo, monkeypatch):
        monkeypatch.setenv("UIPATH_PLAN_GATE", "1")
        project_a = repo / "A"
        project_b = repo / "B"
        project_a.mkdir()
        project_b.mkdir()
        new_out = await plan_tools.call_plan_tool(
            "uipath_plan_new",
            {"project_root": str(repo), "title": "Gate Test", "intent": "Just a test"},
        )
        await plan_tools.call_plan_tool(
            "uipath_plan_accept",
            {
                "project_root": str(repo),
                "slug": new_out["slug"],
                "actor": "ci",
                "project_dir": str(project_a),
            },
        )
        verdict = require_accepted_plan(str(project_b))
        assert verdict["allowed"] is False
        assert verdict["reason"] == "no_accepted_plan"
        assert verdict["skipped"][0]["reason"] == "project_dir_mismatch"


class TestWorkflowHookWired:
    def test_helper_imports_and_defaults_allowed(self, monkeypatch):
        from mcp_server.tools.workflow_tools import _plan_gate_block_or_text

        monkeypatch.delenv("UIPATH_PLAN_GATE", raising=False)
        assert _plan_gate_block_or_text(None, "uipath_workflow_write_file") is None

    def test_helper_returns_blocked_when_gate_on(self, tmp_path, monkeypatch):
        from mcp_server.tools.workflow_tools import _plan_gate_block_or_text

        monkeypatch.setenv("UIPATH_PLAN_GATE", "1")
        msg = _plan_gate_block_or_text(str(tmp_path), "uipath_workflow_write_file")
        assert msg is not None
        assert msg.startswith("[BLOCKED]")
        assert "uipath_plan_accept" in msg

    def test_helper_fails_closed_when_gate_check_raises(self, tmp_path, monkeypatch):
        import mcp_server.tools.workflow_tools as workflow_tools

        monkeypatch.setenv("UIPATH_PLAN_GATE", "1")
        monkeypatch.setattr(
            plan_tools,
            "require_accepted_plan",
            lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        msg = workflow_tools._plan_gate_block_or_text(
            str(tmp_path), "uipath_workflow_write_file"
        )
        assert msg is not None
        assert msg.startswith("[BLOCKED]")
        assert "check failed" in msg
