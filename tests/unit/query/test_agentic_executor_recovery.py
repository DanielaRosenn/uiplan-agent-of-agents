"""Tests for Bedrock ValidationException recovery in AgenticExecutor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from botocore.exceptions import ClientError
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
