"""Behavior tests for the agentic executor plan nudge."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

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
    # After write_file the executor's verify-gate nudges the model to call
    # build_and_verify_workflow; provide that call and a pass-verdict result
    # so the run can finish cleanly.
    verify_call_msg = _mk_msg(
        "",
        tool_calls=[
            {
                "id": "3",
                "name": "build_and_verify_workflow",
                "args": {"project_dir": ".", "file_path": "Main.xaml"},
            }
        ],
    )
    done_msg = _mk_msg("Done.")

    responses = [read_tool_msg, prose_msg, final_tool_msg, verify_call_msg, done_msg]

    async def _fake_ainvoke(messages, *args, **kwargs):
        return responses.pop(0)

    @tool
    def list_directory(directory_path: str = ".") -> str:
        """List directory contents (test stub)."""
        return "[OK] (stub)"

    @tool
    def write_file(file_path: str, content: str) -> str:
        """Write file (test stub)."""
        return f"[OK] wrote {file_path}"

    @tool
    def build_and_verify_workflow(project_dir: str, file_path: str = "") -> str:
        """Build and verify workflow (test stub returning a pass verdict)."""
        return "[OK] BUILD+VERIFY phase=done attempt=1 verdict=pass success=True"

    fake_tools = [list_directory, write_file, build_and_verify_workflow]

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_fake_ainvoke)

        result = asyncio.run(
            ex.execute(
                user_request="build hello",
                skill_content=skill,
                skill_name="uipath-automation",
                tools=fake_tools,
                max_iterations=6,
            )
        )

    names = [c["name"] for c in result.tool_calls_made]
    assert "write_file" in names, f"Nudge did not drive a write tool. Calls: {names}"
    assert result.success is True
