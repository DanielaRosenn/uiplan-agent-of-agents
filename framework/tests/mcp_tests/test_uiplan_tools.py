"""Integration tests for UiPlan MCP tools."""
from __future__ import annotations

import pytest

from mcp_server.tools import plan_tools, plan_uiplan


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_tools, "_regen_plan_index", lambda r: {"skipped": True})
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"tmp\"\n", encoding="utf-8")
    (tmp_path / "langgraph.json").write_text("{}", encoding="utf-8")
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / ".cursor" / "plans").mkdir(parents=True)
    kit = tmp_path / "templates" / "uiplan"
    kit.mkdir(parents=True)
    for name in ("_spec-template.md", "_plan-template.md", "_tasks-template.md"):
        (kit / name).write_text("# T\n\n{{TITLE}}\n{{INTENT}}\n", encoding="utf-8")
    return tmp_path


@pytest.mark.asyncio
async def test_uiplan_full_scaffold(repo, monkeypatch):
    """Minimal templates: use tiny files so _fill leaves unreplaced tokens acceptable."""
    tpl = repo / "templates" / "uiplan"
    (tpl / "_spec-template.md").write_text(
        "# {{TITLE}}\n{{INTENT}}\n## User Scenarios\n### User Story 1 - A (Priority: P1)\n"
        "**Given** g **When** w **Then** t\n## Requirements\n### Functional Requirements\n"
        "**FR-001**: System MUST x\n## Success Criteria\n### Measurable Outcomes\n**SC-001**: m\n",
        encoding="utf-8",
    )
    (tpl / "_plan-template.md").write_text(
        "# {{TITLE}}\n## Technical Context\nx\n## Constitution Check\n"
        "- [ ] **modern_experience_only**: ok\n## Project Structure\n```\nx\n```\n"
        "**Structure Decision**: {{STRUCTURE_DECISION}}\n## Complexity Tracking\nx\n",
        encoding="utf-8",
    )
    (tpl / "_tasks-template.md").write_text(
        "# {{TITLE}}\n## Phase 3: User Story 1 - MVP (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [P] [US1] test `src/x.py`\n"
        "### Implementation for User Story 1\n- [ ] T011 [US1] impl `src/y.py`\n",
        encoding="utf-8",
    )
    out = await plan_tools.call_plan_tool(
        "uipath_plan_uiplan_new",
        {"project_root": str(repo), "title": "UiPlan Integration Test", "intent": "test intent"},
    )
    assert out.get("status") == "ok"
    drafts = repo / ".cursor" / "plans"
    folders = [p for p in drafts.iterdir() if p.is_dir() and (p / ".meta.yaml").is_file()]
    assert len(folders) == 1
    folder = folders[0]
    assert folder.is_dir()
    assert (folder / "spec.md").is_file()
    assert (folder / "plan.md").is_file()
    assert (folder / "tasks.md").is_file()
    rev = out.get("review") or {}
    assert "ok" in rev


@pytest.mark.asyncio
async def test_uiplan_ground_smoke(repo):
    out = await plan_tools.call_plan_tool(
        "uipath_plan_ground",
        {"project_root": str(repo), "topic": "orchestrator queue invoice"},
    )
    assert out.get("status") == "ok"
    assert "matched_skills" in out


