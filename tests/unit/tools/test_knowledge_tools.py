"""Unit tests for knowledge_tools (library-first lookup and web search gating)."""

from unittest.mock import MagicMock

import pytest

from uipath_claude.tools._result import ToolOutcome
from uipath_claude.tools.knowledge_tools import (
    lookup_uipath_knowledge,
    web_search,
)


@pytest.fixture
def fake_library_hit():
    b = MagicMock()
    b.id = "uipath-docs"
    ch = MagicMock()
    ch.id = "studio"
    sec = MagicMock()
    sec.id = "selectors"
    return b, ch, sec


def test_lookup_returns_library_when_section_found(
    monkeypatch, fake_library_hit
):
    b, ch, sec = fake_library_hit
    mock_cat = MagicMock()
    mock_cat.search_sections.return_value = [(b, ch, sec)]
    monkeypatch.setattr(
        "uipath_claude.tools.knowledge_tools.LibraryCatalog.load",
        classmethod(lambda cls: mock_cat),
    )
    mock_reader = MagicMock()
    mock_reader.read_section.return_value = "Body text"
    monkeypatch.setattr(
        "uipath_claude.tools.knowledge_tools.LibraryReader",
        lambda: mock_reader,
    )

    out = lookup_uipath_knowledge.invoke(
        {"question": "selectors", "allow_network": True}
    )
    assert "Body text" in out
    assert "SOURCE: library:uipath-docs/studio/selectors" in out


def test_lookup_skips_web_when_allow_network_false(monkeypatch, fake_library_hit):
    b, ch, sec = fake_library_hit
    mock_cat = MagicMock()
    mock_cat.search_sections.return_value = []
    monkeypatch.setattr(
        "uipath_claude.tools.knowledge_tools.LibraryCatalog.load",
        classmethod(lambda cls: mock_cat),
    )
    monkeypatch.setenv("UIPATH_WEB_SEARCH_ENABLED", "1")
    monkeypatch.setenv("TAVILY_API_KEY", "fake")

    monkeypatch.setattr(
        "uipath_claude.tools.knowledge_tools.query_uipath_documentation",
        lambda q: ToolOutcome(False, "ask failed"),
    )
    web_mock = MagicMock()
    monkeypatch.setattr(
        "uipath_claude.tools.knowledge_tools._run_web_search",
        web_mock,
    )

    lookup_uipath_knowledge.invoke(
        {"question": "x", "allow_network": False}
    )
    web_mock.assert_not_called()


def test_web_search_disabled_without_env(monkeypatch):
    monkeypatch.delenv("UIPATH_WEB_SEARCH_ENABLED", raising=False)
    out = web_search.invoke({"query": "test", "max_results": 3})
    assert "[ERROR]" in out or "disabled" in out.lower()
