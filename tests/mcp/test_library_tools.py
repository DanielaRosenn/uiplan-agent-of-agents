"""Tests for the uipath_library_* MCP tools."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from mcp_server.tools.library_tools import call_library_tool, get_library_tools


def test_get_library_tools_names():
    names = {t.name for t in get_library_tools()}
    assert {
        "uipath_library_list",
        "uipath_library_toc",
        "uipath_library_read_section",
        "uipath_library_search",
        "uipath_library_lookup",
        "uipath_library_list_proposals",
        "uipath_library_approve_proposal",
        "uipath_library_reject_proposal",
    } <= names


@pytest.mark.asyncio
async def test_call_list_delegates_to_tool():
    out = await call_library_tool("uipath_library_list", {})
    assert isinstance(out, str)


@pytest.mark.asyncio
async def test_reject_missing_proposal_returns_message(tmp_path, monkeypatch):
    from uipath_claude.library.proposals import PROPOSALS_ENV_VAR

    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "props"))
    out = await call_library_tool(
        "uipath_library_reject_proposal", {"proposal_id": "does-not-exist"}
    )
    assert "not found" in out.lower()


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    with pytest.raises(ValueError):
        await call_library_tool("uipath_library_bogus", {})


@pytest.mark.asyncio
async def test_approve_proposal_happy_path(tmp_path, monkeypatch):
    """MCP approve must actually apply the proposal and clear the queue."""
    import yaml

    from uipath_claude.library.catalog import LIBRARY_PATH_ENV_VAR
    from uipath_claude.library.proposals import (
        PROPOSALS_ENV_VAR,
        LibraryProposal,
        ProposalKind,
        ProposalStore,
    )

    lib = tmp_path / "library"
    book = lib / "books" / "demo-book"
    chapter = book / "chapters" / "01-ch"
    chapter.mkdir(parents=True)
    (lib / "catalog.yaml").write_text(
        yaml.dump({"books": [{"id": "demo-book", "path": "books/demo-book", "title": "Demo"}]}),
        encoding="utf-8",
    )
    (book / "book.yaml").write_text(
        yaml.dump({
            "id": "demo-book",
            "title": "Demo",
            "chapters": [{"id": "ch", "title": "Ch", "path": "chapters/01-ch", "order": 1}],
        }),
        encoding="utf-8",
    )
    (chapter / "chapter.yaml").write_text(
        yaml.dump({"id": "ch", "title": "Ch", "sections": []}),
        encoding="utf-8",
    )
    monkeypatch.setenv(LIBRARY_PATH_ENV_VAR, str(lib))
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "props"))

    store = ProposalStore()
    store.enqueue(
        LibraryProposal(
            proposal_id="",
            book_id="demo-book",
            chapter_id="ch",
            section_id="hello",
            section_title="Hello",
            kind=ProposalKind.NEW_SECTION,
            content="# Hello\n",
            keywords=["hello"],
            rationale="test",
            source_session="test",
        )
    )
    pid = store.list_pending()[0].proposal_id

    out = await call_library_tool(
        "uipath_library_approve_proposal", {"proposal_id": pid}
    )
    assert "Applied" in out
    assert ProposalStore().get(pid) is None
    assert (chapter / "hello.md").exists()
