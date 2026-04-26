#!/usr/bin/env python3
"""Regenerate docs/MCP_TOOLS.md from live MCP Tool definitions.

Run from repo root:
  python ops/scripts/generate_mcp_tools_doc.py

Do not hand-edit generated sections if you want drift tests to stay
meaningful; re-run this script when tools change.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNTIME = REPO_ROOT / "framework"
if (_RUNTIME / "uipath_claude").is_dir():
    sys.path.insert(0, str(_RUNTIME))
elif str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_SCRIPTS = REPO_ROOT / "ops" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from mcp.types import Tool

from mcp_server.tools.agent_tools import get_agent_tools
from mcp_server.tools.assistant_tools import get_assistant_tools
from mcp_server.tools.answer_tools import get_answer_tools
from mcp_server.tools.design_tools import get_design_tools
from mcp_server.tools.doc_tools import get_doc_tools
from mcp_server.tools.intent_tools import get_intent_tools
from mcp_server.tools.library_tools import get_library_tools
from mcp_server.tools.memory_tools import get_memory_tools
from mcp_server.tools.plan_tools import get_plan_tools
from mcp_server.tools.skill_tools import get_skill_tools
from mcp_server.tools.workflow_tools import get_workflow_tools

from mcp_tools_doc_diagrams import diagram_body_for_tool

MODULE_GETTERS: list[tuple[str, Any]] = [
    ("workflow", get_workflow_tools),
    ("skill", get_skill_tools),
    ("agent", get_agent_tools),
    ("doc", get_doc_tools),
    ("memory", get_memory_tools),
    ("library", get_library_tools),
    ("design", get_design_tools),
    ("intent", get_intent_tools),
    ("plan", get_plan_tools),
    ("answer", get_answer_tools),
    ("assistant", get_assistant_tools),
]


def _side_effect(tool: Tool) -> str:
    ann = tool.annotations
    if ann is None:
        return "unknown (missing annotations)"
    if ann.readOnlyHint:
        return "read-only"
    if ann.destructiveHint:
        if getattr(ann, "idempotentHint", False):
            return "destructive (idempotent where noted)"
        return "destructive"
    return "staging / non-read-only (not marked destructive)"


def _quote_description(text: str) -> str:
    return "\n".join("> " + (line if line else ">") for line in text.splitlines())


def _format_schema(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2)


def _dispatch_function(module: str) -> str:
    if module == "intent":
        return "`call_intent_tool`"
    return f"`call_{module}_tool`"


def _required_params_md(schema: dict[str, Any]) -> str:
    req = schema.get("required") or []
    props = schema.get("properties") or {}
    if not req:
        return "_No required parameters (all optional)._"
    lines = []
    for key in req:
        p = props.get(key) or {}
        desc = (p.get("description") or "").strip()
        extra = ""
        if "enum" in p:
            extra = f" Allowed values: `{p['enum']}`."
        elif "default" in p:
            extra = f" Default: `{p['default']}`."
        line = f"- **`{key}`**"
        if desc:
            line += f" — {desc}"
        line += extra
        lines.append(line)
    return "\n".join(lines)


def _audience_summary(tool: Tool) -> str:
    """Single readable paragraph derived from title + description (not raw copy)."""
    raw = (tool.description or "").strip()
    desc = raw
    head = desc[:120]
    if "PREFER THIS" in head.upper():
        dot = desc.find(". ", 0, min(500, len(desc)))
        if dot != -1:
            desc = desc[dot + 2 :].strip()
    desc = " ".join(desc.split())
    if len(desc) > 720:
        window = desc[:720]
        cut = window.rfind(". ")
        desc = window[: cut + 1].strip() if cut > 320 else window.rstrip() + "..."
    title = ""
    if tool.annotations and getattr(tool.annotations, "title", None):
        title = str(tool.annotations.title).strip()
    if title:
        return f"**{title}.** {desc}"
    return desc


def _returns_line(module: str, tool_name: str) -> str:
    if module in ("workflow", "doc", "memory", "library", "design"):
        if "json" in tool_name or tool_name.endswith("_status") or tool_name.endswith(
            "_deploy"
        ) or tool_name.endswith("_publish"):
            return "Usually a **string** (sometimes JSON text) returned from the underlying helper."
        return "Typically a **string** or structured value serialized by the MCP server as text or JSON."
    if module == "skill":
        return "**List, dict, or string**, depending on the operation (registry rows, insights dict, or plain text)."
    if module == "agent":
        return "**Dict** with keys such as `success`, `final_response`, `iterations`, `tool_calls`, previews, or intent classification fields."
    if module == "intent":
        return "**Dict** with `intent`, `reason`, `recommended_next_tool`, `persona`, `library_hints`, `project_root`."
    if module == "plan":
        return "**Dict** (or similar) from the planner-with-discovery pipeline, including trace metadata."
    if module == "answer":
        return "**Markdown string** (or wrapped text) from the persona router using read-only doc/library tools only."
    return "See dispatch implementation for the concrete return type."


def _full_mermaid_chart(tool: Tool) -> str:
    body = diagram_body_for_tool(tool.name).strip()
    parts = [
        "```mermaid",
        body,
        "```",
    ]
    return "\n".join(parts)


def build_markdown() -> str:
    lines: list[str] = []
    lines.append("# MCP tools reference (`uipath-builder-agent`)")
    lines.append("")
    lines.append(
        "This file is generated by `ops/scripts/generate_mcp_tools_doc.py`. "
        "Regenerate after changing tool definitions in `framework/mcp_server/tools/`."
    )
    lines.append("")
    lines.append("Server entrypoint: `python -m mcp_server.server` (stdio).")
    lines.append("")
    lines.append(
        "Each tool has an **audience guide** (synthesized from the registered "
        "`Tool` metadata), the **author registration text** (verbatim "
        "`Tool.description` from code), the JSON **input schema**, and a "
        "**behavior flow** Mermaid chart that reflects the real dispatch path "
        "(see `framework/mcp_server/tools/*_tools.py` and `call_*_tool`). Diagrams follow "
        "a renderer-safe subset of Mermaid syntax to maximize compatibility "
        "across GitHub, Cursor, and CLI previews."
    )
    lines.append("")
    lines.append("## Index (all tool names)")
    lines.append("")
    lines.append("| Tool | Module | Side-effect hint |")
    lines.append("|------|--------|------------------|")
    for mod, getter in MODULE_GETTERS:
        for tool in getter():
            lines.append(
                f"| `{tool.name}` | {mod} | {_side_effect(tool)} |"
            )
    lines.append("")
    lines.append("## How to add a new MCP tool")
    lines.append("")
    lines.append(
        "1. Implement `Tool(...)` in the appropriate `framework/mcp_server/tools/*.py` "
        "and wire `call_*_tool` dispatch."
    )
    lines.append(
        "2. Register the name branch in "
        "[`framework/mcp_server/server.py`](../framework/mcp_server/server.py) `call_tool`."
    )
    lines.append(
        "3. Add `ToolAnnotations` (read-only vs destructive vs staging) and "
        "extend [`framework/tests/mcp_tests/test_tool_annotations.py`](../framework/tests/mcp_tests/test_tool_annotations.py) "
        "so `READ_ONLY` / `DESTRUCTIVE` / `STAGING` covers every tool."
    )
    lines.append(
        "4. Add or adjust the tool-specific Mermaid body in "
        "[`ops/scripts/mcp_tools_doc_diagrams.py`](../ops/scripts/mcp_tools_doc_diagrams.py) "
        "(`diagram_body_for_tool`) so generated docs match real behavior."
    )
    lines.append("5. Re-run `python ops/scripts/generate_mcp_tools_doc.py`.")
    lines.append("")
    for mod, getter in MODULE_GETTERS:
        lines.append(f"## Module: `{mod}`")
        lines.append("")
        for tool in getter():
            lines.append(f"### `{tool.name}`")
            lines.append("")
            lines.append("#### Audience guide")
            lines.append("")
            lines.append(_audience_summary(tool))
            lines.append("")
            lines.append("**Required MCP arguments:**")
            lines.append("")
            lines.append(_required_params_md(dict(tool.inputSchema)))
            lines.append("")
            lines.append(f"**Typical return:** {_returns_line(mod, tool.name)}")
            lines.append("")
            lines.append(f"**Side effect (MCP `ToolAnnotations`):** {_side_effect(tool)}")
            lines.append("")
            lines.append(
                f"**Dispatch:** [`framework/mcp_server/tools/{mod}_tools.py`](../framework/mcp_server/tools/{mod}_tools.py) "
                f"{_dispatch_function(mod)}"
            )
            lines.append("")
            lines.append("#### Author registration (`Tool.description` verbatim)")
            lines.append("")
            lines.append(_quote_description(tool.description))
            lines.append("")
            lines.append("#### Input schema (JSON Schema)")
            lines.append("")
            lines.append("```json")
            lines.append(_format_schema(dict(tool.inputSchema)))
            lines.append("```")
            lines.append("")
            lines.append("#### Behavior flow")
            lines.append("")
            lines.append(_full_mermaid_chart(tool))
            lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    out = REPO_ROOT / "docs" / "MCP_TOOLS.md"
    out.write_text(build_markdown(), encoding="utf-8")
    print(f"Wrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
