"""Agent tools for documentation library."""
import json

from langchain_core.tools import tool

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.proposals import (
    LibraryProposal,
    ProposalKind,
    ProposalStore,
)
from uipath_claude.library.reader import LibraryReader


@tool
def list_library_books() -> str:
    """List all documentation books in the library.

    Returns a list of available books with their chapter counts.
    Use this to discover what documentation is available.
    """
    catalog = LibraryCatalog.load()

    if not catalog.books:
        return "No books found in library. Run the seed script to populate."

    lines = ["Available documentation books:\n"]
    for book in catalog.books:
        chapter_count = len(book.chapters)
        lines.append(f"- **{book.title}** (`{book.id}`): {chapter_count} chapters")
        if book.description:
            lines.append(f"  {book.description}")

    return "\n".join(lines)


@tool
def browse_book_toc(book_id: str) -> str:
    """Browse the table of contents for a documentation book.

    Args:
        book_id: The book identifier (e.g., 'uipath-docs')

    Returns a hierarchical view of chapters and sections.
    """
    catalog = LibraryCatalog.load()
    book = catalog.get_book(book_id)

    if not book:
        available = ", ".join(b.id for b in catalog.books) or "none"
        return f"Book '{book_id}' not found. Available: {available}"

    lines = [f"# {book.title}\n"]
    if book.version:
        lines.append(f"Version: {book.version}")
    if book.source:
        lines.append(f"Source: {book.source}")
    lines.append("")

    for chapter in sorted(book.chapters, key=lambda c: c.order):
        lines.append(f"## {chapter.title}")
        for section in chapter.sections:
            keywords = ", ".join(section.keywords[:3]) if section.keywords else ""
            kw_str = f" ({keywords})" if keywords else ""
            lines.append(f"  - {section.title}{kw_str}")
        lines.append("")

    return "\n".join(lines)


@tool
def read_section(book_id: str, chapter_id: str, section_id: str) -> str:
    """Read a specific section from a documentation book.

    Args:
        book_id: The book identifier (e.g., 'uipath-docs')
        chapter_id: The chapter identifier (e.g., 'activities')
        section_id: The section identifier (e.g., 'workflow')

    Returns the full content of the section with citation info.
    """
    reader = LibraryReader()
    content = reader.read_section(book_id, chapter_id, section_id)

    if content is None:
        return f"Section not found: {book_id}/{chapter_id}/{section_id}"

    citation = f"\n\n---\n*Source: {book_id}, Chapter: {chapter_id}, Section: {section_id}*"
    return content + citation


@tool
def search_library(query: str) -> str:
    """Search across all documentation books by keyword.

    Args:
        query: Search term to find in section titles and keywords

    Returns matching sections with their locations.
    """
    catalog = LibraryCatalog.load()
    results = catalog.search_sections(query)

    if not results:
        return f"No matches found for: {query}"

    lines = [f"Found {len(results)} matches for '{query}':\n"]
    for book, chapter, section in results[:10]:
        lines.append(
            f"- **{section.title}** in {book.title} > {chapter.title}"
        )
        lines.append(
            f"  Read with: read_section('{book.id}', '{chapter.id}', '{section.id}')"
        )

    if len(results) > 10:
        lines.append(f"\n...and {len(results) - 10} more results")

    return "\n".join(lines)


@tool
def propose_library_update(
    book_id: str,
    chapter_id: str,
    section_id: str,
    section_title: str,
    content: str,
    keywords: list[str],
    rationale: str = "",
) -> str:
    """Propose a new library section; requires human approval before it is written.

    Does not modify the library. Operator: ``uipath-claude library-proposals approve``.
    """
    store = ProposalStore()
    proposal = LibraryProposal(
        proposal_id="",
        book_id=book_id,
        chapter_id=chapter_id,
        section_id=section_id,
        section_title=section_title,
        kind=ProposalKind.NEW_SECTION,
        content=content,
        keywords=list(keywords),
        rationale=rationale,
    )
    saved = store.enqueue(proposal)
    return json.dumps({"proposal_id": saved.proposal_id, "status": "pending"})


@tool
def propose_library_chapter(
    book_id: str,
    chapter_id: str,
    chapter_title: str,
    order: int = 99,
    rationale: str = "",
    initial_sections_json: str = "[]",
) -> str:
    """Propose a new chapter (TOC entry + folder); requires human approval before apply.

    initial_sections_json: JSON list of objects with keys id, title, content, keywords (optional).
    Does not modify the library until approved via ``uipath-claude library-proposals approve``.
    """
    try:
        parsed = json.loads(initial_sections_json) if initial_sections_json.strip() else []
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"invalid initial_sections_json: {e}"})
    if not isinstance(parsed, list):
        return json.dumps({"error": "initial_sections_json must be a JSON array"})

    store = ProposalStore()
    payload = {"order": order, "initial_sections": parsed}
    proposal = LibraryProposal(
        proposal_id="",
        book_id=book_id,
        chapter_id=chapter_id,
        section_id="__new_chapter__",
        section_title=chapter_title,
        kind=ProposalKind.NEW_CHAPTER,
        content=json.dumps(payload),
        keywords=[],
        rationale=rationale,
    )
    saved = store.enqueue(proposal)
    return json.dumps({"proposal_id": saved.proposal_id, "status": "pending"})


def get_library_tools() -> list[tool]:
    """Return the list of library tools for agent use."""
    return [
        list_library_books,
        browse_book_toc,
        read_section,
        search_library,
        propose_library_update,
        propose_library_chapter,
    ]
