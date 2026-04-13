"""Persistence helpers for skills sync metadata."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_MANIFEST_RELATIVE_PATH = Path(".uipath-claude") / "skills-sync-manifest.json"
_DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_project_root(project_root: Path | None = None) -> Path:
    """Resolve repository root for manifest placement."""
    if project_root is not None:
        return Path(project_root).resolve()

    current = Path(__file__).resolve()
    if current.is_file():
        current = current.parent

    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return _DEFAULT_PROJECT_ROOT


def get_sync_manifest_path(project_root: Path | None = None) -> Path:
    """Return absolute path to the skills sync manifest file."""
    root = _resolve_project_root(project_root)
    return root / _MANIFEST_RELATIVE_PATH


def load_sync_manifest(path: Path | None = None) -> dict[str, Any] | None:
    """Load and return sync manifest metadata if present and valid JSON."""
    manifest_path = path or get_sync_manifest_path()
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        return data
    return None


def save_sync_manifest(metadata: dict[str, Any], path: Path | None = None) -> Path:
    """Persist sync manifest metadata and return the written path."""
    manifest_path = path or get_sync_manifest_path()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(metadata, indent=2, sort_keys=True)
    manifest_path.write_text(f"{payload}\n", encoding="utf-8")
    return manifest_path
