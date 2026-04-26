"""Tests for UiPlan review helpers and MCP review."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.tools.plan_uiplan_review import (
    review_citations,
    review_duplicate_uiplan_slug,
    review_spec_text,
    review_plan_text,
    review_tasks_text,
    run_uiplan_review,
)


def test_review_citations_flags_unknown_skill():
    # framework/tests/mcp_tests/<this_file> -> parents[3] is repo root
    repo = Path(__file__).resolve().parents[3]
    text = "[skill:uipath-planner] [skill:not-a-real-skill-xyz-123]"
    findings = review_citations(text, repo)
    assert any(f.get("rule") == "citation_skill" for f in findings)


def test_review_duplicate_uiplan_slug_warns_on_two_drafts(tmp_path):
    root = tmp_path
    plans = root / ".cursor" / "plans"
    plans.mkdir(parents=True)
    for name in ("2026-01-01-dup", "2026-01-02-dup"):
        d = plans / name
        d.mkdir()
        (d / ".meta.yaml").write_text(
            "slug: dup\nplan_kind: uiplan\nstatus: draft\n",
            encoding="utf-8",
        )
    findings = review_duplicate_uiplan_slug(root, "dup")
    assert findings and findings[0].get("rule") == "duplicate_uiplan"


def test_run_uiplan_review_all_includes_citations():
    repo = Path(__file__).resolve().parents[3]
    spec = "### User Story 1 - A (Priority: P1)\n**Given** a **When** b **Then** c\n"
    spec += "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
    spec += "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
    spec += "## Source routing\nuipath_library_search uipath_library_lookup query_uipath_docs "
    spec += "uipath_doc_get_activity uipath-project-discovery-agent\n"
    spec += "## Development Handoff\n**Implementation paradigm**: modern-rpa\n**CLI family**: uipcli\n"
    spec += "Use tasks.md after uipath_plan_review and acceptance.\n"
    plan = "## Technical Context\nok\n## Constitution Check\n- [ ] **modern_experience_only**: ok\n"
    plan += "## Planner Route & Specialist Handoff\n"
    plan += "[skill:uipath-planner] [skill:uipath-rpa] uipath-project-discovery-agent "
    "project-context.md uipath_library_search uipath_doc_get_activity\n"
    plan += "## Project Structure\n### Source Code (repository root)\nproject.json\nMain.xaml\n"
    plan += "### Paradigm build loop\nuipcli analyze\n```\nx\n```\n"
    plan += "**Structure Decision**: use templates/long-running/ for layout.\n"
    plan += "## Development execution contract\nrestore -> analyze -> test -> pack\n"
    plan += "## Complexity Tracking\nnone\n"
    tasks = "## Phase 3: User Story 1 - A (Priority: P1)\n### Tests for User Story 1\n"
    tasks += "- [ ] T010 [US1] test `t.py` uipath_library_search\n"
    tasks += "### Implementation for User Story 1\n"
    tasks += "- [ ] T011 [US1] impl `m.py` [skill:uipath-rpa] uipath_library_lookup personal workspace Production\n"
    tasks += "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build\n"
    out = run_uiplan_review(
        spec=spec,
        plan=plan,
        tasks=tasks,
        stage="all",
        gate_ids=["modern_experience_only"],
        repo=repo,
        slug="nodup-test-slug",
    )
    assert "findings" in out
    assert "ok" in out


def test_review_requires_development_handoff_in_spec():
    findings = review_spec_text(
        "### User Story 1 - A (Priority: P1)\n"
        "**Given** a **When** b **Then** c\n"
        "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
        "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
    )

    assert any(f.get("rule") == "development_handoff" for f in findings)


def test_review_requires_development_execution_contract_in_plan():
    findings = review_plan_text(
        "## Technical Context\nok\n"
        "## Planner Route & Specialist Handoff\n"
        "[skill:uipath-planner] [skill:uipath-rpa] uipath-project-discovery-agent "
        "project-context.md uipath_library_search uipath_doc_get_activity\n"
        "## Project Structure\n```\nx\n```\n"
        "**Structure Decision**: concrete paths and rationale\n",
        [],
        None,
        None,
    )

    assert any(f.get("rule") == "development_execution_contract" for f in findings)


def test_review_requires_build_verify_handoff_phase_in_tasks():
    findings = review_tasks_text(
        "### Tests for User Story 1\n- [ ] T010 [US1] test\n"
        "### Implementation for User Story 1\n- [ ] T011 [US1] impl\n",
        "### User Story 1 - A (Priority: P1)\n",
    )

    assert any(f.get("rule") == "build_verify_handoff_phase" for f in findings)


def test_review_requires_paradigm_declaration_in_spec():
    findings = review_spec_text(
        "### User Story 1 - A (Priority: P1)\n"
        "**Given** a **When** b **Then** c\n"
        "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
        "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
        "## Development Handoff\nUse tasks.md after uipath_plan_review and acceptance.\n"
    )
    assert any(f.get("rule") == "paradigm_declared" for f in findings)


def test_review_requires_code_structure_and_build_loop_for_declared_paradigm():
    # Declared coded-agent but omit langgraph.json hint -> code_structure_present error.
    findings = review_plan_text(
        "## Technical Context\nok\n"
        "## Planner Route & Specialist Handoff\n"
        "[skill:uipath-planner] [skill:uipath-agents] [agent:uipath-project-discovery-agent] "
        "project-context.md uipath_library_search uipath_doc_get_activity\n"
        "## Development execution contract\nrestore -> analyze -> test -> pack\n"
        "### Source Code (repository root)\npyproject.toml\n"
        "### Paradigm build loop\nuipath run\n",
        [],
        "coded-agent",
        None,
    )
    assert any(f.get("rule") == "code_structure_present" for f in findings)
    # Missing ### Paradigm build loop heading -> build_loop_present error
    findings2 = review_plan_text(
        "## Technical Context\nok\n"
        "## Planner Route & Specialist Handoff\n"
        "[skill:uipath-planner] [skill:uipath-agents] uipath-project-discovery-agent "
        "project-context.md uipath_library_search uipath_doc_get_activity\n"
        "## Development execution contract\nrestore -> analyze -> test -> pack\n"
        "### Source Code (repository root)\npyproject.toml\nlanggraph.json\n",
        [],
        "coded-agent",
        None,
    )
    assert any(f.get("rule") == "build_loop_present" for f in findings2)


def test_review_requires_artifacts_and_grounding_in_tasks():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [US1] test\n"
        "### Implementation for User Story 1\n- [ ] T011 [US1] impl\n"
        "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build\n",
        "### User Story 1 - A (Priority: P1)\n",
    )
    assert any(f.get("rule") == "tasks_have_artifacts" for f in findings)
    assert any(f.get("rule") == "feasibility_grounding" for f in findings)


def test_review_warns_on_unknown_activity_tag():
    repo = Path(__file__).resolve().parents[3]
    spec = (
        "### User Story 1 - A (Priority: P1)\n**Given** a **When** b **Then** c\n"
        "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
        "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
        "## Development Handoff\n"
        "**Implementation paradigm**: coded-agent\n"
        "**CLI family**: uipath\n"
        "Use tasks.md after uipath_plan_review and acceptance.\n"
        "`uipath_library_search` `uipath_library_lookup` `query_uipath_docs` `uipath_doc_get_activity`\n"
    )
    plan = (
        "## Technical Context\nok\n## Constitution Check\n- [ ] **modern_experience_only**: ok\n"
        "## Planner Route & Specialist Handoff\n"
        "[skill:uipath-planner] [skill:uipath-agents] uipath-project-discovery-agent "
        "project-context.md uipath_library_search uipath_doc_get_activity\n"
        "## Project Structure\n### Source Code (repository root)\npyproject.toml\nlanggraph.json\n"
        "### Paradigm build loop\nuipath run\n"
        "## Development execution contract\nrestore -> analyze -> test -> pack\n"
    )
    tasks = (
        "## Phase 3: User Story 1 - A (Priority: P1)\n### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/test_us1.py`\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] impl `main.py` [skill:uipath-agents] uipath run personal workspace Production\n"
        "- [ ] T012 [US1] use [activity:Fake.Package:MissingActivity]\n"
        "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build\n"
    )
    out = run_uiplan_review(
        spec=spec,
        plan=plan,
        tasks=tasks,
        stage="all",
        gate_ids=[],
        repo=repo,
        slug="activity-tag-test",
    )
    assert any(f.get("rule") == "no_invented_activities" for f in out["findings"])


def test_tasks_document_grounding_accepts_uipath_library_search_only():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [US1] test `tests/t.py` uipath_library_search\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] impl `main.py` uipath_library_search personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build `x.py` uipcli queue\n",
        "### User Story 1 - A (Priority: P1)\n",
    )
    assert not any(f.get("rule") == "feasibility_grounding" for f in findings)
