"""Tests for Cursor-native UiPlan command files."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[4]

EXPECTED_COMMANDS = {
    "uiplan.md": ("name: uiplan", "uipath_plan_uiplan_new"),
    "uiplan-full.md": ("name: uiplan-full", "uipath_plan_uiplan_new"),
    "uiplan-ground.md": ("name: uiplan-ground", "uipath_plan_ground"),
    "uiplan-spec.md": ("name: uiplan-spec", "uipath_plan_spec_new"),
    "uiplan-plan.md": ("name: uiplan-plan", "uipath_plan_plan_new"),
    "uiplan-tasks.md": ("name: uiplan-tasks", "uipath_plan_tasks_new"),
    "uiplan-review.md": ("name: uiplan-review", "uipath_plan_review"),
}


def test_cursor_uiplan_commands_are_trackable() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "!.cursor/commands" in gitignore
    assert "!.cursor/commands/**" in gitignore


def test_cursor_uiplan_command_files_exist_and_route_to_plan_tools() -> None:
    commands_dir = REPO_ROOT / ".cursor" / "commands"

    for filename, required_fragments in EXPECTED_COMMANDS.items():
        command_file = commands_dir / filename
        assert command_file.exists(), f"Missing Cursor command file: {filename}"

        content = command_file.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert ".cursor/skills/uiplan/SKILL.md" in content
        assert "@docs/uiplan/" in content

        for fragment in required_fragments:
            assert fragment in content
