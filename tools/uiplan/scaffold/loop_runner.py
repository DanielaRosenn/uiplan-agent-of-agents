from __future__ import annotations

import os

_DEFAULT_LOOPS = 5
_MIN_LOOPS = 1
_MAX_LOOPS = 25

DEFAULT_GATE_NAMES = ["restore", "analyze", "test", "pack"]


def _parse_int_bounds(value: int, *, what: str) -> int:
    if value < _MIN_LOOPS or value > _MAX_LOOPS:
        raise ValueError(
            f"{what} must be between {_MIN_LOOPS} and {_MAX_LOOPS} inclusive, got {value!r}"
        )
    return value


def resolve_max_loops_from_env() -> int:
    """Resolve max loops using ``UIPLAN_MAX_LOOPS`` from the process environment."""
    return resolve_max_loops(flag_value=None, env_value=os.environ.get("UIPLAN_MAX_LOOPS"))


def resolve_max_loops(flag_value: int | None, env_value: str | None = None) -> int:
    """
    Effective max loops: CLI flag wins, else env int, else default 5.
    Values must be in 1..25 inclusive.
    """
    if flag_value is not None:
        return _parse_int_bounds(flag_value, what="max_loops")
    if env_value is None or env_value.strip() == "":
        return _DEFAULT_LOOPS
    try:
        parsed = int(env_value.strip(), 10)
    except ValueError as e:
        raise ValueError(
            f"UIPLAN_MAX_LOOPS must be an integer between {_MIN_LOOPS} and {_MAX_LOOPS}, "
            f"got {env_value!r}"
        ) from e
    return _parse_int_bounds(parsed, what="UIPLAN_MAX_LOOPS")


def run_gate_sequence(
    skill_executor,
    max_loops: int,
    *,
    gates: list[str] | None = None,
) -> dict:
    """
    Run up to ``max_loops`` iterations. Each iteration calls
    ``skill_executor(iteration=i, gates=...)`` with the standard gate list.

    Stops on first successful status (``status == "ok"``), non-recoverable failure, or loop exhaustion.
    """
    _parse_int_bounds(max_loops, what="max_loops")
    gate_list = list(DEFAULT_GATE_NAMES if gates is None else gates)
    last: dict = {}
    for iteration in range(1, max_loops + 1):
        last = skill_executor(iteration=iteration, gates=gate_list)
        status = last.get("status", "failed")
        if status == "ok":
            return {
                "status": "ok",
                "iteration": iteration,
                "result": last,
            }
        if not last.get("recoverable", False):
            return {
                "status": "failed",
                "iteration": iteration,
                "result": last,
                "reason": "non_recoverable",
            }
    return {
        "status": "failed",
        "iteration": max_loops,
        "result": last,
        "reason": "max_loops_exhausted",
    }
