"""Route ambiguous or multi-skill requests to the uipath-planner skill."""

from __future__ import annotations

import re
from typing import Final

PLANNER_SKILL_NAME: Final[str] = "uipath-planner"
PLANNER_CONFIDENCE_THRESHOLD: Final[int] = 70
# Match uipath_claude.cli.app._SKILL_SELECTION_MIN_SCORE: need some signal before planner.
PLANNER_LOW_SIGNAL_MIN: Final[int] = 2

_MULTI_SKILL_PHRASES: Final[tuple[str, ...]] = (
    "build and deploy",
    "create and deploy",
    "pack and publish",
    "publish and deploy",
    "build and publish",
    "then deploy",
    "then publish",
    "and deploy to",
    "and publish to",
    "deploy to orchestrator",
    "publish to orchestrator",
)

_EXPLORATION_PHRASES: Final[tuple[str, ...]] = (
    "what can i",
    "what should i",
    "help me",
    "recommend",
    "should i",
    "not sure",
    "don't know",
    "dont know",
    "which option",
    "how do i start",
    "what to build",
)

# When these appear, the user likely named a specialist domain; do not force planner
# only from generic exploration phrases.
_SPECIALIST_SURFACE_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "xaml",
        "workflow",
        "workflows",
        "excel",
        "outlook",
        "orchestrator",
        "coded",
        "csharp",
        "flow",
        "maestro",
        "pdd",
        "sdd",
        "connector",
        "servo",
        "queue",
        "smtp",
        "imap",
        "browser",
        "selector",
        "agent",
        "agents",
        "python",
        "langgraph",
        "integration",
    }
)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _matches_multi_skill(lower_input: str) -> bool:
    return any(phrase in lower_input for phrase in _MULTI_SKILL_PHRASES)


def _matches_exploration(lower_input: str) -> bool:
    return any(phrase in lower_input for phrase in _EXPLORATION_PHRASES)


def _has_specialist_surface(user_tokens: set[str]) -> bool:
    return bool(user_tokens & _SPECIALIST_SURFACE_TOKENS)


def should_use_planner(user_input: str, top_score: int) -> tuple[bool, str]:
    """Return whether the uipath-planner skill should run before specialists.

    top_score is the highest relevance score among all loaded skills for this turn
    (not only skills above the selection floor).
    """
    lower = user_input.lower()
    user_tokens = _tokenize(user_input)

    if _matches_multi_skill(lower):
        return True, "multi_skill"

    if _matches_exploration(lower) and not _has_specialist_surface(user_tokens):
        return True, "exploration"

    if (
        top_score < PLANNER_CONFIDENCE_THRESHOLD
        and top_score >= PLANNER_LOW_SIGNAL_MIN
        and not _has_specialist_surface(user_tokens)
    ):
        return True, "low_confidence"

    return False, "clear_request"


def get_planner_skill_name() -> str:
    return PLANNER_SKILL_NAME


def find_planner_skill(skills: list[dict]) -> dict | None:
    """Return the planner skill dict if present in the loaded skill list."""
    for skill in skills:
        if str(skill.get("name", "")).strip() == PLANNER_SKILL_NAME:
            return skill
    return None
