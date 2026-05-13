"""Shared state and helpers for the UiPlan Studio API routers.

This module owns process-local state (bundle resolution root, pending
generation previews) and the small helpers that several routers need to
share. Splitting this out of ``app.main`` lets each router live in its own
file without circular imports.

Tests import some of these names through ``app.main`` for backwards
compatibility (notably ``main._PENDING_GENERATION_PREVIEWS`` and
``main.LEGACY_DIRECT_SAVE_POLICY``); ``app.main`` re-exports them.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict
from collections.abc import Iterator, MutableMapping
from pathlib import Path

from fastapi import HTTPException

from app.generation_contracts.models import FileProposal, ProposalState, StageManifest

DOCUMENT_TARGETS = {"spec.md", "plan.md", "tasks.md"}
LEGACY_DIRECT_SAVE_POLICY = "legacy_internal_direct_write"
APPROVAL_PACKAGE_ONLY_POLICY = "approval_package_only"

# `PLANS_ROOT` can be overridden via the ``UIPLAN_PLANS_ROOT`` env var so that
# downstream forks of this template (where the studio may be nested
# differently) can keep ``studio/api/app/main.py`` at a path
# other than ``<repo>/studio/api/app/main.py`` without breaking bundle
# resolution.
_PLANS_ROOT_ENV = os.environ.get("UIPLAN_PLANS_ROOT")
PLANS_ROOT: Path = (
    Path(_PLANS_ROOT_ENV).resolve()
    if _PLANS_ROOT_ENV
    else (Path(__file__).resolve().parents[3] / ".cursor" / "plans").resolve()
)

class PreviewStore(MutableMapping[str, dict[str, str]]):
    """TTL-aware in-memory preview storage with bounded size."""

    def __init__(self, ttl_seconds: int = 900, max_entries: int = 200) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._entries: OrderedDict[str, tuple[float, dict[str, str]]] = OrderedDict()

    def _purge_expired(self, now: float | None = None) -> None:
        if self.ttl_seconds <= 0:
            self._entries.clear()
            return
        current_time = time.time() if now is None else now
        expired_keys = [
            key
            for key, (created_at, _) in self._entries.items()
            if current_time - created_at > self.ttl_seconds
        ]
        for key in expired_keys:
            self._entries.pop(key, None)

    def _enforce_capacity(self) -> None:
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)

    def set(self, key: str, value: dict[str, str]) -> None:
        self._purge_expired()
        now = time.time()
        if key in self._entries:
            self._entries.pop(key, None)
        self._entries[key] = (now, value)
        self._enforce_capacity()

    def get(self, key: str, default: dict[str, str] | None = None) -> dict[str, str] | None:
        self._purge_expired()
        entry = self._entries.get(key)
        if entry is None:
            return default
        return entry[1]

    def pop(self, key: str, default: dict[str, str] | None = None) -> dict[str, str] | None:
        self._purge_expired()
        entry = self._entries.pop(key, None)
        if entry is None:
            return default
        return entry[1]

    def clear(self) -> None:
        self._entries.clear()

    def __getitem__(self, key: str) -> dict[str, str]:
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value

    def __setitem__(self, key: str, value: dict[str, str]) -> None:
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        removed = self.pop(key)
        if removed is None:
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        self._purge_expired()
        return iter(self._entries.keys())

    def __len__(self) -> int:
        self._purge_expired()
        return len(self._entries)

    def __contains__(self, key: object) -> bool:
        self._purge_expired()
        return key in self._entries


PENDING_GENERATION_PREVIEWS = PreviewStore()


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def resolve_bundle_root(bundle_root: str) -> Path:
    """Map a (possibly relative) bundle root onto an absolute path under
    ``PLANS_ROOT``. Raises 403 if the resolved path escapes the plans root.
    """
    requested = Path(bundle_root)
    if requested.is_absolute():
        root = requested.resolve()
    else:
        parts = requested.parts
        if len(parts) >= 2 and parts[0] == ".cursor" and parts[1] == "plans":
            root = (PLANS_ROOT.parent.parent / requested).resolve()
        elif parts and parts[0] == "plans":
            root = (PLANS_ROOT.parent / requested).resolve()
        else:
            root = (PLANS_ROOT / requested).resolve()
    try:
        root.relative_to(PLANS_ROOT)
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail=f"bundle_root must be under {PLANS_ROOT}",
        ) from exc
    return root


def load_package_root(bundle_root: Path, package_id: str) -> Path:
    package_root = bundle_root / ".uiplan" / "generation" / "packages" / package_id
    if not package_root.exists():
        raise HTTPException(status_code=404, detail=f"Package not found: {package_id}")
    return package_root


def load_stage_manifests(package_root: Path) -> list[StageManifest]:
    stages: list[StageManifest] = []
    for stage_manifest_path in sorted(package_root.glob("stages/*/stage.manifest.json")):
        payload = json.loads(stage_manifest_path.read_text(encoding="utf-8"))
        stages.append(StageManifest.model_validate(payload))
    return stages


def load_file_proposals(package_root: Path) -> list[FileProposal]:
    proposals: list[FileProposal] = []
    for proposal_manifest_path in sorted(package_root.glob("stages/*/proposals/*.proposal.json")):
        payload = json.loads(proposal_manifest_path.read_text(encoding="utf-8"))
        proposals.append(FileProposal.model_validate(payload))
    return proposals


def load_package_proposal(package_root: Path, proposal_id: str) -> FileProposal:
    proposals = load_file_proposals(package_root)
    proposal = next((c for c in proposals if c.proposal_id == proposal_id), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    return proposal


def read_target_for_proposal_preview(bundle_root: Path, target_path: str) -> tuple[str, str]:
    target = (bundle_root / target_path).resolve()
    try:
        target.relative_to(bundle_root.resolve())
    except ValueError as exc:
        raise HTTPException(
            status_code=403,
            detail="proposal target path escapes bundle root",
        ) from exc
    if target.exists():
        try:
            before = target.read_text(encoding="utf-8")
        except (IsADirectoryError, PermissionError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return before, content_hash(before)
    return "", "__missing__"


def proposal_state_or_404(
    approval_state: dict[str, ProposalState], proposal_id: str
) -> ProposalState:
    proposal_state = approval_state.get(proposal_id)
    if proposal_state is None:
        raise HTTPException(
            status_code=404, detail=f"Proposal state not found: {proposal_id}"
        )
    return proposal_state
