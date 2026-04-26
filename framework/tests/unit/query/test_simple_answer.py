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
    async def test_system_prompt_includes_project_capabilities(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Yes, use /uiplan."
        mock_chat.ainvoke = AsyncMock(return_value=mock_response)
        mock_chat_cls.return_value = mock_chat

        await simple_llm_answer(
            user_input="can we use the uiplan?",
            history=[],
            model_name="test-model",
            region="us-east-1",
            capabilities_context=(
                "Loaded skills:\n"
                "- uiplan - UiPath planning\n"
                "Available slash commands:\n"
                "- /uiplan - UiPlan dispatcher"
            ),
        )

        call_args = mock_chat.ainvoke.call_args[0][0]
        system_msg = call_args[0]
        assert "Local project capabilities available in this session" in system_msg.content
        assert "- /uiplan - UiPlan dispatcher" in system_msg.content
        assert "Do NOT claim you have no access to skills" in system_msg.content

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

    @pytest.mark.asyncio
    @patch("uipath_claude.query.simple_answer.ChatBedrockConverse")
    async def test_streaming_calls_on_delta(self, mock_chat_cls):
        from uipath_claude.query.simple_answer import simple_llm_answer

        mock_chat = MagicMock()
        
        # Mock streaming chunks
        async def mock_astream(messages):
            chunks = ["project", ".json", " contains"]
            for chunk_text in chunks:
                chunk = MagicMock()
                chunk.content = chunk_text
                yield chunk
        
        mock_chat.astream = mock_astream
        mock_chat_cls.return_value = mock_chat

        deltas = []
        def capture_delta(delta):
            deltas.append(delta)

        result = await simple_llm_answer(
            user_input="What is project.json?",
            history=[],
            model_name="test-model",
            region="us-east-1",
            stream=True,
            on_delta=capture_delta,
        )

        assert len(deltas) == 3
        assert "project" in deltas[0]
        assert "project.json contains" in result


class TestFollowupSuggestions:
    def test_generates_relevant_suggestions(self):
        from uipath_claude.query.simple_answer import generate_followup_suggestions

        answer = "project.json contains metadata about your UiPath project including dependencies."
        question = "What is project.json?"
        
        suggestions = generate_followup_suggestions(answer, question)
        
        assert len(suggestions) > 0
        assert len(suggestions) <= 4
        assert any("dependencies" in s.lower() or "project.json" in s.lower() for s in suggestions)

    def test_provides_fallback_suggestions(self):
        from uipath_claude.query.simple_answer import generate_followup_suggestions

        answer = "Some generic answer"
        question = "What is X?"
        
        suggestions = generate_followup_suggestions(answer, question)
        
        assert len(suggestions) > 0
