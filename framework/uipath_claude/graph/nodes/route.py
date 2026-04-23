"""Skill routing node."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


def make_route_node(
    select_skills_fn: Callable[[str], list[dict[str, Any]]],
) -> Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]:
    async def route_node(state: dict[str, Any]) -> dict[str, Any]:
        messages = list(state.get("messages") or [])
        if not messages:
            return {"messages": messages, "phase": "route", "selected_skill_names": []}
        last = messages[-1]
        if last.get("role") != "user":
            return {"messages": messages, "phase": "route", "selected_skill_names": []}
        user_input = str(last.get("content", ""))
        selected = select_skills_fn(user_input)
        names = [str(s.get("name", "")) for s in selected if s.get("name")]
        return {
            "messages": messages,
            "selected_skill_names": names,
            "phase": "execute",
        }

    return route_node
