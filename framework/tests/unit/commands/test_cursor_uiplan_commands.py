"""Tests for Cursor-native UiPlan command files."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]

EXPECTED_PLAN_TOOLS = (
    "uipath_plan_ground",
    "uipath_plan_spec_new",
    "uipath_plan_plan_new",
    "uipath_plan_tasks_new",
    "uipath_plan_review",
    "uipath_plan_uiplan_new",
)

EXPECTED_SUBCOMMANDS = ("full", "ground", "spec", "plan", "tasks", "review")


def test_cursor_uiplan_commands_are_trackable() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "!.cursor/commands" in gitignore
    assert "!.cursor/commands/**" in gitignore


def test_cursor_uiplan_command_files_exist_and_route_to_plan_tools() -> None:
    commands_dir = REPO_ROOT / ".cursor" / "commands"
    command_file = commands_dir / "uiplan.md"

    assert command_file.exists()

    content = command_file.read_text(encoding="utf-8")
    assert content.startswith("---\n")
    assert "name: uiplan" in content
    assert "single Cursor-native UiPlan dispatcher" in content
    assert ".cursor/skills/uiplan/SKILL.md" in content
    assert "@docs/uiplan/" in content

    for subcommand in EXPECTED_SUBCOMMANDS:
        assert subcommand in content

    for tool_name in EXPECTED_PLAN_TOOLS:
        assert tool_name in content


def test_cursor_uiplan_command_guides_project_building_flow() -> None:
    content = (REPO_ROOT / ".cursor" / "commands" / "uiplan.md").read_text(
        encoding="utf-8"
    )

    assert "ground -> spec -> plan -> tasks -> review -> human acceptance" in content
    assert ".cursor/plans/<YYYY-MM-DD-slug>/" in content
    assert "Do not start implementation" in content
    assert "human accepts the plan" in content


def test_cursor_uiplan_uses_single_dispatcher_command() -> None:
    commands_dir = REPO_ROOT / ".cursor" / "commands"
    uiplan_commands = sorted(path.name for path in commands_dir.glob("uiplan*.md"))

    assert uiplan_commands == ["uiplan.md"]
