"""Executor accumulates token counts from Bedrock responses."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import AgenticExecutor


def _ai(text: str, tokens_in: int, tokens_out: int) -> AIMessage:
    msg = AIMessage(content=text)
    msg.tool_calls = []
    msg.usage_metadata = {"input_tokens": tokens_in, "output_tokens": tokens_out}
    return msg


def test_executor_aggregates_usage() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    responses = [_ai("done.", tokens_in=50, tokens_out=7)]

    async def _fake_ainvoke(messages, *args, **kwargs):
        return responses.pop(0)

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        m_llm.return_value.bind_tools.return_value.ainvoke = AsyncMock(side_effect=_fake_ainvoke)
        result = asyncio.run(
            ex.execute(
                user_request="x",
                skill_content="",
                skill_name="s",
                tools=[],
                max_iterations=2,
            )
        )

    assert result.tokens_in == 50
    assert result.tokens_out == 7
