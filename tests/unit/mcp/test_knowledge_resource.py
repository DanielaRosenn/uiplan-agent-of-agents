"""MCP knowledge index resource."""
from __future__ import annotations

import asyncio
import json

from mcp_server.resources.knowledge import fetch_knowledge_resource


def test_knowledge_index_resource_json() -> None:
    out = asyncio.run(fetch_knowledge_resource("uipath://knowledge/index"))
    payload = json.loads(out[0].content)
    assert "skills" in payload
    assert "project_root" in payload
