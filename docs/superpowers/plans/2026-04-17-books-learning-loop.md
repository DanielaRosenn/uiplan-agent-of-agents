# Books Learning Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the library (books) learning loop: allow sessions to **propose** new sections or patches to books, gate them behind **human approval**, and then **apply** them into the committable library — mirroring the pattern already used for skill insights.

**Architecture:** Three components. (1) A `LibraryWriter` that can create/overwrite sections and update `chapter.yaml` / `book.yaml` atomically. (2) A proposals queue stored at `~/.uipath-claude/library-proposals/<book_id>.json`, an append-only JSON list of pending edits. (3) A `library_proposals` CLI verb: `list`, `show`, `approve <id>`, `reject <id>`. Approved proposals are applied via `LibraryWriter` into the in-repo library, then removed from the queue. Agent-side: one new tool `propose_library_update(...)` is exposed through `library_tools.py`, so the agent can emit a proposal at the end of a session when it synthesized a useful new piece of knowledge.

**Tech Stack:** Python 3.12, pytest, PyYAML, Typer (`uipath_claude/cli/app.py`). No new third-party deps.

**Implementation notes (2026-04-17):** (1) CLI lives in `uipath_claude/commands/library_proposals.py` as `register_library_proposals_command(app: typer.Typer)` and is wired from `app.py` via `app.add_typer(...)`. (2) `approve`/`reject` emit `StructuredLogger().emit(event="library_proposal_approved"|"library_proposal_rejected", ...)`; CLI tests set `UIPATH_EVENT_LOG` to a temp file and assert JSON lines. (3) Task 3 tests append to `tests/unit/tools/test_library_tools.py` only.

---

## Scope Check

This plan **depends on** `2026-04-17-library-relocate-to-repo.md` being executed first. Reason: proposals apply to the in-repo library; if the library is still at `~/.uipath-claude/library/`, approvals would modify user-scope state instead of producing reviewable diffs in git. If you execute this plan standalone, the approval step still works but loses the git-review benefit.

This plan covers **one** subsystem (proposal lifecycle). Intentionally out of scope:

