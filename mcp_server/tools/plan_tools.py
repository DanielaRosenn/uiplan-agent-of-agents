"""MCP tool ``uipath_plan_build``.

Chains the submodule guard, the UiPath project discovery agent from the pinned
``skills/`` submodule, and the existing planner. Exposed to MCP clients as a
single call so a chat-front-end can route a BUILD intent straight to a
discovery-aware plan.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from mcp.types import Tool, ToolAnnotations

from uipath_claude.query.planner import run_planner_agent_with_discovery
from uipath_claude.skills.submodule_guard import verify as verify_guard


def get_plan_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_plan_build",
            description=(
                "Produce an executable UiPath build plan. First runs the "
                "submodule guard to ensure the UiPath/skills submodule is "
                "pinned and clean, then runs the uipath-project-discovery-"
                "agent from that submodule to populate "
                ".claude/rules/project-context.md, then invokes the read-only "
                "planner with the discovery document as context. Returns the "
                "planner's final response plus traceability metadata."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "Natural-language build request.",
                    },
                    "project_root": {
                        "type": "string",
                        "description": (
                            "Optional absolute path to the UiPath project root. "
                            "Defaults to the workspace the MCP server is running in."
                        ),
                    },
                    "force_rediscover": {
                        "type": "boolean",
                        "description": (
                            "Force re-running the discovery agent even when a "
                            "recent project-context.md exists."
                        ),
                        "default": False,
                    },
                    "bypass_guard": {
                        "type": "boolean",
                        "description": (
                            "Opt-out of the submodule guard check. Only for "
                            "read-only tooling development; never set this in "
                            "production flows."
                        ),
                        "default": False,
                    },
                },
                "required": ["user_request"],
            },
            annotations=ToolAnnotations(
                title="Plan a UiPath build (discovery-fronted)",
                readOnlyHint=True,
            ),
        ),
    ]


def _result_to_dict(result: Any) -> dict[str, Any]:
    if is_dataclass(result):
        return asdict(result)
    return {"value": str(result)}


async def call_plan_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name != "uipath_plan_build":
        raise ValueError(f"Unknown plan tool: {name}")

    user_request = arguments.get("user_request", "")
    if not isinstance(user_request, str) or not user_request.strip():
        raise ValueError("'user_request' must be a non-empty string")

    project_root = arguments.get("project_root")
    force_rediscover = bool(arguments.get("force_rediscover", False))
    bypass_guard = bool(arguments.get("bypass_guard", False))

    guard_report: dict[str, Any] | None = None
    if not bypass_guard:
        guard_result = verify_guard(
            strict=True,
            repo_root=Path(project_root).resolve() if project_root else None,
        )
        guard_report = {
            "ok": guard_result.ok,
            "errors": list(guard_result.errors),
            "warnings": list(guard_result.warnings),
            "checked": list(guard_result.checked),
        }
        if not guard_result.ok:
            return {
                "status": "blocked",
                "reason": "submodule_guard_failed",
                "guard": guard_report,
                "plan": None,
            }

    planner_result = await run_planner_agent_with_discovery(
        user_request,
        repo_root=project_root,
        force_rediscover=force_rediscover,
    )

    return {
        "status": "ok",
        "guard": guard_report,
        "plan": _result_to_dict(planner_result),
    }
