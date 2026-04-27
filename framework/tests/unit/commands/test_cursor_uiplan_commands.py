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


def test_uiplan_implement_reviews_then_controls_building() -> None:
    content = (
        REPO_ROOT / ".cursor" / "skills" / "uiplan-implement" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "Validation evidence ledger" in content
    assert "exit code" in content.lower()
    assert "No static-only completion" in content
    assert "human" in content.lower() and "validation" in content.lower()
    assert "uv run pytest" in content
    assert "uipath_plan_review" in content
    assert "stage=all" in content
    assert "ask the user before starting implementation" in content
    assert "--run-to-completion" in content
    assert "asking again between tasks" in content
    assert "Per-Task UiPath Loop" in content
    assert "Plan alignment" in content
    assert "Source reality snapshot" in content
    assert "Dependency and tooling check" in content
    assert "Artifact completeness gate" in content
    assert "Spec compliance review" in content
    assert "Code quality review" in content
    assert "Completion ledger" in content
    assert "No scaffold completion rule" in content
    assert "XAML runtime rule" in content
    assert "LangGraph runtime rule" in content
    assert "Behavior test rule" in content
    assert "Mismatch stop rule" in content
    assert "Still stop and report before" in content
    assert "tasks.md" in content
    assert "Planner Route &" in content
    assert "Specialist Handoff" in content
    assert ".meta.yaml" in content
    assert "acceptance_ready" in content
    assert "uipath-planner" in content
    assert "project discovery agent" in content
    assert "specialist UiPath skills" in content
    assert "MCP tools" in content
    assert "subagents" in content
    assert "library lookup" in content
    assert "AskAI-style documentation lookup" in content
    assert "restore -> analyze -> test" in content
    assert "Never deploy to Production" in content


def test_canonical_uiplan_skill_requires_implement_evidence_ledger() -> None:
    content = _skill_content()
    assert "Evidence ledger" in content
    assert "No static-only completion" in content
    assert "human validation" in content.lower()


def test_how_to_use_documents_runtime_validation_for_implement() -> None:
    text = (REPO_ROOT / "docs" / "uiplan" / "HOW_TO_USE.md").read_text(encoding="utf-8")
    assert "validation evidence ledger" in text.lower()
    assert "runtime evidence" in text.lower() or "runtime" in text.lower()
    assert "/uiplan-implement" in text


def test_scaffold_code_doc_rejects_static_only_completion() -> None:
    text = (REPO_ROOT / "docs" / "uiplan" / "SCAFFOLD_CODE.md").read_text(encoding="utf-8")
    assert "static-only" in text.lower() or "static-only" in text
    assert "validation evidence ledger" in text.lower()


def test_uiplan_review_wrapper_requires_feasibility_checks() -> None:
    content = (
        REPO_ROOT / ".cursor" / "skills" / "uiplan-review" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "uipath_plan_review" in content
    assert "stage=all" in content or "stage=all" in content.lower()
    assert "implementation paradigm" in content.lower()
    assert "project structure" in content.lower()
    assert "uipath_library_lookup" in content
    assert "uipath_library_search" in content
    assert "query_uipath_docs" in content
    assert "uipath_doc_get_activity" in content
    assert "uipath_skill_match" in content
    assert "project discovery" in content.lower()
    assert "personal workspace" in content.lower()
    assert "production" in content.lower()
    assert ".net 8" in content.lower()


def test_uiplan_tasks_wrapper_requires_artifacts_and_handoff() -> None:
    content = (
        REPO_ROOT / ".cursor" / "skills" / "uiplan-tasks" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "uipath_plan_tasks_new" in content
    assert "artifact path" in content.lower()
    assert "activity" in content.lower()
    assert "cli" in content.lower()
    assert "queue" in content.lower() or "orchestrator" in content.lower()
    assert "tests before implementation" in content.lower()
    assert "Build, Verify, and Handoff" in content
    assert "TODO" in content
    assert "NEEDS CLARIFICATION" in content
