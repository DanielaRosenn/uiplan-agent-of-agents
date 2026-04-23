"""Tests for LibraryWriter."""
from pathlib import Path

import pytest
import yaml

from uipath_claude.library.writer import LibraryWriter


@pytest.fixture
def seeded_library(tmp_path, monkeypatch):
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(tmp_path))
    (tmp_path / "catalog.yaml").write_text(
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
    book = tmp_path / "books" / "uipath-docs"
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
    return tmp_path


def test_create_section_writes_markdown_and_updates_chapter_yaml(seeded_library):
    writer = LibraryWriter()
    writer.create_section(
        book_id="uipath-docs",
        chapter_id="activities",
        section_id="retry-scope",
        section_title="Retry Scope",
        content="# Retry Scope\n\nRetries a scope.",
        keywords=["retry", "scope"],
    )

    md = seeded_library / "books/uipath-docs/chapters/01-activities/retry-scope.md"
    assert md.exists()
    assert "Retries a scope." in md.read_text(encoding="utf-8")

    ch_yaml = yaml.safe_load(
        (
            seeded_library / "books/uipath-docs/chapters/01-activities/chapter.yaml"
        ).read_text(encoding="utf-8")
    )
    ids = [s["id"] for s in ch_yaml["sections"]]
    assert "retry-scope" in ids


def test_create_section_is_idempotent_on_same_content(seeded_library):
    writer = LibraryWriter()
    for _ in range(2):
        writer.create_section(
            book_id="uipath-docs",
            chapter_id="activities",
            section_id="retry-scope",
            section_title="Retry Scope",
            content="body",
            keywords=["retry"],
        )
    ch_yaml = yaml.safe_load(
        (
            seeded_library / "books/uipath-docs/chapters/01-activities/chapter.yaml"
        ).read_text(encoding="utf-8")
    )
    assert [s["id"] for s in ch_yaml["sections"]] == ["retry-scope"]


def test_update_section_overwrites_content_only(seeded_library):
    writer = LibraryWriter()
    writer.create_section(
        book_id="uipath-docs",
        chapter_id="activities",
        section_id="retry-scope",
        section_title="Retry Scope",
        content="v1",
        keywords=["retry"],
    )
    writer.update_section(
        book_id="uipath-docs",
        chapter_id="activities",
        section_id="retry-scope",
        content="v2",
    )
    md = seeded_library / "books/uipath-docs/chapters/01-activities/retry-scope.md"
    assert md.read_text(encoding="utf-8") == "v2"


def test_create_section_raises_for_unknown_book(seeded_library):
    writer = LibraryWriter()
    with pytest.raises(ValueError, match="unknown book"):
        writer.create_section(
            book_id="nope",
            chapter_id="activities",
            section_id="x",
            section_title="X",
            content="",
            keywords=[],
        )


def test_create_section_raises_for_unknown_chapter(seeded_library):
    writer = LibraryWriter()
    with pytest.raises(ValueError, match="unknown chapter"):
        writer.create_section(
            book_id="uipath-docs",
            chapter_id="nope",
            section_id="x",
            section_title="X",
            content="",
            keywords=[],
        )


def test_create_section_rejects_path_traversal_in_section_id(seeded_library):
    writer = LibraryWriter()
    with pytest.raises(ValueError, match="invalid section_id"):
        writer.create_section(
            book_id="uipath-docs",
            chapter_id="activities",
            section_id="../evil",
            section_title="X",
            content="",
            keywords=[],
        )
