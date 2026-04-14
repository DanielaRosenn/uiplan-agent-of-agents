"""Human-in-the-loop bookkeeping (state only; CLI handles prompts)."""

from __future__ import annotations

from collections.abc import Callable


def make_feedback_node() -> Callable[[dict], dict]:
    def feedback_node(state: dict) -> dict:
        return {"phase": "feedback", "pending_question": state.get("pending_question")}

    return feedback_node
