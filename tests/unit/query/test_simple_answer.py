"""Tests for simple_answer module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSimpleLlmAnswer:
    @pytest.mark.asyncio
    @patch("uipath_claude.query.simple_answer.ChatBedrockConverse")
    async def test_returns_informational_response(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "A project.json file contains metadata about your UiPath project including name, dependencies, and entry points."
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        result = await simple_llm_answer(
            user_input="What is project.json?",
            history=[],
            model_name="test-model",
            region="us-east-1",
        )

        assert "project.json" in result.lower() or "metadata" in result.lower()
        assert mock_chat.ainvoke.called

    @pytest.mark.asyncio
    @patch("uipath_claude.query.simple_answer.ChatBedrockConverse")
    async def test_system_prompt_forbids_file_generation(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Explanation here."
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        await simple_llm_answer(
            user_input="Explain project.json",
            history=[],
            model_name="test-model",
            region="us-east-1",
        )

        call_args = mock_chat.ainvoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Do NOT generate files" in system_msg.content

    @pytest.mark.asyncio
    @patch("uipath_claude.query.simple_answer.ChatBedrockConverse")
    async def test_includes_history_in_messages(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Answer."
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        await simple_llm_answer(
            user_input="Follow up question",
            history=history,
            model_name="test-model",
            region="us-east-1",
        )

        call_args = mock_chat.ainvoke.call_args[0][0]
        # System + 2 history + 1 current = 4 messages
        assert len(call_args) == 4
