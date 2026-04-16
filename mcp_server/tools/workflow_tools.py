"""Workflow validation, execution, and project management MCP tools."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.types import Tool

from uipath_claude.tools.deploy_tool import deploy_to_orchestrator as _deploy
from uipath_claude.tools.skill_execution_tools import (
    debug_workflow as _debug_workflow,
    ensure_project_structure as _ensure_project_structure,
    install_package as _install_package,
    list_directory as _list_directory,
    read_file as _read_file,
    read_project_json as _read_project_json,
    run_uip_command as _run_uip_command,
    run_workflow as _run_workflow,
    validate_and_fix_loop as _validate_and_fix_loop,
    validate_file as _validate_file,
    write_file as _write_file,
)


def get_workflow_tools() -> list[Tool]:
    """Return workflow-related MCP tools."""
    return [
        Tool(
            name="uipath_workflow_read_file",
            description="Read contents of a file in a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file"},
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="uipath_workflow_write_file",
            description="Write content to a file in a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["file_path", "content"],
            },
        ),
        Tool(
            name="uipath_workflow_list_directory",
            description="List files and directories in a path",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "Directory path"},
                    "pattern": {"type": "string", "description": "Glob pattern", "default": "*"},
                },
                "required": ["directory_path"],
            },
        ),
        Tool(
            name="uipath_workflow_read_project",
            description="Read and parse project.json from a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "default": "."},
                },
            },
        ),
        Tool(
            name="uipath_workflow_install_package",
            description="Install a NuGet package in a UiPath project (uip rpa install-or-update-packages)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string"},
                    "package_id": {"type": "string"},
                    "version": {"type": "string", "description": "Optional version"},
                },
                "required": ["project_dir", "package_id"],
            },
        ),
        Tool(
            name="uipath_workflow_validate",
            description="Validate a XAML workflow (uip rpa get-errors; use Studio for full validation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string"},
                    "file_path": {"type": "string"},
                },
                "required": ["project_dir", "file_path"],
            },
        ),
        Tool(
            name="uipath_workflow_validate_loop",
            description="Run validation loop and return errors to fix (see validate_and_fix_loop)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string"},
                    "file_path": {"type": "string"},
                    "max_attempts": {"type": "integer", "default": 5},
                },
                "required": ["project_dir", "file_path"],
            },
        ),
        Tool(
            name="uipath_workflow_run",
            description="Execute a workflow (uip rpa run-file). Use after validation when safe.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string"},
                    "file_path": {"type": "string"},
                    "input_arguments": {"type": "string", "description": "JSON string"},
                    "timeout_seconds": {"type": "integer", "default": 60},
                    "verbose": {"type": "boolean", "default": False},
                },
                "required": ["project_dir", "file_path"],
            },
        ),
        Tool(
            name="uipath_workflow_debug",
            description="Start workflow in debug mode (uip rpa run-file StartDebugging). Destructive.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string"},
                    "file_path": {"type": "string"},
                },
                "required": ["project_dir", "file_path"],
            },
        ),
        Tool(
            name="uipath_workflow_ensure_project",
            description="Ensure project.json exists under project_dir (creates minimal if missing)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project root path"},
                    "project_name": {
                        "type": "string",
                        "description": "If set, project is created at project_dir/project_name",
                    },
                },
                "required": ["project_dir"],
            },
        ),
        Tool(
            name="uipath_workflow_run_command",
            description="Run uip CLI: command is first token (e.g. rpa), args are rest",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "e.g. rpa"},
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Args after command, e.g. [\"get-errors\", \"--project-dir\", \".\"]",
                    },
                    "project_dir": {"type": "string"},
                },
                "required": ["command", "args"],
            },
        ),
        Tool(
            name="uipath_workflow_deploy",
            description="Pack and deploy project to Orchestrator (requires URL and tenant)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string"},
                    "orchestrator_url": {"type": "string"},
                    "tenant_name": {"type": "string"},
                    "folder_path": {"type": "string", "default": "Shared"},
                    "account_name": {"type": "string"},
                    "process_name": {"type": "string"},
                    "create_process": {"type": "boolean", "default": True},
                    "environment": {"type": "string"},
                },
                "required": ["project_path", "orchestrator_url", "tenant_name"],
            },
        ),
    ]


async def call_workflow_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Dispatch workflow MCP tools to LangChain tool implementations."""
    if name == "uipath_workflow_read_file":
        return _read_file.invoke({"file_path": arguments["file_path"]})

    if name == "uipath_workflow_write_file":
        return _write_file.invoke(
            {"file_path": arguments["file_path"], "content": arguments["content"]}
        )

    if name == "uipath_workflow_list_directory":
        return _list_directory.invoke(
            {
                "dir_path": arguments["directory_path"],
                "pattern": arguments.get("pattern", "*"),
            }
        )

    if name == "uipath_workflow_read_project":
        return _read_project_json.invoke({"project_dir": arguments.get("project_dir", ".")})

    if name == "uipath_workflow_install_package":
        payload = {
            "project_dir": arguments["project_dir"],
            "package_id": arguments["package_id"],
        }
        if arguments.get("version"):
            payload["version"] = arguments["version"]
        return _install_package.invoke(payload)

    if name == "uipath_workflow_validate":
        return _validate_file.invoke(
            {"project_dir": arguments["project_dir"], "file_path": arguments["file_path"]}
        )

    if name == "uipath_workflow_validate_loop":
        return _validate_and_fix_loop.invoke(
            {
                "project_dir": arguments["project_dir"],
                "file_path": arguments["file_path"],
                "max_attempts": int(arguments.get("max_attempts", 5)),
            }
        )

    if name == "uipath_workflow_run":
        payload: dict[str, Any] = {
            "project_dir": arguments["project_dir"],
            "file_path": arguments["file_path"],
        }
        if arguments.get("input_arguments") is not None:
            payload["input_arguments"] = arguments["input_arguments"]
        if arguments.get("timeout_seconds") is not None:
            payload["timeout_seconds"] = int(arguments["timeout_seconds"])
        if arguments.get("verbose") is not None:
            payload["verbose"] = bool(arguments["verbose"])
        return _run_workflow.invoke(payload)

    if name == "uipath_workflow_debug":
        return _debug_workflow.invoke(
            {"project_dir": arguments["project_dir"], "file_path": arguments["file_path"]}
        )

    if name == "uipath_workflow_ensure_project":
        base = Path(arguments["project_dir"]).expanduser()
        if arguments.get("project_name"):
            target = (base / arguments["project_name"]).resolve()
            target.mkdir(parents=True, exist_ok=True)
            project_dir = str(target)
        else:
            project_dir = str(base.resolve())
        return _ensure_project_structure.invoke({"project_dir": project_dir})

    if name == "uipath_workflow_run_command":
        return _run_uip_command.invoke(
            {
                "command": arguments["command"],
                "command_args": list(arguments.get("args") or []),
                "project_dir": arguments.get("project_dir"),
            }
        )

    if name == "uipath_workflow_deploy":
        result = _deploy(
            project_path=arguments["project_path"],
            orchestrator_url=arguments["orchestrator_url"],
            tenant_name=arguments["tenant_name"],
            folder_path=arguments.get("folder_path", "Shared"),
            account_name=arguments.get("account_name"),
            process_name=arguments.get("process_name"),
            create_process=bool(arguments.get("create_process", True)),
            environment=arguments.get("environment"),
        )
        return json.dumps(result, indent=2)

    raise ValueError(f"Unknown workflow tool: {name}")
