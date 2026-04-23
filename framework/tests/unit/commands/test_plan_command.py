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


def test_plan_command_invokes_planner():
    registry = CommandRegistry()
    captured = []

    def fake_planner(desc):
        captured.append(desc)
        return "## Step 1\nDo something"

    register_plan_command(registry, run_planner=fake_planner)
    result = registry.execute("plan", "build", "invoice", "processor")
    assert captured == ["build invoice processor"]
    assert "## Step 1" in result
    assert "[Type 'y' to execute" in result


def test_plan_command_handles_planner_exception():
    registry = CommandRegistry()

    def failing_planner(desc):
        raise RuntimeError("API connection failed")

    register_plan_command(registry, run_planner=failing_planner)
    result = registry.execute("plan", "some", "task")
    assert "Plan generation failed:" in result
    assert "API connection failed" in result
