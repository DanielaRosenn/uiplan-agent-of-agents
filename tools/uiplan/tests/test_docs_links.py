from pathlib import Path


def test_uiplan_skill_mentions_generate_then_scaffold():
    root = Path(__file__).resolve().parents[3]
    text = (root / ".cursor" / "skills" / "uiplan" / "SKILL.md").read_text(encoding="utf-8")
    assert "generate-docs" in text
    assert "scaffold-code" in text
