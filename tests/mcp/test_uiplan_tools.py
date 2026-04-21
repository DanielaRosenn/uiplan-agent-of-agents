"""Integration tests for UiPlan MCP tools."""
from __future__ import annotations

import pytest

from mcp_server.tools import plan_tools


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_tools, "_regen_plan_index", lambda r: {"skipped": True})
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / ".cursor" / "plans").mkdir(parents=True)
    (tmp_path / "docs" / "plans" / "_uiplan").mkdir(parents=True)
    for name in ("_spec-template.md", "_plan-template.md", "_tasks-template.md"):
        (tmp_path / "docs" / "plans" / "_uiplan" / name).write_text(
            "# T\n\n{{TITLE}}\n{{INTENT}}\n", encoding="utf-8"
        )
    return tmp_path


@pytest.mark.asyncio
async def test_uiplan_full_scaffold(repo, monkeypatch):
    """Minimal templates: use tiny files so _fill leaves unreplaced tokens acceptable."""
    tpl = repo / "docs" / "plans" / "_uiplan"
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
    slug = out["slug"]
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
