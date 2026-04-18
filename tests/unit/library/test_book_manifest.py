"""Tests for book MANIFEST.yaml support."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from uipath_claude.library.catalog import LIBRARY_PATH_ENV_VAR, LibraryCatalog


@pytest.fixture
def lib_with_manifest(tmp_path, monkeypatch):
    root = tmp_path / "library"
    book_dir = root / "books" / "demo-book"
    chapter_dir = book_dir / "chapters" / "01-intro"
    chapter_dir.mkdir(parents=True)

    (root / "catalog.yaml").write_text(
        yaml.dump({"books": [{"id": "demo-book", "path": "books/demo-book", "title": "Demo"}]}),
        encoding="utf-8",
    )
    (book_dir / "book.yaml").write_text(
        yaml.dump(
            {
                "id": "demo-book",
                "title": "Demo Book",
                "chapters": [
                    {"id": "intro", "title": "Intro", "path": "chapters/01-intro", "order": 1}
                ],
            }
        ),
        encoding="utf-8",
    )
    (chapter_dir / "chapter.yaml").write_text(
        yaml.dump({"id": "intro", "title": "Intro", "sections": []}),
        encoding="utf-8",
    )
    (book_dir / "MANIFEST.yaml").write_text(
        yaml.dump(
            {
                "audience": "agent",
                "curator": "daniela",
                "last_reviewed": "2026-04-18",
                "homepage": "https://example.com",
                "license": "MIT",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv(LIBRARY_PATH_ENV_VAR, str(root))
    return root


def test_catalog_loads_manifest(lib_with_manifest):
    catalog = LibraryCatalog.load()
    assert len(catalog.books) == 1
    book = catalog.books[0]
    assert book.manifest.audience == "agent"
    assert book.manifest.curator == "daniela"
    assert book.manifest.homepage == "https://example.com"


def test_catalog_tolerates_missing_manifest(tmp_path, monkeypatch):
    root = tmp_path / "library"
    book_dir = root / "books" / "no-man"
    book_dir.mkdir(parents=True)
    (root / "catalog.yaml").write_text(
        yaml.dump({"books": [{"id": "no-man", "path": "books/no-man", "title": "X"}]}),
        encoding="utf-8",
    )
    (book_dir / "book.yaml").write_text(
        yaml.dump({"id": "no-man", "title": "X", "chapters": []}),
        encoding="utf-8",
    )
    monkeypatch.setenv(LIBRARY_PATH_ENV_VAR, str(root))
    catalog = LibraryCatalog.load()
    assert catalog.books[0].manifest.audience == ""
