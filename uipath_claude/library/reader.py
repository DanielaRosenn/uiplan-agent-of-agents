"""Library section reader with caching."""
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import json

from uipath_claude.library.catalog import LibraryCatalog


class LibraryReader:
    """Read sections from the documentation library."""

    CACHE_TTL = timedelta(days=30)

    def __init__(self, catalog: LibraryCatalog | None = None):
        """Initialize reader with optional catalog."""
        self.catalog = catalog or LibraryCatalog.load()
        self.library_path = LibraryCatalog.get_library_path()

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

    def get_cached_response(self, query: str) -> str | None:
        """Check cache for a query response."""
        cache_dir = self.library_path / "books" / "uipath-docs" / "_cache"
        if not cache_dir.exists():
            return None

        cache_key = hashlib.md5(query.lower().encode()).hexdigest()
        cache_file = cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            return None

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data["cached_at"])

            if datetime.now() - cached_at > self.CACHE_TTL:
                return None

            return data["response"]
        except (json.JSONDecodeError, KeyError):
            return None

    def cache_response(self, query: str, response: str) -> None:
        """Cache a query response."""
        cache_dir = self.library_path / "books" / "uipath-docs" / "_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_key = hashlib.md5(query.lower().encode()).hexdigest()
        cache_file = cache_dir / f"{cache_key}.json"

        data = {
            "query": query,
            "response": response,
            "cached_at": datetime.now().isoformat(),
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
