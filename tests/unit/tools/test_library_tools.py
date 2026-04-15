"""Tests for library tools."""
import pytest
from unittest.mock import MagicMock, patch

from uipath_claude.tools.library_tools import (
    list_library_books,
    browse_book_toc,
    read_section,
    search_library,
)


def test_list_library_books_returns_string():
    result = list_library_books.invoke({})
    assert isinstance(result, str)


def test_search_library_returns_results_or_no_match():
    result = search_library.invoke({"query": "nonexistent12345"})
    assert "No matches" in result or "match" in result.lower()
