from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from app.schemas import LibraryContextItem

_log = logging.getLogger(__name__)


def _ensure_framework_on_path() -> None:
    import sys

    repo_root = Path(__file__).resolve().parents[3]
    framework_dir = repo_root / "framework"
    if framework_dir.is_dir() and str(framework_dir) not in sys.path:
        sys.path.insert(0, str(framework_dir))


def _trim_snippet(text: str, limit: int = 240) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[: limit - 3]}..."


def _iter_context_items(
    rows: Iterable[tuple[object, object, object, int]],
    reader: object,
    top_n: int,
) -> list[LibraryContextItem]:
    items: list[LibraryContextItem] = []
    for index, row in enumerate(rows):
        book, chapter, section, score = row
        full_text = reader.read_section(book.id, chapter.id, section.id) or ""
        snippet = _trim_snippet(full_text) if full_text else section.title
        items.append(
            LibraryContextItem(
                book_id=book.id,
                chapter_id=chapter.id,
                section_id=section.id,
                score=score,
                snippet=snippet,
                full_text=full_text if index == 0 else None,
            )
        )
        if len(items) >= top_n:
            break
    return items


def search_library_context(query: str, top_n: int = 5) -> list[LibraryContextItem]:
    normalized_query = query.strip()
    if not normalized_query:
        return []

    _ensure_framework_on_path()
    try:
        from uipath_claude.library.catalog import LibraryCatalog
        from uipath_claude.library.reader import LibraryReader
    except Exception:
        _log.warning("Library framework unavailable; search returns empty results")
        return []

    effective_top_n = max(1, min(top_n, 20))
    catalog = LibraryCatalog.load()
    reader = LibraryReader(catalog=catalog)
    scored = catalog.search_sections_scored(normalized_query)
    return _iter_context_items(scored, reader, effective_top_n)
