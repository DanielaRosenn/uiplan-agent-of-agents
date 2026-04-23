"""Tests for Bedrock ValidationException recovery in AgenticExecutor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from botocore.exceptions import ClientError, ReadTimeoutError
from langchain_core.messages import AIMessage

from uipath_claude.query.agentic_executor import AgenticExecutor


def _validation_client_error() -> ClientError:
    return ClientError(
        {"Error": {"Code": "ValidationException", "Message": "invalid tool_use"}},
        "Converse",
    )


def test_execute_recovers_once_from_validation_exception() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    ok = AIMessage(content="Recovered without tools.")

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        llm_instance.bind_tools.return_value.ainvoke = AsyncMock(
            side_effect=[_validation_client_error(), ok]
        )

        result = asyncio.run(
            ex.execute(
                user_request="ping",
                skill_content="skill",
                skill_name="test",
                tools=[],
                max_iterations=5,
            )
        )

    assert result.success is True
    assert "Recovered" in result.final_response
    assert llm_instance.bind_tools.return_value.ainvoke.await_count == 2


def test_execute_retries_after_read_timeout() -> None:
    """A single ReadTimeoutError should be retried (same iteration), not surface as failure."""
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    ok = AIMessage(content="Recovered after timeout.")

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        bound = llm_instance.bind_tools.return_value
        bound.ainvoke = AsyncMock(
            side_effect=[ReadTimeoutError(endpoint_url="https://bedrock-runtime/"), ok]
        )

        result = asyncio.run(
            ex.execute(
                user_request="ping",
                skill_content="skill",
                skill_name="test",
                tools=[],
                max_iterations=5,
            )
        )

    assert bound.ainvoke.await_count >= 2
    assert "ReadTimeoutError" not in (result.error or "")


def test_execute_gives_up_after_repeated_timeouts() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        bound = llm_instance.bind_tools.return_value
        bound.ainvoke = AsyncMock(
            side_effect=ReadTimeoutError(endpoint_url="https://bedrock-runtime/")
        )

        result = asyncio.run(
            ex.execute(
                user_request="ping",
                skill_content="skill",
                skill_name="test",
                tools=[],
                max_iterations=10,
            )
        )

    assert result.success is False
    assert "ReadTimeoutError" in (result.error or "")
    assert bound.ainvoke.await_count == 3
