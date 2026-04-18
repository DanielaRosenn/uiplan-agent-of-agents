"""UiPath Builder Agent MCP Server (stdio).

Aggregates workflow, skill, agent, documentation, and memory tools plus
skill/doc resources for Cursor and other MCP clients.

Usage:
    python -m mcp_server.server
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from mcp.server import Server
    from mcp.server.lowlevel.helper_types import ReadResourceContents
    from mcp.server.stdio import stdio_server
    from mcp.types import Resource, TextContent, Tool
except ImportError:
    print("MCP package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

from mcp_server.resources.docs import fetch_doc_resource, get_doc_resources
from mcp_server.resources.knowledge import fetch_knowledge_resource, get_knowledge_resources
from mcp_server.resources.project import fetch_project_resource, get_project_resources
from mcp_server.resources.skills import fetch_skill_resource, get_skill_resources
from mcp_server.tools.agent_tools import call_agent_tool, get_agent_tools
from mcp_server.tools.doc_tools import call_doc_tool, get_doc_tools
from mcp_server.tools.library_tools import (
    call_library_tool,
    get_library_tools as _get_library_tools,
)
from mcp_server.tools.memory_tools import call_memory_tool, get_memory_tools
from mcp_server.tools.skill_tools import call_skill_tool, get_skill_tools
from mcp_server.tools.workflow_tools import call_workflow_tool, get_workflow_tools

server = Server("uipath-builder-agent")


def _text_result(result: Any) -> list[TextContent]:
    if isinstance(result, str):
        return [TextContent(type="text", text=result)]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


@server.list_tools()
async def list_tools() -> list[Tool]:
    tools: list[Tool] = []
    tools.extend(get_workflow_tools())
    tools.extend(get_skill_tools())
    tools.extend(get_agent_tools())
    tools.extend(get_doc_tools())
    tools.extend(get_memory_tools())
    tools.extend(_get_library_tools())
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name.startswith("uipath_workflow_"):
            result = await call_workflow_tool(name, arguments)
        elif name.startswith("uipath_skill_"):
            result = await call_skill_tool(name, arguments)
        elif name.startswith("uipath_agent_"):
            result = await call_agent_tool(name, arguments)
        elif name.startswith("uipath_doc_"):
            result = await call_doc_tool(name, arguments)
        elif name.startswith("uipath_memory_"):
            result = await call_memory_tool(name, arguments)
        elif name.startswith("uipath_library_"):
            result = await call_library_tool(name, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        return _text_result(result)
    except Exception as exc:
        return [TextContent(type="text", text=f"Error: {exc}")]


@server.list_resources()
async def list_resources() -> list[Resource]:
    resources: list[Resource] = []
    resources.extend(await get_skill_resources())
    resources.extend(await get_doc_resources())
    resources.extend(await get_project_resources())
    resources.extend(await get_knowledge_resources())
    return resources


@server.read_resource()
async def read_resource(uri: str):
    if str(uri).startswith("uipath://skill/"):
        return await fetch_skill_resource(str(uri))
    if str(uri).startswith("uipath://doc/"):
        return await fetch_doc_resource(str(uri))
    if str(uri).startswith("uipath://project/"):
        return await fetch_project_resource(str(uri))
    if str(uri).startswith("uipath://knowledge/"):
        return await fetch_knowledge_resource(str(uri))
    return [
        ReadResourceContents(
            content=f"Unknown resource: {uri}",
            mime_type="text/plain",
        )
    ]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
