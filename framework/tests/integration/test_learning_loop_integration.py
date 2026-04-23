"""End-to-end integration test for the Hermes-style learning loop.

Pipeline under test (all real modules, no mocks):

    SkillExecutionContext (execution_hook)
        -> SkillUsageTracker.record_usage (usage_tracker)
            -> SkillInsightsStore.add_insight / update_insight_stats (insights)
    lessons.load_for_skill / render_lessons_block   (lessons)
    upstream_scan.take_snapshot / compute_diff       (upstream_scan)

A ``HOME`` override is required because ``SkillInsightsStore`` writes to
``~/.cursor/skill-insights/`` by default; the fixture redirects that to a
temp dir so the test is isolated.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from uipath_claude.skills import upstream_scan
from uipath_claude.skills.execution_hook import SkillExecutionHooks
from uipath_claude.skills.insights import (
    InsightLayer,
    InsightType,
    SkillInsightsStore,
)
from uipath_claude.skills.lessons import load_for_skill, render_lessons_block
from uipath_claude.skills.usage_tracker import (
    SkillUsageEvent,
    SkillUsageTracker,
    UsageTrackerConfig,
    create_usage_tracker,
)


@pytest.fixture
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    return tmp_path / "repo"


def _make_store(project_root: Path) -> SkillInsightsStore:
    project_root.mkdir(parents=True, exist_ok=True)
    return SkillInsightsStore(project_root=project_root)


class TestExecutionHookToInsights:
    def test_failure_is_captured_as_failure_pattern(self, project_root: Path):
        store = _make_store(project_root)
        tracker = SkillUsageTracker(store, UsageTrackerConfig())
        hooks = SkillExecutionHooks(project_root)
        hooks.tracker = tracker

        ctx = hooks.create_context("uipath-rpa")
        with ctx:
            ctx.add_tool_call()
            ctx.set_error("pack failed: solution.uipx not found")
            ctx.set_context("Packing a coded workflow")

        captured = ctx.captured_insight
        assert captured is not None
        assert captured.insight_type == InsightType.FAILURE_PATTERN
        assert "pack failed" in captured.content

        insights = list(store.iter_insights("uipath-rpa"))
        assert any(i.content_hash == captured.content_hash for i in insights)

    def test_complex_success_is_captured_as_edge_case(self, project_root: Path):
        store = _make_store(project_root)
        tracker = SkillUsageTracker(
            store,
            UsageTrackerConfig(complexity_threshold=5),
        )
        hooks = SkillExecutionHooks(project_root)
        hooks.tracker = tracker

        ctx = hooks.create_context("uipath-agents")
        with ctx:
            for _ in range(6):
                ctx.add_tool_call()
            ctx.set_context("Built a LangGraph agent with auth, pack, publish")

        captured = ctx.captured_insight
        assert captured is not None
        assert captured.insight_type == InsightType.EDGE_CASE

    def test_recovery_is_captured_as_success_pattern(self, project_root: Path):
        store = _make_store(project_root)
        tracker = SkillUsageTracker(store)
        hooks = SkillExecutionHooks(project_root)
        hooks.tracker = tracker

        fail_ctx = hooks.create_context("uipath-platform")
        with fail_ctx:
            fail_ctx.add_tool_call()
            fail_ctx.set_error("auth failed: no UIPATH_URL")

        ok_ctx = hooks.create_context("uipath-platform")
        with ok_ctx:
            ok_ctx.add_tool_call()
            ok_ctx.set_context("Re-ran after exporting UIPATH_URL")

        captured = ok_ctx.captured_insight
        assert captured is not None
        assert captured.insight_type == InsightType.SUCCESS_PATTERN


class TestLessonsRendering:
    def test_load_and_render_surfaces_high_confidence_insights(
        self, project_root: Path
    ):
        store = _make_store(project_root)
        tracker = SkillUsageTracker(store, UsageTrackerConfig(min_confidence=0.0))

        tracker.record_usage(
            SkillUsageEvent(
                skill_name="uipath-rpa",
                started_at="t0",
                ended_at="t1",
                success=True,
                tool_calls=6,
                context_summary="Invoke a coded workflow after REFramework init",
            )
        )

        insights = list(store.iter_insights("uipath-rpa"))
        assert insights, "expected at least one captured insight"
        target = insights[0]
        store.update_insight_stats(
            "uipath-rpa",
            target.content_hash,
            success=True,
            layer=InsightLayer.USER,
        )
        store.update_insight_stats(
            "uipath-rpa",
            target.content_hash,
            success=True,
            layer=InsightLayer.USER,
        )

        lessons = load_for_skill(
            "uipath-rpa",
            project_root=project_root,
            limit=5,
            min_confidence=0.6,
        )
        assert lessons, "high-confidence lessons should survive the filter"

        block = render_lessons_block(lessons, project_root=project_root)
        assert "Past Lessons" in block
        assert "confidence" in block


class TestUpstreamScan:
    def test_snapshot_and_diff_detects_added_skill(self, tmp_path: Path):
        skills_root = tmp_path / "skills"
        (skills_root / "skills" / "uipath-rpa").mkdir(parents=True)
        (skills_root / "skills" / "uipath-rpa" / "SKILL.md").write_text(
            "---\nname: uipath-rpa\n---", encoding="utf-8"
        )
        (skills_root / ".git").mkdir()

        snap_v1 = upstream_scan.take_snapshot(skills_root=skills_root)
        assert "uipath-rpa" in snap_v1.skills

        (skills_root / "skills" / "uipath-agents").mkdir(parents=True)
        (skills_root / "skills" / "uipath-agents" / "SKILL.md").write_text(
            "---\nname: uipath-agents\n---", encoding="utf-8"
        )
        snap_v2 = upstream_scan.take_snapshot(skills_root=skills_root)

        diff = upstream_scan.compute_diff(snap_v1, snap_v2)
        assert "uipath-agents" in diff.new_skills
        assert "uipath-rpa" not in diff.new_skills


class TestFullLoopSmoke:
    """Walk the whole pipeline once to prove wiring is unchanged."""

    def test_hook_then_tracker_then_store_then_lessons(self, project_root: Path):
        store = _make_store(project_root)
        tracker = SkillUsageTracker(store)
        hooks = SkillExecutionHooks(project_root)
        hooks.tracker = tracker

        ctx = hooks.create_context("uipath-case-management")
        with ctx:
            ctx.add_tool_call()
            ctx.set_error("caseplan.json: invalid JSON")
            ctx.set_context("uip case build after edit")

        assert ctx.captured_insight is not None
        first_hash = ctx.captured_insight.content_hash

        store.update_insight_stats(
            "uipath-case-management",
            first_hash,
            success=True,
            layer=InsightLayer.USER,
        )

        lessons = load_for_skill(
            "uipath-case-management",
            project_root=project_root,
            limit=3,
            min_confidence=0.0,
        )
        assert any(
            lesson.insight.content_hash == first_hash for lesson in lessons
        )

    def test_create_usage_tracker_default_wiring(self, project_root: Path):
        project_root.mkdir(parents=True, exist_ok=True)
        tracker = create_usage_tracker(project_root)
        assert isinstance(tracker, SkillUsageTracker)
        assert tracker.insights_store.project_root == project_root