- Automated proposer that decides *when* to propose (ties into agent graph; separate plan).
- Embedding/semantic retrieval for section dedup (nice-to-have; separate plan).
- Web scraping / LLM fetch of new content (the proposer passes content in; we don't generate it).

---

## File Structure

**Created:**
- `uipath_claude/library/writer.py` — `LibraryWriter` class: create/overwrite sections, update `chapter.yaml` and `book.yaml`.
- `uipath_claude/library/proposals.py` — `ProposalStore` class + `LibraryProposal` dataclass.
- `uipath_claude/commands/library_proposals.py` — `register_library_proposals_command(app)`; Typer sub-app `list`, `show`, `approve`, `reject` with structured audit logging on approve/reject.
- `tests/unit/library/test_writer.py` — writer behavior + atomicity.
- `tests/unit/library/test_proposals.py` — store behavior (enqueue, load, remove).
- `tests/unit/cli/test_library_proposals_cli.py` — CLI end-to-end.
- `docs/LIBRARY_LEARNING.md` — operator doc: lifecycle, file formats, CLI.

**Modified:**
- `uipath_claude/tools/library_tools.py` — add `propose_library_update` tool.
- `uipath_claude/cli/app.py` — call `register_library_proposals_command(app)` after `app = typer.Typer(...)`.
- `README.md` — one paragraph + link to `docs/LIBRARY_LEARNING.md`.

---

## Data Model (used in multiple tasks)

```python
# uipath_claude/library/proposals.py  (defined in Task 2)
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class ProposalKind(str, Enum):
    NEW_SECTION = "new_section"
    UPDATE_SECTION = "update_section"

class ProposalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

@dataclass
class LibraryProposal:
    proposal_id: str                # uuid4 hex[:12]
    book_id: str
    chapter_id: str
    section_id: str
    section_title: str
    kind: ProposalKind
    content: str                    # markdown body
    keywords: list[str] = field(default_factory=list)
    rationale: str = ""             # why propose; shown at review
    source_session: Optional[str] = None
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
```

---

## Task 1: `LibraryWriter` — minimal create/update API

**Files:**
- Create: `uipath_claude/library/writer.py`
- Test: `tests/unit/library/test_writer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/library/test_writer.py`:

```python
"""Tests for LibraryWriter."""
from pathlib import Path

import pytest
import yaml

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.writer import LibraryWriter


@pytest.fixture
def seeded_library(tmp_path, monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path))
    (tmp_path / "catalog.yaml").write_text(
        yaml.dump({"version": 1, "books": [
            {"id": "uipath-docs", "title": "UiPath Docs",
             "path": "books/uipath-docs", "description": ""}
        ]}),
        encoding="utf-8",
    )
    book = tmp_path / "books" / "uipath-docs"
    book.mkdir(parents=True)
    (book / "book.yaml").write_text(
        yaml.dump({
            "id": "uipath-docs", "title": "UiPath Docs",
            "version": "1", "source": "test",
            "chapters": [{"id": "activities", "title": "Activities",
                          "path": "chapters/01-activities", "order": 1}],
        }),
        encoding="utf-8",
    )
    ch = book / "chapters" / "01-activities"
    ch.mkdir(parents=True)
    (ch / "chapter.yaml").write_text(
        yaml.dump({"id": "activities", "title": "Activities", "sections": []}),
        encoding="utf-8",
    )
    return tmp_path


def test_create_section_writes_markdown_and_updates_chapter_yaml(seeded_library):
    writer = LibraryWriter()
    writer.create_section(
        book_id="uipath-docs",
        chapter_id="activities",
        section_id="retry-scope",
        section_title="Retry Scope",
        content="# Retry Scope\n\nRetries a scope.",
        keywords=["retry", "scope"],
    )

    md = seeded_library / "books/uipath-docs/chapters/01-activities/retry-scope.md"
    assert md.exists()
    assert "Retries a scope." in md.read_text(encoding="utf-8")

    ch_yaml = yaml.safe_load(
        (seeded_library / "books/uipath-docs/chapters/01-activities/chapter.yaml")
        .read_text(encoding="utf-8")
    )
    ids = [s["id"] for s in ch_yaml["sections"]]
    assert "retry-scope" in ids


def test_create_section_is_idempotent_on_same_content(seeded_library):
    writer = LibraryWriter()
    for _ in range(2):
        writer.create_section(
            book_id="uipath-docs", chapter_id="activities",
            section_id="retry-scope", section_title="Retry Scope",
            content="body", keywords=["retry"],
        )
    ch_yaml = yaml.safe_load(
        (seeded_library / "books/uipath-docs/chapters/01-activities/chapter.yaml")
        .read_text(encoding="utf-8")
    )
    assert [s["id"] for s in ch_yaml["sections"]] == ["retry-scope"]


def test_update_section_overwrites_content_only(seeded_library):
    writer = LibraryWriter()
    writer.create_section(
        book_id="uipath-docs", chapter_id="activities",
        section_id="retry-scope", section_title="Retry Scope",
        content="v1", keywords=["retry"],
    )
    writer.update_section(
        book_id="uipath-docs", chapter_id="activities",
        section_id="retry-scope", content="v2",
    )
    md = (seeded_library
          / "books/uipath-docs/chapters/01-activities/retry-scope.md")
    assert md.read_text(encoding="utf-8") == "v2"


def test_create_section_raises_for_unknown_book(seeded_library):
    writer = LibraryWriter()
    with pytest.raises(ValueError, match="book"):
        writer.create_section(
            book_id="nope", chapter_id="activities",
            section_id="x", section_title="X", content="", keywords=[],
        )


def test_create_section_raises_for_unknown_chapter(seeded_library):
    writer = LibraryWriter()
    with pytest.raises(ValueError, match="chapter"):
        writer.create_section(
            book_id="uipath-docs", chapter_id="nope",
            section_id="x", section_title="X", content="", keywords=[],
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/library/test_writer.py -v`
Expected: FAIL — `writer.py` doesn't exist.

- [ ] **Step 3: Implement `LibraryWriter`**

Create `uipath_claude/library/writer.py`:

```python
"""Write operations for the documentation library (sections + yaml)."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from uipath_claude.library.catalog import LibraryCatalog


class LibraryWriter:
    """Create/update sections and keep chapter.yaml in sync.

    Operates on the resolved library path from ``LibraryCatalog.get_library_path()``.
    """

    def __init__(self, library_path: Path | None = None) -> None:
        self.library_path = library_path or LibraryCatalog.get_library_path()

    def _book_dir(self, book_id: str) -> Path:
        catalog_file = self.library_path / "catalog.yaml"
        if not catalog_file.exists():
            raise ValueError(f"no catalog at {catalog_file}")
        data = yaml.safe_load(catalog_file.read_text(encoding="utf-8")) or {}
        for entry in data.get("books", []):
            if entry.get("id") == book_id:
                return self.library_path / entry["path"]
        raise ValueError(f"unknown book: {book_id}")

    def _chapter_dir(self, book_id: str, chapter_id: str) -> Path:
        book_dir = self._book_dir(book_id)
        book_yaml = book_dir / "book.yaml"
        data = yaml.safe_load(book_yaml.read_text(encoding="utf-8")) or {}
        for ch in data.get("chapters", []):
            if ch.get("id") == chapter_id:
                return book_dir / ch["path"]
        raise ValueError(f"unknown chapter: {chapter_id} in {book_id}")

    def create_section(
        self,
        *,
        book_id: str,
        chapter_id: str,
        section_id: str,
        section_title: str,
        content: str,
        keywords: Iterable[str],
    ) -> Path:
        """Create (or idempotently upsert) a section.

        Writes ``<section_id>.md`` and adds a stanza to ``chapter.yaml`` if absent.
        Returns the markdown file path.
        """
        chapter_dir = self._chapter_dir(book_id, chapter_id)
        md_path = chapter_dir / f"{section_id}.md"
        md_path.write_text(content, encoding="utf-8")

        chapter_yaml = chapter_dir / "chapter.yaml"
        data = yaml.safe_load(chapter_yaml.read_text(encoding="utf-8")) or {}
        sections = data.get("sections", [])
        if not any(s.get("id") == section_id for s in sections):
            sections.append({
                "id": section_id,
                "title": section_title,
                "file": f"{section_id}.md",
                "keywords": list(keywords),
            })
            data["sections"] = sections
            chapter_yaml.write_text(
                yaml.dump(data, default_flow_style=False, sort_keys=False),
                encoding="utf-8",
            )
        return md_path

    def update_section(
        self,
        *,
        book_id: str,
        chapter_id: str,
        section_id: str,
        content: str,
    ) -> Path:
        """Overwrite an existing section's markdown body. YAML is untouched."""
        chapter_dir = self._chapter_dir(book_id, chapter_id)
        md_path = chapter_dir / f"{section_id}.md"
        if not md_path.exists():
            raise ValueError(
                f"section does not exist: {book_id}/{chapter_id}/{section_id}"
            )
        md_path.write_text(content, encoding="utf-8")
        return md_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/library/test_writer.py -v`
Expected: all 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/library/writer.py tests/unit/library/test_writer.py
git commit -m "feat(library): add LibraryWriter for section create/update"
```

---

## Task 2: `ProposalStore` — enqueue, load, remove

**Files:**
- Create: `uipath_claude/library/proposals.py`
- Test: `tests/unit/library/test_proposals.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/library/test_proposals.py`:

```python
"""Tests for library proposal store."""
from pathlib import Path

import pytest

from uipath_claude.library.proposals import (
    LibraryProposal,
    PROPOSALS_ENV_VAR,
    ProposalKind,
    ProposalStatus,
    ProposalStore,
)


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path))
    return ProposalStore()


