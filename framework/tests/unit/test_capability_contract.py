"""Tests for the canonical CLI/Cursor capability contract."""

from __future__ import annotations

from uipath_claude.capabilities import (
    CORE_SLASH_COMMANDS,
    OUT_OF_SCOPE_CLAUDE_CODE_FEATURES,
    is_supported_mcp_tool,
)
from uipath_claude.cli.app import _build_command_registry

from mcp_server.tools.agent_tools import get_agent_tools
from mcp_server.tools.answer_tools import get_answer_tools
from mcp_server.tools.design_tools import get_design_tools
from mcp_server.tools.doc_tools import get_doc_tools
from mcp_server.tools.intent_tools import get_intent_tools
from mcp_server.tools.library_tools import get_library_tools
from mcp_server.tools.memory_tools import get_memory_tools
from mcp_server.tools.assistant_tools import get_assistant_tools
from mcp_server.tools.plan_tools import get_plan_tools
from mcp_server.tools.skill_tools import get_skill_tools
from mcp_server.tools.workflow_tools import get_workflow_tools


class _DummySkillRegistry:
    def load_skills(self):
        return []

    def filter_by_agent(self, _agent_role: str):
        return []


def _all_mcp_tools():
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
        *get_assistant_tools(),
    ]


def test_core_slash_commands_are_registered() -> None:
    registry = _build_command_registry(
        _DummySkillRegistry(),
        get_status=lambda: "ok",
        get_history=lambda: [],
        run_planner=lambda _description: "plan",
    )

    missing = sorted(set(CORE_SLASH_COMMANDS) - set(registry.commands))

    assert not missing


def test_every_mcp_tool_belongs_to_capability_contract() -> None:
    unsupported = sorted(tool.name for tool in _all_mcp_tools() if not is_supported_mcp_tool(tool.name))

    assert not unsupported


def test_capability_contract_names_explicit_non_goals() -> None:
    assert "native TypeScript/Bun/Ink terminal UI" in OUT_OF_SCOPE_CLAUDE_CODE_FEATURES
    assert "IDE bridge protocol" in OUT_OF_SCOPE_CLAUDE_CODE_FEATURES
