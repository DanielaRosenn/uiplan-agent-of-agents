"""CLI: ``/books`` — list library books with manifest info."""
from __future__ import annotations

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.library.catalog import LibraryCatalog


def register_books_command(registry: CommandRegistry) -> None:
    """Register the ``/books`` command (alias for list_library_books)."""

    def handle_books(*args: str) -> str:
        catalog = LibraryCatalog.load()
        if not catalog.books:
            return "No books found. Add a book under data/library/books/<book-id>/."
        wants_info = bool(args) and args[0] in ("--info", "-i")
        lines: list[str] = [f"Library books ({len(catalog.books)}):"]
        for book in catalog.books:
            lines.append(
                f"- {book.title} (id={book.id}) — {len(book.chapters)} chapters"
            )
            if wants_info:
                m = book.manifest
                if book.description:
                    lines.append(f"    description: {book.description}")
                if book.source:
                    lines.append(f"    source: {book.source}")
                if book.version:
                    lines.append(f"    version: {book.version}")
                if m.audience:
                    lines.append(f"    audience: {m.audience}")
                if m.curator:
                    lines.append(f"    curator: {m.curator}")
                if m.last_reviewed:
                    lines.append(f"    last_reviewed: {m.last_reviewed}")
                if m.homepage:
                    lines.append(f"    homepage: {m.homepage}")
                if m.license:
                    lines.append(f"    license: {m.license}")
        return "\n".join(lines)

    registry.register(
        "books",
        "List documentation library books; '--info' for manifest details",
        handle_books,
    )
