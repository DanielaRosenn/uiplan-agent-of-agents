"""Floor-level checks for MCP tool descriptions.

These tests intentionally avoid pinning exact wording so they survive copy
edits, but they catch the regressions the description-rewrite plan was meant
to prevent: missing titles, one-liner descriptions, undocumented parameters,
and loss of the two cross-tool steers.
"""
from __future__ import annotations

import pytest

from pathlib import Path

from mcp_server.tools.agent_tools import get_agent_tools
from mcp_server.tools.answer_tools import get_answer_tools
from mcp_server.tools.design_tools import get_design_tools
from mcp_server.tools.doc_tools import get_doc_tools
from mcp_server.tools.intent_tools import get_intent_tools
from mcp_server.tools.library_tools import get_library_tools
from mcp_server.tools.memory_tools import get_memory_tools
from mcp_server.tools.plan_tools import get_plan_tools
from mcp_server.tools.skill_tools import get_skill_tools
from mcp_server.tools.workflow_tools import get_workflow_tools


def _all_tools():
    return [
        *get_doc_tools(),
        *get_library_tools(),
        *get_workflow_tools(),
        *get_skill_tools(),
        *get_agent_tools(),
        *get_memory_tools(),
        *get_design_tools(),
        *get_intent_tools(),
        *get_plan_tools(),
        *get_answer_tools(),
    ]


def test_mcp_tools_doc_lists_every_registered_tool():
    """``docs/MCP_TOOLS.md`` must mention each tool name (backtick-wrapped)."""
    root = Path(__file__).resolve().parents[2]
    doc_path = root / "docs" / "MCP_TOOLS.md"
    text = doc_path.read_text(encoding="utf-8")
    missing = [t.name for t in _all_tools() if f"`{t.name}`" not in text]
    assert not missing, f"MCP_TOOLS.md missing tools: {missing}"


@pytest.mark.parametrize("tool", _all_tools(), ids=lambda t: t.name)
def test_tool_has_title(tool):
    assert tool.annotations is not None, f"{tool.name} has no annotations"
    title = getattr(tool.annotations, "title", None)
    assert isinstance(title, str) and title.strip(), f"{tool.name} missing annotations.title"
    assert len(title) <= 60, f"{tool.name} title too long: {title!r}"


@pytest.mark.parametrize("tool", _all_tools(), ids=lambda t: t.name)
def test_tool_description_is_substantive(tool):
    desc = tool.description or ""
    assert len(desc) >= 80, f"{tool.name} description too short ({len(desc)} chars)"
    assert "." in desc, f"{tool.name} description should be multi-sentence"


@pytest.mark.parametrize("tool", _all_tools(), ids=lambda t: t.name)
def test_required_params_have_descriptions(tool):
    schema = tool.inputSchema or {}
    properties = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []
    missing = [
        name
        for name in required
        if not (properties.get(name, {}).get("description") or "").strip()
    ]
    assert not missing, f"{tool.name} required params missing description: {missing}"


def _find(tools, name):
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool {name!r} not found")


def test_query_uipath_docs_steers_to_library():
    tool = _find(get_doc_tools(), "query_uipath_docs")
    assert "uipath_library_lookup" in (tool.description or "")


def test_validate_loop_steers_to_validate():
    tool = _find(get_workflow_tools(), "uipath_workflow_validate_loop")
    desc = (tool.description or "")
    assert "uipath_workflow_build_and_verify" in desc or "uipath_workflow_validate" in desc
