"""Proposal queue for library learning: proposed new/updated sections.

Storage: one JSON file per book at ``<proposals_root>/<book_id>.json``,
each file an array of proposal dicts. Default root is
``~/.uipath-claude/library-proposals/``; override with
``UIPATH_CLAUDE_LIBRARY_PROPOSALS`` (constant ``PROPOSALS_ENV_VAR``).
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

PROPOSALS_ENV_VAR = "UIPATH_CLAUDE_LIBRARY_PROPOSALS"


class ProposalKind(str, Enum):
    NEW_SECTION = "new_section"
    UPDATE_SECTION = "update_section"
    NEW_CHAPTER = "new_chapter"


class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass
class LibraryProposal:
    proposal_id: str
    book_id: str
    chapter_id: str
    section_id: str
    section_title: str
    kind: ProposalKind
    content: str
    keywords: list[str] = field(default_factory=list)
    rationale: str = ""
    source_session: Optional[str] = None
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "LibraryProposal":
        data = dict(data)
        if "kind" in data and isinstance(data["kind"], str):
            data["kind"] = ProposalKind(data["kind"])
        if "status" in data and isinstance(data["status"], str):
            data["status"] = ProposalStatus(data["status"])
        return cls(**data)


def _default_root() -> Path:
    override = os.environ.get(PROPOSALS_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".uipath-claude" / "library-proposals"


class ProposalStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else _default_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def _book_file(self, book_id: str) -> Path:
        if not book_id or ".." in book_id or "/" in book_id or "\\" in book_id:
            raise ValueError(f"invalid book_id: {book_id!r}")
        return self.root / f"{book_id}.json"

    def _load(self, book_id: str) -> list[LibraryProposal]:
        path = self._book_file(book_id)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(raw, list):
            return []
        return [LibraryProposal.from_dict(d) for d in raw]

    def _save(self, book_id: str, proposals: list[LibraryProposal]) -> None:
        path = self._book_file(book_id)
        path.write_text(
            json.dumps([p.to_dict() for p in proposals], indent=2),
            encoding="utf-8",
        )

    def enqueue(self, proposal: LibraryProposal) -> LibraryProposal:
        if not proposal.proposal_id:
            proposal.proposal_id = uuid.uuid4().hex[:12]
        proposals = self._load(proposal.book_id)
        proposals.append(proposal)
        self._save(proposal.book_id, proposals)
        return proposal

    def _iter_all(self) -> Iterable[tuple[str, LibraryProposal]]:
        for path in self.root.glob("*.json"):
            book_id = path.stem
            for p in self._load(book_id):
                yield book_id, p

    def list_pending(self) -> list[LibraryProposal]:
        return [p for _, p in self._iter_all() if p.status == ProposalStatus.PENDING]

    def get(self, proposal_id: str) -> Optional[LibraryProposal]:
        for _, p in self._iter_all():
            if p.proposal_id == proposal_id:
                return p
        return None

    def mark_status(
        self, proposal_id: str, status: ProposalStatus
    ) -> Optional[LibraryProposal]:
        for path in self.root.glob("*.json"):
            book_id = path.stem
            proposals = self._load(book_id)
            for p in proposals:
                if p.proposal_id == proposal_id:
                    p.status = status
                    self._save(book_id, proposals)
                    return p
        return None

    def remove(self, proposal_id: str) -> bool:
        for path in self.root.glob("*.json"):
            book_id = path.stem
            proposals = self._load(book_id)
            new = [p for p in proposals if p.proposal_id != proposal_id]
            if len(new) != len(proposals):
                self._save(book_id, new)
                return True
        return False
