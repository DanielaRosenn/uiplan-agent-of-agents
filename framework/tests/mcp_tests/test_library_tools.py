"""Tests for the uipath_library_* MCP tools."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

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
        "uipath_library_propose_section",
        "uipath_library_propose_chapter",
        "uipath_library_list_proposals",
        "uipath_library_approve_proposal",
        "uipath_library_reject_proposal",
    } <= names


def test_mcp_library_tools_register_propose_endpoints():
    names = {t.name for t in get_library_tools()}
    assert {
        "uipath_library_propose_section",
        "uipath_library_propose_chapter",
    } <= names


def test_mcp_library_tools_descriptions_meet_min_length():
    for tool in get_library_tools():
        assert len(tool.description) >= 60, (
            f"{tool.name} description too thin: {tool.description!r}"
        )
        assert "uipath" in tool.description.lower(), (
            f"{tool.name} description should mention UiPath: {tool.description!r}"
        )


def test_mcp_library_search_schema_has_top_n():
    search = next(t for t in get_library_tools() if t.name == "uipath_library_search")
    props = search.inputSchema["properties"]
    assert "top_n" in props
    assert props["top_n"]["type"] == "integer"


def test_mcp_lookup_schema_documents_allow_network_default():
    lookup = next(t for t in get_library_tools() if t.name == "uipath_library_lookup")
    props = lookup.inputSchema["properties"]
    assert props["allow_network"].get("default") is True


def test_mcp_doc_tools_register_query_uipath_docs():
    from mcp_server.tools.doc_tools import get_doc_tools

    names = {t.name for t in get_doc_tools()}
    assert "query_uipath_docs" in names
    assert "uipath_doc_query" in names  # deprecated alias retained


@pytest.mark.asyncio
async def test_call_list_delegates_to_tool():
    out = await call_library_tool("uipath_library_list", {})
    assert isinstance(out, str)


@pytest.mark.asyncio
async def test_call_search_passes_top_n_through(monkeypatch):
    captured: dict = {}

    def fake_search(query, top_n=5):
        captured["query"] = query
        captured["top_n"] = top_n
        return "ok"

    from mcp_server.tools import library_tools as lt

    monkeypatch.setattr(lt._search_library, "func", fake_search)
    await call_library_tool(
        "uipath_library_search", {"query": "orchestrator schedule", "top_n": 3}
    )
    assert captured == {"query": "orchestrator schedule", "top_n": 3}


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


@pytest.mark.asyncio
async def test_toc_delegates(monkeypatch):
    from mcp_server.tools import library_tools as lt

    fake_tool = MagicMock()
    fake_tool.invoke = MagicMock(return_value={"book": "uipath-docs"})
    monkeypatch.setattr(lt, "_browse_book_toc", fake_tool)
    out = await call_library_tool("uipath_library_toc", {"book_id": "uipath-docs"})
    assert out == {"book": "uipath-docs"}
    fake_tool.invoke.assert_called_once_with({"book_id": "uipath-docs"})


@pytest.mark.asyncio
async def test_read_section_delegates(monkeypatch):
    from mcp_server.tools import library_tools as lt

    fake_tool = MagicMock()
    fake_tool.invoke = MagicMock(return_value="# Section\n")
    monkeypatch.setattr(lt, "_read_section", fake_tool)
    out = await call_library_tool(
        "uipath_library_read_section",
        {
            "book_id": "uipath-docs",
            "chapter_id": "orch",
            "section_id": "intro",
        },
    )
    assert out == "# Section\n"
    fake_tool.invoke.assert_called_once_with(
        {
            "book_id": "uipath-docs",
            "chapter_id": "orch",
            "section_id": "intro",
        }
    )


@pytest.mark.asyncio
async def test_lookup_delegates(monkeypatch):
    from mcp_server.tools import library_tools as lt

    fake_tool = MagicMock()
    fake_tool.invoke = MagicMock(return_value="answer from lookup")
    monkeypatch.setattr(lt, "_lookup_knowledge", fake_tool)
    out = await call_library_tool(
        "uipath_library_lookup",
        {"question": "retry scope?", "allow_network": False},
    )
    assert out == "answer from lookup"
    fake_tool.invoke.assert_called_once_with(
        {"question": "retry scope?", "allow_network": False}
    )


@pytest.mark.asyncio
async def test_propose_chapter_delegates(monkeypatch):
    from mcp_server.tools import library_tools as lt

    fake_tool = MagicMock()
    fake_tool.invoke = MagicMock(return_value="queued chapter")
    monkeypatch.setattr(lt, "_propose_library_chapter", fake_tool)
    out = await call_library_tool(
        "uipath_library_propose_chapter",
        {
            "book_id": "demo",
            "chapter_id": "ch-new",
            "chapter_title": "New chapter",
            "order": 10,
            "rationale": "test",
            "initial_sections_json": "[]",
        },
    )
    assert out == "queued chapter"
    assert fake_tool.invoke.call_count == 1


@pytest.mark.asyncio
async def test_list_proposals_empty_message(tmp_path, monkeypatch):
    from uipath_claude.library.proposals import PROPOSALS_ENV_VAR

    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path / "empty_props"))
    out = await call_library_tool("uipath_library_list_proposals", {})
    assert "no pending" in str(out).lower()
