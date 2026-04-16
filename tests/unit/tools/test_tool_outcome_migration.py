"""Skill execution tools return ``[OK]`` / ``[ERROR]`` prefixed strings."""
from __future__ import annotations

import inspect

import uipath_claude.tools.skill_execution_tools as st


def test_all_tools_return_prefixed_strings() -> None:
    offenders: list[str] = []
    for name, obj in inspect.getmembers(st):
        if not callable(obj):
            continue
        if getattr(obj, "__module__", None) != st.__name__:
            continue
        if not name.startswith(
            ("read_", "write_", "list_", "ensure_", "validate_", "run_", "debug_", "deploy_", "install_")
        ):
            continue
        src = inspect.getsource(obj)
        if "[OK]" not in src and "[ERROR]" not in src and "ToolOutcome" not in src and "_tool(" not in src:
            offenders.append(name)
    assert not offenders, f"Tools missing structured outcome: {offenders}"
