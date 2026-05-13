from __future__ import annotations

import re
from importlib import metadata
from typing import Any

from fastapi import FastAPI, HTTPException

from app.context_sources import get_context_sources
from app.library_service import search_library_context

COPILOT_ACTION_NAMES = [
    "list_context_sources",
    "load_context_source",
    "search_library_context",
    "suggest_diagram_node",
    "summarize_diagram_state",
    "draft_section_preview_request",
    "draft_plan_package_request",
    "draft_scaffold_package_request",
]

DOCUMENT_NAMES = {"spec.md", "plan.md", "tasks.md"}
NODE_KINDS = {"document", "workflow", "skill", "library", "review"}
MAX_LIBRARY_CONTEXT_RESULTS = 20

_FALLBACK_REASON: str | None = None

try:
    from copilotkit import Action, CopilotKitRemoteEndpoint
    from copilotkit.integrations.fastapi import add_fastapi_endpoint
except Exception as exc:  # pragma: no cover - only used when the SDK is unavailable.
    Action = None  # type: ignore[assignment]
    CopilotKitRemoteEndpoint = None  # type: ignore[assignment]
    add_fastapi_endpoint = None  # type: ignore[assignment]
    _FALLBACK_REASON = f"CopilotKit Python SDK unavailable: {exc}"


def _model_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return slug or "copilot-suggestion"


def list_context_sources(category_id: str | None = None) -> dict[str, Any]:
    """Return available builder context sources without reading source file contents."""
    payload = _model_to_dict(get_context_sources())
    if category_id:
        payload["categories"] = [
            category for category in payload["categories"] if category["id"] == category_id
        ]
    return payload


def load_context_source(source_id: str, category_id: str | None = None) -> dict[str, Any]:
    """Return metadata for one source. Full document writes remain outside Copilot actions."""
    sources = list_context_sources(category_id)
    for category in sources["categories"]:
        for source in category["sources"]:
            if source["id"] == source_id or source["source"] == source_id:
                return {"category": category["id"], "source": source}
    raise ValueError(f"Context source not found: {source_id}")


def search_library_context_action(query: str, top_n: int = 5) -> dict[str, Any]:
    """Search indexed library context and return ranked snippets."""
    if not isinstance(query, str):
        raise ValueError("query must be a string")
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query is required")
    if isinstance(top_n, bool) or not isinstance(top_n, int):
        raise ValueError("top_n must be an integer")
    if top_n < 1 or top_n > MAX_LIBRARY_CONTEXT_RESULTS:
        raise ValueError(f"top_n must be between 1 and {MAX_LIBRARY_CONTEXT_RESULTS}")

    items = search_library_context(normalized_query, top_n)
    return {"query": normalized_query, "items": items}


