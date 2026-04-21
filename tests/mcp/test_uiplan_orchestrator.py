"""Full UiPlan orchestrator smoke test (mirrors test_uiplan_tools intent)."""
from __future__ import annotations

import pytest

from mcp_server.tools import plan_tools


@pytest.fixture
def orch_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(plan_tools, "_regen_plan_index", lambda r: {"skipped": True})
    (tmp_path / "docs" / "plans").mkdir(parents=True)
    (tmp_path / "docs" / "plans" / "_uiplan").mkdir(parents=True)
    tpl = (
        "# {{TITLE}}\n{{INTENT}}\n## User Scenarios\n### User Story 1 - A (Priority: P1)\n"
        "**Given** g **When** w **Then** t\n## Requirements\n### Functional Requirements\n"
        "**FR-001**: System MUST x\n## Success Criteria\n### Measurable Outcomes\n**SC-001**: m\n"
    )
    (tmp_path / "docs" / "plans" / "_uiplan" / "_spec-template.md").write_text(tpl, encoding="utf-8")
    (tmp_path / "docs" / "plans" / "_uiplan" / "_plan-template.md").write_text(
        "# {{TITLE}}\n## Technical Context\nx\n## Constitution Check\n"
        "- [ ] **modern_experience_only**: ok\n## Project Structure\n```\nx\n```\n"
        "**Structure Decision**: {{STRUCTURE_DECISION}}\n## Complexity Tracking\nx\n",
        encoding="utf-8",
    )
    (tmp_path / "docs" / "plans" / "_uiplan" / "_tasks-template.md").write_text(
        "# {{TITLE}}\n## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [P] [US1] test `src/x.py`\n"
        "### Implementation for User Story 1\n- [ ] T011 [US1] impl `src/y.py`\n",
        encoding="utf-8",
    )
    (tmp_path / ".cursor" / "plans").mkdir(parents=True)
    return tmp_path


@pytest.mark.asyncio
async def test_uiplan_orchestrator_end_to_end(orch_repo):
    out = await plan_tools.call_plan_tool(
        "uipath_plan_uiplan_new",
        {
            "project_root": str(orch_repo),
            "title": "Orchestrator Smoke",
            "intent": "verify full pipeline",
        },
    )
    assert out.get("status") == "ok"
    assert out.get("review", {}).get("ok") in (True, False)
    drafts = list((orch_repo / ".cursor" / "plans").iterdir())
    uiplan_dirs = [p for p in drafts if p.is_dir() and (p / ".meta.yaml").is_file()]
    assert len(uiplan_dirs) == 1
