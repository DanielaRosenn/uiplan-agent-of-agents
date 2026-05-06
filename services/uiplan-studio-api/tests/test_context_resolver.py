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


def test_resolve_node_context_defaults_to_library_when_sources_missing(monkeypatch) -> None:
    calls: list[tuple[str, int]] = []

    def fake_search(query: str, top_n: int = 3):
        calls.append((query, top_n))
        return []

    monkeypatch.setattr(context_resolver, "search_library_context", fake_search)

    payload = context_resolver.resolve_node_context(
        node_id="plan",
        query="retry scope",
        sources=[],
    )

    assert payload["citations"] == []
    assert calls == [("retry scope", 3)]


def test_resolve_node_context_includes_skill_citations(monkeypatch) -> None:
    monkeypatch.setattr(
        context_resolver,
        "search_library_context",
        lambda _query, top_n=3: [],
    )
    monkeypatch.setattr(
        context_resolver,
        "get_context_sources",
        lambda: SimpleNamespace(
            categories=[
                SimpleNamespace(
                    sources=[
                        SimpleNamespace(
                            id="uipath-rpa",
                            title="uipath-rpa",
                            description="Build Retry Scope workflows in UiPath.",
                            source=".cursor/skills/uipath-rpa",
                            category="skills",
                            kind="skill",
                        ),
                        SimpleNamespace(
                            id="uipath-platform",
                            title="uipath-platform",
                            description="Platform operations.",
                            source=".cursor/skills/uipath-platform",
                            category="skills",
                            kind="skill",
                        ),
                    ]
                )
            ]
        ),
    )

    payload = context_resolver.resolve_node_context(
        node_id="plan",
        query="retry",
        sources=["skills"],
    )

    assert payload["node_id"] == "plan"
    assert payload["citations"] == [
        {
            "source_type": "skills",
            "source_id": "uipath-rpa",
            "snippet": "Build Retry Scope workflows in UiPath.",
            "strict": False,
        }
    ]
