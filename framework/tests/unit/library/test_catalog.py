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
    expected = Path(__file__).resolve().parents[4] / "data" / "library"
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


def _build_catalog():
    sec_jobs = Section(
        id="jobs",
        title="Job Management",
        file="jobs.md",
        keywords=["job", "schedule", "trigger"],
    )
    sec_queues = Section(
        id="queues",
        title="Queue Operations",
        file="queues.md",
        keywords=["queue", "transaction"],
    )
    sec_unrelated = Section(
        id="excel",
        title="Excel Activities",
        file="excel.md",
        keywords=["readrange"],
    )
    ch_orch = Chapter(
        id="orchestrator",
        title="Orchestrator Guide",
        path="chapters/02-orchestrator",
        order=2,
        sections=[sec_jobs, sec_queues],
    )
    ch_act = Chapter(
        id="activities",
        title="Activities Reference",
        path="chapters/01-activities",
        order=1,
        sections=[sec_unrelated],
    )
    book = Book(
        id="uipath-docs",
        title="UiPath Documentation",
        path="books/uipath-docs",
        chapters=[ch_orch, ch_act],
    )
    return LibraryCatalog(books=[book])


def test_search_sections_multiword_phrase_matches_when_tokens_split_across_title_and_keywords():
    """The exact phrase 'orchestrator schedule' didn't match before tokenisation."""
    cat = _build_catalog()
    results = cat.search_sections("orchestrator schedule")
    ids = [s.id for _, _, s in results]
    assert "jobs" in ids


def test_search_sections_returns_score_ranked_results():
    cat = _build_catalog()
    scored = cat.search_sections_scored("orchestrator schedule")
    assert len(scored) >= 1
    section_ids = [s.id for _, _, s, _ in scored]
    assert section_ids[0] == "jobs"
    scores = [score for _, _, _, score in scored]
    assert scores == sorted(scores, reverse=True)


def test_search_sections_single_token_still_works():
    cat = _build_catalog()
    results = cat.search_sections("schedule")
    assert any(s.id == "jobs" for _, _, s in results)


def test_search_sections_empty_query_returns_no_results():
    cat = _build_catalog()
    assert cat.search_sections("   ") == []
    assert cat.search_sections_scored("") == []
