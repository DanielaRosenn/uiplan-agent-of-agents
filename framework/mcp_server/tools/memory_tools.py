"""Session memory MCP tools."""
from __future__ import annotations

from typing import Any

from mcp.types import Tool, ToolAnnotations

from uipath_claude.memory.loader import load_memory
from uipath_claude.memory.store import save_memory


def get_memory_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_memory_load",
            description=(
                "Read-only. Returns the combined global memory "
                "(~/.uipath-claude/memory.md) plus the project memory at "
                "<project_path>/.uipath-claude/memory.md when project_path is "
                "provided. Use before writing so uipath_memory_save / _append "
                "do not clobber existing notes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Optional project root for the project memory layer.",
                    },
                },
            },
            annotations=ToolAnnotations(title="Load memory", readOnlyHint=True),
        ),
        Tool(
            name="uipath_memory_save",
            description=(
                "Overwrite the memory file at the chosen layer (project when "
                "project_path is set, otherwise global) with the given content. "
                "Destructive but idempotent (same content yields same file). "
                "Use uipath_memory_append when you want to extend existing "
                "memory without losing it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Full markdown body to write (overwrites the file).",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "If set, writes the project layer; otherwise writes the global layer.",
                    },
                },
                "required": ["content"],
            },
            annotations=ToolAnnotations(
                title="Overwrite memory layer",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=True,
            ),
        ),
        Tool(
            name="uipath_memory_append",
            description=(
                "Load the chosen memory layer, append the new content separated "
                "by a blank line, and save. Destructive and idempotent only when "
                "the content is unique. Prefer uipath_memory_save when replacing "
                "the file wholesale."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Markdown to append (added after a blank line separator).",
                    },
                    "project_path": {
                        "type": "string",
                        "description": "If set, appends to the project layer; otherwise the global layer.",
                    },
                },
                "required": ["content"],
            },
            annotations=ToolAnnotations(
                title="Append to memory",
                readOnlyHint=False,
                destructiveHint=True,
                idempotentHint=False,
            ),
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
