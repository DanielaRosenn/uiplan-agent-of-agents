"""Tests for the /pdd slash command."""
from __future__ import annotations

from typing import Any

from uipath_claude.commands.pdd import register_pdd_command
from uipath_claude.commands.registry import CommandRegistry


def _make_registry(captured: dict[str, Any], result: dict[str, Any]):
    async def fake_lifecycle(request: str, **kwargs: Any) -> dict[str, Any]:
        captured["request"] = request
        captured.update(kwargs)
        return result

    registry = CommandRegistry()
    register_pdd_command(registry, run_lifecycle=fake_lifecycle)
    return registry


def test_pdd_command_usage_when_no_request():
    registry = _make_registry({}, {"status": "ok", "stages": {}, "paths": {}})
    out = registry.execute("pdd")
    assert "usage: /pdd" in out.lower()


def test_pdd_command_dispatches_with_defaults():
    captured: dict[str, Any] = {}
    result = {
        "status": "ok",
        "stages": {
            "pdd": {"status": "ok", "length": 12},
            "deploy": {"status": "skipped", "reason": "deploy=False"},
        },
        "paths": {"pdd": "/tmp/pdd.md"},
    }
    registry = _make_registry(captured, result)

    out = registry.execute("pdd", "build", "invoice", "processor")

    assert captured["request"] == "build invoice processor"
    assert captured["project_type"] == "process"
    assert captured["deploy"] is False
    assert captured["folder"] == "Shared"
    assert "pdd lifecycle: ok" in out.lower()
    assert "pdd" in out.lower()
    assert "deploy" in out.lower()
    assert "/tmp/pdd.md" in out


def test_pdd_command_propagates_flags():
    captured: dict[str, Any] = {}
    registry = _make_registry(
        captured, {"status": "ok", "stages": {}, "paths": {}}
    )
    out = registry.execute(
        "pdd",
        "make",
        "maestro",
        "flow",
        "--project-type=maestro",
        "--deploy",
        "--folder=Custom",
    )
    assert captured["request"] == "make maestro flow"
    assert captured["project_type"] == "maestro"
    assert captured["deploy"] is True
    assert captured["folder"] == "Custom"
    assert "ok" in out.lower()


def test_pdd_command_reports_failure():
    registry = _make_registry(
        {},
        {
            "status": "failed",
            "failed_at": "validate",
            "error": "boom",
            "stages": {"validate": {"status": "failed", "error": "boom"}},
            "paths": {},
        },
    )
    out = registry.execute("pdd", "x")
    assert "failed at validate" in out.lower()
    assert "boom" in out.lower()
