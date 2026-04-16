"""Prune and consolidate entries in a :class:`SkillInsightsFile`."""
from __future__ import annotations

from uipath_claude.skills.insights import SkillInsight, SkillInsightsFile


def retire(
    data: SkillInsightsFile,
    min_confidence: float = 0.3,
    min_samples: int = 3,
) -> SkillInsightsFile:
    """Drop low-confidence rows with enough samples; merge identical ``content_hash``."""
    merged_by_hash: dict[str, SkillInsight] = {}
    consolidated = 0
    for i in data.insights:
        key = i.content_hash
        if key in merged_by_hash:
            prev = merged_by_hash[key]
            prev.success_count += i.success_count
            prev.failure_count += i.failure_count
            consolidated += 1
        else:
            merged_by_hash[key] = SkillInsight(
                skill_name=i.skill_name,
                insight_type=i.insight_type,
                content=i.content,
                context=i.context,
                created_at=i.created_at,
                source=i.source,
                success_count=i.success_count,
                failure_count=i.failure_count,
            )

    kept: list[SkillInsight] = []
    retired = 0
    for i in merged_by_hash.values():
        total = i.success_count + i.failure_count
        if total >= min_samples and i.confidence < min_confidence:
            retired += 1
            continue
        kept.append(i)

    stats = dict(data.stats or {})
    stats["retired"] = stats.get("retired", 0) + retired
    stats["consolidated"] = stats.get("consolidated", 0) + consolidated

    return SkillInsightsFile(skill_name=data.skill_name, insights=kept, stats=stats)
