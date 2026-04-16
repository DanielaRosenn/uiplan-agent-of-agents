"""Tests for clarifier module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRunClarifierAgent:
    @pytest.mark.asyncio
    @patch("uipath_claude.query.clarifier.ChatBedrockConverse")
    async def test_returns_clarifying_questions(self, mock_chat_cls):
        from uipath_claude.query.clarifier import run_clarifier_agent

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "What email provider do you want to use? Do you need to read or send emails?"
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        result = await run_clarifier_agent(
            user_request="automate my email",
            model_name="test-model",
            region="us-east-1",
        )

        assert "?" in result
        assert mock_chat.ainvoke.called

    @pytest.mark.asyncio
    @patch("uipath_claude.query.clarifier.ChatBedrockConverse")
    async def test_system_prompt_forbids_code_generation(self, mock_chat_cls):
        from uipath_claude.query.clarifier import run_clarifier_agent

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "What provider?"
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        await run_clarifier_agent(
            user_request="automate my email",
            model_name="test-model",
            region="us-east-1",
        )

        call_args = mock_chat.ainvoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Do NOT generate" in system_msg.content
        assert "code" in system_msg.content.lower()


class TestIncrementalClarification:
    @pytest.mark.asyncio
    @patch("uipath_claude.query.clarifier.ChatBedrockConverse")
    async def test_generate_next_question(self, mock_chat_cls):
        from uipath_claude.query.clarifier import generate_next_clarifying_question

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "What actions do you need to perform?"
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        result = await generate_next_clarifying_question(
            original_request="automate my email",
            questions_asked=["Which provider do you use?"],
            answers_received=["Outlook"],
            model_name="test-model",
            region="us-east-1",
        )

        assert "?" in result or "READY_TO_BUILD" in result
        assert mock_chat.ainvoke.called

    @pytest.mark.asyncio
    @patch("uipath_claude.query.clarifier.ChatBedrockConverse")
    async def test_signals_ready_when_enough_info(self, mock_chat_cls):
        from uipath_claude.query.clarifier import (
            generate_next_clarifying_question,
            should_transition_to_build,
        )

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "READY_TO_BUILD"
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        result = await generate_next_clarifying_question(
            original_request="automate my email",
            questions_asked=["Which provider?", "What actions?"],
            answers_received=["Outlook", "Read emails"],
            model_name="test-model",
            region="us-east-1",
        )

        assert should_transition_to_build(result)
