"""MCP skill tools: registry + dispatch (minimal real registry; fakes for git/update)."""
from __future__ import annotations

import pytest

import mcp_server.tools.skill_tools as st
from mcp_server.tools.skill_tools import call_skill_tool, get_skill_tools


@pytest.fixture(autouse=True)
def reset_skill_registry():
    st._registry = None
    yield
    st._registry = None


def test_skill_tool_registry():
    names = {t.name for t in get_skill_tools()}
    assert len(names) == 10
    assert all(n.startswith("uipath_skill_") for n in names)


@pytest.mark.asyncio
async def test_unknown_raises():
    with pytest.raises(ValueError, match="Unknown skill tool"):
        await call_skill_tool("uipath_skill_nope", {})


@pytest.mark.asyncio
async def test_list_returns_list(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_MCP_PROJECT_ROOT", str(tmp_path))
    out = await call_skill_tool("uipath_skill_list", {})
    assert isinstance(out, list)


@pytest.mark.asyncio
async def test_get_unknown_skill_string(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_MCP_PROJECT_ROOT", str(tmp_path))
    out = await call_skill_tool(
        "uipath_skill_get", {"skill_name": "__definitely_missing_skill__"}
    )
    assert isinstance(out, str)
    assert "not found" in out.lower()


@pytest.mark.asyncio
async def test_match_requires_user_input():
    with pytest.raises(KeyError):
        await call_skill_tool("uipath_skill_match", {})


@pytest.mark.asyncio
async def test_match_returns_ranked(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_MCP_PROJECT_ROOT", str(tmp_path))
    out = await call_skill_tool(
        "uipath_skill_match",
        {"user_input": "orchestrator queue item", "top_k": 2},
    )
    assert isinstance(out, list)
    assert len(out) <= 2


@pytest.mark.asyncio
async def test_manifest_structure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_MCP_PROJECT_ROOT", str(tmp_path))
    out = await call_skill_tool("uipath_skill_manifest", {})
    assert isinstance(out, dict)
    assert "skills" in out


@pytest.mark.asyncio
async def test_insights_query_and_add_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_MCP_PROJECT_ROOT", str(tmp_path))
    st._registry = None
    add_out = await call_skill_tool(
        "uipath_skill_insights_add",
        {
            "skill_name": "uipath-rpa",
            "insight_type": "gotcha",
            "content": "MCP test gotcha unique 7f3c2a1b",
            "layer": "project",
        },
    )
    assert isinstance(add_out, dict)
    assert add_out.get("success") is True
    q = await call_skill_tool(
        "uipath_skill_insights_query", {"skill_name": "uipath-rpa"}
    )
    assert isinstance(q, dict)
    assert "insights" in q


@pytest.mark.asyncio
async def test_check_updates_shape(monkeypatch):
    monkeypatch.setattr(
        st,
        "check_for_updates",
        lambda: (False, "ok", "abc", "abc"),
    )
    out = await call_skill_tool("uipath_skill_check_updates", {})
    assert out["has_updates"] is False
    assert "message" in out


@pytest.mark.asyncio
async def test_update_delegates(monkeypatch):
    monkeypatch.setattr(
        st,
        "ensure_fresh",
        lambda max_age_seconds=0: "fresh",
    )
    monkeypatch.setattr(
        st,
        "get_skills_info",
        lambda: {"current_commit": "deadbeef", "skills_count": 3},
    )
    out = await call_skill_tool("uipath_skill_update", {"force": True})
    assert out["status"] == "fresh"
    assert out["current_commit"] == "deadbeef"


@pytest.mark.asyncio
async def test_lessons_list_empty_ok(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_MCP_PROJECT_ROOT", str(tmp_path))
    out = await call_skill_tool(
        "uipath_skill_lessons_list",
        {"skill_name": "uipath-rpa", "limit": 3},
    )
    assert isinstance(out, dict)
    assert out["skill"] == "uipath-rpa"
    assert "lessons" in out


@pytest.mark.asyncio
async def test_lessons_approve_persists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("UIPATH_MCP_PROJECT_ROOT", str(tmp_path))
    out = await call_skill_tool(
        "uipath_skill_lessons_approve",
        {"skill_name": "uipath-rpa", "content": "Lesson: always validate"},
    )
    assert out.get("ok") is True
    assert "content_hash" in out
