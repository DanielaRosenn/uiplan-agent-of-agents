"""Per-project verification gate for the UiPath builder MCP.

The gate enforces the rule: after any mutation to a UiPath project, the agent
MUST run ``uipath_workflow_build_and_verify`` and reach ``success=true``
before further mutations / runs / deploys are accepted. This prevents Cursor
(or any LLM caller) from "claiming done" after a static edit without a real
debug+verify cycle.

State is in-process (per MCP server lifetime), keyed by absolute project
directory. Three states:

- ``unknown``: no writes observed yet. Gated tools are *warned* but not
  blocked (otherwise a server restart would deadlock honest users).
- ``dirty``: at least one write touched this project since the last clean
  ``build_and_verify``. Gated tools are *blocked* until verified.
- ``verified``: ``build_and_verify_workflow`` returned ``success=true``
  after the last write. Gated tools pass freely.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Literal

ProjectStatus = Literal["unknown", "dirty", "verified"]


@dataclass
class ProjectState:
    status: ProjectStatus = "unknown"
    last_dirty_files: list[str] = field(default_factory=list)
    last_verify_at: float | None = None
    last_dirty_at: float | None = None
    last_verdict: str | None = None


class GateError(Exception):
    """Raised when a gated tool is invoked while the project is dirty."""

    def __init__(self, message: str, project_dir: str, calling_tool: str) -> None:
        super().__init__(message)
        self.project_dir = project_dir
        self.calling_tool = calling_tool


_LOCK = RLock()
_STATES: dict[str, ProjectState] = {}


def _gate_enabled() -> bool:
    """Honor ``UIPATH_MCP_GATE_ENABLED`` (default on)."""
    val = os.environ.get("UIPATH_MCP_GATE_ENABLED")
    if val is None:
        return True
    return val.strip().lower() not in {"0", "false", "no", "off", ""}


def _normalize(project_dir: str | os.PathLike[str]) -> str:
    """Canonical absolute key for a project directory."""
    try:
        return str(Path(project_dir).expanduser().resolve())
    except Exception:
        return str(project_dir)


_TRACKED_SUFFIXES = (".xaml", ".cs", ".json", ".uiproj")


def _iter_tracked_files(project_dir: str) -> list[Path]:
    """Return tracked files under ``project_dir`` (xaml/cs/json/uiproj)."""
    root = Path(project_dir)
    if not root.exists():
        return []
    skip_dirs = {".local", ".objects", ".tmh", ".entities", "bin", "obj"}
    out: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() in _TRACKED_SUFFIXES:
            out.append(path)
    return out


def detect_out_of_band_changes(project_dir: str) -> list[str]:
    """Mark a project dirty when tracked files were modified outside the MCP.

    Compares mtimes of every tracked file in ``project_dir`` against
    ``last_verify_at``. When ``last_verify_at`` is unset, the project has
    never been verified by the MCP, so any tracked file present is treated
    as out-of-band. Files newer than ``last_verify_at`` are appended to
    ``last_dirty_files`` and the status is flipped to ``dirty``.

    Returns the list of file paths (strings) that triggered the dirty flag
    in this sweep (empty when no out-of-band change was found).
    """
    key = _normalize(project_dir)
    state = status(key)
    threshold = state.last_verify_at
    changed: list[str] = []
    for path in _iter_tracked_files(key):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if threshold is None or mtime > threshold:
            changed.append(str(path))
    if not changed:
        return []
    with _LOCK:
        state = _STATES.setdefault(key, ProjectState())
        state.status = "dirty"
        state.last_dirty_at = time.time()
        for entry in changed:
            if entry not in state.last_dirty_files:
                state.last_dirty_files.append(entry)
        if len(state.last_dirty_files) > 25:
            state.last_dirty_files = state.last_dirty_files[-25:]
    return changed


def _project_dir_for_file(file_path: str | os.PathLike[str]) -> str | None:
    """Walk up from ``file_path`` to the nearest ``project.json`` directory.

    Returns the normalized project dir, or ``None`` when no project.json is
    found within a reasonable bound. The caller is responsible for deciding
    what to do with ``None`` (typically: skip the gate update).
    """
    try:
        path = Path(file_path).expanduser().resolve()
    except Exception:
        return None
    if path.is_file():
        candidates = [path.parent, *path.parent.parents]
    else:
        candidates = [path, *path.parents]
    for parent in candidates:
        if (parent / "project.json").exists():
            return str(parent)
    return None


def mark_dirty(project_dir: str, file_path: str | None = None) -> ProjectState:
    """Mark a project as having unverified changes."""
    key = _normalize(project_dir)
    now = time.time()
    with _LOCK:
        state = _STATES.setdefault(key, ProjectState())
        state.status = "dirty"
        state.last_dirty_at = now
        if file_path:
            rel = str(file_path)
            if rel not in state.last_dirty_files:
                state.last_dirty_files.append(rel)
            if len(state.last_dirty_files) > 25:
                state.last_dirty_files = state.last_dirty_files[-25:]
        return state


def mark_verified(project_dir: str, verdict: str | None = None) -> ProjectState:
    """Clear the dirty flag and record a successful verify.

    ``last_verify_at`` is stamped slightly in the future (small skew) so the
    out-of-band sweep does not immediately re-flag files whose mtimes were
    set during the verify itself (cfn-lint touchups, packaging artifacts,
    etc.).
    """
    key = _normalize(project_dir)
    now = time.time() + 1.0
    with _LOCK:
        state = _STATES.setdefault(key, ProjectState())
        state.status = "verified"
        state.last_verify_at = now
        state.last_verdict = verdict
        state.last_dirty_files = []
        return state


def status(project_dir: str) -> ProjectState:
    """Return the current state (creating an ``unknown`` entry if absent)."""
    key = _normalize(project_dir)
    with _LOCK:
        return _STATES.setdefault(key, ProjectState())


def reset(project_dir: str | None = None) -> None:
    """Drop in-memory state (test helper / explicit human reset)."""
    with _LOCK:
        if project_dir is None:
            _STATES.clear()
            return
        _STATES.pop(_normalize(project_dir), None)


def require_verified(
    project_dir: str,
    calling_tool: str,
    *,
    allow_unverified: bool = False,
) -> None:
    """Raise :class:`GateError` if ``project_dir`` is dirty.

    ``unknown`` is treated as a soft pass: the MCP cannot tell whether the
    project was edited before the server started, so we let the call through
    but do not change the state. Only ``dirty`` blocks.

    Pass ``allow_unverified=True`` to bypass the gate (explicit human
    override; the MCP layer should only set this when the user explicitly
    asks for it). Disabling via ``UIPATH_MCP_GATE_ENABLED=0`` also bypasses.
    """
    if not _gate_enabled() or allow_unverified:
        return
    detect_out_of_band_changes(project_dir)
    state = status(project_dir)
    if state.status != "dirty":
        return
    files = ", ".join(state.last_dirty_files[-5:]) or "(unknown files)"
    raise GateError(
        (
            f"Project '{project_dir}' has unverified changes ({files}). "
            f"Call uipath_workflow_build_and_verify and reach success=true "
            f"before invoking {calling_tool}. Pass allow_unverified=true "
            f"only when explicitly overriding."
        ),
        project_dir=project_dir,
        calling_tool=calling_tool,
    )


def require_approved_design(
    project_dir: str,
    calling_tool: str,
    *,
    allow_unapproved: bool = False,
) -> None:
    """Raise :class:`GateError` if no approved design exists for ``project_dir``.

    Imported lazily so :mod:`session_gate` stays free of design-store
    dependencies in environments that disable approval (or import the gate
    standalone for testing).

    Pass ``allow_unapproved=True`` to bypass for one call (explicit human
    override). Disable globally with ``UIPATH_DESIGN_APPROVAL_ENABLED=0``.
    """
    if allow_unapproved:
        return
    try:
        from uipath_claude.tools import design_store
    except Exception:
        return
    if not design_store._approval_enabled():
        return
    if design_store.has_approved(project_dir):
        return
    pending = design_store.latest_pending(project_dir)
    if pending is not None:
        msg = (
            f"Project '{project_dir}' has a pending design ({pending.design_id}: "
            f"{pending.title!r}) awaiting human approval. Run "
            f"uipath_design_approve {{ design_id: '{pending.design_id}' }} "
            f"to unblock {calling_tool}, or uipath_design_reject to drop it. "
            f"Pass allow_unapproved=true only when explicitly overriding."
        )
    else:
        msg = (
            f"Project '{project_dir}' has no approved design. Use "
            f"uipath_design_propose to submit a design summary first; the "
            f"MCP returns a design_id and {calling_tool} stays blocked "
            f"until uipath_design_approve is invoked. Pass "
            f"allow_unapproved=true only when explicitly overriding."
        )
    raise GateError(msg, project_dir=project_dir, calling_tool=calling_tool)


def state_to_dict(state: ProjectState) -> dict:
    """JSON-serializable view of a :class:`ProjectState`."""
    return {
        "status": state.status,
        "last_dirty_files": list(state.last_dirty_files),
        "last_dirty_at": state.last_dirty_at,
        "last_verify_at": state.last_verify_at,
        "last_verdict": state.last_verdict,
    }
