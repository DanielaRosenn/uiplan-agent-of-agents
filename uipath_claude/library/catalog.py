"""Library catalog management."""
from dataclasses import dataclass, field
from pathlib import Path

import yaml


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
class Book:
    """A documentation book."""

    id: str
    title: str
    path: str
    description: str = ""
    version: str = ""
    source: str = ""
    chapters: list[Chapter] = field(default_factory=list)


@dataclass
class LibraryCatalog:
    """Library catalog containing all books."""

    books: list[Book] = field(default_factory=list)

    @classmethod
    def get_library_path(cls) -> Path:
        """Get the library root path."""
        return Path.home() / ".uipath-claude" / "library"

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

                books.append(
                    Book(
                        id=book_data.get("id", book_entry["id"]),
                        title=book_data.get("title", book_entry["title"]),
                        path=book_entry["path"],
                        description=book_entry.get("description", ""),
                        version=book_data.get("version", ""),
                        source=book_data.get("source", ""),
                        chapters=chapters,
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
        """Search sections by keyword."""
        query_lower = query.lower()
        results = []

        for book in self.books:
            for chapter in book.chapters:
                for section in chapter.sections:
                    if query_lower in section.title.lower() or any(
                        query_lower in kw.lower() for kw in section.keywords
                    ):
                        results.append((book, chapter, section))

        return results
