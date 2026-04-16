"""UiPath Builder Agent MCP Server.

Exposes the agent's tools to Cursor and other MCP clients, enabling:
- Workflow validation (static and runtime)
- Package installation
- Project structure creation
- UiPath CLI commands
- Activity documentation queries

Usage:
    # Start the server
    python -m mcp_server.server
    
    # Or with uv
    uv run python -m mcp_server.server
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

from uipath_claude.tools.skill_execution_tools import (
    read_file as _read_file,
    write_file as _write_file,
    list_directory as _list_directory,
    read_project_json as _read_project_json,
    install_package as _install_package,
    validate_file as _validate_file,
    run_workflow as _run_workflow,
    run_uip_command as _run_uip_command,
    find_activity_info as _find_activity_info,
    ensure_project_structure as _ensure_project_structure,
    query_uipath_docs as _query_uipath_docs,
)

# Create MCP server
server = Server("uipath-builder-agent")


def _tool_result(result: Any) -> list[TextContent]:
    """Convert tool result to MCP TextContent."""
    if isinstance(result, str):
        return [TextContent(type="text", text=result)]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available UiPath tools."""
    return [
        Tool(
            name="uipath_read_file",
            description="Read contents of a file in a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file (absolute or relative to project)"
                    }
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="uipath_write_file",
            description="Write content to a file in a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["file_path", "content"]
            }
        ),
        Tool(
            name="uipath_list_directory",
            description="List files and directories in a path",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory"
                    }
                },
                "required": ["directory_path"]
            }
        ),
        Tool(
            name="uipath_read_project_json",
            description="Read and parse project.json from a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path to the UiPath project directory",
                        "default": "."
                    }
                }
            }
        ),
        Tool(
            name="uipath_install_package",
            description="Install a NuGet package in a UiPath project using uip rpa install-or-update-packages",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path to the UiPath project directory"
                    },
                    "package_id": {
                        "type": "string",
                        "description": "NuGet package ID (e.g., 'UiPath.Excel.Activities')"
                    },
                    "version": {
                        "type": "string",
                        "description": "Package version (optional, uses latest if not specified)"
                    }
                },
                "required": ["project_dir", "package_id"]
            }
        ),
        Tool(
            name="uipath_validate_file",
            description="Validate a XAML workflow file using UiPath Studio validation (uip rpa get-errors --use-studio)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path to the UiPath project directory"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the XAML file to validate"
                    }
                },
                "required": ["project_dir", "file_path"]
            }
        ),
        Tool(
            name="uipath_run_workflow",
            description="Execute a workflow to verify runtime behavior. Use AFTER static validation passes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path to the UiPath project directory"
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Workflow file to execute (e.g., 'Main.xaml')"
                    },
                    "input_arguments": {
                        "type": "string",
                        "description": "Optional JSON string with input arguments"
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "Maximum execution time (default: 60)",
                        "default": 60
                    }
                },
                "required": ["project_dir", "file_path"]
            }
        ),
        Tool(
            name="uipath_run_command",
            description="Run a UiPath CLI (uip) command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The uip command to run (e.g., 'rpa get-errors', 'rpa find-activities')"
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Additional arguments for the command"
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Working directory for the command"
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="uipath_find_activity",
            description="Find information about a UiPath activity by name or capability",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Activity name or capability to search for"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="uipath_ensure_project_structure",
            description="Create or validate UiPath project structure with project.json",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {
                        "type": "string",
                        "description": "Path for the project directory"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Name for the project"
                    },
                    "target_framework": {
                        "type": "string",
                        "description": "Target framework (Windows or Portable)",
                        "default": "Windows"
                    }
                },
                "required": ["project_dir", "project_name"]
            }
        ),
        Tool(
            name="uipath_query_docs",
            description="Search UiPath documentation for information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for UiPath documentation"
                    }
                },
                "required": ["query"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "uipath_read_file":
            result = _read_file.invoke(arguments)
        elif name == "uipath_write_file":
            result = _write_file.invoke(arguments)
        elif name == "uipath_list_directory":
            result = _list_directory.invoke(arguments)
        elif name == "uipath_read_project_json":
            result = _read_project_json.invoke(arguments)
        elif name == "uipath_install_package":
            result = _install_package.invoke(arguments)
        elif name == "uipath_validate_file":
            result = _validate_file.invoke(arguments)
        elif name == "uipath_run_workflow":
            result = _run_workflow.invoke(arguments)
        elif name == "uipath_run_command":
            result = _run_uip_command.invoke(arguments)
        elif name == "uipath_find_activity":
            result = _find_activity_info.invoke(arguments)
        elif name == "uipath_ensure_project_structure":
            result = _ensure_project_structure.invoke(arguments)
        elif name == "uipath_query_docs":
            result = _query_uipath_docs.invoke(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        
        return _tool_result(result)
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
