"""Library catalog management."""
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

LIBRARY_PATH_ENV_VAR = "UIPATH_CLAUDE_LIBRARY"


@dataclass
class Section:
    """A section within a chapter."""

    id: str
    title: str
    file: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class Chapter:
    """A chapter within a book."""

    id: str
    title: str
    path: str
    order: int
    sections: list[Section] = field(default_factory=list)


@dataclass
class BookManifest:
    """Optional per-book metadata loaded from ``MANIFEST.yaml``."""

    audience: str = ""  # "agent" | "human" | ""
    curator: str = ""
    last_reviewed: str = ""
    homepage: str = ""
    license: str = ""


@dataclass
class Book:
    """A documentation book."""

    id: str
    title: str
    path: str
    description: str = ""
    version: str = ""
    source: str = ""
    chapters: list[Chapter] = field(default_factory=list)
    manifest: BookManifest = field(default_factory=BookManifest)


@dataclass
class LibraryCatalog:
    """Library catalog containing all books."""

    books: list[Book] = field(default_factory=list)

    @classmethod
    def _default_library_path(cls) -> Path:
        """Repo-relative default: ``<repo>/data/library``.

        ``catalog.py`` lives at ``<repo>/uipath_claude/library/catalog.py``;
        ``parents[2]`` is the repository root.
        """
        return Path(__file__).resolve().parents[2] / "data" / "library"

    @classmethod
    def get_library_path(cls) -> Path:
        """Get the library root path.

        Resolves in this order:
        1. ``UIPATH_CLAUDE_LIBRARY`` environment variable, if set.
        2. Repo-relative default: ``<repo>/data/library``.
        """
        override = os.environ.get(LIBRARY_PATH_ENV_VAR)
        if override:
            return Path(override).expanduser()
        return cls._default_library_path()

    @classmethod
    def load(cls) -> "LibraryCatalog":
        """Load catalog from disk."""
        library_path = cls.get_library_path()
        catalog_file = library_path / "catalog.yaml"

        if not catalog_file.exists():
            return cls(books=[])

        with open(catalog_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        books = []
        for book_entry in data.get("books", []):
            book_path = library_path / book_entry["path"]
            book_file = book_path / "book.yaml"

            if book_file.exists():
                with open(book_file, encoding="utf-8") as f:
                    book_data = yaml.safe_load(f) or {}

                chapters = []
                for ch in book_data.get("chapters", []):
                    chapter_path = book_path / ch["path"]
                    chapter_file = chapter_path / "chapter.yaml"

                    sections = []
                    if chapter_file.exists():
                        with open(chapter_file, encoding="utf-8") as f:
                            ch_data = yaml.safe_load(f) or {}
                        for sec in ch_data.get("sections", []):
                            sections.append(
                                Section(
                                    id=sec["id"],
                                    title=sec["title"],
                                    file=sec["file"],
                                    keywords=sec.get("keywords", []),
                                )
                            )

                    chapters.append(
                        Chapter(
                            id=ch["id"],
                            title=ch["title"],
                            path=ch["path"],
                            order=ch.get("order", 0),
                            sections=sections,
                        )
                    )

                manifest = BookManifest()
                manifest_file = book_path / "MANIFEST.yaml"
                if manifest_file.exists():
                    try:
                        with open(manifest_file, encoding="utf-8") as f:
                            m = yaml.safe_load(f) or {}
                        manifest = BookManifest(
                            audience=str(m.get("audience", "")),
                            curator=str(m.get("curator", "")),
                            last_reviewed=str(m.get("last_reviewed", "")),
                            homepage=str(m.get("homepage", "")),
                            license=str(m.get("license", "")),
                        )
                    except (OSError, yaml.YAMLError):
                        manifest = BookManifest()

                books.append(
                    Book(
                        id=book_data.get("id", book_entry["id"]),
                        title=book_data.get("title", book_entry["title"]),
                        path=book_entry["path"],
                        description=book_entry.get("description", ""),
                        version=book_data.get("version", ""),
                        source=book_data.get("source", ""),
                        chapters=chapters,
                        manifest=manifest,
                    )
                )

        return cls(books=books)

    def get_book(self, book_id: str) -> Book | None:
        """Get a book by ID."""
        for book in self.books:
            if book.id == book_id:
                return book
        return None

    def search_sections(self, query: str) -> list[tuple[Book, Chapter, Section]]:
        """Search sections by keyword.

        Backwards-compatible wrapper around :meth:`search_sections_scored` that
        drops the score so existing callers keep working.
        """
        return [(b, c, s) for b, c, s, _ in self.search_sections_scored(query)]

    def search_sections_scored(
        self, query: str
    ) -> list[tuple[Book, Chapter, Section, int]]:
        """Tokenized, ranked section search.

        The query is split on whitespace; each token contributes to a score when
        it appears (case-insensitively) as a substring of the section title,
        any keyword, the chapter title, or the book title. Keyword and section
        title hits are weighted slightly higher so the most relevant sections
        sort first. Sections with score 0 are dropped.
        """
        tokens = [t for t in query.lower().split() if t]
        if not tokens:
            return []

        scored: list[tuple[Book, Chapter, Section, int]] = []
        for book in self.books:
            book_title = book.title.lower()
            for chapter in book.chapters:
                chapter_title = chapter.title.lower()
                for section in chapter.sections:
                    section_title = section.title.lower()
                    keyword_blob = " ".join(k.lower() for k in section.keywords)
                    score = 0
                    for tok in tokens:
                        if tok in section_title:
                            score += 3
                        if tok in keyword_blob:
                            score += 3
                        if tok in chapter_title:
                            score += 1
                        if tok in book_title:
                            score += 1
                    if score > 0:
                        scored.append((book, chapter, section, score))

        scored.sort(key=lambda r: r[3], reverse=True)
        return scored
