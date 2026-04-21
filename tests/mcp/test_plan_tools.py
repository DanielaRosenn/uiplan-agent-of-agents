"""Tests for MCP plan tools (build + docs/plans CRUD)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.tools import plan_tools
from uipath_claude.query.agentic_executor import AgenticResult
from uipath_claude.skills.submodule_guard import GuardResult


def _sample_plan_md() -> str:
    return """---
slug: test-feature
title: Test Feature Plan
date: 2026-04-21
status: draft
owner: tester
project_type: mixed
linked_pdd: ""
supersedes: null
---

# Test

## Architecture

```mermaid
flowchart LR
  A[A]:::process --> B[B]:::process
  classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A
```
"""


class TestGetPlanTools:
    def test_includes_build_and_crud(self):
        tools = plan_tools.get_plan_tools()
        names = {t.name for t in tools}
        assert names == {
            "uipath_plan_build",
            "uipath_plan_save",
            "uipath_plan_list",
            "uipath_plan_read",
            "uipath_plan_status_set",
            "uipath_plan_render_mermaid",
        }


class TestCallPlanBuild:
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


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_tools, "_regen_plan_index", lambda r: {"skipped": True})
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    return tmp_path


class TestPlanCrud:
    @pytest.mark.asyncio
    async def test_save_list_read_roundtrip(self, repo):
        out = await plan_tools.call_plan_tool(
            "uipath_plan_save",
            {"project_root": str(repo), "content": _sample_plan_md()},
        )
        assert out["status"] == "ok"
        assert out["relative"].replace("\\", "/") == "docs/plans/2026-04-21-test-feature.md"

        listed = await plan_tools.call_plan_tool(
            "uipath_plan_list", {"project_root": str(repo)}
        )
        assert listed["status"] == "ok"
        assert len(listed["plans"]) == 1
        assert listed["plans"][0]["slug"] == "test-feature"

        read = await plan_tools.call_plan_tool(
            "uipath_plan_read",
            {
                "project_root": str(repo),
                "filename": "2026-04-21-test-feature.md",
            },
        )
        assert "test-feature" in read["content"]

    @pytest.mark.asyncio
    async def test_read_by_slug(self, repo):
        await plan_tools.call_plan_tool(
            "uipath_plan_save",
            {"project_root": str(repo), "content": _sample_plan_md()},
        )
        read = await plan_tools.call_plan_tool(
            "uipath_plan_read",
            {"project_root": str(repo), "slug": "test-feature"},
        )
        assert read["status"] == "ok"
        assert "```mermaid" in read["content"].lower()

    @pytest.mark.asyncio
    async def test_render_mermaid(self, repo):
        await plan_tools.call_plan_tool(
            "uipath_plan_save",
            {"project_root": str(repo), "content": _sample_plan_md()},
        )
        r = await plan_tools.call_plan_tool(
            "uipath_plan_render_mermaid",
            {"project_root": str(repo), "slug": "test-feature"},
        )
        assert r["status"] == "ok"
        assert r["count"] == 1
        assert "flowchart LR" in r["blocks"][0]

    @pytest.mark.asyncio
    async def test_save_rejects_without_mermaid(self, repo):
        bad = """---
slug: bad
title: Bad
date: 2026-04-21
status: draft
owner: x
project_type: mixed
---

# No diagram
"""
        with pytest.raises(ValueError, match="mermaid"):
            await plan_tools.call_plan_tool(
                "uipath_plan_save",
                {"project_root": str(repo), "content": bad},
            )

    @pytest.mark.asyncio
    async def test_status_set_done_blocked_without_design(self, repo, monkeypatch):
        monkeypatch.setenv("UIPATH_DESIGN_APPROVAL_ENABLED", "1")
        await plan_tools.call_plan_tool(
            "uipath_plan_save",
            {"project_root": str(repo), "content": _sample_plan_md()},
        )
        with patch.object(plan_tools.design_store, "has_approved", return_value=False):
            out = await plan_tools.call_plan_tool(
                "uipath_plan_status_set",
                {
                    "project_root": str(repo),
                    "slug": "test-feature",
                    "new_status": "done",
                    "project_dir": str(repo),
                },
            )
        assert out["status"] == "blocked"
        assert out["reason"] == "design_not_approved"

    @pytest.mark.asyncio
    async def test_status_set_done_ok_when_design_approved(self, repo, monkeypatch):
        monkeypatch.setenv("UIPATH_DESIGN_APPROVAL_ENABLED", "1")
        await plan_tools.call_plan_tool(
            "uipath_plan_save",
            {"project_root": str(repo), "content": _sample_plan_md()},
        )
        with patch.object(plan_tools.design_store, "has_approved", return_value=True):
            out = await plan_tools.call_plan_tool(
                "uipath_plan_status_set",
                {
                    "project_root": str(repo),
                    "filename": "2026-04-21-test-feature.md",
                    "new_status": "done",
                    "project_dir": str(repo),
                },
            )
        assert out["status"] == "ok"
        read = await plan_tools.call_plan_tool(
            "uipath_plan_read",
            {"project_root": str(repo), "slug": "test-feature"},
        )
        assert "status: done" in read["content"]

    @pytest.mark.asyncio
    async def test_status_in_progress_no_gate(self, repo):
        await plan_tools.call_plan_tool(
            "uipath_plan_save",
            {"project_root": str(repo), "content": _sample_plan_md()},
        )
        out = await plan_tools.call_plan_tool(
            "uipath_plan_status_set",
            {
                "project_root": str(repo),
                "slug": "test-feature",
                "new_status": "in-progress",
            },
        )
        assert out["status"] == "ok"


class TestGeneratePlanIndexScript:
    def test_regenerates_readme(self, tmp_path):
        plans = tmp_path / "docs" / "plans"
        plans.mkdir(parents=True)
        (plans / "2026-04-21-a.md").write_text(_sample_plan_md(), encoding="utf-8")
        readme = plans / "README.md"
        readme.write_text("stale", encoding="utf-8")
        script = tmp_path / "scripts" / "generate_plan_index.py"
        script.parent.mkdir(parents=True)
        repo_root = Path(plan_tools.__file__).resolve().parents[2]
        shutil.copyfile(
            repo_root / "scripts" / "generate_plan_index.py",
            script,
        )
        r = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0
        text = readme.read_text(encoding="utf-8")
        assert "test-feature" in text
        assert "2026-04-21-a.md" in text
