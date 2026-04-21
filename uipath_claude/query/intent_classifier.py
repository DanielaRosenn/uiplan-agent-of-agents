"""Classify free-form user input for chat routing (question vs build vs ambiguous)."""

from __future__ import annotations

import re
from enum import Enum

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)


def _strip_urls(text: str) -> str:
    """Remove http(s) URLs so pasted links do not break question heuristics."""
    return _URL_RE.sub("", text).strip()


def _looks_interrogative(classification_text: str) -> bool:
    """True when the text ends with a question mark (after stripping URLs)."""
    t = classification_text.strip().rstrip(" \t.")
    if not t:
        return False
    return t.rstrip("!)").endswith("?")


class IntentType(str, Enum):
    """High-level intent for a user message."""

    QUESTION = "question"
    BUILD = "build"
    AMBIGUOUS = "ambiguous"
    DOCUMENTATION = "documentation"


_QUESTION_PHRASES = (
    "tell me about ",
    "tell me what ",
    "what's ",
    "what're ",
    "whats ",
    "who's ",
    "how's ",
    "where's ",
    "what is ",
    "what are ",
    "what ",
    "how does ",
    "how do ",
    "how can ",
    "how would ",
    "explain ",
    "why ",
    "when should ",
    "when ",
    "where ",
    "which ",
    "who ",
    "can you tell me",
    "do you know",
    "do we ",
    "does ",
    "did ",
    "is there ",
    "are there ",
    "is it ",
    "have we ",
    "has ",
    "should i ",
    "should we ",
)

_STATUS_QUESTION_PHRASES = (
    "did you create",
    "did you build",
    "did you make",
    "did you write",
    "did you generate",
    "did you add",
    "have you created",
    "have you built",
    "have you made",
    "have you written",
    "have you generated",
    "was the project created",
    "was the project built",
    "was it created",
    "was it built",
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


def _is_vague(lower: str, user_tokens: set[str], *, raw_stripped_len: int) -> bool:
    """Heuristic: very short or only generic tokens with no concrete object."""
    # Use raw (pre-URL-strip) length for the short-input gate so pasted links
    # do not suppress vague detection incorrectly.
    if raw_stripped_len < 12:
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

    classification_text = _strip_urls(stripped)
    lower = classification_text.lower()
    user_tokens = _tokenize(classification_text)

    has_doc_phrase = any(p in lower for p in _DOC_PHRASES)
    has_doc_keyword = bool(user_tokens & _DOC_KEYWORDS)
    has_build = any(p in lower for p in _BUILD_PHRASES)
    has_question = any(p in lower for p in _QUESTION_PHRASES)
    has_status_question = any(p in lower for p in _STATUS_QUESTION_PHRASES)

    has_capability = any(lower.startswith(p) for p in _CAPABILITY_OPENERS)
    ends_interrogative = _looks_interrogative(classification_text)
    has_imperative_chain = any(c in lower for c in _IMPERATIVE_CONJUNCTIONS)
    is_capability_question = (
        has_capability and ends_interrogative and not has_imperative_chain
    )

    # Status follow-ups ("did you create the project?") route to QUESTION even
    # when the sentence contains a build verb like "create".
    if has_status_question:
        return IntentType.QUESTION, "status_question"
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

    if ends_interrogative and not has_build:
        return IntentType.QUESTION, "interrogative_punctuation"

    if has_build:
        if _is_vague(lower, user_tokens, raw_stripped_len=len(stripped)):
            return IntentType.AMBIGUOUS, "vague_build"
        return IntentType.BUILD, "build_phrase"

    if _is_vague(lower, user_tokens, raw_stripped_len=len(stripped)):
        return IntentType.AMBIGUOUS, "vague_request"

    return IntentType.AMBIGUOUS, "default"
