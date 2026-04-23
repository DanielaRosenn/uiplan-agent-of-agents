"""knowledge_index.build_index returns authored skills + top lessons."""
from __future__ import annotations

from pathlib import Path

from uipath_claude.skills.insights import InsightLayer, InsightType, SkillInsight, SkillInsightsStore
from uipath_claude.skills.knowledge_index import build_index


def _write_skill(root: Path, name: str, body: str = "skill body") -> None:
    d = root / "skills" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(body, encoding="utf-8")


def test_index_includes_authored_skills_and_top_lessons(tmp_path: Path) -> None:
    _write_skill(tmp_path, "uipath-automation")
    store = SkillInsightsStore(project_root=tmp_path)
    store.append(
        SkillInsight(
            skill_name="uipath-automation",
            insight_type=InsightType.GOTCHA,
            content="Use UseExcelFile scope before ForEachExcelRow",
            success_count=3,
        ),
        layer=InsightLayer.PROJECT,
    )

    index = build_index(project_root=tmp_path, top_lessons=3)
    names = [s["name"] for s in index["skills"]]
    assert "uipath-automation" in names

    entry = next(s for s in index["skills"] if s["name"] == "uipath-automation")
    assert entry["lessons"], "expected at least one lesson"
    assert entry["lessons"][0]["content"].startswith("Use UseExcelFile")