@pytest.mark.asyncio
async def test_tasks_new_resolved_activity_docs(repo, monkeypatch):
    tpl = repo / "templates" / "uiplan"
    (tpl / "_spec-template.md").write_text(
        "# {{TITLE}}\n{{INTENT}}\n## User Scenarios\n### User Story 1 - A (Priority: P1)\n"
        "**Given** g **When** w **Then** t\n## Requirements\n### Functional Requirements\n"
        "**FR-001**: System MUST x\n## Success Criteria\n### Measurable Outcomes\n**SC-001**: m\n",
        encoding="utf-8",
    )
    (tpl / "_plan-template.md").write_text(
        "# {{TITLE}}\n## Technical Context\nx\n## Constitution Check\n"
        "- [ ] **modern_experience_only**: ok\n## Project Structure\n```\nx\n```\n"
        "**Structure Decision**: {{STRUCTURE_DECISION}}\n## Complexity Tracking\nx\n",
        encoding="utf-8",
    )
    (tpl / "_tasks-template.md").write_text(
        "# {{TITLE}}\n## Phase 3: User Story 1 - MVP (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [P] [US1] test `src/x.py`\n",
        encoding="utf-8",
    )
    spec_out = await plan_tools.call_plan_tool(
        "uipath_plan_spec_new",
        {
            "project_root": str(repo),
            "title": "Activity Doc Task Test",
            "intent": "verify activity inline",
            "slug": "act-doc-task-test",
        },
    )
    assert spec_out.get("status") == "ok"
    slug = spec_out["slug"]
    plan_out = await plan_tools.call_plan_tool(
        "uipath_plan_plan_new",
        {
            "project_root": str(repo),
            "slug": slug,
            "title": "Activity Doc Task Test",
        },
    )
    assert plan_out.get("status") == "ok"
    folder = repo / ".cursor" / "plans" / spec_out["folder_name"]
    plan_path = folder / "plan.md"
    plan_path.write_text(
        plan_path.read_text(encoding="utf-8")
        + "\n\nUses `[activity:UiPath.System.Activities:LogMessage]`.\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        plan_uiplan,
        "get_activity_doc",
        lambda pkg, act, version=None: "SYNTHETIC_ACTIVITY_DOC\n",
    )
    tasks_out = await plan_tools.call_plan_tool(
        "uipath_plan_tasks_new",
        {
            "project_root": str(repo),
            "slug": slug,
            "title": "Activity Doc Task Test",
        },
    )
    assert tasks_out.get("status") == "ok"
    tasks_text = (folder / "tasks.md").read_text(encoding="utf-8")
    assert "## Resolved activity docs" in tasks_text
    assert "SYNTHETIC_ACTIVITY_DOC" in tasks_text
    assert "`UiPath.System.Activities` / `LogMessage`" in tasks_text


@pytest.mark.asyncio
async def test_plan_new_writes_grounding_inputs(repo, monkeypatch):
    tpl = repo / "templates" / "uiplan"
    (tpl / "_spec-template.md").write_text(
        "# {{TITLE}}\n{{INTENT}}\n## User Scenarios\n### User Story 1 - A (Priority: P1)\n"
        "**Given** g **When** w **Then** t\n## Requirements\n### Functional Requirements\n"
        "**FR-001**: System MUST x\n## Success Criteria\n### Measurable Outcomes\n**SC-001**: m\n",
        encoding="utf-8",
    )
    (tpl / "_plan-template.md").write_text(
        "# {{TITLE}}\n## Summary\n{{SUMMARY}}\n## Grounding Inputs\n{{GROUNDING_CONTEXT}}\n"
        "## Technical Context\n**Primary Dependencies**: {{DEPS}}\n"
        "## Constitution Check\n{{CONSTITUTION_CHECKLIST}}\n"
        "## Project Structure\n```text\n{{SOURCE_TREE}}\n```\n"
        "**Structure Decision**: {{STRUCTURE_DECISION}}\n## Complexity Tracking\nx\n",
        encoding="utf-8",
    )

    pack = {
        "status": "ok",
        "planning_skill": {
            "name": "uipath-planner",
            "excerpt": "Planner guidance should be visible in generated plan.",
        },
        "matched_skills": [
            {
                "name": "uipath-rpa",
                "description": "RPA guidance",
                "excerpt": "Use modern activities and analyze before pack.",
            }
        ],
        "knowledge_lookups": [
            {
                "query": "queues",
                "source": "SOURCE: library:uipath-docs/orchestrator/queues",
                "excerpt": "Queue guidance excerpt.",
            }
        ],
        "library_hits": [{"query": "queues", "excerpt": "Queue section excerpt."}],
        "candidate_project_template": "templates/long-running/",
        "constitution": {"gates": [{"id": "modern", "text": "Modern only"}]},
        "suggested_citations": ["[skill:uipath-planner]", "[skill:uipath-rpa]"],
        "unanswered": [],
    }

    spec_out = await plan_tools.call_plan_tool(
        "uipath_plan_spec_new",
        {
            "project_root": str(repo),
            "title": "Grounded Plan Test",
            "intent": "queue automation",
            "slug": "grounded-plan-test",
            "grounding_pack": pack,
        },
    )
    assert spec_out.get("status") == "ok"

    plan_out = await plan_tools.call_plan_tool(
        "uipath_plan_plan_new",
        {
            "project_root": str(repo),
            "slug": spec_out["slug"],
            "grounding_pack": pack,
        },
    )
    assert plan_out.get("status") == "ok"
    plan_text = (repo / ".cursor" / "plans" / spec_out["folder_name"] / "plan.md").read_text(
        encoding="utf-8"
    )
    assert "## Grounding Inputs" in plan_text
    assert "[skill:uipath-planner]" in plan_text
    assert "[skill:uipath-rpa]" in plan_text
    assert "SOURCE: library:uipath-docs/orchestrator/queues" in plan_text
    assert "Queue guidance excerpt" in plan_text
