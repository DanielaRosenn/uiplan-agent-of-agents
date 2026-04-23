"""Presence tests for operator docs."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_library_learning_doc_exists_and_covers_cli():
    doc = REPO_ROOT / "docs" / "LIBRARY_LEARNING.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    for token in [
        "library-proposals list",
        "library-proposals show",
        "library-proposals approve",
        "library-proposals reject",
        "propose_library_update",
        "UIPATH_CLAUDE_LIBRARY_PROPOSALS",
    ]:
        assert token in text, f"missing from LIBRARY_LEARNING.md: {token}"


def test_readme_links_to_learning_doc():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/LIBRARY_LEARNING.md" in text
