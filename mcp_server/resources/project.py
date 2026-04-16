"""Optional project context resource (project.json summary)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.types import Resource

from mcp.server.lowlevel.helper_types import ReadResourceContents

from uipath_claude.memory.loader import load_memory
from uipath_claude.tools.skill_execution_tools import read_project_json as _read_project_json


def _strip_tool_prefix(text: str) -> str:
    if text.startswith("[OK] "):
        return text[5:].lstrip()
    if text.startswith("[ERROR] "):
        return text[8:].lstrip()
    return text


def _root() -> Path:
    return Path(os.environ.get("UIPATH_MCP_PROJECT_ROOT", os.getcwd())).resolve()


async def get_project_resources() -> list[Resource]:
    root = _root()
    if not (root / "project.json").exists():
        return []
    return [
        Resource(
            uri="uipath://project/context",
            name="project-context",
            description="project.json summary + optional memory.md excerpts",
            mimeType="application/json",
        )
    ]


async def fetch_project_resource(uri: str) -> list[ReadResourceContents]:
    if str(uri) != "uipath://project/context":
        return [ReadResourceContents(content=f"Unknown project resource: {uri}", mime_type="text/plain")]
    mem = load_memory(str(_root()))
    proj = _strip_tool_prefix(_read_project_json.invoke({"project_dir": str(_root())}))
    payload = {"memory_excerpt": mem[:4000] if mem else "", "project_json_summary": proj}
    return [
        ReadResourceContents(
            content=json.dumps(payload, indent=2),
            mime_type="application/json",
        )
    ]
