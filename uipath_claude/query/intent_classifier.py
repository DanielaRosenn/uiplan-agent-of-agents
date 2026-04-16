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

_CAPABILITY_OPENERS = (
    "can you ",
    "could you ",
    "would you ",
    "will you ",
    "do you ",
    "are you able to ",
    "is it possible to ",
    "how would you ",
)

_IMPERATIVE_CONJUNCTIONS = (
    " and build ",
    " and create ",
    " and make ",
    " and generate ",
    " and write ",
    " and implement ",
    " and scaffold ",
    " then build ",
    " then create ",
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

    has_doc_phrase = any(p in lower for p in _DOC_PHRASES)
    has_doc_keyword = bool(user_tokens & _DOC_KEYWORDS)
    has_build = any(p in lower for p in _BUILD_PHRASES)
    has_question = any(p in lower for p in _QUESTION_PHRASES)

    has_capability = any(lower.startswith(p) for p in _CAPABILITY_OPENERS)
    ends_interrogative = stripped.endswith("?")
    has_imperative_chain = any(c in lower for c in _IMPERATIVE_CONJUNCTIONS)
    is_capability_question = (
        has_capability and ends_interrogative and not has_imperative_chain
    )

    # Explicit doc phrases ("create a sdd", etc.) always route to documentation.
    if has_doc_phrase:
        return IntentType.DOCUMENTATION, "doc_phrase"
    # Yes/no capability questions ("can you help me build X if ...?") use QA path.
    if is_capability_question:
        return IntentType.QUESTION, "capability_question"
    # Questions ("what is an sdd?") beat bare doc-keyword routing.
    if has_question and not has_build:
        return IntentType.QUESTION, "question_phrase"
    # Bare doc keywords ("sdd", "pdd") alone route to documentation, unless the user
    # also asks to build/implement (e.g. "read an sdd and build a project").
    if has_doc_keyword and not has_build:
        return IntentType.DOCUMENTATION, "doc_keyword"

    if has_build:
        if _is_vague(lower, user_tokens):
            return IntentType.AMBIGUOUS, "vague_build"
        return IntentType.BUILD, "build_phrase"

    if _is_vague(lower, user_tokens):
        return IntentType.AMBIGUOUS, "vague_request"

    return IntentType.BUILD, "default"
