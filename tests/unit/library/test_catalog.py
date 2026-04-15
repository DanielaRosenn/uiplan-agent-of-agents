"""Tests for library catalog."""
import pytest
from uipath_claude.library.catalog import Section, Chapter, Book, LibraryCatalog


def test_section_dataclass():
    section = Section(id="test", title="Test Section", file="test.md")
    assert section.id == "test"
    assert section.keywords == []


def test_chapter_dataclass():
    chapter = Chapter(id="ch1", title="Chapter 1", path="ch1", order=1)
    assert chapter.sections == []


def test_catalog_empty_when_no_library():
    catalog = LibraryCatalog.load()
    assert isinstance(catalog.books, list)


def test_get_book_returns_none_for_missing():
    catalog = LibraryCatalog(books=[])
    assert catalog.get_book("nonexistent") is None


def test_search_sections_empty_when_no_books():
    catalog = LibraryCatalog(books=[])
    results = catalog.search_sections("test")
    assert results == []
