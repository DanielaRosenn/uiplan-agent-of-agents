"""Canonical representation of the approved implementation plan block.

Keeping the heading and builder in one place avoids string drift between
the CLI (which injects the block into ``runtime_extra``) and the executor
(which detects it to enforce tool usage).
"""

from __future__ import annotations

PLAN_BLOCK_HEADING = "Approved Implementation Plan"


def build_plan_block(plan_text: str) -> str:
    """Return markdown that embeds ``plan_text`` under the standard plan heading."""
    plan_text = (plan_text or "").strip()
    return f"## {PLAN_BLOCK_HEADING}\n\n{plan_text}\n"


def contains_plan_block(text: str | None) -> bool:
    """True if ``text`` includes the canonical plan heading (any format)."""
    return bool(text) and PLAN_BLOCK_HEADING in text
