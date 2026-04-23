"""MCP wrappers for project doc templates (parity with CLI doc_tools helpers)."""
from __future__ import annotations

import pytest

from mcp_server.tools.doc_tools import call_doc_tool


@pytest.mark.parametrize("doc_type", ["pdd", "sdd", "add", "tdd"])
@pytest.mark.asyncio
async def test_read_template_returns_content(doc_type: str):
    text = await call_doc_tool(
        "uipath_doc_read_template", {"doc_type": doc_type}
    )
    assert isinstance(text, str)
    assert len(text.strip()) > 50


@pytest.mark.asyncio
async def test_invalid_doc_type_raises():
    with pytest.raises(ValueError, match="Unknown template type"):
        await call_doc_tool("uipath_doc_read_template", {"doc_type": "bogus"})


@pytest.mark.asyncio
async def test_write_read_list_roundtrip(tmp_path):
    root = str(tmp_path)
    wrote = await call_doc_tool(
        "uipath_doc_write_doc",
        {"doc_type": "pdd", "content": "# My PDD\n\nHello.", "project_dir": root},
    )
    assert wrote["success"] is True
    assert wrote["path"].replace("\\", "/").endswith("docs/pdd.md")

    body = await call_doc_tool(
        "uipath_doc_read_doc", {"doc_type": "pdd", "project_dir": root}
    )
    assert "# My PDD" in body

    listed = await call_doc_tool("uipath_doc_list_docs", {"project_dir": root})
    assert listed["pdd"]["exists"] is True
