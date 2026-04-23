from pathlib import Path


def test_uiplan_kit_contains_required_templates():
    root = Path(__file__).resolve().parents[3]
    kit = root / "docs" / "plans" / "_uiplan-kit"
    required = ["_spec-template.md", "_plan-template.md", "_tasks-template.md", "README.md"]
    assert all((kit / name).is_file() for name in required)
