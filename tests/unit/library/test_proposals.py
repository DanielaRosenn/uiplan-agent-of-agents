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
        proposal_id="",
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
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path))
    fresh = ProposalStore()
    got = fresh.get(p.proposal_id)
    assert got is not None
    assert got.section_id == "keep"
