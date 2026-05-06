from types import SimpleNamespace

from app import context_resolver


def test_resolve_node_context_returns_citations(monkeypatch) -> None:
    monkeypatch.setattr(
        context_resolver,
        "search_library_context",
        lambda _query, top_n=3: [
            SimpleNamespace(
                book_id="uipath-docs",
                chapter_id="activities",
                section_id="retry-scope",
                snippet="Retry Scope retries failed actions.",
            )
        ],
    )

    payload = context_resolver.resolve_node_context(
        node_id="plan",
        query="retry scope",
        sources=["library", "skills"],
    )

    assert payload["node_id"] == "plan"
    assert "citations" in payload
    assert payload["citations"] == [
        {
            "source_type": "library",
            "source_id": "uipath-docs/activities/retry-scope",
            "snippet": "Retry Scope retries failed actions.",
            "strict": True,
        }
    ]
