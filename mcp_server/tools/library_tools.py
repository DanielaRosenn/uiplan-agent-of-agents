"""MCP surface for the documentation library and proposal queue."""
from __future__ import annotations

from typing import Any

from mcp.types import Tool, ToolAnnotations

def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


def _staging(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
    )

from uipath_claude.library.apply import apply_proposal, reject_proposal
from uipath_claude.library.proposals import ProposalStore
from uipath_claude.tools.knowledge_tools import (
    lookup_uipath_knowledge as _lookup_knowledge,
)
from uipath_claude.tools.library_tools import (
    browse_book_toc as _browse_book_toc,
    list_library_books as _list_library_books,
    propose_library_chapter as _propose_library_chapter,
    propose_library_update as _propose_library_update,
    read_section as _read_section,
    search_library as _search_library,
)


def get_library_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_library_list",
            description=(
                "List all curated UiPath documentation books available locally, "
                "including each book's id, title, audience, curator, and chapter "
                "count. Call this first to discover which book_id values are "
                "valid for the other uipath_library_* tools."
            ),
            inputSchema={"type": "object", "properties": {}},
            annotations=_ro("List library books"),
        ),
        Tool(
            name="uipath_library_toc",
            description=(
                "Return the chapter and section hierarchy of a UiPath "
                "documentation book. Use this to discover the chapter_id and "
                "section_id values needed by uipath_library_read_section."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "Book id from uipath_library_list (e.g. 'uipath-docs').",
                    }
                },
                "required": ["book_id"],
            },
            annotations=_ro("Read book table of contents"),
        ),
        Tool(
            name="uipath_library_read_section",
            description=(
                "Fetch the full markdown body of a specific section of a UiPath "
                "documentation book and append a citation line. Requires the "
                "exact book_id/chapter_id/section_id triple; obtain those from "
                "uipath_library_toc or uipath_library_search."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "Book id from uipath_library_list.",
                    },
                    "chapter_id": {
                        "type": "string",
                        "description": "Chapter id from uipath_library_toc.",
                    },
                    "section_id": {
                        "type": "string",
                        "description": "Section id from uipath_library_toc or _search.",
                    },
                },
                "required": ["book_id", "chapter_id", "section_id"],
            },
            annotations=_ro("Read library section"),
        ),
        Tool(
            name="uipath_library_search",
            description=(
                "Keyword search across all UiPath library section titles, "
                "keywords, chapter titles, and book titles. Multi-word queries "
                "are tokenised and ranked. Returns the top_n matches with the "
                "machine-parseable 'book_id/chapter_id/section_id' triple "
                "suitable for uipath_library_read_section."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Free-text query; tokens are matched against titles and keywords.",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Maximum number of ranked results to return (1-20).",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 20,
                    },
                },
                "required": ["query"],
            },
            annotations=_ro("Search the UiPath library"),
        ),
        Tool(
            name="uipath_library_lookup",
            description=(
                "Answer a UiPath product or RPA question using the local library "
                "first, then UiPath Ask AI, then optional web search if "
                "allow_network=true and UIPATH_WEB_SEARCH_ENABLED=1. The reply "
                "always ends with a 'SOURCE:' line and an optional "
                "CAPTURED_SOURCE JSON suitable for proposing a new library "
                "section. Prefer this over uipath_doc_query when the answer "
                "might exist locally."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to answer about UiPath / RPA.",
                    },
                    "allow_network": {
                        "type": "boolean",
                        "description": "If false, skip the web-search fallback even when enabled.",
                        "default": True,
                    },
                },
                "required": ["question"],
            },
            annotations=_ro("Lookup UiPath knowledge"),
        ),
        Tool(
            name="uipath_library_propose_section",
            description=(
                "Enqueue a NEW_SECTION proposal for the UiPath library. Stages "
                "in the proposal queue only; does NOT write to data/library/ "
                "until uipath_library_approve_proposal is invoked on the returned "
                "proposal_id. Typical trigger: uipath_library_lookup returned "
                "Ask-AI or web content worth promoting locally."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "Target book id (from uipath_library_list).",
                    },
                    "chapter_id": {
                        "type": "string",
                        "description": "Target chapter id (existing chapter in the book).",
                    },
                    "section_id": {
                        "type": "string",
                        "description": "New section slug (lowercase, dash-separated).",
                    },
                    "section_title": {
                        "type": "string",
                        "description": "Human-readable section title.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Markdown body of the new section.",
                    },
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Search keywords for the section.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why this section should be added (shown in proposal queue).",
                        "default": "",
                    },
                },
                "required": [
                    "book_id",
                    "chapter_id",
                    "section_id",
                    "section_title",
                    "content",
                    "keywords",
                ],
            },
            annotations=_staging("Propose new library section"),
        ),
        Tool(
            name="uipath_library_propose_chapter",
            description=(
                "Enqueue a NEW_CHAPTER proposal for the UiPath library (creates "
                "the TOC entry plus folder when approved). Optionally include "
                "initial sections inline via initial_sections_json. Stages only; "
                "does NOT write to data/library/ until "
                "uipath_library_approve_proposal is invoked on the returned id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "Target book id (from uipath_library_list).",
                    },
                    "chapter_id": {
                        "type": "string",
                        "description": "New chapter slug (lowercase, dash-separated).",
                    },
                    "chapter_title": {
                        "type": "string",
                        "description": "Human-readable chapter title.",
                    },
                    "order": {
                        "type": "integer",
                        "description": "Sort order in the book TOC.",
                        "default": 99,
                    },
                    "rationale": {"type": "string", "default": ""},
                    "initial_sections_json": {
                        "type": "string",
                        "description": (
                            "JSON array of section objects, each with id, title, "
                            "content, optional keywords. Use '[]' for none."
                        ),
                        "default": "[]",
                    },
                },
                "required": ["book_id", "chapter_id", "chapter_title"],
            },
            annotations=_staging("Propose new library chapter"),
        ),
        Tool(
            name="uipath_library_list_proposals",
            description=(
                "List pending UiPath library proposals waiting for human "
                "approval, with id, target book/chapter/section, kind "
                "(new_section / new_chapter / update_section), and title."
            ),
            inputSchema={"type": "object", "properties": {}},
            annotations=_ro("List pending library proposals"),
        ),
        Tool(
            name="uipath_library_approve_proposal",
            description=(
                "Approve a pending UiPath library proposal by id and write the "
                "proposed chapter or section to data/library/. Irreversible; "
                "the proposal is removed from the queue on success."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proposal_id": {
                        "type": "string",
                        "description": "Proposal id from uipath_library_list_proposals.",
                    },
                },
                "required": ["proposal_id"],
            },
            annotations=ToolAnnotations(
                title="Approve library proposal (writes data/library/)",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
            ),
        ),
        Tool(
            name="uipath_library_reject_proposal",
            description=(
                "Drop a pending UiPath library proposal by id without modifying "
                "the library on disk. The proposal disappears from "
                "uipath_library_list_proposals."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "proposal_id": {
                        "type": "string",
                        "description": "Proposal id from uipath_library_list_proposals.",
                    },
                },
                "required": ["proposal_id"],
            },
            annotations=ToolAnnotations(
                title="Reject library proposal (drops from queue)",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=True,
            ),
        ),
    ]


