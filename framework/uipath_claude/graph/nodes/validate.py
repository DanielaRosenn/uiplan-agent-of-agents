"""Post-generation validation hook (optional)."""

from __future__ import annotations

from typing import Any, Callable


def make_validate_node(
    validate_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def validate_node(state: dict[str, Any]) -> dict[str, Any]:
        if validate_fn:
            return validate_fn(state)
        return {"validation_errors": state.get("validation_errors") or []}

    return validate_node
