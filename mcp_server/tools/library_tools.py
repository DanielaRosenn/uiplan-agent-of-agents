"""MCP surface for the documentation library and proposal queue."""
from __future__ import annotations

from typing import Any

from mcp.types import Tool

from uipath_claude.library.apply import apply_proposal, reject_proposal
from uipath_claude.library.proposals import ProposalStore
from uipath_claude.tools.knowledge_tools import (
    lookup_uipath_knowledge as _lookup_knowledge,
)
from uipath_claude.tools.library_tools import (
    browse_book_toc as _browse_book_toc,
    list_library_books as _list_library_books,
    read_section as _read_section,
    search_library as _search_library,
)


def get_library_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_library_list",
            description="List documentation books in the library.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="uipath_library_toc",
            description="Show the table of contents (chapters + sections) for a book.",
            inputSchema={
                "type": "object",
                "properties": {"book_id": {"type": "string"}},
                "required": ["book_id"],
            },
        ),
        Tool(
            name="uipath_library_read_section",
            description="Read a section from the library with citation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "book_id": {"type": "string"},
                    "chapter_id": {"type": "string"},
                    "section_id": {"type": "string"},
                },
                "required": ["book_id", "chapter_id", "section_id"],
            },
        ),
        Tool(
            name="uipath_library_search",
            description="Search sections by keyword.",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        Tool(
            name="uipath_library_lookup",
            description="Library-first knowledge lookup, then Ask AI, then optional web.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "allow_network": {"type": "boolean"},
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="uipath_library_list_proposals",
            description="List pending library proposals.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="uipath_library_approve_proposal",
            description="Apply a pending library proposal by ID.",
            inputSchema={
                "type": "object",
                "properties": {"proposal_id": {"type": "string"}},
                "required": ["proposal_id"],
            },
        ),
        Tool(
            name="uipath_library_reject_proposal",
            description="Reject and remove a pending library proposal by ID.",
            inputSchema={
                "type": "object",
                "properties": {"proposal_id": {"type": "string"}},
                "required": ["proposal_id"],
            },
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
        return _search_library.invoke({"query": arguments["query"]})
    if name == "uipath_library_lookup":
        payload = {"question": arguments["question"]}
        if "allow_network" in arguments:
            payload["allow_network"] = bool(arguments["allow_network"])
        return _lookup_knowledge.invoke(payload)
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
