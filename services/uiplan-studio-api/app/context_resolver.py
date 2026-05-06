from __future__ import annotations

from typing import Any

from app.context_sources import get_context_sources
from app.library_service import search_library_context


def _normalize_requested_sources(sources: list[str] | None) -> set[str]:
    normalized = {source.strip().lower() for source in (sources or []) if source.strip()}
    if not normalized:
        return {"library"}
    return normalized


def _build_skill_citations(query: str) -> list[dict[str, Any]]:
    normalized_query = query.lower().strip()
    citations: list[dict[str, Any]] = []
    for category in get_context_sources().categories:
        for source in category.sources:
            if source.kind != "skill" and source.category != "skills":
                continue
            haystack = " ".join(
                (
                    source.id,
                    source.title,
                    source.description or "",
                    source.source or "",
                    source.category or "",
                )
            ).lower()
            if normalized_query and normalized_query not in haystack:
                continue
            citations.append(
                {
                    "source_type": "skills",
                    "source_id": source.id,
                    "snippet": source.description or source.title,
                    "strict": False,
                }
            )
    return citations


def resolve_node_context(
    node_id: str,
    query: str,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    normalized_query = query.strip()
    requested_sources = _normalize_requested_sources(sources)
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

    if "skills" in requested_sources:
        citations.extend(_build_skill_citations(normalized_query))

    return {
        "node_id": node_id,
        "query": normalized_query,
        "citations": citations,
    }
