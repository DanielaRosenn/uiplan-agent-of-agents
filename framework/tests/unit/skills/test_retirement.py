"""Retirement: prune low-confidence and consolidate near-duplicates."""
from __future__ import annotations

from uipath_claude.skills.insights import InsightType, SkillInsight, SkillInsightsFile
from uipath_claude.skills.retirement import retire


def _ins(content: str, success: int, fail: int) -> SkillInsight:
    return SkillInsight(
        skill_name="uipath-automation",
        insight_type=InsightType.FAILURE_PATTERN,
        content=content,
        success_count=success,
        failure_count=fail,
    )


def test_retire_drops_low_confidence_with_enough_samples() -> None:
    f = SkillInsightsFile(
        skill_name="uipath-automation",
        insights=[
            _ins("Noisy low confidence", 0, 5),
            _ins("Good rule", 5, 0),
        ],
    )
    out = retire(f, min_confidence=0.3, min_samples=3)
    contents = [i.content for i in out.insights]
    assert contents == ["Good rule"]
    assert out.stats.get("retired") == 1


def test_retire_keeps_low_sample_uncertain_entries() -> None:
    f = SkillInsightsFile(
        skill_name="uipath-automation",
        insights=[
            _ins("New uncertain rule", 0, 1),
        ],
    )
    out = retire(f, min_confidence=0.3, min_samples=3)
    assert len(out.insights) == 1


def test_retire_consolidates_exact_content_hash_duplicates() -> None:
    f = SkillInsightsFile(
        skill_name="uipath-automation",
        insights=[
            _ins("Use UseExcelFile scope before ForEachExcelRow", 2, 0),
            _ins("Use UseExcelFile scope before ForEachExcelRow", 1, 1),
        ],
    )
    out = retire(f, min_confidence=0.0, min_samples=1)
    assert len(out.insights) == 1
    merged = out.insights[0]
    assert merged.success_count == 3
    assert merged.failure_count == 1
    assert out.stats.get("consolidated") == 1
