"""MCP memory tools (project + global layers via HOME redirect)."""
from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.tools.memory_tools import call_memory_tool, get_memory_tools


def test_memory_registry():
    names = {t.name for t in get_memory_tools()}
    assert names == {"uipath_memory_load", "uipath_memory_save", "uipath_memory_append"}


@pytest.mark.asyncio
async def test_unknown_raises():
    with pytest.raises(ValueError, match="Unknown memory tool"):
        await call_memory_tool("uipath_memory_nope", {})


@pytest.mark.asyncio
async def test_save_load_roundtrip_project(tmp_path):
    out = await call_memory_tool(
        "uipath_memory_save",
        {"content": "# Notes\n\nLine A", "project_path": str(tmp_path)},
    )
    assert "saved" in str(out).lower()
    loaded = await call_memory_tool(
        "uipath_memory_load", {"project_path": str(tmp_path)}
    )
    assert "Line A" in str(loaded)
    mem_file = tmp_path / ".uipath-claude" / "memory.md"
    assert mem_file.is_file()


@pytest.mark.asyncio
async def test_append_merges(tmp_path):
    await call_memory_tool(
        "uipath_memory_save",
        {"content": "first", "project_path": str(tmp_path)},
    )
    out = await call_memory_tool(
        "uipath_memory_append",
        {"content": "second", "project_path": str(tmp_path)},
    )
    assert "append" in str(out).lower()
    loaded = await call_memory_tool(
        "uipath_memory_load", {"project_path": str(tmp_path)}
    )
    assert "first" in str(loaded)
    assert "second" in str(loaded)


@pytest.mark.asyncio
async def test_global_layer_via_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    await call_memory_tool("uipath_memory_save", {"content": "global only"})
    gf = Path(tmp_path) / ".uipath-claude" / "memory.md"
    assert gf.read_text(encoding="utf-8") == "global only"
    loaded = await call_memory_tool("uipath_memory_load", {})
    assert "global only" in str(loaded)


@pytest.mark.asyncio
async def test_save_requires_content():
    with pytest.raises(KeyError):
        await call_memory_tool("uipath_memory_save", {})