async def call_library_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "uipath_library_list":
        return _list_library_books.invoke({})
    if name == "uipath_library_toc":
        return _browse_book_toc.invoke({"book_id": arguments["book_id"]})
    if name == "uipath_library_read_section":
        return _read_section.invoke(
            {
                "book_id": arguments["book_id"],
                "chapter_id": arguments["chapter_id"],
                "section_id": arguments["section_id"],
            }
        )
    if name == "uipath_library_search":
        payload: dict[str, Any] = {"query": arguments["query"]}
        if "top_n" in arguments and arguments["top_n"] is not None:
            payload["top_n"] = int(arguments["top_n"])
        return _search_library.invoke(payload)
    if name == "uipath_library_lookup":
        lookup_payload: dict[str, Any] = {"question": arguments["question"]}
        if "allow_network" in arguments:
            lookup_payload["allow_network"] = bool(arguments["allow_network"])
        return _lookup_knowledge.invoke(lookup_payload)
    if name == "uipath_library_propose_section":
        return _propose_library_update.invoke(
            {
                "book_id": arguments["book_id"],
                "chapter_id": arguments["chapter_id"],
                "section_id": arguments["section_id"],
                "section_title": arguments["section_title"],
                "content": arguments["content"],
                "keywords": list(arguments.get("keywords", [])),
                "rationale": arguments.get("rationale", ""),
            }
        )
    if name == "uipath_library_propose_chapter":
        return _propose_library_chapter.invoke(
            {
                "book_id": arguments["book_id"],
                "chapter_id": arguments["chapter_id"],
                "chapter_title": arguments["chapter_title"],
                "order": int(arguments.get("order", 99)),
                "rationale": arguments.get("rationale", ""),
                "initial_sections_json": arguments.get("initial_sections_json", "[]"),
            }
        )
    if name == "uipath_library_list_proposals":
        store = ProposalStore()
        pending = store.list_pending()
        if not pending:
            return "No pending proposals."
        lines = []
        for p in pending:
            lines.append(
                f"{p.proposal_id}  {p.book_id}/{p.chapter_id}/{p.section_id}  "
                f"[{p.kind.value}]  {p.section_title}"
            )
        return "\n".join(lines)
    if name == "uipath_library_approve_proposal":
        return apply_proposal(arguments["proposal_id"]).message
    if name == "uipath_library_reject_proposal":
        return reject_proposal(arguments["proposal_id"]).message
    raise ValueError(f"Unknown library tool: {name}")
