from __future__ import annotations

from typing import Any

from app.library_service import search_library_context


def resolve_node_context(
    node_id: str,
    query: str,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    normalized_query = query.strip()
    requested_sources = {source.strip().lower() for source in (sources or []) if source.strip()}
    citations: list[dict[str, Any]] = []

    if "library" in requested_sources and normalized_query:
        for item in search_library_context(normalized_query, top_n=3):
            citations.append(
                {
                    "source_type": "library",
                    "source_id": f"{item.book_id}/{item.chapter_id}/{item.section_id}",
                    "snippet": item.snippet,
                    "strict": True,
                }
            )

    return {
        "node_id": node_id,
        "query": normalized_query,
        "citations": citations,
    }