def _make(book_id="uipath-docs", section_id="s1", kind=ProposalKind.NEW_SECTION):
    return LibraryProposal(
        proposal_id="",  # assigned by store
        book_id=book_id,
        chapter_id="activities",
        section_id=section_id,
        section_title="Title",
        kind=kind,
        content="body",
        keywords=["k"],
        rationale="r",
    )


def test_enqueue_assigns_id_and_persists(store, tmp_path):
    p = store.enqueue(_make())
    assert p.proposal_id
    assert len(p.proposal_id) == 12
    assert (tmp_path / "uipath-docs.json").exists()


def test_list_returns_pending_only(store):
    p1 = store.enqueue(_make(section_id="a"))
    p2 = store.enqueue(_make(section_id="b"))
    store.mark_status(p1.proposal_id, ProposalStatus.APPROVED)
    pending = store.list_pending()
    ids = [p.proposal_id for p in pending]
    assert p2.proposal_id in ids
    assert p1.proposal_id not in ids


def test_get_by_id(store):
    p = store.enqueue(_make(section_id="x"))
    got = store.get(p.proposal_id)
    assert got is not None
    assert got.section_id == "x"


def test_remove_drops_proposal(store):
    p = store.enqueue(_make())
    store.remove(p.proposal_id)
    assert store.get(p.proposal_id) is None


