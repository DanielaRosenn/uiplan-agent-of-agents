"""MCP tools: shared LLM orchestration context and route (read-only)."""
from __future__ import annotations

import asyncio
from typing import Any

from mcp.types import Tool, ToolAnnotations

from uipath_claude.query.orchestration_context import build_orchestration_context
from uipath_claude.query.orchestration_router import context_to_public_dict, route_user_request


def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


def get_assistant_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_assistant_context",
            description=(
                "Build a compact orchestration context for the current request: "
                "grounding pack (including referenced .md paths from the request), "
                "matched skills, deterministic intent hint, and command names. "
                "Read-only. Use before uipath_assistant_route in plain Claude Code."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "request": {
                        "type": "string",
                        "description": "User message to route or understand.",
                    },
                    "project_root": {
                        "type": "string",
                        "description": "Optional repo root; defaults to workspace / cwd.",
                    },
                    "tool_profile": {
                        "type": "string",
                        "description": "Tool profile label for documentation (default all).",
                    },
                    "command_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of slash command names (no leading slash).",
                    },
                    "history": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                        "description": "Optional recent chat turns.",
                    },
                },
                "required": ["request"],
            },
            annotations=_ro("Assistant context pack"),
        ),
        Tool(
            name="uipath_assistant_route",
            description=(
                "LLM orchestration router: returns a structured route (answer, clarify, "
                "documentation, uiplan, plan, execute, command_hint, refuse) with "
                "confidence and rationale. Read-only. Same logic as uipath-claude chat "
                "when orchestration routing is enabled."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "request": {"type": "string", "description": "User message."},
                    "project_root": {"type": "string"},
                    "tool_profile": {"type": "string"},
                    "command_names": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "history": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                    "allowed_routes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional allow-list of route string values.",
                    },
                },
                "required": ["request"],
            },
            annotations=_ro("Assistant route decision"),
        ),
    ]


def call_assistant_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "uipath_assistant_context":
        return _call_context(arguments)
    if name == "uipath_assistant_route":
        return _call_route(arguments)
    raise ValueError(f"Unknown assistant tool: {name}")


def _call_context(arguments: dict[str, Any]) -> dict[str, Any]:
    request = str(arguments.get("request", "")).strip()
    if not request:
        raise ValueError("request is required")
    pr = arguments.get("project_root")
    ctx = build_orchestration_context(
        request,
        project_root=pr,
        tool_profile=str(arguments.get("tool_profile", "all") or "all"),
        command_names=list(arguments.get("command_names") or []),
        history=arguments.get("history"),
    )
    return {"status": "ok", "context": context_to_public_dict(ctx)}


def _call_route(arguments: dict[str, Any]) -> dict[str, Any]:
    request = str(arguments.get("request", "")).strip()
    if not request:
        raise ValueError("request is required")
    pr = arguments.get("project_root")
    allowed = arguments.get("allowed_routes")
    alist: list[str] | None
    if isinstance(allowed, list) and allowed:
        alist = [str(x) for x in allowed]
    else:
        alist = None

    ctx = build_orchestration_context(
        request,
        project_root=pr,
        tool_profile=str(arguments.get("tool_profile", "all") or "all"),
        command_names=list(arguments.get("command_names") or []),
        history=arguments.get("history"),
    )
    dec = asyncio.run(
        route_user_request(ctx, model_name=None, region=None, allowed_routes=alist)
    )
    return {
        "status": "ok",
        "decision": dec.to_dict(),
        "context": context_to_public_dict(ctx),
    }
