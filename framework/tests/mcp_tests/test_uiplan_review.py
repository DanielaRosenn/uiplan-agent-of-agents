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
    spec += "## Development Handoff\nUse tasks.md after uipath_plan_review and acceptance.\n"
    plan = "## Technical Context\nok\n## Constitution Check\n- [ ] **modern_experience_only**: ok\n"
    plan += "## Project Structure\n```\nx\n```\n**Structure Decision**: use templates/long-running/ for layout.\n"
    plan += "## Development execution contract\nrestore -> analyze -> test -> pack\n"
    plan += "## Complexity Tracking\nnone\n"
    tasks = "## Phase 3: User Story 1 - A (Priority: P1)\n### Tests for User Story 1\n"
    tasks += "- [ ] T010 [US1] test\n### Implementation for User Story 1\n- [ ] T011 [US1] impl\n"
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
        "## Project Structure\n```\nx\n```\n"
        "**Structure Decision**: concrete paths and rationale\n",
        [],
    )

    assert any(f.get("rule") == "development_execution_contract" for f in findings)


def test_review_requires_build_verify_handoff_phase_in_tasks():
    findings = review_tasks_text(
        "### Tests for User Story 1\n- [ ] T010 [US1] test\n"
        "### Implementation for User Story 1\n- [ ] T011 [US1] impl\n",
        "### User Story 1 - A (Priority: P1)\n",
    )

    assert any(f.get("rule") == "build_verify_handoff_phase" for f in findings)
