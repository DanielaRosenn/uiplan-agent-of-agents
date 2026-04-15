"""Tests for /plan command."""
from uipath_claude.commands.plan import register_plan_command
from uipath_claude.commands.registry import CommandRegistry


def test_plan_command_is_registered():
    registry = CommandRegistry()
    register_plan_command(registry, run_planner=lambda x: "Plan for: " + x)
    assert "plan" in registry.commands


def test_plan_command_requires_description():
    registry = CommandRegistry()
    register_plan_command(registry, run_planner=lambda x: "Plan")
    result = registry.execute("plan")
    assert "Usage:" in result
