"""Behavior tests for the agentic executor plan nudge."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import AgenticExecutor
from uipath_claude.query.plan_block import PLAN_BLOCK_HEADING, build_plan_block


def _mk_msg(text: str, tool_calls: list | None = None) -> AIMessage:
    msg = AIMessage(content=text)
    msg.tool_calls = tool_calls or []
    return msg


def test_system_prompt_references_approved_implementation_plan() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    text = ex._build_system_prompt("skill body", {})
    assert PLAN_BLOCK_HEADING in text


def test_nudge_fires_when_only_read_tools_used_then_prose() -> None:
    """Regression: model used read tools but ended in prose while a plan exists."""
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    skill = "skill body\n" + build_plan_block("1. scaffold\n2. write Main.xaml")

    read_tool_msg = _mk_msg(
        "",
        tool_calls=[{"id": "1", "name": "list_directory", "args": {"directory_path": "."}}],
    )
    prose_msg = _mk_msg("Here is a summary of what I would do.")
    final_tool_msg = _mk_msg(
        "",
        tool_calls=[{"id": "2", "name": "write_file", "args": {"file_path": "Main.xaml", "content": "<x/>"}}],
    )
    done_msg = _mk_msg("Done.")

    responses = [read_tool_msg, prose_msg, final_tool_msg, done_msg]

    async def _fake_ainvoke(messages, *args, **kwargs):
        return responses.pop(0)

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_fake_ainvoke)

        result = asyncio.run(
            ex.execute(
                user_request="build hello",
                skill_content=skill,
                skill_name="uipath-automation",
                tools=[],
                max_iterations=6,
            )
        )

    names = [c["name"] for c in result.tool_calls_made]
    assert "write_file" in names, f"Nudge did not drive a write tool. Calls: {names}"
    assert result.success is True
