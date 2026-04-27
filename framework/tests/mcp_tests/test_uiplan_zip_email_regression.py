"""Regression: Zip-email style intent produces XAML-first Solution UiPlan contract."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from mcp_server.tools import plan_tools, plan_uiplan_review


@pytest.fixture
def repo_with_real_uiplan_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolated repo root with production UiPlan templates copied from this checkout."""
    root = Path(__file__).resolve().parents[3]
    dst = tmp_path / "uiprepo"
    dst.mkdir()
    (dst / ".cursor" / "plans").mkdir(parents=True)
    (dst / "docs" / "plans").mkdir(parents=True)
    shutil.copytree(root / "templates" / "uiplan", dst / "templates" / "uiplan")
    monkeypatch.setattr(plan_tools, "_regen_plan_index", lambda r: {"skipped": True})
    return dst


@pytest.mark.asyncio
async def test_zip_email_fixture_generates_solution_xaml_contract(
    repo_with_real_uiplan_templates: Path,
) -> None:
    repo = repo_with_real_uiplan_templates
    intent_path = (
        Path(__file__).resolve().parent.parent / "fixtures" / "uiplan" / "zip-email" / "intent.md"
    )
    intent = intent_path.read_text(encoding="utf-8")

    out = await plan_tools.call_plan_tool(
        "uipath_plan_spec_new",
        {
            "project_root": str(repo),
            "title": "Zip Email Smart Invoice Routing",
            "intent": intent,
            "slug": "zip-email-regression",
            "project_type": "solution",
            "paradigm": "solution",
        },
    )
    assert out.get("status") == "ok"
    slug = out["slug"]
    pack = out.get("grounding_pack") or {}
    merged = {
        "project_root": str(repo),
        "slug": slug,
        "grounding_pack": pack,
        "paradigm": "solution",
    }
    assert (await plan_tools.call_plan_tool("uipath_plan_plan_new", merged)).get("status") == "ok"
    assert (await plan_tools.call_plan_tool("uipath_plan_tasks_new", merged)).get("status") == "ok"

    folder = repo / ".cursor" / "plans" / out["folder_name"]
    spec = (folder / "spec.md").read_text(encoding="utf-8")
    plan = (folder / "plan.md").read_text(encoding="utf-8")
    tasks = (folder / "tasks.md").read_text(encoding="utf-8")
    combo = f"{spec}\n{plan}\n{tasks}"

    assert "ZipEmailIntakeQueue" in combo
    assert "ZipEmailHumanReviewQueue" in combo
    assert "**Implementation paradigm**: solution" in spec
    assert "solution.uipx" in plan
    assert "bindings" in plan.lower()
    assert "XAML-first" in plan or ".xaml" in plan.lower()
    assert "Sequence" in plan or "Flowchart" in plan
    assert "Long Running" in plan or "Long Running Workflow" in plan
    assert "LogMessage" in tasks
    assert "correlation" in tasks.lower()
    assert "smoke" in tasks.lower()
    for phrase in (
        "T011C1",
        "ZipEmail.Dispatcher",
        "Graph/Office365",
        "uipath_doc_get_activity",
        "Dispatcher Graph read in `projects/ZipEmail.Dispatcher/Main.xaml`",
        "AnalyzerRunner Invoke Agent boundary",
        "Diagnose and fix verification failures",
        "parse analyzer",
        "solution.uipx",
        "project metadata/Automation Hub setting inspection",
    ):
        assert phrase in tasks, f"expected solution RPA task vocabulary in tasks: {phrase}"
    assert "validates except explicit tenant policy findings" not in tasks

    review = plan_uiplan_review.run_uiplan_review(
        spec=spec,
        plan=plan,
        tasks=tasks,
        stage="all",
        gate_ids=[],
        repo=repo,
        slug=slug,
    )
    err_rules = {f.get("rule") for f in review["findings"] if f.get("severity") == "error"}
    assert review.get("ok") is True, f"review errors: {err_rules}"


def test_zip_detailed_build_spec_has_grouped_readable_clarifications() -> None:
    """Example draft uses grouped SME headings and full-sentence questions (not marker-only)."""
    root = Path(__file__).resolve().parents[3]
    spec_path = root / ".cursor" / "plans" / "2026-04-27-zip-email-automation-detailed-build" / "spec.md"
    if not spec_path.is_file():
        pytest.skip("detailed Zip UiPlan example not in workspace")
    text = spec_path.read_text(encoding="utf-8")
    assert "### Mailboxes and routing" in text
    assert "eleven regional payable mailboxes" in text.lower() or "eleven" in text.lower()

    plan_path = root / ".cursor" / "plans" / "2026-04-27-zip-email-automation-detailed-build" / "plan.md"
    tasks_path = root / ".cursor" / "plans" / "2026-04-27-zip-email-automation-detailed-build" / "tasks.md"
    spec = spec_path.read_text(encoding="utf-8")
    plan = plan_path.read_text(encoding="utf-8") if plan_path.is_file() else ""
    tasks = tasks_path.read_text(encoding="utf-8") if tasks_path.is_file() else ""
    review = plan_uiplan_review.run_uiplan_review(
        spec=spec,
        plan=plan,
        tasks=tasks,
        stage="all",
        gate_ids=[],
        repo=root,
        slug="zip-email-automation-detailed-build",
    )
    assert review.get("ok") is True
    cl = review.get("clarifications") or {}
    # SME block replaced open NEEDS CLARIFICATION markers — bundle may have zero parsed items.
    assert int(cl.get("open_count") or 0) == 0
    na = (review.get("next_action") or "").lower()
    assert "clarification" in na or "accept" in na or "warning" in na


def test_plan_warns_on_vb_without_legacy():
    plan = (
        "## Technical Context\nVB.NET for all expressions\n"
        "## Planner Route & Specialist Handoff\n[skill:uipath-planner] [skill:uipath-rpa] "
        "uipath-project-discovery-agent project-context.md uipath_library_search uipath_doc_get_activity\n"
        "## Project Structure\n### Source Code (repository root)\nproject.json\nMain.xaml\n"
        "### Paradigm build loop\nuipcli\n```\nx\n```\n"
        "**Structure Decision**: concrete layout under repo.\n"
        "## Development execution contract\nok\n"
    )
    findings = plan_uiplan_review.review_plan_text(plan, [], "modern-rpa", None)
    assert any(f.get("rule") == "plan_vbnet_modern" for f in findings)


def test_plan_warns_when_workflow_types_missing():
    plan = (
        "## Technical Context\nC# / XAML hosts\n"
        "## Planner Route & Specialist Handoff\n[skill:uipath-planner] [skill:uipath-rpa] "
        "uipath-project-discovery-agent project-context.md uipath_library_search uipath_doc_get_activity\n"
        "## Project Structure\n### Source Code (repository root)\nproject.json\nMain.xaml\n"
        "### Paradigm build loop\nuipcli\n```\nx\n```\n"
        "**Structure Decision**: concrete layout under repo.\n"
        "## Development execution contract\nok\n"
    )
    findings = plan_uiplan_review.review_plan_text(plan, [], "solution", None)
    assert any(f.get("rule") == "plan_workflow_types" for f in findings)
