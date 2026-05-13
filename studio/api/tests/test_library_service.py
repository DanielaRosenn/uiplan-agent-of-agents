from pathlib import Path

from app.library_service import search_library_context


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_search_library_context_returns_ranked_items(monkeypatch, tmp_path: Path) -> None:
    library_root = tmp_path / "library"
    _write_text(
        library_root / "catalog.yaml",
        """
books:
  - id: uipath-cli
    title: UiPath CLI
    path: books/uipath-cli
""".strip(),
    )
    _write_text(
        library_root / "books" / "uipath-cli" / "book.yaml",
        """
id: uipath-cli
title: UiPath CLI
chapters:
  - id: agent
    title: Agent
    path: chapters/agent
""".strip(),
    )
    _write_text(
        library_root / "books" / "uipath-cli" / "chapters" / "agent" / "chapter.yaml",
        """
sections:
  - id: deploy
    title: Deploy agent package
    file: deploy.md
    keywords: [deploy, publish]
""".strip(),
    )
    _write_text(
        library_root / "books" / "uipath-cli" / "chapters" / "agent" / "deploy.md",
        "Use uipath deploy for agent package deployment.",
    )
    monkeypatch.setenv("UIPATH_CLAUDE_LIBRARY", str(library_root))

    items = search_library_context("deploy package", top_n=5)
    assert len(items) == 1
    assert items[0].book_id == "uipath-cli"
    assert items[0].chapter_id == "agent"
    assert items[0].section_id == "deploy"
    assert items[0].score > 0
    assert items[0].full_text is not None


def test_search_library_context_handles_blank_query() -> None:
    assert search_library_context("   ", top_n=3) == []
