"""Planner passthrough (reserved for multi-step plans)."""

from __future__ import annotations

from collections.abc import Callable


def make_plan_node() -> Callable[[dict], dict]:
    def plan_node(state: dict) -> dict:
        return {"phase": state.get("phase", "plan")}

    return plan_node
