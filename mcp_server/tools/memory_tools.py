"""Session memory MCP tools."""
from __future__ import annotations

from typing import Any

from mcp.types import Tool

from uipath_claude.memory.loader import load_memory
from uipath_claude.memory.store import save_memory


def get_memory_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_memory_load",
            description="Load combined global + project memory from ~/.uipath-claude and optional project path",
            inputSchema={
                "type": "object",
                "properties": {"project_path": {"type": "string"}},
            },
        ),
        Tool(
            name="uipath_memory_save",
            description="Overwrite memory at global or project layer",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="uipath_memory_append",
            description="Append text to existing memory (load then save)",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "project_path": {"type": "string"},
                },
                "required": ["content"],
            },
        ),
    ]


async def call_memory_tool(name: str, arguments: dict[str, Any]) -> Any:
    project_path = arguments.get("project_path")

    if name == "uipath_memory_load":
        text = load_memory(project_path)
        return text or ""

    if name == "uipath_memory_save":
        save_memory(arguments["content"], project_path)
        return "Memory saved"

    if name == "uipath_memory_append":
        existing = load_memory(project_path) or ""
        merged = existing + "\n\n" + arguments["content"] if existing else arguments["content"]
        save_memory(merged, project_path)
        return "Memory appended"

    raise ValueError(f"Unknown memory tool: {name}")
