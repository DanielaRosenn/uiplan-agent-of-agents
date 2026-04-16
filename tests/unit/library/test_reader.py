"""Tests for library reader, especially cache path independence."""
from pathlib import Path

import pytest

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.reader import (
    LIBRARY_CACHE_ENV_VAR,
    LibraryReader,
)


def test_default_cache_path_is_user_scoped(monkeypatch):
    monkeypatch.delenv(LIBRARY_CACHE_ENV_VAR, raising=False)
    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    assert reader.cache_path == Path.home() / ".uipath-claude" / "library-cache"


def test_cache_path_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(tmp_path / "cache"))
    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    assert reader.cache_path == tmp_path / "cache"


def test_cache_path_constructor_arg_wins(monkeypatch, tmp_path):
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(tmp_path / "env"))
    explicit = tmp_path / "explicit"
    reader = LibraryReader(catalog=LibraryCatalog(books=[]), cache_path=explicit)
    assert reader.cache_path == explicit


def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(tmp_path))
    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    assert reader.get_cached_response("hello") is None
    reader.cache_response("hello", "world")
    assert reader.get_cached_response("hello") == "world"


def test_cache_does_not_touch_library_dir(tmp_path, monkeypatch):
    library_root = tmp_path / "library"
    library_root.mkdir()
    cache_root = tmp_path / "cache"
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(library_root))
    monkeypatch.setenv(LIBRARY_CACHE_ENV_VAR, str(cache_root))

    reader = LibraryReader(catalog=LibraryCatalog(books=[]))
    reader.cache_response("x", "y")

    assert list(library_root.rglob("*")) == []
    assert any(cache_root.rglob("*.json"))
