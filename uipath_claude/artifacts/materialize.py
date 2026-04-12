"""Materialize file blocks from assistant text (deterministic writes)."""
from __future__ import annotations

import re
from pathlib import Path

_BLOCK = re.compile(
    r"<<<UIPATH_FILE path=(?P<q>[\"'])(?P<rel>.+?)(?P=q)>>>(?P<body>.*?)<<<END_UIPATH_FILE>>>",
    re.DOTALL,
)

# First line inside fence: `path: relative/path.ext` then body until closing ```
_FENCE_PATH = re.compile(
    r"```[^\n`]*\npath:\s*(?P<rel>[^\n]+)\n(?P<body>.*?)```",
    re.DOTALL,
)


def _safe_join(root: Path, rel: str) -> Path | None:
    rel = rel.strip().replace("\\", "/")
    if not rel or rel.startswith("/"):
        return None
    if Path(rel).is_absolute():
        return None
    parts = Path(rel).parts
    if ".." in parts:
        return None
    dest = (root / rel).resolve()
    try:
        dest.relative_to(root.resolve())
    except ValueError:
        return None
    return dest


def _write_under_root(root: Path, rel: str, body: str) -> Path | None:
    dest = _safe_join(root, rel)
    if dest is None:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    return dest


def materialize_from_assistant_text(text: str, output_root: Path) -> list[Path]:
    """
    Extract file blocks and write under output_root.

    Supported formats:
    1) <<<UIPATH_FILE path="relative/path">>>...<<<END_UIPATH_FILE>>>
    2) Markdown fence whose first line is ``path: relative/path`` then file body.
    """
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    listed: set[Path] = set()

    for m in _BLOCK.finditer(text):
        rel = m.group("rel")
        body = m.group("body").strip("\n")
        dest = _write_under_root(root, rel, body)
        if dest is None:
            continue
        if dest not in listed:
            written.append(dest)
            listed.add(dest)

    for m in _FENCE_PATH.finditer(text):
        rel = m.group("rel").strip()
        body = m.group("body").strip("\n")
        dest = _write_under_root(root, rel, body)
        if dest is None:
            continue
        if dest not in listed:
            written.append(dest)
            listed.add(dest)

    return written
