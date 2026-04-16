"""Tests for library tools."""
import pytest
from unittest.mock import MagicMock, patch

from uipath_claude.library.proposals import PROPOSALS_ENV_VAR, ProposalStatus, ProposalStore
from uipath_claude.tools.library_tools import (
    browse_book_toc,
    get_library_tools,
    list_library_books,
    propose_library_update,
    read_section,
    search_library,
)


def test_list_library_books_returns_string():
    result = list_library_books.invoke({})
    assert isinstance(result, str)


def test_search_library_returns_results_or_no_match():
    result = search_library.invoke({"query": "nonexistent12345"})
    assert "No matches" in result or "match" in result.lower()


def test_browse_book_toc_returns_error_for_missing_book():
    result = browse_book_toc.invoke({"book_id": "nonexistent"})
    assert "not found" in result.lower()


def test_read_section_returns_error_for_missing():
    result = read_section.invoke({"book_id": "x", "chapter_id": "y", "section_id": "z"})
    assert "not found" in result.lower()


def test_get_library_tools_returns_five_tools():
    tools = get_library_tools()
    assert len(tools) == 5


def test_get_library_tools_contains_expected_tools():
    tools = get_library_tools()
    tool_names = [t.name for t in tools]
    assert "list_library_books" in tool_names
    assert "browse_book_toc" in tool_names
    assert "read_section" in tool_names
    assert "search_library" in tool_names
    assert "propose_library_update" in tool_names


@patch("uipath_claude.tools.library_tools.LibraryCatalog")
def test_browse_book_toc_with_mock_book(mock_catalog_class):
    mock_section = MagicMock()
    mock_section.title = "Test Section"
    mock_section.keywords = ["keyword1", "keyword2"]

    mock_chapter = MagicMock()
    mock_chapter.title = "Test Chapter"
    mock_chapter.order = 1
    mock_chapter.sections = [mock_section]

    mock_book = MagicMock()
    mock_book.id = "test-book"
    mock_book.title = "Test Book"
    mock_book.version = "1.0"
    mock_book.source = "test"
    mock_book.chapters = [mock_chapter]

    mock_catalog = MagicMock()
    mock_catalog.get_book.return_value = mock_book
    mock_catalog_class.load.return_value = mock_catalog

    result = browse_book_toc.invoke({"book_id": "test-book"})

    assert "Test Book" in result
    assert "Test Chapter" in result
    assert "Test Section" in result


@patch("uipath_claude.tools.library_tools.LibraryReader")
def test_read_section_with_mock_content(mock_reader_class):
    mock_reader = MagicMock()
    mock_reader.read_section.return_value = "This is the section content."
    mock_reader_class.return_value = mock_reader

    result = read_section.invoke({
        "book_id": "test-book",
        "chapter_id": "test-chapter",
        "section_id": "test-section",
    })

    assert "This is the section content." in result
    assert "Source: test-book" in result
    mock_reader.read_section.assert_called_once_with(
        "test-book", "test-chapter", "test-section"
    )


@patch("uipath_claude.tools.library_tools.LibraryCatalog")
def test_list_library_books_empty_catalog(mock_catalog_class):
    mock_catalog = MagicMock()
    mock_catalog.books = []
    mock_catalog_class.load.return_value = mock_catalog

    result = list_library_books.invoke({})
    assert "No books found" in result


@patch("uipath_claude.tools.library_tools.LibraryCatalog")
def test_list_library_books_with_books(mock_catalog_class):
    mock_book = MagicMock()
    mock_book.id = "test-book"
    mock_book.title = "Test Book"
    mock_book.description = "A test book"
    mock_book.chapters = [MagicMock(), MagicMock()]

    mock_catalog = MagicMock()
    mock_catalog.books = [mock_book]
    mock_catalog_class.load.return_value = mock_catalog

    result = list_library_books.invoke({})
    assert "Test Book" in result
    assert "2 chapters" in result


def test_propose_library_update_enqueues_pending_proposal(tmp_path, monkeypatch):
    monkeypatch.setenv(PROPOSALS_ENV_VAR, str(tmp_path))
    result = propose_library_update.invoke(
        {
            "book_id": "uipath-docs",
            "chapter_id": "activities",
            "section_id": "retry-scope",
            "section_title": "Retry Scope",
            "content": "# Retry Scope\n\nDetails.",
            "keywords": ["retry", "scope"],
            "rationale": "Missing from library; came up this session.",
        }
    )
    assert "proposal_id" in result
    store = ProposalStore()
    pending = store.list_pending()
    assert len(pending) == 1
    assert pending[0].section_id == "retry-scope"
    assert pending[0].status == ProposalStatus.PENDING
