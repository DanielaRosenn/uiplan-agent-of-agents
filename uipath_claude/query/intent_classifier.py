"""Classify free-form user input for chat routing (question vs build vs ambiguous)."""

from __future__ import annotations

import re
from enum import Enum


class IntentType(str, Enum):
    """High-level intent for a user message."""

    QUESTION = "question"
    BUILD = "build"
    AMBIGUOUS = "ambiguous"
    DOCUMENTATION = "documentation"


_QUESTION_PHRASES = (
    "what is ",
    "what are ",
    "how does ",
    "how do ",
    "explain ",
    "why ",
    "when should ",
    "can you tell me",
    "do you know",
)

_BUILD_PHRASES = (
    "create ",
    "build ",
    "make ",
    "generate ",
    "write ",
    "add ",
    "implement ",
    "scaffold ",
)

_DOC_PHRASES = (
    "create a pdd",
    "create pdd",
    "write a pdd",
    "create a sdd",
    "create sdd",
    "write a sdd",
    "create a tdd",
    "create tdd",
    "process definition document",
    "process definition",
    "solution design document",
    "technical design document",
    "agent design document",
    "help me document",
    "document this process",
    "document this automation",
    "need documentation",
    "create documentation",
    "write documentation",
)

_DOC_KEYWORDS = frozenset({
    "pdd",
    "sdd",
    "tdd",
})

_VAGUE_ONLY = frozenset(
    {
        "automate",
        "help",
        "something",
        "thing",
        "stuff",
        "this",
        "that",
        "it",
        "email",
        "data",
        "process",
    }
)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _is_vague(lower: str, user_tokens: set[str]) -> bool:
    """Heuristic: very short or only generic tokens with no concrete object."""
    stripped = lower.strip()
    if len(stripped) < 12:
        return True
    if len(user_tokens) <= 2 and user_tokens <= _VAGUE_ONLY:
        return True
    if "automate" in lower and len(user_tokens) <= 4:
        return "outlook" not in lower and "excel" not in lower and "browser" not in lower
    return False


def classify_intent(user_input: str) -> tuple[IntentType, str]:
    """
    Classify user intent.

    Returns:
        (IntentType, short reason code for logging/tests)
    """
    stripped = user_input.strip()
    if not stripped:
        return IntentType.AMBIGUOUS, "empty"

    lower = stripped.lower()
    user_tokens = _tokenize(stripped)

    has_doc = any(p in lower for p in _DOC_PHRASES)
    has_doc_keyword = bool(user_tokens & _DOC_KEYWORDS)

    if has_doc or has_doc_keyword:
        return IntentType.DOCUMENTATION, "doc_phrase"

    has_build = any(p in lower for p in _BUILD_PHRASES)
    has_question = any(p in lower for p in _QUESTION_PHRASES)

    if has_question and not has_build:
        return IntentType.QUESTION, "question_phrase"

    if has_build:
        if _is_vague(lower, user_tokens):
            return IntentType.AMBIGUOUS, "vague_build"
        return IntentType.BUILD, "build_phrase"

    if _is_vague(lower, user_tokens):
        return IntentType.AMBIGUOUS, "vague_request"

    return IntentType.BUILD, "default"
