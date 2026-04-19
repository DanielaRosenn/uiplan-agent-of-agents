"""Activity documentation, Ask-AI, and project-doc MCP tools."""
from __future__ import annotations

from typing import Any

from mcp.types import Tool, ToolAnnotations

from uipath_claude.skills.activity_docs import (
    get_activity_doc,
    get_latest_version,
    get_package_overview,
    list_activities,
    list_available_packages,
    search_activities,
)
from uipath_claude.tools.doc_tools import (
    list_docs as _list_project_docs,
    read_doc as _read_project_doc,
    read_template as _read_doc_template,
    write_doc as _write_project_doc,
)
from uipath_claude.tools.skill_execution_tools import (
    find_activity_info as _find_activity_info,
    query_uipath_docs as _query_uipath_docs,
)


def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


_WRITE_DOC = ToolAnnotations(
    title="Write project documentation file",
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
)

_DOC_TYPE_SCHEMA = {
    "type": "string",
    "enum": ["pdd", "sdd", "add", "tdd"],
    "description": "Document kind: pdd, sdd, add (agentic), or tdd.",
}

_PROJECT_DIR_SCHEMA = {
    "type": "string",
    "description": "Project root (default: current working directory).",
}

_DOC_GUIDE_BLURB = (
    "Classic RPA: PDD then SDD then TDD. Agentic: PDD then ADD then TDD. "
    "Full guidance: see uipath_claude/templates/README.md."
)


