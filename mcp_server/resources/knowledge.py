"""Cross-skill knowledge index MCP resource."""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.types import Resource

from uipath_claude.skills.knowledge_index import build_index


def _root() -> Path:
    return Path(os.environ.get("UIPATH_MCP_PROJECT_ROOT", os.getcwd())).resolve()


async def get_knowledge_resources() -> list[Resource]:
    return [
        Resource(
            uri="uipath://knowledge/index",
            name="knowledge-index",
            description="Authored skills + top learned lessons for the project",
            mimeType="application/json",
        )
    ]


async def fetch_knowledge_resource(uri: str) -> list[ReadResourceContents]:
    if str(uri) != "uipath://knowledge/index":
        return [
            ReadResourceContents(
                content=f"Unknown knowledge resource: {uri}", mime_type="text/plain"
            )
        ]
    idx = build_index(_root())
    return [
        ReadResourceContents(
            content=json.dumps(idx, indent=2),
            mime_type="application/json",
        )
    ]
