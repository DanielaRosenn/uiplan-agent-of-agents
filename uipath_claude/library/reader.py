"""Library section reader with optional query-response caching."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from uipath_claude.library.catalog import LibraryCatalog

LIBRARY_CACHE_ENV_VAR = "UIPATH_CLAUDE_LIBRARY_CACHE"


def _default_cache_path() -> Path:
    """Default cache: ``~/.uipath-claude/library-cache`` (mutable, not in repo).

    Override with ``UIPATH_CLAUDE_LIBRARY_CACHE``.
    """
    override = os.environ.get(LIBRARY_CACHE_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".uipath-claude" / "library-cache"


class LibraryReader:
    """Read sections from the documentation library."""

    CACHE_TTL = timedelta(days=30)

    def __init__(
        self,
        catalog: LibraryCatalog | None = None,
        cache_path: Path | None = None,
    ) -> None:
        """Initialize reader.

        Args:
            catalog: Optional preloaded catalog.
            cache_path: Override for query-cache directory; else env or default.
        """
        self.catalog = catalog or LibraryCatalog.load()
        self.library_path = LibraryCatalog.get_library_path()
        self.cache_path = Path(cache_path) if cache_path else _default_cache_path()

    def read_section(
        self, book_id: str, chapter_id: str, section_id: str
    ) -> str | None:
        """Read a section's content."""
        book = self.catalog.get_book(book_id)
        if not book:
            return None

        chapter = None
        for ch in book.chapters:
            if ch.id == chapter_id:
                chapter = ch
                break

        if not chapter:
            return None

        section = None
        for sec in chapter.sections:
            if sec.id == section_id:
                section = sec
                break

        if not section:
            return None

        section_path = (
            self.library_path / book.path / chapter.path / section.file
        )

        if not section_path.exists():
            return None

        return section_path.read_text(encoding="utf-8")

    def _cache_file(self, query: str) -> Path:
        cache_key = hashlib.md5(query.lower().encode()).hexdigest()
        return self.cache_path / f"{cache_key}.json"

    def get_cached_response(self, query: str) -> str | None:
        """Return a cached response for ``query`` if present and within TTL."""
        cache_file = self._cache_file(query)
        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data["cached_at"])
            if datetime.now() - cached_at > self.CACHE_TTL:
                return None
            return data["response"]
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def cache_response(self, query: str, response: str) -> None:
        """Persist a query to response pair in the cache directory."""
        self.cache_path.mkdir(parents=True, exist_ok=True)
        cache_file = self._cache_file(query)
        data = {
            "query": query,
            "response": response,
            "cached_at": datetime.now().isoformat(),
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
