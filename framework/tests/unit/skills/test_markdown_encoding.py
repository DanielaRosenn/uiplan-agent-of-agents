"""Regression tests for markdown encoding drift."""

from __future__ import annotations

from pathlib import Path


_MOJIBAKE_PATTERNS = ("\u0393\u00c7", "\u0393\u00e5")

# Skip large vendored / generated trees so this stays fast in CI and locally.
_SKIPPED_DIR_PARTS = frozenset(
    {".git", ".venv", "node_modules", "skills", "generated", "__pycache__", ".pytest_cache", "data"}
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_markdown_files_do_not_contain_common_mojibake() -> None:
    repo_root = _repo_root()
    offenders: list[str] = []
    for path in repo_root.rglob("*.md"):
        if any(p in _SKIPPED_DIR_PARTS for p in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for pattern in _MOJIBAKE_PATTERNS:
            if pattern in text:
                offenders.append(f"{path.relative_to(repo_root)}: contains {pattern!r}")

    assert not offenders, "\n".join(offenders[:25])
