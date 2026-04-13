"""Capability checks for request handling."""

import re

_ACTION_TOKENS = {
    "analyze",
    "automate",
    "build",
    "create",
    "draft",
    "explain",
    "fix",
    "generate",
    "implement",
    "summarize",
    "update",
    "validate",
    "write",
}

_DOMAIN_TOKENS = {
    "automation",
    "excel",
    "mail",
    "outlook",
    "process",
    "project",
    "queue",
    "uipath",
    "workflow",
    "xaml",
}

_VAGUE_TOKENS = {"assist", "guidance", "help", "support"}
_VAGUE_REFERENCES = {"it", "something", "stuff", "that", "this"}
_GREETING_TOKENS = {"hello", "hey", "hi", "thanks", "thank", "yo"}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def needs_clarification(user_input: str) -> bool:
    """Return True when the request is too vague for reliable generation."""
    tokens = _tokenize(user_input.strip())
    if not tokens:
        return False
    if tokens <= _GREETING_TOKENS:
        return False

    has_domain = bool(tokens & _DOMAIN_TOKENS)
    has_action = bool(tokens & _ACTION_TOKENS)
    has_vague_prompt = bool(tokens & _VAGUE_TOKENS)
    has_vague_reference = bool(tokens & _VAGUE_REFERENCES)

    if has_vague_prompt and (has_vague_reference or not has_action):
        return True

    if has_domain and has_vague_prompt and not has_action:
        return True

    return False

