from pathlib import Path

from tools.uiplan.generators.docs_bundle import generate_docs_bundle
from tools.uiplan.validators.visual_density import validate_uiplan_docs


def test_generate_docs_bundle_passes_visual_density(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[3]
    out = tmp_path / "bundle"
    generate_docs_bundle(
        repo_root=repo,
        plan_slug="2099-01-01-test-feature",
        output_dir=out,
    )
    issues = validate_uiplan_docs(out, strict=True)
    assert not issues, issues
    assert "## Development Handoff" in (out / "spec.md").read_text(encoding="utf-8")
    assert "## Development execution contract" in (out / "plan.md").read_text(
        encoding="utf-8"
    )
    plan_text = (out / "plan.md").read_text(encoding="utf-8")
    assert "### Paradigm build loop" in plan_text
    assert "Implementation Paradigm" in plan_text
    assert "## Phase 5: Build, Verify, and Handoff" in (out / "tasks.md").read_text(
        encoding="utf-8"
    )
    tasks_text = (out / "tasks.md").read_text(encoding="utf-8")
    assert "### Paradigm-specific tasks" in tasks_text
    assert "personal workspace" in tasks_text.lower()
    assert "## Task detail contract" in tasks_text
    assert "Runtime evidence" in tasks_text
    assert "uipath_doc_get_activity" in tasks_text
