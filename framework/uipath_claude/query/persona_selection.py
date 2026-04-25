"""Lightweight persona selection for read-only UiPath Q&A."""

from __future__ import annotations

from uipath_claude.query.intent_classifier import IntentType


_PERSONA_KEYWORDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "ba",
        "business/process keyword",
        ("requirement", "stakeholder", "process map", "business process", "interview", "pdd"),
    ),
    (
        "add",
        "agent design keyword",
        ("agent design", "add doc", "agent design doc", "agent design document"),
    ),
    (
        "tdd",
        "technical design keyword",
        ("tdd", "technical design", "technical design document"),
    ),
    (
        "qa",
        "quality/testing keyword",
        ("test", "testing", "validation", "regression", "acceptance", "verify"),
    ),
    (
        "developer",
        "implementation/tooling keyword",
        ("implement", "implementation", "code", "bug", "refactor", "cli", "tooling", "xaml"),
    ),
    (
        "sa",
        "architecture/design keyword",
        ("architecture", "architect", "design", "trade-off", "tradeoff", "pattern", "sdd"),
    ),
)


def select_persona_for_text(text: str, intent: IntentType) -> tuple[str | None, str | None]:
    """Return ``(persona, reason)`` for read-only Q&A/documentation routing.

    BUILD intent deliberately returns ``None`` because the planner owns
    multi-persona build orchestration.
    """
    if intent == IntentType.BUILD:
        return None, "build_intent_uses_planner"

    lower = (text or "").lower()
    for persona, reason, keywords in _PERSONA_KEYWORDS:
        if any(keyword in lower for keyword in keywords):
            return persona, reason

    if intent == IntentType.DOCUMENTATION:
        return "sa", "documentation_default"
    if intent == IntentType.QUESTION:
        return "sa", "question_default"
    return None, None
