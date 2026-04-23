"""Tests for discovery-fronted planner entry point."""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uipath_claude.query import planner as planner_mod
from uipath_claude.query.agentic_executor import AgenticResult


def _make_result(text: str = "PLAN") -> AgenticResult:
    return AgenticResult(success=True, final_response=text)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    agent_dir = tmp_path / "skills" / "agents"
    agent_dir.mkdir(parents=True)
    (agent_dir / "uipath-project-discovery-agent.md").write_text(
        "# discovery agent body", encoding="utf-8"
    )
    return tmp_path


class TestFreshness:
    def test_missing_context_is_not_fresh(self, tmp_path: Path):
        assert not planner_mod._existing_context_is_fresh(
            tmp_path / "missing.md", max_age_seconds=60
        )

    def test_recent_context_is_fresh(self, tmp_path: Path):
        path = tmp_path / "ctx.md"
        path.write_text("x", encoding="utf-8")
        assert planner_mod._existing_context_is_fresh(path, max_age_seconds=60)

    def test_stale_context_is_not_fresh(self, tmp_path: Path):
        path = tmp_path / "ctx.md"
        path.write_text("x", encoding="utf-8")
        old = time.time() - 10_000
        import os as _os

        _os.utime(path, (old, old))
        assert not planner_mod._existing_context_is_fresh(
            path, max_age_seconds=60
        )


class TestRunPlannerAgentWithDiscovery:
    @pytest.mark.asyncio
    async def test_runs_discovery_when_no_context(self, project: Path):
        discovery = AsyncMock(return_value="DISCOVERY_DOC")
        planner = AsyncMock(return_value=_make_result())

        with patch.object(planner_mod, "_run_discovery_agent", discovery), \
             patch.object(planner_mod, "run_planner_agent", planner):
            result = await planner_mod.run_planner_agent_with_discovery(
                "build an invoice agent", repo_root=project
            )

        assert result.success
        discovery.assert_awaited_once()
        planner.assert_awaited_once()
        ctx_path = project / planner_mod.PROJECT_CONTEXT_RELATIVE
        assert ctx_path.exists()
        assert ctx_path.read_text(encoding="utf-8") == "DISCOVERY_DOC"

        _, kwargs = planner.call_args
        assert kwargs["project_context"]["discovery_document"] == "DISCOVERY_DOC"
        assert kwargs["project_context"]["discovery_source"] == str(ctx_path)

    @pytest.mark.asyncio
    async def test_reuses_fresh_context(self, project: Path):
        ctx_path = project / planner_mod.PROJECT_CONTEXT_RELATIVE
        ctx_path.parent.mkdir(parents=True, exist_ok=True)
        ctx_path.write_text("CACHED_DOC", encoding="utf-8")

        discovery = AsyncMock(return_value="NEW_DOC")
        planner = AsyncMock(return_value=_make_result())

        with patch.object(planner_mod, "_run_discovery_agent", discovery), \
             patch.object(planner_mod, "run_planner_agent", planner):
            await planner_mod.run_planner_agent_with_discovery(
                "build something", repo_root=project
            )

        discovery.assert_not_awaited()
        _, kwargs = planner.call_args
        assert kwargs["project_context"]["discovery_document"] == "CACHED_DOC"

    @pytest.mark.asyncio
    async def test_force_rediscover_overrides_cache(self, project: Path):
        ctx_path = project / planner_mod.PROJECT_CONTEXT_RELATIVE
        ctx_path.parent.mkdir(parents=True, exist_ok=True)
        ctx_path.write_text("CACHED_DOC", encoding="utf-8")

        discovery = AsyncMock(return_value="FRESH_DOC")
        planner = AsyncMock(return_value=_make_result())

        with patch.object(planner_mod, "_run_discovery_agent", discovery), \
             patch.object(planner_mod, "run_planner_agent", planner):
            await planner_mod.run_planner_agent_with_discovery(
                "build something", repo_root=project, force_rediscover=True
            )

        discovery.assert_awaited_once()
        assert ctx_path.read_text(encoding="utf-8") == "FRESH_DOC"

    @pytest.mark.asyncio
    async def test_missing_discovery_agent_raises(self, tmp_path: Path):
        (tmp_path / ".git").mkdir()
        with pytest.raises(FileNotFoundError):
            await planner_mod._run_discovery_agent(
                "hi", repo_root=tmp_path
            )

    @pytest.mark.asyncio
    async def test_run_discovery_agent_uses_executor(self, project: Path):
        exe = MagicMock()
        exe.execute = AsyncMock(return_value=_make_result("DOC_BODY"))

        out = await planner_mod._run_discovery_agent(
            "req", repo_root=project, executor=exe
        )
        assert out == "DOC_BODY"
        exe.execute.assert_awaited_once()
        _, kwargs = exe.execute.call_args
        assert kwargs["skill_name"] == "uipath-project-discovery-agent"
        assert "# discovery agent body" in kwargs["skill_content"]
