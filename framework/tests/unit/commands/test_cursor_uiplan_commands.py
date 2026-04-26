"""Tests for the Cursor-native UiPlan skill slash command surface."""

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

EXPECTED_WRAPPERS = {
    "uiplan-full": "uipath_plan_uiplan_new",
    "uiplan-ground": "uipath_plan_ground",
    "uiplan-spec": "uipath_plan_spec_new",
    "uiplan-plan": "uipath_plan_plan_new",
    "uiplan-tasks": "uipath_plan_tasks_new",
    "uiplan-review": "uipath_plan_review",
    "uiplan-implement": "uipath_plan_review",
}


def _skill_content() -> str:
    return (REPO_ROOT / ".cursor" / "skills" / "uiplan" / "SKILL.md").read_text(
        encoding="utf-8"
    )


def test_cursor_uiplan_skill_is_explicit_slash_surface() -> None:
    content = _skill_content()

    assert content.startswith("---\n")
    assert "name: uiplan" in content
    assert "disable-model-invocation: true" in content
    assert "canonical contract" in content

    for subcommand in EXPECTED_SUBCOMMANDS:
        assert subcommand in content

    for tool_name in EXPECTED_PLAN_TOOLS:
        assert tool_name in content


def test_cursor_uiplan_stage_wrappers_exist_and_map_to_tools() -> None:
    skills_dir = REPO_ROOT / ".cursor" / "skills"

    for skill_name, expected_tool in EXPECTED_WRAPPERS.items():
        skill_file = skills_dir / skill_name / "SKILL.md"
        assert skill_file.exists(), f"Missing Cursor skill wrapper: {skill_name}"

        content = skill_file.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert f"name: {skill_name}" in content
        assert "disable-model-invocation: true" in content
        assert ".cursor/skills/uiplan/SKILL.md" in content
        assert expected_tool in content


def test_cursor_uiplan_skill_guides_project_building_flow() -> None:
    content = _skill_content()

    assert ".cursor/plans/<YYYY-MM-DD-slug>/" in content
    assert "uipath_plan_ground" in content
    assert "uipath_plan_review" in content
    assert "Do **not** start implementation" in content
    assert "human accepts via `uipath_plan_accept`" in content


def test_legacy_cursor_command_file_is_not_required() -> None:
    commands_dir = REPO_ROOT / ".cursor" / "commands"

    assert not (commands_dir / "uiplan.md").exists()


def test_uiplan_implement_reviews_then_asks_before_building() -> None:
    content = (
        REPO_ROOT / ".cursor" / "skills" / "uiplan-implement" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "uipath_plan_review" in content
    assert "stage=all" in content
    assert "ask the user before starting implementation" in content
    assert "tasks.md" in content
    assert "Planner Route &" in content
    assert "Specialist Handoff" in content
    assert "uipath-planner" in content
    assert "project discovery agent" in content
    assert "specialist UiPath skills" in content
    assert "MCP tools" in content
    assert "subagents" in content
    assert "library lookup" in content
    assert "AskAI-style documentation lookup" in content
    assert "restore -> analyze -> test" in content
    assert "Never deploy to Production" in content
