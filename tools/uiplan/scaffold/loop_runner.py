"""Loop policy and skill-driven gate iteration for UiPlan scaffold."""

from __future__ import annotations

import os
from collections.abc import Callable

_DEFAULT_LOOPS = 5
_MIN_LOOPS = 1
_MAX_LOOPS = 25

# Gate ids passed to the skill executor each iteration (UiPlan bundle shape).
DEFAULT_GATES: list[str] = ["spec", "plan", "tasks", "constitution"]


def _parse_loop_int(raw: str, *, source: str) -> int:
    s = raw.strip()
    if not s:
        return _DEFAULT_LOOPS
    try:
        return int(s, 10)
    except ValueError as e:
        raise ValueError(
            f"{source}: expected integer, got {raw!r}"
        ) from e


def _enforce_bounds(value: int, *, source: str) -> int:
    if value < _MIN_LOOPS or value > _MAX_LOOPS:
        raise ValueError(
            f"{source}: max loops must be between {_MIN_LOOPS} and {_MAX_LOOPS} "
            f"(inclusive), got {value}"
        )
    return value


def resolve_max_loops_from_env() -> int:
    """Read ``UIPLAN_MAX_LOOPS`` from the environment; default 5 if unset or blank."""
    raw = os.environ.get("UIPLAN_MAX_LOOPS")
    if raw is None:
        return _DEFAULT_LOOPS
    return _parse_loop_int(raw, source="UIPLAN_MAX_LOOPS")


def resolve_max_loops(flag_value: int | None, env_value: str | None = None) -> int:
    """
    Resolve effective max loops: CLI flag wins, then explicit env string, then
    ``UIPLAN_MAX_LOOPS`` from the environment. Default 5. Result is always in 1..25.
    """
    if flag_value is not None:
        candidate = flag_value
        source = "--max-loops"
    elif env_value is not None:
        candidate = _parse_loop_int(env_value, source="UIPLAN_MAX_LOOPS")
        source = "UIPLAN_MAX_LOOPS"
    else:
        candidate = resolve_max_loops_from_env()
        source = "UIPLAN_MAX_LOOPS"

    return _enforce_bounds(candidate, source=source)


SkillExecutor = Callable[..., dict]


def run_gate_sequence(
    skill_executor: SkillExecutor,
    max_loops: int,
    *,
    gates: list[str] | None = None,
) -> dict:
    """
    For iteration ``i`` in ``1..max_loops``, call
    ``skill_executor(iteration=i, gates=<gates>)``.

    Stops early when the executor returns ``status == "ok"``. On unrecoverable
    failure, returns immediately. If loops exhaust without ok, returns failed.
    """
    gate_list = gates if gates is not None else DEFAULT_GATES
    last: dict = {}

    for i in range(1, max_loops + 1):
        last = skill_executor(iteration=i, gates=gate_list)
        status = last.get("status")
        if status == "ok":
            return {
                "status": "ok",
                "iteration": i,
                "last": last,
            }
        if not last.get("recoverable", False):
            return {
                "status": "failed",
                "iteration": i,
                "last": last,
            }

    return {
        "status": "failed",
        "iteration": max_loops,
        "last": last,
        "reason": "max_loops_exhausted",
    }
