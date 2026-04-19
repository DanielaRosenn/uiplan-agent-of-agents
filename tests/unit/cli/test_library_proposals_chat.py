"""Unit tests for the in-chat /library-proposals slash command."""
from __future__ import annotations

import os

import pytest
import yaml

from uipath_claude.commands.library_proposals import (
    register_library_proposals_chat_command,
)
from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.library.proposals import (
    LibraryProposal,
    ProposalKind,
    ProposalStore,
)


@pytest.fixture
def seeded_env(tmp_path, monkeypatch):
    library = tmp_path / "library"
    library.mkdir()
    (library / "catalog.yaml").write_text(
        yaml.dump(
            {
                "version": 1,
                "books": [
                    {
                        "id": "uipath-docs",
                        "title": "UiPath Docs",
                        "path": "books/uipath-docs",
                        "description": "",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    book = library / "books" / "uipath-docs"
    book.mkdir(parents=True)
    (book / "book.yaml").write_text(
        yaml.dump(
            {
                "id": "uipath-docs",
                "title": "UiPath Docs",
                "version": "1",
                "source": "test",
                "chapters": [
                    {
                        "id": "activities",
                        "title": "Activities",
                        "path": "chapters/01-activities",
                        "order": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    ch = book / "chapters" / "01-activities"
    ch.mkdir(parents=True)
    (ch / "chapter.yaml").write_text(
        yaml.dump({"id": "activities", "title": "Activities", "sections": []}),
        encoding="utf-8",
    )

    proposals = tmp_path / "proposals"
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(library))
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY_PROPOSALS", str(proposals))
    monkeypatch.setenv("UIPATH_EVENT_LOG", str(tmp_path / "events.log"))
    return {"library": library, "proposals": proposals}


def _enqueue() -> LibraryProposal:
    return ProposalStore().enqueue(
        LibraryProposal(
            proposal_id="",
            book_id="uipath-docs",
            chapter_id="activities",
            section_id="retry-scope",
            section_title="Retry Scope",
            kind=ProposalKind.NEW_SECTION,
            content="# Retry Scope\n\nbody",
            keywords=["retry"],
            rationale="came up",
        )
    )


def _registry() -> CommandRegistry:
    reg = CommandRegistry()
    register_library_proposals_chat_command(reg)
    return reg


def test_default_lists_pending(seeded_env):
    p = _enqueue()
    out = _registry().execute("library-proposals")
    assert p.proposal_id in out
    assert "retry-scope" in out


def test_list_subcommand(seeded_env):
    p = _enqueue()
    out = _registry().execute("library-proposals", "list")
    assert p.proposal_id in out


def test_list_empty(seeded_env):
    out = _registry().execute("library-proposals", "list")
    assert "No pending proposals" in out


def test_show_returns_content(seeded_env):
    p = _enqueue()
    out = _registry().execute("library-proposals", "show", p.proposal_id)
    assert "Retry Scope" in out
    assert "came up" in out


def test_show_missing_id(seeded_env):
    out = _registry().execute("library-proposals", "show")
    assert "Usage" in out


def test_approve_applies_and_removes(seeded_env):
    p = _enqueue()
    out = _registry().execute("library-proposals", "approve", p.proposal_id)
    assert "Applied" in out
    md = (
        seeded_env["library"]
        / "books/uipath-docs/chapters/01-activities/retry-scope.md"
    )
    assert md.exists()
    follow = _registry().execute("library-proposals", "list")
    assert p.proposal_id not in follow


def test_reject_drops(seeded_env):
    p = _enqueue()
    out = _registry().execute("library-proposals", "reject", p.proposal_id)
    assert "Rejected" in out
    follow = _registry().execute("library-proposals", "list")
    assert p.proposal_id not in follow


def test_unknown_subcommand(seeded_env):
    out = _registry().execute("library-proposals", "frobnicate")
    assert "Unknown subcommand" in out
