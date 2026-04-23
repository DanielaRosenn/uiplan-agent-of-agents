"""Tests for MCP server modules (no Bedrock / no uip CLI required)."""
from __future__ import annotations

import pytest

from mcp_server.server import server
from mcp_server.tools import agent_tools
from mcp_server.tools.agent_tools import get_agent_tools
from mcp_server.tools.doc_tools import get_doc_tools
from mcp_server.tools.memory_tools import get_memory_tools
from mcp_server.tools.skill_tools import get_skill_tools
from mcp_server.tools.workflow_tools import get_workflow_tools


def test_server_name():
    assert server.name == "uipath-builder-agent"


def test_workflow_tool_names_prefixed():
    tools = get_workflow_tools()
    assert tools
    for t in tools:
        assert t.name.startswith("uipath_workflow_")


def test_skill_tool_names_prefixed():
    tools = get_skill_tools()
    assert tools
    for t in tools:
        assert t.name.startswith("uipath_skill_")


def test_agent_tool_names_prefixed():
    tools = get_agent_tools()
    assert tools
    for t in tools:
        assert t.name.startswith("uipath_agent_")


def test_doc_tool_names_prefixed():
    tools = get_doc_tools()
    assert tools
    for t in tools:
        assert t.name.startswith("uipath_doc_") or t.name == "query_uipath_docs"


def test_memory_tool_names_prefixed():
    tools = get_memory_tools()
    assert tools
    for t in tools:
        assert t.name.startswith("uipath_memory_")


@pytest.mark.asyncio
async def test_memory_load_returns_string():
    from mcp_server.tools.memory_tools import call_memory_tool

    out = await call_memory_tool("uipath_memory_load", {})
    assert isinstance(out, str)


@pytest.mark.asyncio
async def test_skill_manifest_structure():
    from mcp_server.tools.skill_tools import call_skill_tool

    manifest = await call_skill_tool("uipath_skill_manifest", {})
    assert isinstance(manifest, dict)
    assert "skills" in manifest
    assert "total_skills" in manifest


@pytest.mark.asyncio
async def test_agent_classify_intent():
    from mcp_server.tools.agent_tools import call_agent_tool

    out = await call_agent_tool(
        "uipath_agent_classify_intent",
        {"user_input": "how does GetQueueItem work"},
    )
    assert out["intent"] == "question"


def test_agent_model_region_defers_model_resolution(monkeypatch):
    """``_model_region`` no longer pre-resolves the model id; the routing
    helper inside each downstream call (AgenticExecutor, ConversationEngine)
    resolves it lazily so dynamic routing + fallback can apply per call."""
    monkeypatch.setenv(
        "UIPATH_CLAUDE_MODEL_HEAVY",
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    )
    monkeypatch.setenv("UIPATH_CLAUDE_MODEL", "anthropic.claude-sonnet-4-5-20250929-v1:0")
    model, region = agent_tools._model_region()
    assert model is None
    assert region == "us-east-1"
