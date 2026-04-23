"""Lesson retrieval + prompt-block rendering."""
from __future__ import annotations

from pathlib import Path

from uipath_claude.skills.insights import (
    InsightLayer,
    InsightType,
    SkillInsight,
    SkillInsightsStore,
)
from uipath_claude.skills.lessons import load_for_skill, render_lessons_block


def _seed(store: SkillInsightsStore, skill: str, content: str, sc: int, fc: int) -> None:
    insight = SkillInsight(
        skill_name=skill,
        insight_type=InsightType.FAILURE_PATTERN,
        content=content,
        success_count=sc,
        failure_count=fc,
    )
    store.append(insight, layer=InsightLayer.PROJECT)


def test_load_for_skill_filters_by_confidence(tmp_path: Path) -> None:
    store = SkillInsightsStore(project_root=tmp_path)
    _seed(store, "uipath-automation", "Always include Microsoft.Activities namespace", 4, 1)
    _seed(store, "uipath-automation", "Noisy guess", 0, 3)

    lessons = load_for_skill("uipath-automation", project_root=tmp_path, limit=5, min_confidence=0.6)
    texts = [l.content for l in lessons]
    assert "Always include Microsoft.Activities namespace" in texts
    assert "Noisy guess" not in texts


def test_render_lessons_block_produces_heading_and_bullets(tmp_path: Path) -> None:
    store = SkillInsightsStore(project_root=tmp_path)
    _seed(store, "uipath-automation", "Use UseExcelFile scope before ForEachExcelRow", 3, 0)

    lessons = load_for_skill("uipath-automation", project_root=tmp_path, min_confidence=0.0)
    block = render_lessons_block(lessons, project_root=tmp_path)
    assert block.startswith("## Past Lessons")
    assert "Use UseExcelFile scope" in block
    assert "(confidence" in block


def test_render_lessons_block_empty_returns_empty_string() -> None:
    assert render_lessons_block([]) == ""
