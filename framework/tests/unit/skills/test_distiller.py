"""Distiller: LLM rewrite with offline fallback, never raises."""
from __future__ import annotations

from unittest.mock import patch

from uipath_claude.skills.distiller import distill
from uipath_claude.skills.insights import InsightType, SkillInsight


def _candidate() -> SkillInsight:
    return SkillInsight(
        skill_name="uipath-automation",
        insight_type=InsightType.FAILURE_PATTERN,
        content="tool 'write_file' failed: permission denied. Next time, verify preconditions.",
        source="auto",
        failure_count=1,
    )


def test_distill_returns_rewritten_text_when_llm_available() -> None:
    with patch(
        "uipath_claude.skills.distiller._invoke_llm",
        return_value="Ensure destination is writable before calling write_file.",
    ):
        out = distill(_candidate(), existing_top=[])
    assert out is not None
    assert out.content == "Ensure destination is writable before calling write_file."
    assert out.source == "auto+distilled"


def test_distill_falls_back_on_llm_failure() -> None:
    with patch("uipath_claude.skills.distiller._invoke_llm", side_effect=RuntimeError("offline")):
        out = distill(_candidate(), existing_top=[])
    assert out is not None
    assert out.content.startswith("tool 'write_file' failed")
    assert out.source == "auto"


def test_distill_drops_semantic_duplicate() -> None:
    existing = [_candidate()]
    with patch("uipath_claude.skills.distiller._invoke_llm", return_value="DUPLICATE"):
        out = distill(_candidate(), existing_top=existing)
    assert out is None
