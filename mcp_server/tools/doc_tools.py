"""Activity documentation and Ask-AI MCP tools."""
from __future__ import annotations

from typing import Any

from mcp.types import Tool

from uipath_claude.skills.activity_docs import (
    get_activity_doc,
    get_latest_version,
    get_package_overview,
    list_activities,
    list_available_packages,
    search_activities,
)
from uipath_claude.tools.skill_execution_tools import (
    find_activity_info as _find_activity_info,
    query_uipath_docs as _query_uipath_docs,
)


def get_doc_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_doc_list_packages",
            description="List packages that have bundled activity-docs under skills/references/activity-docs",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="uipath_doc_list_activities",
            description="List documented activities for a package (latest version unless version set)",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {"type": "string"},
                    "version": {"type": "string"},
                },
                "required": ["package_id"],
            },
        ),
        Tool(
            name="uipath_doc_get_activity",
            description="Read markdown activity doc for a package/version",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {"type": "string"},
                    "activity_name": {"type": "string"},
                    "version": {"type": "string"},
                },
                "required": ["package_id", "activity_name"],
            },
        ),
        Tool(
            name="uipath_doc_get_package_overview",
            description="Read package overview markdown",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {"type": "string"},
                    "version": {"type": "string"},
                },
                "required": ["package_id"],
            },
        ),
        Tool(
            name="uipath_doc_search",
            description="Search activity names across bundled activity-docs",
            inputSchema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        ),
        Tool(
            name="uipath_doc_find_activity",
            description="Resolve activity documentation (bundled docs, .local/docs, uip find-activities)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "project_dir": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="uipath_doc_query",
            description="Query UiPath official documentation via Ask AI (requires uipath-askai client setup)",
            inputSchema={
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        ),
    ]


async def call_doc_tool(name: str, arguments: dict[str, Any]) -> Any:
    if name == "uipath_doc_list_packages":
        return list_available_packages()

    if name == "uipath_doc_list_activities":
        return list_activities(arguments["package_id"], arguments.get("version"))

    if name == "uipath_doc_get_activity":
        doc = get_activity_doc(
            arguments["package_id"],
            arguments["activity_name"],
            arguments.get("version"),
        )
        return doc or "No documentation found"

    if name == "uipath_doc_get_package_overview":
        overview = get_package_overview(arguments["package_id"], arguments.get("version"))
        return overview or "No overview found"

    if name == "uipath_doc_search":
        return search_activities(arguments["query"])

    if name == "uipath_doc_find_activity":
        payload: dict[str, Any] = {"query": arguments["query"]}
        if arguments.get("project_dir"):
            payload["project_dir"] = arguments["project_dir"]
        return _find_activity_info.invoke(payload)

    if name == "uipath_doc_query":
        return _query_uipath_docs.invoke({"question": arguments["question"]})

    raise ValueError(f"Unknown doc tool: {name}")
