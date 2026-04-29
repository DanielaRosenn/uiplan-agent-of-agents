"""Lightweight persona selection for read-only UiPath Q&A."""

from __future__ import annotations

import re

from uipath_claude.query.intent_classifier import IntentType


_PERSONA_KEYWORDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "ba",
        "business/process keyword",
        (
            "requirement",
            "stakeholder",
            "process map",
            "business process",
            "interview",
            "pdd",
        ),
    ),
    (
        "qa",
        "quality/testing keyword",
        (
            "test",
            "testing",
            "validation",
            "regression",
            "acceptance",
            "verify",
        ),
    ),
    (
        "developer",
        "implementation/tooling keyword",
        (
            "implement",
            "implementation",
            "code",
            "bug",
            "refactor",
            "cli",
            "tooling",
            "xaml",
        ),
    ),
    (
        "sa",
        "architecture/design keyword",
        (
            "architecture",
            "architect",
            "design",
            "trade-off",
            "tradeoff",
            "pattern",
            "sdd",
        ),
    ),
)


def detect_document_type_for_prompt(text: str) -> str | None:
    """Return ``ADD``, ``TDD``, or ``None`` for document-output hints in user text."""
    doc_type, _ = _detect_document_type(text)
    return doc_type


def _detect_document_type(text: str) -> tuple[str | None, str | None]:
    """Return (document_type, reason) for ADD/TDD-style prompts, or (None, None).

    ADD and TDD are document outputs routed through the Solution Architect persona,
    not standalone personas.
    """
    lower = (text or "").lower()

    add_kw = (
        "agent design",
        "add doc",
        "agent design doc",
        "agent design document",
    )
    if any(k in lower for k in add_kw):
        return "ADD", "agent_design_document"

    if "technical design document" in lower:
        return "TDD", "technical_design_document"
    if "technical design" in lower:
        return "TDD", "technical_design_document"
    if re.search(r"\btdd\b", lower):
        return "TDD", "technical_design_document"

    return None, None


def select_persona_for_text(
    text: str, intent: IntentType
) -> tuple[str | None, str | None, str | None]:
    """Return ``(persona, reason, document_type)`` for read-only Q&A/documentation routing.

    ``document_type`` is ``\"ADD\"``, ``\"TDD\"``, or ``None``. When non-None, the
    persona is always ``sa`` and the runtime uses ADD/TDD prompt templates under the
    Solution Architect role.

    BUILD intent deliberately returns ``(None, \"build_intent_uses_planner\", None)``
    because the planner owns multi-persona build orchestration.
    """
    if intent == IntentType.BUILD:
        return None, "build_intent_uses_planner", None

    doc_type, doc_reason = _detect_document_type(text)
    if doc_type is not None:
        return "sa", doc_reason, doc_type

    lower = (text or "").lower()
    for persona, reason, keywords in _PERSONA_KEYWORDS:
        if any(keyword in lower for keyword in keywords):
            return persona, reason, None

    if intent == IntentType.DOCUMENTATION:
        return "sa", "documentation_default", None
    if intent == IntentType.QUESTION:
        return "sa", "question_default", None
    return None, None, None