def test_round_trip_survives_reload(store, tmp_path, monkeypatch):
    p = store.enqueue(_make(section_id="keep"))
    # New store instance, same dir
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path))
    fresh = ProposalStore()
    got = fresh.get(p.proposal_id)
    assert got is not None
    assert got.section_id == "keep"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/library/test_proposals.py -v`
Expected: FAIL — module doesn't exist.

- [ ] **Step 3: Implement `ProposalStore`**

Create `uipath_claude/library/proposals.py`:

```python
"""Proposal queue for library learning: proposed new/updated sections.

Storage: one JSON file per book at ``<proposals_root>/<book_id>.json``,
each file an array of proposal dicts. Default root is
``~/.uipath-claude/library-proposals/``; override with
``UIPATH_CLAUDE_LIBRARY_PROPOSALS``.
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional

PROPOSALS_ENV_VAR = "UIPATH_CLAUDE_LIBRARY_PROPOSALS"


class ProposalKind(str, Enum):
    NEW_SECTION = "new_section"
    UPDATE_SECTION = "update_section"


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
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
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
        return self.root / f"{book_id}.json"

    def _load(self, book_id: str) -> list[LibraryProposal]:
        path = self._book_file(book_id)
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/library/test_proposals.py -v`
Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/library/proposals.py tests/unit/library/test_proposals.py
git commit -m "feat(library): add ProposalStore for pending book updates"
```

---

## Task 3: Agent tool — `propose_library_update`

**Files:**
- Modify: `uipath_claude/tools/library_tools.py` (add the tool + include it in `get_library_tools`)
- Test: `tests/unit/tools/test_library_tools.py` (append new test; do not remove existing)

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/tools/test_library_tools.py`:

```python
import os
from pathlib import Path

from uipath_claude.library.proposals import (
    PROPOSALS_ENV_VAR,
    ProposalStatus,
    ProposalStore,
)
from uipath_claude.tools.library_tools import propose_library_update


def test_propose_library_update_enqueues_pending_proposal(tmp_path, monkeypatch):
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path))
    result = propose_library_update.invoke({
        "book_id": "uipath-docs",
        "chapter_id": "activities",
        "section_id": "retry-scope",
        "section_title": "Retry Scope",
        "content": "# Retry Scope\n\nDetails.",
        "keywords": ["retry", "scope"],
        "rationale": "Missing from library; came up this session.",
    })
    assert "proposal_id" in result
    store = ProposalStore()
    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0].section_id == "retry-scope"
    assert pending[0].status == ProposalStatus.PENDING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/tools/test_library_tools.py -v -k propose`
Expected: FAIL — `propose_library_update` not importable.

- [ ] **Step 3: Add the tool to `library_tools.py`**

Add at the bottom of `uipath_claude/tools/library_tools.py`, **before** `get_library_tools`:

```python
from uipath_claude.library.proposals import (
    LibraryProposal,
    ProposalKind,
    ProposalStore,
)


@tool
def propose_library_update(
    book_id: str,
    chapter_id: str,
    section_id: str,
    section_title: str,
    content: str,
    keywords: list[str],
    rationale: str = "",
) -> str:
    """Propose a new section (or update to an existing section) for a book.

    The proposal is enqueued for human approval. It does NOT modify the library
    directly. An operator must approve via ``uipath-claude library-proposals approve <id>``.

    Use this when you learned something during a session that would be durably
    useful across future runs (e.g. a corrected selector pattern, a missing
    activity nuance, a confirmed API contract).

    Args:
        book_id: The book identifier (e.g., 'uipath-docs').
        chapter_id: The chapter identifier (e.g., 'activities').
        section_id: A url-safe identifier for the new/updated section.
        section_title: Human-readable title.
        content: Full markdown body for the section.
        keywords: Search keywords (3-8 recommended).
        rationale: Short explanation of why this should be in the library.

    Returns a JSON string with the assigned ``proposal_id``.
    """
    import json
    store = ProposalStore()
    proposal = LibraryProposal(
        proposal_id="",
        book_id=book_id,
        chapter_id=chapter_id,
        section_id=section_id,
        section_title=section_title,
        kind=ProposalKind.NEW_SECTION,
        content=content,
        keywords=list(keywords),
        rationale=rationale,
    )
    saved = store.enqueue(proposal)
    return json.dumps({"proposal_id": saved.proposal_id, "status": "pending"})
```

Then update `get_library_tools` to include it:

```python
def get_library_tools() -> list[tool]:
    """Return the list of library tools for agent use."""
    return [
        list_library_books,
        browse_book_toc,
        read_section,
        search_library,
        propose_library_update,
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/tools/test_library_tools.py -v`
Expected: existing tests still pass, new test passes.

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/tools/library_tools.py tests/unit/tools/test_library_tools.py
git commit -m "feat(library): expose propose_library_update agent tool"
```

---

## Task 4: CLI — `library-proposals list|show|approve|reject`

**Files:**
- Create: `uipath_claude/commands/library_proposals.py` — `register_library_proposals_command(app: typer.Typer) -> None` registers a nested Typer with `app.add_typer(..., name="library-proposals")`. Handlers call `StructuredLogger` on approve/reject with `event` in `{"library_proposal_approved","library_proposal_rejected"}`.
- Modify: `uipath_claude/cli/app.py` — import and call `register_library_proposals_command(app)` once at module level after `app` is created.
- Test: `tests/unit/cli/test_library_proposals_cli.py` — extend env with `UIPATH_EVENT_LOG` pointing at a temp file; after approve/reject, assert the log file contains a line with the matching `event` key.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/cli/test_library_proposals_cli.py`:

```python
"""End-to-end tests for the library-proposals CLI subcommand."""
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def seeded_env(tmp_path, monkeypatch):
    library = tmp_path / "library"
    library.mkdir()
    (library / "catalog.yaml").write_text(
        yaml.dump({"version": 1, "books": [
            {"id": "uipath-docs", "title": "UiPath Docs",
             "path": "books/uipath-docs", "description": ""}
        ]}),
        encoding="utf-8",
    )
    book = library / "books" / "uipath-docs"
    book.mkdir(parents=True)
    (book / "book.yaml").write_text(
        yaml.dump({
            "id": "uipath-docs", "title": "UiPath Docs",
            "version": "1", "source": "test",
            "chapters": [{"id": "activities", "title": "Activities",
                          "path": "chapters/01-activities", "order": 1}],
        }),
        encoding="utf-8",
    )
    ch = book / "chapters" / "01-activities"
    ch.mkdir(parents=True)
    (ch / "chapter.yaml").write_text(
        yaml.dump({"id": "activities", "title": "Activities", "sections": []}),
        encoding="utf-8",
    )

    proposals = tmp_path / "proposals"
    env = {
        "UIPATH_CLAUDE_LIBRARY": str(library),
        "UIPATH_CLAUDE_LIBRARY_PROPOSALS": str(proposals),
    }
    return {"library": library, "proposals": proposals, "env": env}


def _run(args, env):
    import os
    result = subprocess.run(
        [sys.executable, "-m", "uipath_claude.cli.app", *args],
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )
    return result


def _enqueue_proposal(env):
    from uipath_claude.library.proposals import (
        LibraryProposal, ProposalKind, ProposalStore,
    )
    import os
    for k, v in env.items():
        os.environ[k] = v
    store = ProposalStore()
    return store.enqueue(LibraryProposal(
        proposal_id="",
        book_id="uipath-docs",
        chapter_id="activities",
        section_id="retry-scope",
        section_title="Retry Scope",
        kind=ProposalKind.NEW_SECTION,
        content="# Retry Scope\n\nbody",
        keywords=["retry"],
        rationale="came up",
    ))


def test_list_shows_pending_proposals(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(["library-proposals", "list"], seeded_env["env"])
    assert result.returncode == 0, result.stderr
    assert p.proposal_id in result.stdout
    assert "retry-scope" in result.stdout


def test_show_prints_full_proposal(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(
        ["library-proposals", "show", p.proposal_id], seeded_env["env"]
    )
    assert result.returncode == 0, result.stderr
    assert "Retry Scope" in result.stdout
    assert "came up" in result.stdout


def test_approve_applies_to_library_and_removes_proposal(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(
        ["library-proposals", "approve", p.proposal_id], seeded_env["env"]
    )
    assert result.returncode == 0, result.stderr

    md = (seeded_env["library"]
          / "books/uipath-docs/chapters/01-activities/retry-scope.md")
    assert md.exists()
    assert "body" in md.read_text(encoding="utf-8")

    ch_yaml = yaml.safe_load((seeded_env["library"]
        / "books/uipath-docs/chapters/01-activities/chapter.yaml"
    ).read_text(encoding="utf-8"))
    assert "retry-scope" in [s["id"] for s in ch_yaml["sections"]]

    follow = _run(["library-proposals", "list"], seeded_env["env"])
    assert p.proposal_id not in follow.stdout


def test_reject_drops_without_touching_library(seeded_env):
    p = _enqueue_proposal(seeded_env["env"])
    result = _run(
        ["library-proposals", "reject", p.proposal_id], seeded_env["env"]
    )
    assert result.returncode == 0, result.stderr

    md = (seeded_env["library"]
          / "books/uipath-docs/chapters/01-activities/retry-scope.md")
    assert not md.exists()

    follow = _run(["library-proposals", "list"], seeded_env["env"])
    assert p.proposal_id not in follow.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/cli/test_library_proposals_cli.py -v`
Expected: FAIL — subcommand unknown.

- [ ] **Step 3: Implement the CLI subcommand**

First, read the existing CLI to match its framework:

Run: `Get-Content uipath_claude\cli\app.py | Select-Object -First 40`

If Typer is used (you see `import typer` and `app = typer.Typer(...)`), create `uipath_claude/cli/library_proposals.py`:

```python
"""`library-proposals` subcommand: review and apply proposed book updates."""
from __future__ import annotations

import json

import typer

from uipath_claude.library.proposals import ProposalStatus, ProposalStore
from uipath_claude.library.writer import LibraryWriter

app = typer.Typer(help="Review, approve, or reject proposed library updates.")


@app.command("list")
def list_cmd() -> None:
    """List pending proposals across all books."""
    store = ProposalStore()
    pending = store.list_pending()
    if not pending:
        typer.echo("No pending proposals.")
        return
    for p in pending:
        typer.echo(
            f"{p.proposal_id}  {p.book_id}/{p.chapter_id}/{p.section_id}  "
            f"[{p.kind.value}]  {p.section_title}"
        )


@app.command("show")
def show_cmd(proposal_id: str) -> None:
    """Show a proposal in full, including the proposed markdown."""
    store = ProposalStore()
    p = store.get(proposal_id)
    if not p:
        typer.echo(f"Proposal not found: {proposal_id}", err=True)
        raise typer.Exit(code=1)
    summary = {
        "proposal_id": p.proposal_id,
        "book_id": p.book_id,
        "chapter_id": p.chapter_id,
        "section_id": p.section_id,
        "section_title": p.section_title,
        "kind": p.kind.value,
        "status": p.status.value,
        "keywords": p.keywords,
        "rationale": p.rationale,
        "created_at": p.created_at,
    }
    typer.echo(json.dumps(summary, indent=2))
    typer.echo("---")
    typer.echo(p.content)


@app.command("approve")
def approve_cmd(proposal_id: str) -> None:
    """Apply a proposal to the library, then remove it from the queue."""
    store = ProposalStore()
    p = store.get(proposal_id)
    if not p:
        typer.echo(f"Proposal not found: {proposal_id}", err=True)
        raise typer.Exit(code=1)

    writer = LibraryWriter()
    writer.create_section(
        book_id=p.book_id,
        chapter_id=p.chapter_id,
        section_id=p.section_id,
        section_title=p.section_title,
        content=p.content,
        keywords=p.keywords,
    )
    store.remove(proposal_id)
    typer.echo(f"Applied: {p.book_id}/{p.chapter_id}/{p.section_id}")


@app.command("reject")
def reject_cmd(proposal_id: str) -> None:
    """Drop a proposal without applying it."""
    store = ProposalStore()
    if not store.remove(proposal_id):
        typer.echo(f"Proposal not found: {proposal_id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Rejected: {proposal_id}")
```

Then in `uipath_claude/cli/app.py`, after the existing Typer app is created, register the subgroup. Find the line that looks like `app = typer.Typer(...)` and add these two lines immediately after:

```python
from uipath_claude.cli import library_proposals as _library_proposals
app.add_typer(_library_proposals.app, name="library-proposals")
```

If `app.py` uses **argparse** instead (no `typer` import), create the same file but use argparse subparsers; wire them in by adding a `library-proposals` subparser group in `app.py` that dispatches to the four functions above (`list_cmd`, `show_cmd(proposal_id)`, `approve_cmd(proposal_id)`, `reject_cmd(proposal_id)`) with bodies identical to the Typer version except for I/O (`print` instead of `typer.echo`, `sys.exit(1)` instead of `raise typer.Exit(code=1)`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/cli/test_library_proposals_cli.py -v`
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/cli/library_proposals.py uipath_claude/cli/app.py tests/unit/cli/test_library_proposals_cli.py
git commit -m "feat(cli): add library-proposals list/show/approve/reject"
```

---

## Task 5: Operator documentation

**Files:**
- Create: `docs/LIBRARY_LEARNING.md`
- Modify: `README.md` (add one paragraph + link)

- [ ] **Step 1: Write a presence test**

Create `tests/unit/meta/test_docs_presence.py`:

```python
"""Presence tests for operator docs."""
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/meta/test_docs_presence.py -v`
Expected: FAIL — doc missing, no README link.

- [ ] **Step 3: Write the operator doc**

Create `docs/LIBRARY_LEARNING.md`:

```markdown
# Library Learning Loop

The agent's documentation library (`data/library/`) is curated. To let
sessions contribute durable knowledge without letting them edit books
directly, we use a **proposal → review → approve** loop.

## Lifecycle

1. During a session the agent calls the `propose_library_update` tool
   when it has synthesized something worth keeping (e.g. a confirmed
   gotcha, a missing activity note).
2. The proposal is written to the queue at
   `~/.uipath-claude/library-proposals/<book_id>.json` (override path with
   `UIPATH_CLAUDE_LIBRARY_PROPOSALS`).
3. An operator reviews with the CLI and approves or rejects.
4. Approved proposals are applied by `LibraryWriter` into
   `data/library/` so they land as a reviewable git diff.

## CLI

```
uipath-claude library-proposals list
uipath-claude library-proposals show <proposal_id>
uipath-claude library-proposals approve <proposal_id>
uipath-claude library-proposals reject <proposal_id>
```

- `list` — show pending proposals across all books.
- `show` — print the proposal's metadata and full markdown body.
- `approve` — apply the proposal to `data/library/` and dequeue it.
- `reject` — dequeue the proposal without touching the library.

## Agent tool

The agent exposes one tool for proposing updates:

- `propose_library_update(book_id, chapter_id, section_id, section_title,
  content, keywords, rationale)` — enqueue a pending proposal. Returns a
  JSON string with the assigned `proposal_id`.

The tool **never** modifies the library; only an operator approval does.

## Environment variables

| Var | Purpose | Default |
|---|---|---|
| `UIPATH_CLAUDE_LIBRARY` | Library root | `<repo>/data/library` |
| `UIPATH_CLAUDE_LIBRARY_CACHE` | Query-cache root | `~/.uipath-claude/library-cache` |
| `UIPATH_CLAUDE_LIBRARY_PROPOSALS` | Proposal queue root | `~/.uipath-claude/library-proposals` |

## Why not auto-apply?

Books are surfaced verbatim into agent prompts; wrong content poisons
future sessions. Human review is cheap (a few lines of markdown per
proposal) and the approval step produces a normal git commit in
`data/library/`, which means every learning is versioned and reversible.
```

- [ ] **Step 4: Add README link**

In `README.md`, append this paragraph to the "Runtime data locations" section (added by the library-relocate plan; if that plan hasn't been executed yet, add it to whatever "Documentation" section exists):

```markdown
### Library learning loop

The library can accept new/updated content via a proposal + approval flow.
See [`docs/LIBRARY_LEARNING.md`](docs/LIBRARY_LEARNING.md) for the CLI and
agent tool.
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/meta/test_docs_presence.py -v`
Expected: both tests pass.

- [ ] **Step 6: Commit**

```bash
git add docs/LIBRARY_LEARNING.md README.md tests/unit/meta/test_docs_presence.py
git commit -m "docs(library): document learning-loop proposal/approval flow"
```

---

## Self-Review

**1. Spec coverage:**

| Goal component | Task |
|---|---|
| Writer API (create/update sections + yaml sync) | Task 1 |
| Proposal queue persistence | Task 2 |
| Agent-facing tool to propose | Task 3 |
| Human approval CLI | Task 4 |
| Operator documentation | Task 5 |

The goal ("sessions propose, humans approve, library absorbs") is covered end-to-end.

**2. Placeholder scan:** no TBD/TODO; every code step is complete; CLI Typer/argparse branch is explicit not vague.

**3. Type consistency:**
- `LibraryProposal` — same field list everywhere it's constructed (Tasks 2, 3, 4). `proposal_id=""` used at enqueue sites; store always re-assigns.
- `ProposalKind` / `ProposalStatus` — enum values quoted consistently as `.value` strings in JSON.
- `ProposalStore` API — `enqueue`, `list_pending`, `get`, `mark_status`, `remove` are the same names in Tasks 2, 3, 4.
- `LibraryWriter.create_section(**kwargs)` — same keyword set in Task 1 definition, Task 4 CLI approve call.
- Env vars — `UIPATH_CLAUDE_LIBRARY_PROPOSALS` spelled identically in `proposals.py`, tests, and docs.
- `parents[3]` for repo-root resolution consistent across test files at depth 3.

Plan ready.

---

## Execution Handoff

Both plans are complete and saved:

- `docs/superpowers/plans/2026-04-17-library-relocate-to-repo.md`
- `docs/superpowers/plans/2026-04-17-books-learning-loop.md`

**Recommended order:** run the relocate plan first, then the learning-loop plan (the learning loop's approval step assumes the library lives in the repo so approvals produce git diffs).
