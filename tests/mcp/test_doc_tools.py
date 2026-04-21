"""MCP doc tools: activity index + Ask-AI wrappers (fakes, no network)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import mcp_server.tools.doc_tools as dt
from mcp_server.tools.doc_tools import call_doc_tool, get_doc_tools


def test_doc_tool_names_include_query_alias():
    names = {t.name for t in get_doc_tools()}
    assert "query_uipath_docs" in names
    assert "uipath_doc_query" in names
    assert len(names) == 12


@pytest.mark.asyncio
async def test_unknown_doc_tool_raises():
    with pytest.raises(ValueError, match="Unknown doc tool"):
        await call_doc_tool("uipath_doc_nope", {})


@pytest.mark.asyncio
async def test_list_packages_delegates(monkeypatch):
    monkeypatch.setattr(dt, "list_available_packages", lambda: ["UiPath.X.Y"])
    out = await call_doc_tool("uipath_doc_list_packages", {})
    assert out == ["UiPath.X.Y"]


@pytest.mark.asyncio
async def test_list_activities_requires_package_id():
    with pytest.raises(KeyError):
        await call_doc_tool("uipath_doc_list_activities", {})


@pytest.mark.asyncio
async def test_list_activities_delegates(monkeypatch):
    monkeypatch.setattr(dt, "list_activities", lambda pid, ver=None: ["A1", "A2"])
    out = await call_doc_tool(
        "uipath_doc_list_activities",
        {"package_id": "UiPath.System.Activities"},
    )
    assert out == ["A1", "A2"]


@pytest.mark.asyncio
async def test_get_activity_delegates(monkeypatch):
    monkeypatch.setattr(
        dt,
        "get_activity_doc",
        lambda pkg, act, ver=None: f"# {act}\nbody",
    )
    out = await call_doc_tool(
        "uipath_doc_get_activity",
        {
            "package_id": "UiPath.System.Activities",
            "activity_name": "LogMessage",
        },
    )
    assert "LogMessage" in str(out)


@pytest.mark.asyncio
async def test_get_package_overview_delegates(monkeypatch):
    monkeypatch.setattr(
        dt,
        "get_package_overview",
        lambda pkg, ver=None: "# Overview",
    )
    out = await call_doc_tool(
        "uipath_doc_get_package_overview",
        {"package_id": "UiPath.System.Activities"},
    )
    assert "Overview" in str(out)


@pytest.mark.asyncio
async def test_search_delegates(monkeypatch):
    monkeypatch.setattr(dt, "search_activities", lambda q: [{"name": "LogMessage"}])
    out = await call_doc_tool("uipath_doc_search", {"query": "Log"})
    assert isinstance(out, list)


@pytest.mark.asyncio
async def test_find_activity_delegates(monkeypatch):
    inv = MagicMock()
    inv.invoke = MagicMock(return_value={"found": True})
    monkeypatch.setattr(dt, "_find_activity_info", inv)
    out = await call_doc_tool(
        "uipath_doc_find_activity",
        {"query": "LogMessage", "project_dir": "/tmp"},
    )
    assert out == {"found": True}
    inv.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_query_uipath_docs_and_deprecated_alias(monkeypatch):
    inv = MagicMock()
    inv.invoke = MagicMock(return_value="ask-ai-answer")

    monkeypatch.setattr(dt, "_query_uipath_docs", inv)
    a = await call_doc_tool("query_uipath_docs", {"question": "queues?"})
    b = await call_doc_tool("uipath_doc_query", {"question": "queues?"})
    assert a == b == "ask-ai-answer"
    assert inv.invoke.call_count == 2
