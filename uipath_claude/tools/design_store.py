"""Per-project design-proposal store for the UiPath builder MCP.

Mirrors the existing library-proposal pattern: the agent submits a design
document via ``uipath_design_propose`` (the MCP returns a ``design_id`` and
keeps the project gated) and a human approves it via
``uipath_design_approve``. Until approval lands, ``uipath_workflow_write_file``
and ``uipath_workflow_install_package`` for that project return ``[BLOCKED]``.

State is persisted to a JSON file under
``UIPATH_DESIGN_STORE_PATH`` (default
``~/.uipath-builder-agent/design_proposals.json``) so approvals survive MCP
restarts. The store is process-safe via an in-process lock; concurrent MCP
servers are out of scope (the gate is meant to run inside a single Cursor
session at a time).
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from threading import RLock
from typing import Any, Literal

DesignStatus = Literal["pending", "approved", "rejected"]

RESOLUTION_KEYS: tuple[str, ...] = (
    "project_type",
    "target_framework",
    "expression_language",
    "attended_unattended",
    "external_systems",
    "orchestrator_folder",
    "deploy",
    "destructive_actions",
    "open_questions_residue",
)


def _normalize_project_dir(project_dir: str | os.PathLike[str]) -> str:
    try:
        return str(Path(project_dir).expanduser().resolve())
    except Exception:
        return str(project_dir)


def _store_path() -> Path:
    override = os.environ.get("UIPATH_DESIGN_STORE_PATH")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".uipath-builder-agent" / "design_proposals.json"


@dataclass
class DesignProposal:
    design_id: str
    project_dir: str
    title: str
    summary: str
    body: str
    rationale: str = ""
    citations: list[str] = field(default_factory=list)
    resolutions: dict[str, Any] = field(default_factory=dict)
    status: DesignStatus = "pending"
    created_at: float = field(default_factory=time.time)
    decided_at: float | None = None
    decided_by: str | None = None
    decision_note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DesignProposal":
        # Drop unknown keys so older store files without `resolutions` and
        # newer files with extra fields both load cleanly.
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        cleaned = {k: v for k, v in data.items() if k in known}
        cleaned.setdefault("resolutions", {})
        return cls(**cleaned)


def _normalize_resolutions(raw: Any) -> tuple[dict[str, Any], list[str]]:
    """Return (resolutions, warnings).

    Accepts a dict and filters to the known keys. Unknown keys are preserved
    under a ``_extra`` bucket so nothing is silently dropped but the approver
    still sees them. If ``raw`` is falsy, returns an empty dict with a
    deprecation warning so callers can nudge the agent toward structured
    resolutions without breaking backwards compatibility.
    """
    warnings: list[str] = []
    if not raw:
        warnings.append(
            "resolutions field is empty; callers should pass a structured "
            "object with keys "
            + ", ".join(RESOLUTION_KEYS)
            + " so the design-approval card shows the resolved triage "
            "decisions (free-text summary alone is deprecated)."
        )
        return {}, warnings
    if not isinstance(raw, dict):
        warnings.append(
            f"resolutions must be an object, got {type(raw).__name__}; ignored."
        )
        return {}, warnings
    known: dict[str, Any] = {}
    extra: dict[str, Any] = {}
    for key, value in raw.items():
        if key in RESOLUTION_KEYS:
            known[key] = value
        else:
            extra[key] = value
    if extra:
        known["_extra"] = extra
    return known, warnings


_LOCK = RLock()
_PROPOSALS: dict[str, DesignProposal] | None = None


def _load_locked() -> dict[str, DesignProposal]:
    global _PROPOSALS
    if _PROPOSALS is not None:
        return _PROPOSALS
    path = _store_path()
    if not path.exists():
        _PROPOSALS = {}
        return _PROPOSALS
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _PROPOSALS = {}
        return _PROPOSALS
    out: dict[str, DesignProposal] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                try:
                    out[key] = DesignProposal.from_dict(value)
                except Exception:
                    continue
    _PROPOSALS = out
    return _PROPOSALS


def _save_locked() -> None:
    proposals = _load_locked()
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(
            json.dumps({k: v.to_dict() for k, v in proposals.items()}, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, path)
    except OSError:
        try:
            tmp.unlink()
        except OSError:
            pass


def reset(in_memory_only: bool = True) -> None:
    """Test/admin helper: drop in-memory cache (and optionally the file)."""
    global _PROPOSALS
    with _LOCK:
        _PROPOSALS = None
        if not in_memory_only:
            try:
                _store_path().unlink()
            except OSError:
                pass


def propose(
    project_dir: str,
    title: str,
    summary: str,
    body: str,
    rationale: str = "",
    citations: list[str] | None = None,
    resolutions: dict[str, Any] | None = None,
) -> tuple[DesignProposal, list[str]]:
    """Stage a new pending design for ``project_dir``.

    Replaces any prior pending design for the same project (only one pending
    proposal per project at a time keeps the gate semantics simple).

    Returns ``(proposal, warnings)``. Warnings currently flag missing or
    malformed ``resolutions`` so the MCP layer can surface a deprecation hint
    without breaking older callers.
    """
    key = _normalize_project_dir(project_dir)
    design_id = f"design_{uuid.uuid4().hex[:12]}"
    normalized, warnings = _normalize_resolutions(resolutions)
    proposal = DesignProposal(
        design_id=design_id,
        project_dir=key,
        title=title,
        summary=summary,
        body=body,
        rationale=rationale,
        citations=list(citations or []),
        resolutions=normalized,
    )
    with _LOCK:
        proposals = _load_locked()
        for existing_id, existing in list(proposals.items()):
            if existing.project_dir == key and existing.status == "pending":
                proposals.pop(existing_id, None)
        proposals[design_id] = proposal
        _save_locked()
    return proposal, warnings


def approve(design_id: str, note: str = "", actor: str = "human") -> DesignProposal:
    with _LOCK:
        proposals = _load_locked()
        proposal = proposals.get(design_id)
        if proposal is None:
            raise KeyError(f"unknown design_id {design_id}")
        proposal.status = "approved"
        proposal.decided_at = time.time()
        proposal.decided_by = actor
        proposal.decision_note = note or None
        _save_locked()
        return proposal


def reject(design_id: str, note: str = "", actor: str = "human") -> DesignProposal:
    with _LOCK:
        proposals = _load_locked()
        proposal = proposals.get(design_id)
        if proposal is None:
            raise KeyError(f"unknown design_id {design_id}")
        proposal.status = "rejected"
        proposal.decided_at = time.time()
        proposal.decided_by = actor
        proposal.decision_note = note or None
        _save_locked()
        return proposal


def list_proposals(
    project_dir: str | None = None,
    status_filter: DesignStatus | None = None,
) -> list[DesignProposal]:
    with _LOCK:
        proposals = list(_load_locked().values())
    if project_dir:
        key = _normalize_project_dir(project_dir)
        proposals = [p for p in proposals if p.project_dir == key]
    if status_filter:
        proposals = [p for p in proposals if p.status == status_filter]
    proposals.sort(key=lambda p: p.created_at, reverse=True)
    return proposals


def has_approved(project_dir: str) -> bool:
    """True iff at least one approved design exists for ``project_dir``.

    When ``UIPATH_DESIGN_APPROVAL_ENABLED`` is set to a falsy value
    (``0``/``false``/``no``/``off``), the gate is considered open for all
    projects so callers can short-circuit the propose/approve dance.
    """
    if not _approval_enabled():
        return True
    key = _normalize_project_dir(project_dir)
    with _LOCK:
        for proposal in _load_locked().values():
            if proposal.project_dir == key and proposal.status == "approved":
                return True
    return False


def latest_pending(project_dir: str) -> DesignProposal | None:
    """The most recent pending proposal for ``project_dir``, if any."""
    pending = list_proposals(project_dir=project_dir, status_filter="pending")
    return pending[0] if pending else None


def _approval_enabled() -> bool:
    """Honor ``UIPATH_DESIGN_APPROVAL_ENABLED`` (default ON)."""
    val = os.environ.get("UIPATH_DESIGN_APPROVAL_ENABLED")
    if val is None:
        return True
    return val.strip().lower() not in {"0", "false", "no", "off", ""}