def suggest_diagram_node(
    source_kind: str,
    title: str,
    description: str,
    source: str | None = None,
    existing_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Suggest a node payload; the caller decides whether to add/save it."""
    kind = source_kind if source_kind in NODE_KINDS else "workflow"
    existing = existing_nodes or []
    existing_ids = {str(node.get("id", "")) for node in existing}
    base_id = f"{kind}-{_slugify(title or source or 'context')}"
    node_id = base_id
    suffix = 2
    while node_id in existing_ids:
        node_id = f"{base_id}-{suffix}"
        suffix += 1

    same_kind_count = sum(1 for node in existing if node.get("kind") == kind)
    return {
        "operation": "suggest_only",
        "suggested_node": {
            "id": node_id,
            "title": title or "Suggested context",
            "kind": kind,
            "description": description or "Copilot-suggested context for the current plan.",
            "x": 760,
            "y": 96 + same_kind_count * 112,
            "source": source,
        },
        "next_step": "Review the node in the canvas before saving the diagram.",
    }


def summarize_diagram_state(
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    selected_node_id: str | None = None,
) -> dict[str, Any]:
    """Summarize the current diagram state without modifying it."""
    safe_nodes = nodes or []
    safe_edges = edges or []
    selected = next(
        (node for node in safe_nodes if str(node.get("id")) == selected_node_id),
        None,
    )
    kind_counts: dict[str, int] = {}
    for node in safe_nodes:
        kind = str(node.get("kind", "unknown"))
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    selected_title = selected.get("title") if selected else None
    summary = (
        f"Diagram has {len(safe_nodes)} nodes, {len(safe_edges)} edges, "
        f"and focus {selected_title or 'none'}."
    )
    return {
        "node_count": len(safe_nodes),
        "edge_count": len(safe_edges),
        "kind_counts": kind_counts,
        "selected_node": selected,
        "summary": summary,
    }


def draft_section_preview_request(
    bundle_root: str,
    document_name: str,
    diagram_summary: str,
    context_focus: str | None = None,
    proposed_content: str | None = None,
) -> dict[str, Any]:
    """Draft a preview request only; applying generated content is a separate user action."""
    if document_name not in DOCUMENT_NAMES:
        raise ValueError(f"Unsupported document_name: {document_name}")

    content = proposed_content or (
        f"<!-- Copilot preview draft\n"
        f"Diagram: {diagram_summary}\n"
        f"Context focus: {context_focus or 'none'}\n"
        f"-->\n"
    )
    return {
        "endpoint": "/generate/section-preview",
        "method": "POST",
        "write_policy": "preview_only",
        "body": {
            "bundle_root": bundle_root,
            "document_name": document_name,
            "proposed_content": content,
            "library_context": [],
        },
    }


def draft_plan_package_request(
    bundle_root: str,
    graph_id: str,
    selected_node_id: str | None = None,
) -> dict[str, Any]:
    """Draft a preview-only Plan package request payload."""
    return {
        "endpoint": "/generation/packages",
        "method": "POST",
        "write_policy": "approval_package_only",
        "body": {
            "bundle_root": bundle_root,
            "stages": ["01-plan"],
            "reviewer": None,
            "graph_ref": {"graph_id": graph_id, "selected_node_id": selected_node_id},
        },
        "next_step": "Submit this request for package drafting and review proposals before preview/apply.",
    }


def draft_scaffold_package_request(
    bundle_root: str,
    graph_id: str,
    selected_node_id: str | None = None,
) -> dict[str, Any]:
    """Draft a preview-only Scaffold package request payload."""
    return {
        "endpoint": "/generation/packages",
        "method": "POST",
        "write_policy": "approval_package_only",
        "body": {
            "bundle_root": bundle_root,
            "stages": ["02-scaffold"],
            "reviewer": None,
            "graph_ref": {"graph_id": graph_id, "selected_node_id": selected_node_id},
        },
        "next_step": "Submit this request for package drafting and review proposals before preview/apply.",
    }


def build_copilot_actions() -> list[Any]:
    if Action is None:
        return []
    return [
        Action(
            name="list_context_sources",
            handler=list_context_sources,
            description="List available UiPlan context sources grouped by skills, library, documents, and review gates.",
            parameters=[
                {
                    "name": "category_id",
                    "type": "string",
                    "required": False,
                    "description": "Optional category id to filter sources.",
                }
            ],
        ),
        Action(
            name="load_context_source",
            handler=load_context_source,
            description="Load metadata for one context source by id or source path.",
            parameters=[
                {"name": "source_id", "type": "string", "description": "Source id or source path."},
                {
                    "name": "category_id",
                    "type": "string",
                    "required": False,
                    "description": "Optional category id to narrow the lookup.",
                },
            ],
        ),
        Action(
            name="search_library_context",
            handler=search_library_context_action,
            description="Search the UiPath library index for relevant snippets.",
            parameters=[
                {"name": "query", "type": "string", "description": "Search query."},
                {
                    "name": "top_n",
                    "type": "number",
                    "required": False,
                    "description": "Maximum number of ranked snippets to return.",
                },
            ],
        ),
        Action(
            name="suggest_diagram_node",
            handler=suggest_diagram_node,
            description="Suggest a diagram node from skill, library, review, workflow, or document context without saving it.",
            parameters=[
                {"name": "source_kind", "type": "string", "description": "Node kind to suggest."},
                {"name": "title", "type": "string", "description": "Suggested node title."},
                {
                    "name": "description",
                    "type": "string",
                    "description": "Suggested node description.",
                },
                {
                    "name": "source",
                    "type": "string",
                    "required": False,
                    "description": "Optional source path or library id.",
                },
                {
                    "name": "existing_nodes",
                    "type": "object[]",
                    "required": False,
                    "description": "Existing diagram nodes for id collision avoidance.",
                    "attributes": [
                        {"name": "id", "type": "string", "required": False},
                        {"name": "kind", "type": "string", "required": False},
                    ],
                },
            ],
        ),
        Action(
            name="summarize_diagram_state",
            handler=summarize_diagram_state,
            description="Summarize the current diagram without changing it.",
            parameters=[
                {
                    "name": "nodes",
                    "type": "object[]",
                    "required": False,
                    "description": "Current diagram nodes.",
                    "attributes": [
                        {"name": "id", "type": "string", "required": False},
                        {"name": "title", "type": "string", "required": False},
                        {"name": "kind", "type": "string", "required": False},
                    ],
                },
                {
                    "name": "edges",
                    "type": "object[]",
                    "required": False,
                    "description": "Current diagram edges.",
                    "attributes": [
                        {"name": "from", "type": "string", "required": False},
                        {"name": "to", "type": "string", "required": False},
                        {"name": "label", "type": "string", "required": False},
                    ],
                },
                {
                    "name": "selected_node_id",
                    "type": "string",
                    "required": False,
                    "description": "Currently selected node id.",
                },
            ],
        ),
        Action(
            name="draft_section_preview_request",
            handler=draft_section_preview_request,
            description="Draft a /generate/section-preview request from diagram/context focus without applying changes.",
            parameters=[
                {"name": "bundle_root", "type": "string", "description": "Current plan bundle root."},
                {
                    "name": "document_name",
                    "type": "string",
                    "description": "Target document name.",
                    "enum": sorted(DOCUMENT_NAMES),
                },
                {
                    "name": "diagram_summary",
                    "type": "string",
                    "description": "Summary of the diagram state.",
                },
                {
                    "name": "context_focus",
                    "type": "string",
                    "required": False,
                    "description": "Selected source, node, or finding focus.",
                },
                {
                    "name": "proposed_content",
                    "type": "string",
                    "required": False,
                    "description": "Optional proposed document content for preview generation.",
                },
            ],
        ),
        Action(
            name="draft_plan_package_request",
            handler=draft_plan_package_request,
            description="Draft a request for generating a Plan approval package without writing target files.",
            parameters=[
                {"name": "bundle_root", "type": "string", "description": "Current plan bundle root."},
                {"name": "graph_id", "type": "string", "description": "Current graph identifier."},
                {
                    "name": "selected_node_id",
                    "type": "string",
                    "required": False,
                    "description": "Optional focused node for request context.",
                },
            ],
        ),
        Action(
            name="draft_scaffold_package_request",
            handler=draft_scaffold_package_request,
            description="Draft a request for generating a Scaffold approval package without writing target files.",
            parameters=[
                {"name": "bundle_root", "type": "string", "description": "Current plan bundle root."},
                {"name": "graph_id", "type": "string", "description": "Current graph identifier."},
                {
                    "name": "selected_node_id",
                    "type": "string",
                    "required": False,
                    "description": "Optional focused node for request context.",
                },
            ],
        ),
    ]


COPILOT_ACTIONS = build_copilot_actions()
COPILOT_SDK = (
    CopilotKitRemoteEndpoint(actions=COPILOT_ACTIONS) if CopilotKitRemoteEndpoint is not None else None
)
_FALLBACK_ACTION_HANDLERS = {
    "list_context_sources": list_context_sources,
    "load_context_source": load_context_source,
    "search_library_context": search_library_context_action,
    "suggest_diagram_node": suggest_diagram_node,
    "summarize_diagram_state": summarize_diagram_state,
    "draft_section_preview_request": draft_section_preview_request,
    "draft_plan_package_request": draft_plan_package_request,
    "draft_scaffold_package_request": draft_scaffold_package_request,
}
_FALLBACK_ACTION_ARGUMENTS = {
    "list_context_sources": {
        "required": {},
        "optional": {"category_id": "string"},
    },
    "load_context_source": {
        "required": {"source_id": "string"},
        "optional": {"category_id": "string"},
    },
    "search_library_context": {
        "required": {"query": "string"},
        "optional": {"top_n": "integer"},
    },
    "suggest_diagram_node": {
        "required": {"source_kind": "string", "title": "string", "description": "string"},
        "optional": {"source": "string", "existing_nodes": "object_list"},
    },
    "summarize_diagram_state": {
        "required": {},
        "optional": {
            "nodes": "object_list",
            "edges": "object_list",
            "selected_node_id": "string",
        },
    },
    "draft_section_preview_request": {
        "required": {
            "bundle_root": "string",
            "document_name": "string",
            "diagram_summary": "string",
        },
        "optional": {"context_focus": "string", "proposed_content": "string"},
    },
    "draft_plan_package_request": {
        "required": {"bundle_root": "string", "graph_id": "string"},
        "optional": {"selected_node_id": "string"},
    },
    "draft_scaffold_package_request": {
        "required": {"bundle_root": "string", "graph_id": "string"},
        "optional": {"selected_node_id": "string"},
    },
}


def _validate_fallback_argument_type(name: str, value: Any, expected_type: str) -> None:
    if value is None:
        return
    if expected_type == "string":
        if not isinstance(value, str):
            raise ValueError(f"{name} must be a string")
        return
    if expected_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        return
    if expected_type == "object_list":
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ValueError(f"{name} must be a list of objects")
        return
    raise ValueError(f"Unsupported validator for {name}: {expected_type}")


def _validate_fallback_action_arguments(
    action_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    schema = _FALLBACK_ACTION_ARGUMENTS[action_name]
    required = schema["required"]
    optional = schema["optional"]
    allowed_names = set(required) | set(optional)
    unexpected = sorted(set(arguments) - allowed_names)
    if unexpected:
        raise ValueError(f"Unexpected argument(s): {', '.join(unexpected)}")

    missing = sorted(name for name in required if name not in arguments or arguments[name] is None)
    if missing:
        raise ValueError(f"Missing required argument(s): {', '.join(missing)}")

    for name, expected_type in {**required, **optional}.items():
        if name in arguments:
            _validate_fallback_argument_type(name, arguments[name], expected_type)

    return dict(arguments)


async def fallback_runtime_action(action_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    handler = _FALLBACK_ACTION_HANDLERS.get(action_name)
    if handler is None:
        raise HTTPException(status_code=404, detail=f"Unknown Copilot action: {action_name}")

    arguments = payload.get("arguments", {})
    if not isinstance(arguments, dict):
        raise HTTPException(status_code=400, detail="arguments must be an object")

    try:
        validated_arguments = _validate_fallback_action_arguments(action_name, arguments)
        result = handler(**validated_arguments)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"result": result}


def register_copilot_runtime(app: FastAPI) -> None:
    app.post("/copilotkit/runtime/action/{action_name}")(fallback_runtime_action)

    if add_fastapi_endpoint is not None and COPILOT_SDK is not None:
        add_fastapi_endpoint(app, COPILOT_SDK, "/copilotkit/runtime")
        return

    @app.get("/copilotkit/runtime")
    def fallback_runtime_info() -> dict[str, Any]:
        return copilot_info_payload()


def copilot_info_payload() -> dict[str, Any]:
    if COPILOT_SDK is not None:
        info = COPILOT_SDK.info(
            context={"properties": {}, "frontend_url": None, "headers": {}},
        )
    else:
        info = {
            "actions": _fallback_action_metadata(),
            "agents": {
                "default": {
                    "description": "Local UiPlan Studio builder agent with preview-only actions.",
                    "capabilities": {},
                }
            },
            "sdkVersion": _sdk_version(),
        }
    return {
        **info,
        "runtime": {
            "name": "uiplan-studio-local-runtime",
            "mode": "official-fastapi" if COPILOT_SDK is not None else "metadata-fallback",
            "official_fastapi": COPILOT_SDK is not None,
            "official_endpoint": "/copilotkit/runtime",
            "fallback_reason": _FALLBACK_REASON,
            "write_policy": "preview_only",
        },
    }


def copilot_generate_response_payload() -> dict[str, Any]:
    action_metadata = copilot_info_payload().get("actions", [])
    return {
        "threadId": "local",
        "runId": "local",
        "messages": [],
        "actions": action_metadata,
        "status": {
            "code": "SUCCESS",
            "reason": "LOCAL_BUILDER_RUNTIME",
            "message": (
                "Builder actions are available through /copilotkit/info and "
                "/copilotkit/runtime/action/{name}."
            ),
        },
    }


def _sdk_version() -> str:
    try:
        return metadata.version("copilotkit")
    except metadata.PackageNotFoundError:
        return ""


def _fallback_action_metadata() -> list[dict[str, Any]]:
    return [
        {"name": name, "description": "Metadata fallback action.", "parameters": []}
        for name in COPILOT_ACTION_NAMES
    ]
