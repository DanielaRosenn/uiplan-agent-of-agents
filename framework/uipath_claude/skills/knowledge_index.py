"""Queryable index of authored skills plus learned lessons."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from uipath_claude.skills.lessons import load_for_skill


def _list_authored_skills(project_root: Path) -> list[str]:
    root = project_root / "skills"
    if not root.exists():
        return []
    return sorted(
        p.name for p in root.iterdir() if p.is_dir() and (p / "SKILL.md").exists()
    )


def build_index(project_root: Path, top_lessons: int = 3) -> dict[str, Any]:
    skills_out: list[dict[str, Any]] = []
    for name in _list_authored_skills(project_root):
        lessons = load_for_skill(name, project_root=project_root, limit=top_lessons, min_confidence=0.0)
        skills_out.append(
            {
                "name": name,
                "lessons": [
                    {
                        "content": r.insight.content,
                        "type": r.insight.insight_type.value,
                        "confidence": r.insight.confidence,
                    }
                    for r in lessons
                ],
            }
        )
    return {"skills": skills_out, "project_root": str(project_root)}
