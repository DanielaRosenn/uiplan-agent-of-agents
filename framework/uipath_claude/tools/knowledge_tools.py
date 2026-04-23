"""High-level knowledge retrieval: library-first, then Ask AI, then optional web search."""
from __future__ import annotations

import json
import os
from typing import Any

import httpx
from langchain_core.tools import tool

from uipath_claude.library.catalog import LibraryCatalog
from uipath_claude.library.reader import LibraryReader
from uipath_claude.tools._result import ToolOutcome
from uipath_claude.tools.uipath.askai import query_uipath_documentation


def _web_search_enabled() -> bool:
    return os.environ.get("UIPATH_WEB_SEARCH_ENABLED", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _run_web_search(query: str, max_results: int = 5) -> ToolOutcome:
    """Tavily or SerpAPI; requires UIPATH_WEB_SEARCH_ENABLED=1."""
    if not _web_search_enabled():
        return ToolOutcome(
            ok=False,
            message=(
                "Web search is disabled. Set UIPATH_WEB_SEARCH_ENABLED=1 and "
                "TAVILY_API_KEY or SERPAPI_KEY."
            ),
        )

    tavily = os.environ.get("TAVILY_API_KEY", "").strip()
    if tavily:
        try:
            r = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily,
                    "query": query,
                    "max_results": max(1, min(max_results, 10)),
                },
                timeout=45.0,
            )
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or []
            lines: list[str] = []
            for item in results[:max_results]:
                title = item.get("title") or ""
                url = item.get("url") or ""
                content = (item.get("content") or "")[:800]
                lines.append(f"- {title}\n  {url}\n  {content}")
            body = "\n".join(lines) if lines else json.dumps(data)[:4000]
            return ToolOutcome(
                ok=True,
                message=body,
                data={
                    "provider": "tavily",
                    "captured_source": {"kind": "web", "query": query},
                },
            )
        except Exception as e:
            return ToolOutcome(ok=False, message=f"Tavily search failed: {e}")

    serp = os.environ.get("SERPAPI_KEY", "").strip()
    if serp:
        try:
            r = httpx.get(
                "https://serpapi.com/search",
                params={
                    "api_key": serp,
                    "q": query,
                    "engine": "google",
                    "num": max_results,
                },
                timeout=45.0,
            )
            r.raise_for_status()
            data = r.json()
            organic = data.get("organic_results") or []
            lines = []
            for item in organic[:max_results]:
                title = item.get("title") or ""
                link = item.get("link") or ""
                snippet = (item.get("snippet") or "")[:800]
                lines.append(f"- {title}\n  {link}\n  {snippet}")
            body = "\n".join(lines) if lines else json.dumps(data)[:4000]
            return ToolOutcome(
                ok=True,
                message=body,
                data={
                    "provider": "serpapi",
                    "captured_source": {"kind": "web", "query": query},
                },
            )
        except Exception as e:
            return ToolOutcome(ok=False, message=f"SerpAPI search failed: {e}")

    return ToolOutcome(
        ok=False,
        message=(
            "No web search API key: set TAVILY_API_KEY or SERPAPI_KEY "
            "(with UIPATH_WEB_SEARCH_ENABLED=1)."
        ),
    )


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """Search the public web for UiPath-related context (Tavily or SerpAPI).

    Requires UIPATH_WEB_SEARCH_ENABLED=1 and TAVILY_API_KEY or SERPAPI_KEY.
    Prefer lookup_uipath_knowledge or the documentation library first.

    Args:
        query: Search query
        max_results: Max snippets to include (capped at 10)

    Returns:
        Bullet list of results or an error envelope.
    """
    out = _run_web_search(query, max_results=max_results)
    base = out.to_text()
    if out.data and out.data.get("captured_source"):
        base += (
            "\nCAPTURED_SOURCE: "
            + json.dumps(out.data["captured_source"], ensure_ascii=False)
        )
    return base


@tool
def lookup_uipath_knowledge(question: str, allow_network: bool = True) -> str:
    """Retrieve UiPath knowledge: local library first, then Ask AI, then optional web.

    Flow: (1) search_library + read first matching section; (2) if insufficient,
    Ask AI (SDK or UIPATH_ASKAI_ENDPOINT); (3) if still failing and allow_network
    and UIPATH_WEB_SEARCH_ENABLED, web_search.

    Args:
        question: What you need to know about UiPath products or RPA patterns
        allow_network: If false, skip web search even when enabled

    Returns:
        Answer text with SOURCE line and optional CAPTURED_SOURCE JSON for proposals.
    """
    catalog = LibraryCatalog.load()
    results = catalog.search_sections(question)

    if results:
        book, chapter, section = results[0]
        reader = LibraryReader()
        body = reader.read_section(book.id, chapter.id, section.id)
        if body:
            src = f"{book.id}/{chapter.id}/{section.id}"
            cap: dict[str, Any] = {
                "kind": "library",
                "book_id": book.id,
                "chapter_id": chapter.id,
                "section_id": section.id,
            }
            return (
                f"{body}\n\n---\nSOURCE: library:{src}\n"
                "Use this citation when stating facts from the library.\n"
                "CAPTURED_SOURCE: "
                + json.dumps(cap, ensure_ascii=False)
            )

    ask = query_uipath_documentation(question)
    if ask.ok:
        extra = (
            "\n---\nSOURCE: askai\n"
            "If this is a durable best practice not in the library, consider "
            "propose_library_update or propose_library_chapter (pending approval)."
        )
        line = ask.to_text() + extra
        line += (
            "\nCAPTURED_SOURCE: "
            + json.dumps({"kind": "askai", "query": question}, ensure_ascii=False)
        )
        return line

    if allow_network and _web_search_enabled():
        web = _run_web_search(question, max_results=5)
        line = web.to_text()
        if web.data and web.data.get("captured_source"):
            line += (
                "\nCAPTURED_SOURCE: "
                + json.dumps(web.data["captured_source"], ensure_ascii=False)
            )
        return line

    fail_part = ask.to_text()
    return (
        f"{fail_part}\n"
        "[ERROR] No library hit; Ask AI unavailable or failed. "
        "Enable UIPATH_ASKAI_ENDPOINT or UIPATH_WEB_SEARCH_ENABLED + API keys as needed.\n"
        "---\nSOURCE: none"
    )


def get_knowledge_tools() -> list[Any]:
    """Tools appended to planning and skill execution registries."""
    return [lookup_uipath_knowledge, web_search]
