"""Tests for library catalog."""
from pathlib import Path

import pytest
from uipath_claude.library.catalog import (
    Book,
    Chapter,
    LibraryCatalog,
    LIBRARY_PATH_ENV_VAR,
    Section,
)


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


def test_get_library_path_defaults_to_repo_data_dir(monkeypatch):
    monkeypatch.delenv(LIBRARY_PATH_ENV_VAR, raising=False)
    expected = Path(__file__).resolve().parents[3] / "data" / "library"
    assert LibraryCatalog.get_library_path() == expected


def test_get_library_path_uses_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(LIBRARY_PATH_ENV_VAR, str(tmp_path))
    assert LibraryCatalog.get_library_path() == tmp_path


def test_get_library_path_expands_user(monkeypatch):
    monkeypatch.setenv(LIBRARY_PATH_ENV_VAR, "~/custom-library")
    expected = Path("~/custom-library").expanduser()
    assert LibraryCatalog.get_library_path() == expected


def test_load_uses_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(LIBRARY_PATH_ENV_VAR, str(tmp_path))
    catalog = LibraryCatalog.load()
    assert catalog.books == []
