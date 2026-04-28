"""Tests for UiPlan review helpers and MCP review."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.tools.plan_uiplan_review import (
    build_clarifications_bundle,
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
    plan += "## XAML workflow shape\nSequence Flowchart Long Running for `.xaml` entry.\n"
    plan += "## Logging contract\nLogMessage correlation smoke job run robot log assert.\n"
    plan += "## Planner Route & Specialist Handoff\n"
    plan += "[skill:uipath-planner] [skill:uipath-rpa] uipath-project-discovery-agent "
    "project-context.md uipath_library_search uipath_doc_get_activity\n"
    plan += "## Project Structure\n### Source Code (repository root)\nproject.json\nMain.xaml\n"
    plan += "### Paradigm build loop\nuipcli analyze\n```\nx\n```\n"
    plan += "**Structure Decision**: use templates/long-running/ for layout.\n"
    plan += "## Development execution contract\nrestore -> analyze -> test -> pack\n"
    plan += "## Complexity Tracking\nnone\n"
    tasks = "## Phase 3: User Story 1 - A (Priority: P1)\n### Tests for User Story 1\n"
    tasks += "- [ ] T010 [US1] test `t.py` uipath_library_search uv run pytest tests/t.py -q\n"
    tasks += "### Implementation for User Story 1\n"
    tasks += "- [ ] T009 [US1] template decision matrix for `Main.xaml`: starter template "
    tasks += "long-running scaffold source from `project.json` / `project.uiproj`, Studio evidence "
    tasks += "from uip rpa create-project, workflow type Long Running, preserve generated structure; "
    tasks += "[skill:uipath-rpa] uipath_library_search\n"
    tasks += "- [ ] T011 [US1] impl `Main.xaml` [skill:uipath-rpa] uipath_library_lookup LogMessage "
    tasks += "correlation id smoke job run robot log assert personal workspace Production\n"
    tasks += "## Phase 5: Build, Verify, and Handoff\n"
    tasks += "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n"
    tasks += "- [ ] T031 diagnose failures: parse analyzer resultPath rule, use uipath_library_search "
    tasks += "and --help, inspect project.json source schema, apply local fix, rerun command\n"
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
    assert "clarifications" in out
    assert out["clarifications"].get("open_count") == 0


def test_build_clarifications_bundle_groups_zip_style_markers():
    spec = (
        "## SME inputs\n"
        "- `[NEEDS CLARIFICATION: monitored mailboxes]` Which mailboxes are in scope?\n"
        "- `[NEEDS CLARIFICATION: final trigger model]` Queue vs schedule?\n"
        "- `[NEEDS CLARIFICATION: Zip mode]` Forward or API?\n"
    )
    out = build_clarifications_bundle(spec=spec, plan="", tasks="")
    assert out["open_count"] == 3
    gids = {g["id"] for g in out["groups"]}
    assert "mailboxes_routing" in gids
    assert "execution_triggers" in gids
    assert "zip_integration" in gids
    assert "Mailboxes and routing" in out["clarifications_text"]
    assert "[NEEDS CLARIFICATION: Zip mode]" in out["clarifications_text"]


def test_run_uiplan_review_next_action_when_clarifications_open():
    repo = Path(__file__).resolve().parents[3]
    spec = "### User Story 1 - A (Priority: P1)\n**Given** a **When** b **Then** c\n"
    spec += "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
    spec += "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
    spec += "## Source routing\nuipath_library_search uipath_library_lookup query_uipath_docs "
    spec += "uipath_doc_get_activity uipath-project-discovery-agent\n"
    spec += "## SME inputs\n"
    spec += "- `[NEEDS CLARIFICATION: Zip mode]` — Forward to mailbox or use Zip API?\n"
    spec += "## LLM / Executor Readiness Contract\n"
    spec += "### Role and scope\n- demo\n"
    spec += "### Environment and conventions\n- cli\n"
    spec += "### Skill routing matrix\n|a|b|c|d|\n|---|---|---|---|\n|x|y|z|w|\n"
    spec += "### Decision logic inventory\n|a|b|c|d|e|f|\n|---|---|---|---|---|---|\n|x|y|z|w|q|r|\n"
    spec += "### Build readiness checklist\n- [ ] ready\n"
    spec += "## Development Handoff\n**Implementation paradigm**: modern-rpa\n**CLI family**: uipcli\n"
    spec += "Use tasks.md after uipath_plan_review and acceptance.\n"
    plan = "## Technical Context\nok\n## Constitution Check\n- [ ] **modern_experience_only**: ok\n"
    plan += "## XAML workflow shape\nSequence Flowchart Long Running for `.xaml` entry.\n"
    plan += "## Logging contract\nLogMessage correlation smoke job run robot log assert.\n"
    plan += "## Planner Route & Specialist Handoff\n"
    plan += "[skill:uipath-planner] [skill:uipath-rpa] uipath-project-discovery-agent "
    "project-context.md uipath_library_search uipath_doc_get_activity\n"
    plan += "## Project Structure\n### Source Code (repository root)\nproject.json\nMain.xaml\n"
    plan += "### Paradigm build loop\nuipcli analyze\n```\nx\n```\n"
    plan += "**Structure Decision**: use templates/long-running/ for layout.\n"
    plan += "## Development execution contract\nrestore -> analyze -> test -> pack\n"
    plan += "## Complexity Tracking\nnone\n"
    tasks = "## Phase 3: User Story 1 - A (Priority: P1)\n### Tests for User Story 1\n"
    tasks += "- [ ] T010 [US1] test `t.py` uipath_library_search uv run pytest tests/t.py -q\n"
    tasks += "### Implementation for User Story 1\n"
    tasks += "### Executor context for User Story 1\n- **Role/scope**: x\n"
    tasks += "- **Environment**: x\n- **Workflow**: x\n- **Guardrails**: x\n"
    tasks += "- **Tools**: x\n- **Patterns**: x\n- **Return/evidence**: x\n"
    tasks += "- [ ] T009 [US1] template decision matrix for `Main.xaml`: starter template "
    tasks += "long-running scaffold source from `project.json` / `project.uiproj`, Studio evidence "
    tasks += "from uip rpa create-project, workflow type Long Running, preserve generated structure; "
    tasks += "[skill:uipath-rpa] uipath_library_search\n"
    tasks += "- [ ] T011 [US1] impl `Main.xaml` [skill:uipath-rpa] uipath_library_lookup LogMessage "
    tasks += "correlation id smoke job run robot log assert personal workspace Production\n"
    tasks += "| Field | Content |\n| --- | --- |\n| Pre-reqs | T010 |\n"
    tasks += "| Depends on | x |\n| Tooling / access | x |\n| Build surface | xaml |\n"
    tasks += "| Verify / evidence | cmd + out |\n| Skills / MCP | [skill:uipath-rpa] |\n"
    tasks += "### Mini-topology: `Main.xaml`\n"
    tasks += "```mermaid\nflowchart LR\nA[Start] --> B[Step]\n```\n"
    tasks += "### Mini-topology: `project.json`\n"
    tasks += "```mermaid\nflowchart LR\nA[Config] --> B[Run]\n```\n"
    tasks += "## Phase 5: Build, Verify, and Handoff\n"
    tasks += "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n"
    tasks += "- [ ] T031 diagnose failures: parse analyzer resultPath rule, use uipath_library_search "
    tasks += "and --help, inspect project.json source schema, apply local fix, rerun command\n"
    out = run_uiplan_review(
        spec=spec,
        plan=plan,
        tasks=tasks,
        stage="all",
        gate_ids=["modern_experience_only"],
        repo=repo,
        slug="nodup-test-slug-2",
    )
    assert out["clarifications"].get("open_count", 0) >= 1
    assert (
        "clarification" in out["next_action"].lower()
        or "address error" in out["next_action"].lower()
    )


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


def test_review_requires_failure_diagnosis_loop_in_phase5():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] impl `Main.xaml` [skill:uipath-rpa] uipath_library_search "
        "LogMessage correlation id smoke job run robot log assert personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log; "
        "stop on analyzer errors\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: modern-rpa\n",
    )

    assert any(f.get("rule") == "task_failure_diagnosis_loop" for f in findings)


def test_review_requires_studio_template_contract_for_rpa_tasks():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] build `projects/ZipEmail.Dispatcher/Main.xaml` [skill:uipath-rpa] "
        "uipath_library_search LogMessage correlation id smoke job run robot log assert "
        "personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n"
        "- [ ] T031 diagnose failures: parse analyzer resultPath rule, use uipath_library_search "
        "and --help, inspect project.json source schema, apply local fix, rerun command\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: modern-rpa\n",
    )

    assert any(f.get("rule") == "tasks_studio_template_contract" for f in findings)


def test_review_rejects_stusg034_blocker_without_diagnosis():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] update `projects/A/Main.xaml` [skill:uipath-rpa] "
        "uipath_library_search LogMessage correlation id smoke job run robot log assert "
        "personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n"
        "- [ ] T031 ST-USG-034 can be blocked by tenant policy after analyze validates except "
        "that finding\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: modern-rpa\n",
    )

    assert any(f.get("rule") == "task_analyzer_rule_diagnosis" for f in findings)


def test_review_rejects_solution_uipx_without_descriptor_diagnosis():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] package `projects/A/Main.xaml` and `solution.uipx` "
        "[skill:uipath-rpa] uipath_library_search LogMessage correlation id smoke job run "
        "robot log assert personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n"
        "- [ ] T031 diagnose failures: parse analyzer resultPath rule, use uipath_library_search "
        "and --help, inspect project.json source schema, apply local fix, rerun command\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: solution\n",
    )

    assert any(f.get("rule") == "task_solution_descriptor_diagnosis" for f in findings)


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
        "- [ ] T010 [US1] test `tests/test_us1.py` uv run pytest tests/test_us1.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] impl `main.py` [skill:uipath-agents] uipath run personal workspace Production\n"
        "- [ ] T012 [US1] use `tests/stub.py` [activity:Fake.Package:MissingActivity] "
        "uipath_library_lookup personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit resultPath robot log\n"
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
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] impl `main.py` uipath_library_search personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `x.py` uipcli queue pytest junit nupkg resultPath\n",
        "### User Story 1 - A (Priority: P1)\n",
    )
    assert not any(f.get("rule") == "feasibility_grounding" for f in findings)


def test_review_rejects_tests_without_command():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [US1] test `tests/t.py` uipath_library_search\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] impl `main.py` uipath_library_search personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build `x.py` pytest junit\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: coded-agent\n",
    )
    assert any(f.get("rule") == "task_test_detail" for f in findings)


def test_review_rejects_impl_missing_workflow_hint_when_paradigm_declared():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [US1] test `t.py` uv run pytest t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] do work with `config.json` only [skill:uipath-rpa] uipath_library_lookup "
        "personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build `x.nupkg` pytest junit\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: solution\n",
    )
    assert any(f.get("rule") == "task_workflow_detail" for f in findings)


def test_review_rejects_studio_handoff_and_broad_rpa_activity_task():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [US1] test `tests/t.py` uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] **[HANDOFF:Studio] `projects/ZipEmail.Dispatcher/Main.xaml`:** "
        "Microsoft Graph + intake queue activities after `uipath_doc_get_activity`; "
        "[skill:uipath-rpa] uipath_library_search `out/analyze.json` uipcli package analyze\n"
        "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build `x.nupkg` pytest junit resultPath robot log\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: solution\n",
    )
    rules = {f.get("rule") for f in findings}
    assert "task_studio_handoff_skip" in rules
    assert "task_rpa_too_broad" in rules


def test_review_rejects_agent_task_without_graph_or_invocation_contract():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n- [ ] T010 [US1] test `tests/t.py` uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] Invoke Agent from `projects/ZipEmail.AnalyzerRunner/Main.xaml`; "
        "[skill:uipath-rpa] [skill:uipath-agents] uipath_library_lookup uipcli package analyze\n"
        "## Phase 5: Build, Verify, and Handoff\n- [ ] T030 build `x.nupkg` pytest junit resultPath robot log\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: solution\n",
    )
    assert any(f.get("rule") == "task_agent_contract_detail" for f in findings)


def test_review_requires_spec_360_visibility_contract():
    findings = review_spec_text(
        "### User Story 1 - A (Priority: P1)\n"
        "**Given** a **When** b **Then** c\n"
        "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
        "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
        "## LLM / Executor Readiness Contract\n"
        "### Role and scope\n- x\n"
        "### Environment and conventions\n- x\n"
        "### Skill routing matrix\n|a|b|c|d|\n|---|---|---|---|\n|x|y|z|w|\n"
        "### Decision logic inventory\n|a|b|c|d|e|f|\n|---|---|---|---|---|---|\n|x|y|z|w|q|r|\n"
        "### Build readiness checklist\n- [ ] x\n"
        "## Development Handoff\n"
        "**Implementation paradigm**: solution\n**CLI family**: uipcli\n"
    )
    assert any(f.get("rule") == "RULE_SPEC_NO_360" for f in findings)


def test_review_requires_spec_workflow_visual_catalog():
    spec = (
        "### User Story 1 - A (Priority: P1)\n"
        "**Given** a **When** b **Then** c\n"
        "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
        "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
        "## 360 Build Visibility Contract\n"
        "### Workflow and artifact visibility inventory\n"
        "| Artifact path | Type/surface | Owns user story | Invocation entrypoint | Cannot be stubbed by | Evidence required |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| `projects/A/Main.xaml` | xaml | US1 | Main | placeholder | out/a.json |\n"
        "### Workflow-level visual and activity conformance\n"
        "| Workflow artifact | Diagram section (spec/plan/tasks) | Mandatory activities/nodes | Skill/tool route | Verification evidence |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `projects/A/Main.xaml` | `spec.md` visual section | Sequence, Log Message | [skill:uipath-rpa] | out/analyze.json |\n"
        "## LLM / Executor Readiness Contract\n"
        "### Role and scope\n- x\n"
        "### Environment and conventions\n- x\n"
        "### Skill routing matrix\n|a|b|c|d|\n|---|---|---|---|\n|x|y|z|w|\n"
        "### Decision logic inventory\n|a|b|c|d|e|f|\n|---|---|---|---|---|---|\n|x|y|z|w|q|r|\n"
        "### Build readiness checklist\n- [ ] x\n"
        "## Development Handoff\n"
        "**Implementation paradigm**: modern-rpa\n**CLI family**: uipcli\n"
        "uipath_library_search uipath_library_lookup query_uipath_docs uipath_doc_get_activity tasks.md uipath_plan_review\n"
    )
    findings = review_spec_text(spec, None)
    assert any(f.get("rule") == "RULE_SPEC_NO_WORKFLOW_VISUAL" for f in findings)


def test_review_accepts_spec_workflow_visual_catalog_when_complete():
    spec = (
        "### User Story 1 - A (Priority: P1)\n"
        "**Given** a **When** b **Then** c\n"
        "## Requirements\n### Functional Requirements\n**FR-001**: System MUST x\n"
        "## Success Criteria\n### Measurable Outcomes\n**SC-001**: y\n"
        "## 360 Build Visibility Contract\n"
        "### Workflow and artifact visibility inventory\n"
        "| Artifact path | Type/surface | Owns user story | Invocation entrypoint | Cannot be stubbed by | Evidence required |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| `projects/A/Main.xaml` | xaml | US1 | Main | placeholder | out/a.json |\n"
        "### Workflow-level visual and activity conformance\n"
        "| Workflow artifact | Diagram section (spec/plan/tasks) | Mandatory activities/nodes | Skill/tool route | Verification evidence |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `projects/A/Main.xaml` | `spec.md` visual section | Sequence, Log Message | [skill:uipath-rpa] | out/analyze.json |\n"
        "### Workflow surface visual catalog (required)\n"
        "#### `projects/A/Main.xaml`\n"
        "```mermaid\nflowchart TD\nA[Start] --> B[Work]\n```\n"
        "## LLM / Executor Readiness Contract\n"
        "### Role and scope\n- x\n"
        "### Environment and conventions\n- x\n"
        "### Skill routing matrix\n|a|b|c|d|\n|---|---|---|---|\n|x|y|z|w|\n"
        "### Decision logic inventory\n|a|b|c|d|e|f|\n|---|---|---|---|---|---|\n|x|y|z|w|q|r|\n"
        "### Build readiness checklist\n- [ ] x\n"
        "## Development Handoff\n"
        "**Implementation paradigm**: modern-rpa\n**CLI family**: uipcli\n"
        "uipath_library_search uipath_library_lookup query_uipath_docs uipath_doc_get_activity tasks.md uipath_plan_review\n"
    )
    findings = review_spec_text(spec, None)
    assert not any(f.get("rule") == "RULE_SPEC_NO_WORKFLOW_VISUAL" for f in findings)


def test_review_requires_plan_connector_boundary_and_log_contract():
    findings = review_plan_text(
        "## Planner Route & Specialist Handoff\n[skill:uipath-planner]\n"
        "## Project Structure\n### Source Code (repository root)\nsolution.uipx\nbindings\n"
        "### Paradigm build loop\nuipcli solution analyze\n"
        "## Development execution contract\nok\n",
        [],
        "solution",
        None,
    )
    rules = {f.get("rule") for f in findings}
    assert "RULE_PLAN_NO_CONNECTOR_INV" in rules
    assert "RULE_PLAN_NO_SURFACE_BOUNDARY" in rules
    assert "RULE_PLAN_NO_LOG_CONTRACT" in rules


def test_review_flags_template_residue_rule():
    out = run_uiplan_review(
        spec="## 360 Build Visibility Contract\n{{TOKEN}}\n",
        plan="connector invocation boundary correlation phase log assertion",
        tasks="## Phase 5: Build, Verify, and Handoff\n",
        stage="all",
        gate_ids=[],
        repo=None,
        slug="template-residue",
    )
    assert any(f.get("rule") == "RULE_ANY_TEMPLATE_RESIDUE" for f in out["findings"])


def test_review_flags_spec_artifact_missing_chain():
    spec = (
        "## 360 Build Visibility Contract\n"
        "| Artifact path | Type/surface | Owns user story | Invocation entrypoint | Cannot be stubbed by | Evidence required |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| projects/A/Main.xaml | xaml | US1 | Main | placeholder | out/a.json |\n"
    )
    out = run_uiplan_review(
        spec=spec,
        plan="connector invocation boundary correlation phase log assertion",
        tasks="## Phase 5: Build, Verify, and Handoff\n",
        stage="all",
        gate_ids=[],
        repo=None,
        slug="artifact-missing",
    )
    assert any(f.get("rule") == "RULE_SPEC_ARTIFACT_MISSING" for f in out["findings"])


def test_review_flags_spec_visual_chain_missing():
    spec = (
        "## 360 Build Visibility Contract\n"
        "### Workflow and artifact visibility inventory\n"
        "| Artifact path | Type/surface | Owns user story | Invocation entrypoint | Cannot be stubbed by | Evidence required |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| `projects/A/Main.xaml` | xaml | US1 | Main | placeholder | out/a.json |\n"
        "### Workflow-level visual and activity conformance\n"
        "| Workflow artifact | Diagram section (spec/plan/tasks) | Mandatory activities/nodes | Skill/tool route | Verification evidence |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| `projects/A/Main.xaml` | `spec.md` visual section | Sequence, Log Message | [skill:uipath-rpa] | out/analyze.json |\n"
        "### Workflow surface visual catalog (required)\n"
        "#### `projects/A/Main.xaml`\n"
        "```mermaid\nflowchart TD\nA[Start] --> B[Work]\n```\n"
    )
    out = run_uiplan_review(
        spec=spec,
        plan=(
            "## Spec artifact chain map\n| Spec artifact path | Plan section owning design | Planned task area | Verify/evidence owner |\n"
            "| --- | --- | --- | --- |\n"
            "| `projects/B/Main.xaml` | `## Workflow Catalog` | `tasks.md` | `## CLI Command Matrix` |\n"
        ),
        tasks=(
            "## Per-workflow activity checklist (required)\n"
            "| Workflow artifact | Activity/node checklist (must exist) | How to confirm | Skill/tool route | Evidence path |\n"
            "| --- | --- | --- | --- | --- |\n"
            "| `projects/B/Main.xaml` | Sequence | analyze | [skill:uipath-rpa] | out/analyze.json |\n"
        ),
        stage="all",
        gate_ids=[],
        repo=None,
        slug="spec-visual-chain-missing",
    )
    assert any(f.get("rule") == "RULE_SPEC_VISUAL_CHAIN_MISSING" for f in out["findings"])


def test_review_flags_stub_xaml_and_missing_diagram_rules():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] implement `projects/A/Main.xaml` placeholder would invoke later "
        "[skill:uipath-rpa] uipath_library_search personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: solution\n",
    )
    rules = {f.get("rule") for f in findings}
    assert "RULE_TASKS_STUB_XAML" in rules
    assert "RULE_TASKS_NO_DIAGRAM" in rules


def test_review_flags_missing_activity_checklist_for_workflow_artifacts():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] implement `projects/A/Main.xaml` [skill:uipath-rpa] "
        "uipath_library_search personal workspace Production\n"
        "### Mini-topology: `projects/A/Main.xaml`\n"
        "```mermaid\nflowchart LR\nA[Start] --> B[End]\n```\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: solution\n",
    )
    assert any(f.get("rule") == "RULE_TASKS_NO_ACTIVITY_CHECKLIST" for f in findings)


def test_review_emits_single_rule_tasks_no_diagram_finding():
    findings = review_tasks_text(
        "## Phase 3: User Story 1 - A (Priority: P1)\n"
        "### Tests for User Story 1\n"
        "- [ ] T010 [US1] test `tests/t.py` uipath_library_search uv run pytest tests/t.py -q\n"
        "### Implementation for User Story 1\n"
        "- [ ] T011 [US1] implement `projects/A/Main.xaml` [skill:uipath-rpa] "
        "uipath_library_search personal workspace Production\n"
        "## Phase 5: Build, Verify, and Handoff\n"
        "- [ ] T030 build `out/pkg.nupkg` pytest junit analyzer resultPath robot log\n",
        "### User Story 1 - A (Priority: P1)\n**Implementation paradigm**: solution\n",
    )
    count = sum(1 for f in findings if f.get("rule") == "RULE_TASKS_NO_DIAGRAM")
    assert count == 1
