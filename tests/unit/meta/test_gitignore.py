"""Meta-tests for .gitignore invariants."""
from pathlib import Path


def test_gitignore_excludes_library_cache_dirs():
    repo_root = Path(__file__).resolve().parents[3]
    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8")
    assert "data/library/**/_cache/" in gitignore, (
        "Defensive ignore for legacy _cache dirs missing from .gitignore"
    )
