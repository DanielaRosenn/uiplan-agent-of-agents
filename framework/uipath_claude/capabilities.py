"""Canonical UiPath assistant capability contract.

This is intentionally small and product-facing. It defines the supported
Claude-Code-style surface for UiPath work without claiming full Claude Code
feature parity.
"""

from __future__ import annotations

CORE_SLASH_COMMANDS: tuple[str, ...] = (
    "help",
    "doctor",
    "status",
    "skills",
    "plan",
    "uiplan",
    "pdd",
    "validate",
    "recall",
    "resume",
    "update-skills",
    "library-proposals",
)

MCP_TOOL_PREFIXES: tuple[str, ...] = (
    "uipath_workflow_",
    "uipath_skill_",
    "uipath_agent_",
    "uipath_doc_",
    "uipath_memory_",
    "uipath_library_",
    "uipath_design_",
    "uipath_intent_",
    "uipath_plan_",
)

MCP_EXACT_TOOLS: tuple[str, ...] = (
    "query_uipath_docs",
    "uipath_answer",
)

CURSOR_APPROVED_SKILL_OVERLAYS: tuple[str, ...] = (
    "brainstorming-plan",
    "mermaid-diagram-builder",
    "uiplan",
    "writing-uipath-plans",
)

OUT_OF_SCOPE_CLAUDE_CODE_FEATURES: tuple[str, ...] = (
    "native TypeScript/Bun/Ink terminal UI",
    "full plugin marketplace/runtime",
    "LSP tool parity",
    "agent swarms/team agents",
    "IDE bridge protocol",
    "cron or remote triggers",
    "git worktree isolation",
)


def is_supported_mcp_tool(name: str) -> bool:
    """Return True when an MCP tool belongs to the supported UiPath contract."""
    return name in MCP_EXACT_TOOLS or any(name.startswith(prefix) for prefix in MCP_TOOL_PREFIXES)