def get_doc_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_doc_list_packages",
            description=(
                "List UiPath activity packages that ship with bundled markdown "
                "docs under skills/references/activity-docs. Read-only; no network. "
                "Call this first to discover valid package_id values for the other "
                "uipath_doc_* activity tools."
            ),
            inputSchema={"type": "object", "properties": {}},
            annotations=_ro("List activity packages"),
        ),
        Tool(
            name="uipath_doc_list_activities",
            description=(
                "List documented activity names for one package (latest version "
                "unless 'version' is set). Read-only; no network. Use after "
                "uipath_doc_list_packages, then feed an activity_name into "
                "uipath_doc_get_activity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {
                        "type": "string",
                        "description": "Package id from uipath_doc_list_packages (e.g. UiPath.System.Activities).",
                    },
                    "version": {
                        "type": "string",
                        "description": "Optional package version; defaults to the latest bundled version.",
                    },
                },
                "required": ["package_id"],
            },
            annotations=_ro("List package activities"),
        ),
        Tool(
            name="uipath_doc_get_activity",
            description=(
                "Read the full markdown documentation for one activity in a package "
                "and version. Read-only; no network. Prefer uipath_doc_find_activity "
                "when you only have a fuzzy name and need fallback resolution."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {
                        "type": "string",
                        "description": "Package id (e.g. UiPath.System.Activities).",
                    },
                    "activity_name": {
                        "type": "string",
                        "description": "Exact activity name as listed by uipath_doc_list_activities.",
                    },
                    "version": {
                        "type": "string",
                        "description": "Optional package version; defaults to latest bundled.",
                    },
                },
                "required": ["package_id", "activity_name"],
            },
            annotations=_ro("Read activity documentation"),
        ),
        Tool(
            name="uipath_doc_get_package_overview",
            description=(
                "Read the package overview markdown (intro, common patterns) for one "
                "UiPath activity package. Read-only. Use before drilling into "
                "individual activities with uipath_doc_get_activity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {
                        "type": "string",
                        "description": "Package id (e.g. UiPath.System.Activities).",
                    },
                    "version": {
                        "type": "string",
                        "description": "Optional package version; defaults to latest bundled.",
                    },
                },
                "required": ["package_id"],
            },
            annotations=_ro("Read package overview"),
        ),
        Tool(
            name="uipath_doc_search",
            description=(
                "Substring-search activity NAMES across all bundled activity docs. "
                "Read-only; no semantic match. Use uipath_doc_find_activity when you "
                "want fallback resolution via .local/docs and the uip CLI."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Substring to match against activity names.",
                    },
                },
                "required": ["query"],
            },
            annotations=_ro("Search activity names"),
        ),
        Tool(
            name="uipath_doc_find_activity",
            description=(
                "Resolve activity documentation by trying bundled docs first, then "
                ".local/docs, then 'uip find-activities' as a last resort. Read-only "
                "but may shell out to the uip CLI. Prefer uipath_doc_search or "
                "uipath_doc_get_activity when you already know the package."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Activity name or fuzzy phrase to look up.",
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Project root used to scope .local/docs and uip lookups.",
                    },
                },
                "required": ["query"],
            },
            annotations=_ro("Find activity (with fallback)"),
        ),
        Tool(
            name="query_uipath_docs",
            description=(
                "Ask UiPath's official Ask AI service a question about UiPath "
                "products (Studio, Orchestrator, Robots, Insights, Apps, etc.). "
                "Network call via the uipath-askai SDK with HTTP fallback. Prefer "
                "uipath_library_lookup when an answer might already exist in the "
                "local library; reach for this when you need fresh, official "
                "guidance straight from UiPath."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Free-text question about UiPath products.",
                    },
                },
                "required": ["question"],
            },
            annotations=_ro("Ask UiPath Ask AI"),
        ),
        Tool(
            name="uipath_doc_query",
            description=(
                "DEPRECATED alias of query_uipath_docs kept for one release for "
                "back-compat with existing Cursor MCP configs. Prefer "
                "query_uipath_docs in new clients; behavior is identical."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Free-text question about UiPath products.",
                    },
                },
                "required": ["question"],
            },
            annotations=_ro("Ask UiPath Ask AI (deprecated)"),
        ),
        Tool(
            name="uipath_doc_read_template",
            description=(
                "Read the bundled markdown template (placeholders only) for a PDD, "
                "SDD, ADD, or TDD. Read-only; does not touch the project. Call this "
                "first, fill the placeholders, then persist with uipath_doc_write_doc. "
                + _DOC_GUIDE_BLURB
            ),
            inputSchema={
                "type": "object",
                "properties": {"doc_type": _DOC_TYPE_SCHEMA},
                "required": ["doc_type"],
            },
            annotations=_ro("Read doc template"),
        ),
        Tool(
            name="uipath_doc_list_docs",
            description=(
                "Report which of pdd.md, sdd.md, add.md, tdd.md exist under the "
                "project's docs/ folder, with size and mtime. Read-only but creates "
                "the docs/ directory if missing so subsequent writes succeed. "
                "Returns a dict keyed by doc_type. " + _DOC_GUIDE_BLURB
            ),
            inputSchema={
                "type": "object",
                "properties": {"project_dir": _PROJECT_DIR_SCHEMA},
            },
            annotations=_ro("List project docs"),
        ),
        Tool(
            name="uipath_doc_read_doc",
            description=(
                "Read an existing project doc from <project_dir>/docs/<doc_type>.md. "
                "Read-only. Use uipath_doc_list_docs first if you are not sure the "
                "file exists. " + _DOC_GUIDE_BLURB
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_type": _DOC_TYPE_SCHEMA,
                    "project_dir": _PROJECT_DIR_SCHEMA,
                },
                "required": ["doc_type"],
            },
            annotations=_ro("Read project doc"),
        ),
        Tool(
            name="uipath_doc_write_doc",
            description=(
                "Write markdown to <project_dir>/docs/<doc_type>.md, OVERWRITING any "
                "existing file at that path. Destructive (Cursor will surface its "
                "approval card). Returns dict with success, path, bytes_written. "
                "Typical flow: uipath_doc_read_template -> fill -> uipath_doc_write_doc. "
                + _DOC_GUIDE_BLURB
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_type": _DOC_TYPE_SCHEMA,
                    "content": {
                        "type": "string",
                        "description": "Full markdown body to write (overwrites existing file).",
                    },
                    "project_dir": _PROJECT_DIR_SCHEMA,
                },
                "required": ["doc_type", "content"],
            },
            annotations=_WRITE_DOC,
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

    if name in ("query_uipath_docs", "uipath_doc_query"):
        return _query_uipath_docs.invoke({"question": arguments["question"]})

    if name == "uipath_doc_read_template":
        return _read_doc_template(arguments["doc_type"])

    if name == "uipath_doc_list_docs":
        return _list_project_docs(arguments.get("project_dir"))

    if name == "uipath_doc_read_doc":
        return _read_project_doc(
            arguments["doc_type"], arguments.get("project_dir")
        )

    if name == "uipath_doc_write_doc":
        return _write_project_doc(
            arguments["doc_type"],
            arguments["content"],
            arguments.get("project_dir"),
        )

    raise ValueError(f"Unknown doc tool: {name}")
