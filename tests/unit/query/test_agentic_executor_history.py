"""Tests that AgenticExecutor.execute injects prior_messages into the LLM call."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from uipath_claude.query.agentic_executor import AgenticExecutor


def test_prior_messages_are_prepended_before_user_request() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    ok = AIMessage(content="done")

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        bound = llm_instance.bind_tools.return_value
        bound.ainvoke = AsyncMock(return_value=ok)

        prior = [
            {"role": "user", "content": "/library-proposals list"},
            {"role": "assistant", "content": "[command output] proposal-a, proposal-b"},
        ]

        asyncio.run(
            ex.execute(
                user_request="add all from the proposal list",
                skill_content="skill",
                skill_name="test",
                tools=[],
                max_iterations=1,
                prior_messages=prior,
            )
        )

        sent = bound.ainvoke.call_args.args[0]
        assert isinstance(sent[0], SystemMessage)
        assert isinstance(sent[1], HumanMessage)
        assert sent[1].content == "/library-proposals list"
        assert isinstance(sent[2], AIMessage)
        assert "proposal-a" in sent[2].content
        assert isinstance(sent[3], HumanMessage)
        assert sent[3].content == "add all from the proposal list"


def test_no_prior_messages_keeps_existing_shape() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    ok = AIMessage(content="done")

    with patch("uipath_claude.query.agentic_executor.ChatBedrockConverse") as m_llm:
        llm_instance = m_llm.return_value
        bound = llm_instance.bind_tools.return_value
        bound.ainvoke = AsyncMock(return_value=ok)

        asyncio.run(
            ex.execute(
                user_request="ping",
                skill_content="skill",
                skill_name="test",
                tools=[],
                max_iterations=1,
            )
        )

        sent = bound.ainvoke.call_args.args[0]
        assert len(sent) == 2
        assert isinstance(sent[0], SystemMessage)
        assert isinstance(sent[1], HumanMessage)
        assert sent[1].content == "ping"
