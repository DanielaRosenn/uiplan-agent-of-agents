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
