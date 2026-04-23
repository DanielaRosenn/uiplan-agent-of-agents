"""Lesson retrieval, rendering, and failure proposals for closed-loop learning."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from uipath_claude.skills.insights import InsightType, SkillInsight, SkillInsightsStore

LESSONS_HEADING = "Past Lessons"


@dataclass
class RankedLesson:
    insight: SkillInsight
    rank: float

    @property
    def content(self) -> str:
        return self.insight.content


def _rank(insight: SkillInsight) -> float:
    return insight.confidence + min(insight.success_count, 10) * 0.001


def load_for_skill(
    skill_name: str,
    project_root: Path,
    limit: int = 5,
    min_confidence: float = 0.6,
) -> list[RankedLesson]:
    store = SkillInsightsStore(project_root=project_root)
    ranked = [
        RankedLesson(insight=i, rank=_rank(i))
        for i in store.iter_insights(skill_name)
        if i.confidence >= min_confidence
    ]
    ranked.sort(key=lambda r: r.rank, reverse=True)
    return ranked[:limit]


def resolve_doc_links(text: str, known_activities: list[str] | None = None) -> list[tuple[str, str]]:
    """Return ``(activity_name, uipath://doc URI)`` pairs found in ``text``."""
    if not text or not known_activities:
        return []
    hits: list[tuple[str, str]] = []
    for name in known_activities:
        if re.search(rf"\b{re.escape(name)}\b", text):
            hits.append((name, f"uipath://doc/activity/{name}"))
    return hits


def _load_memory_excerpt(project_root: Path, max_chars: int = 800) -> str:
    mem = project_root / "memory.md"
    if not mem.exists():
        return ""
    try:
        raw = mem.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return raw[:max_chars]


def render_lessons_block(
    lessons: Iterable[RankedLesson],
    *,
    project_root: Path | None = None,
    known_activities: list[str] | None = None,
) -> str:
    items = list(lessons)
    if not items:
        return ""
    lines = [f"## {LESSONS_HEADING}", ""]
    for r in items:
        kind = r.insight.insight_type.value
        lines.append(
            f"- [{kind}] {r.insight.content} (confidence {r.insight.confidence:.2f})"
        )
        if known_activities:
            for act, uri in resolve_doc_links(r.insight.content, known_activities):
                lines.append(f"  - Doc link: `{act}` → {uri}")
    if project_root:
        mem = _load_memory_excerpt(project_root)
        if mem:
            lines.extend(["", "### Project Memory", "", mem, ""])
    lines.append("")
    return "\n".join(lines)


def propose_from_failure(
    skill_name: str,
    user_request: str,
    failing_tool: str | None,
    error_message: str | None,
) -> SkillInsight:
    snippet_req = (user_request or "").strip().splitlines()[0][:160]
    err = (error_message or "unknown failure").strip().splitlines()[0][:200]
    content = (
        f"When handling '{snippet_req}', tool '{failing_tool or 'n/a'}' failed: {err}. "
        "Next time, verify preconditions before calling this tool."
    )
    return SkillInsight(
        skill_name=skill_name,
        insight_type=InsightType.FAILURE_PATTERN,
        content=content,
        context=snippet_req,
        source="auto",
        failure_count=1,
    )
