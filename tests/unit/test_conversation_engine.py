# tests/unit/test_conversation_engine.py
"""Unit tests for ConversationEngine with model-tools loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.conversation_engine import ConversationEngine, MAX_TOOL_ITERATIONS


class TestConversationEngine:
    """Test the ConversationEngine tool loop."""

    @pytest.fixture
    def engine(self):
        return ConversationEngine()

    @pytest.mark.asyncio
    async def test_terminates_when_no_tool_calls(self, engine):
        """Model response without tool_use ends the loop."""
        mock_response = AIMessage(content="Hello, I can help you with UiPath.")

        with patch.object(engine, "_invoke_model", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_response

            result = await engine.run_turn([HumanMessage(content="Hi")])

            assert mock_invoke.call_count == 1
            assert result.content == "Hello, I can help you with UiPath."

    @pytest.mark.asyncio
    async def test_respects_max_iterations(self, engine):
        """Loop stops after MAX_TOOL_ITERATIONS even if tools keep being called."""
        tool_call = {"id": "call_1", "name": "get_available_skills", "args": {}}
        mock_response = AIMessage(content="", tool_calls=[tool_call])

        with patch.object(engine, "_invoke_model", new_callable=AsyncMock) as mock_invoke:
            with patch.object(engine, "_execute_tools", new_callable=AsyncMock) as mock_exec:
                mock_invoke.return_value = mock_response
                mock_exec.return_value = [ToolMessage(content="skills", tool_call_id="call_1")]

                result = await engine.run_turn([HumanMessage(content="list skills")])

                assert mock_invoke.call_count == MAX_TOOL_ITERATIONS + 1

    @pytest.mark.asyncio
    async def test_executes_tools_and_continues(self, engine):
        """Tool calls are executed and results fed back to model."""
        tool_call = {"id": "call_1", "name": "test_tool", "args": {"param": "value"}}
        first_response = AIMessage(content="", tool_calls=[tool_call])
        final_response = AIMessage(content="Here's the result based on the tool output.")

        with patch.object(engine, "_invoke_model", new_callable=AsyncMock) as mock_invoke:
            with patch.object(engine, "_execute_tools", new_callable=AsyncMock) as mock_exec:
                mock_invoke.side_effect = [first_response, final_response]
                mock_exec.return_value = [ToolMessage(content="tool result", tool_call_id="call_1")]

                result = await engine.run_turn([HumanMessage(content="use the tool")])

                assert mock_invoke.call_count == 2
                assert mock_exec.call_count == 1
                assert result.content == "Here's the result based on the tool output."

    @pytest.mark.asyncio
    async def test_system_prompt_prepended(self, engine):
        """System prompt is prepended to messages when provided."""
        mock_response = AIMessage(content="Response with system context.")

        with patch.object(engine, "_invoke_model", new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_response

            await engine.run_turn(
                [HumanMessage(content="Hi")],
                system_prompt="You are a helpful assistant.",
            )

            call_args = mock_invoke.call_args[0][0]
            assert call_args[0].content == "You are a helpful assistant."
            assert call_args[1].content == "Hi"

    @pytest.mark.asyncio
    async def test_max_iterations_returns_warning_message(self, engine):
        """When max iterations reached, returns a warning message."""
        tool_call = {"id": "call_1", "name": "infinite_tool", "args": {}}
        mock_response = AIMessage(content="", tool_calls=[tool_call])

        with patch.object(engine, "_invoke_model", new_callable=AsyncMock) as mock_invoke:
            with patch.object(engine, "_execute_tools", new_callable=AsyncMock) as mock_exec:
                mock_invoke.return_value = mock_response
                mock_exec.return_value = [ToolMessage(content="result", tool_call_id="call_1")]

                result = await engine.run_turn([HumanMessage(content="loop forever")])

                assert "Max tool iterations reached" in result.content


class TestConversationEngineToolExecution:
    """Test tool execution within ConversationEngine."""

    @pytest.fixture
    def mock_tool(self):
        tool = MagicMock()
        tool.name = "test_tool"
        tool.ainvoke = AsyncMock(return_value="tool output")
        return tool

    @pytest.fixture
    def engine_with_tool(self, mock_tool):
        return ConversationEngine(tools=[mock_tool])

    @pytest.mark.asyncio
    async def test_execute_tools_calls_tool(self, engine_with_tool, mock_tool):
        """_execute_tools invokes the correct tool with args."""
        tool_calls = [{"id": "call_1", "name": "test_tool", "args": {"key": "value"}}]

        results = await engine_with_tool._execute_tools(tool_calls)

        mock_tool.ainvoke.assert_called_once_with({"key": "value"})
        assert len(results) == 1
        assert results[0].content == "tool output"
        assert results[0].tool_call_id == "call_1"

    @pytest.mark.asyncio
    async def test_execute_tools_handles_missing_tool(self, engine_with_tool):
        """_execute_tools returns error for unknown tool."""
        tool_calls = [{"id": "call_1", "name": "unknown_tool", "args": {}}]

        results = await engine_with_tool._execute_tools(tool_calls)

        assert len(results) == 1
        assert "not found" in results[0].content
        assert results[0].tool_call_id == "call_1"

    @pytest.mark.asyncio
    async def test_execute_tools_handles_tool_error(self, engine_with_tool, mock_tool):
        """_execute_tools catches and reports tool exceptions."""
        mock_tool.ainvoke = AsyncMock(side_effect=ValueError("Tool failed"))
        tool_calls = [{"id": "call_1", "name": "test_tool", "args": {}}]

        results = await engine_with_tool._execute_tools(tool_calls)

        assert len(results) == 1
        assert "Error" in results[0].content
        assert "ValueError" in results[0].content
        assert results[0].tool_call_id == "call_1"

    @pytest.mark.asyncio
    async def test_execute_multiple_tools(self, mock_tool):
        """_execute_tools handles multiple tool calls in sequence."""
        tool2 = MagicMock()
        tool2.name = "tool_two"
        tool2.ainvoke = AsyncMock(return_value="output two")

        engine = ConversationEngine(tools=[mock_tool, tool2])

        tool_calls = [
            {"id": "call_1", "name": "test_tool", "args": {}},
            {"id": "call_2", "name": "tool_two", "args": {}},
        ]

        results = await engine._execute_tools(tool_calls)

        assert len(results) == 2
        assert results[0].content == "tool output"
        assert results[1].content == "output two"


class TestConversationEngineInitialization:
    """Test ConversationEngine initialization and configuration."""

    def test_default_initialization(self):
        """Engine initializes with sensible defaults."""
        engine = ConversationEngine()

        assert engine.model_id == "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
        assert engine.region == "us-east-1"
        assert engine.temperature == 0.3
        assert engine.tools == []

    def test_custom_initialization(self):
        """Engine accepts custom configuration."""
        mock_tool = MagicMock()
        engine = ConversationEngine(
            model_id="custom-model",
            region="us-west-2",
            temperature=0.7,
            tools=[mock_tool],
        )

        assert engine.model_id == "custom-model"
        assert engine.region == "us-west-2"
        assert engine.temperature == 0.7
        assert engine.tools == [mock_tool]

    def test_llm_lazy_initialization(self):
        """LLM is not created until first access."""
        engine = ConversationEngine()

        assert engine._llm is None

    def test_find_tool_returns_correct_tool(self):
        """_find_tool returns the tool with matching name."""
        tool1 = MagicMock()
        tool1.name = "tool_one"
        tool2 = MagicMock()
        tool2.name = "tool_two"

        engine = ConversationEngine(tools=[tool1, tool2])

        assert engine._find_tool("tool_one") is tool1
        assert engine._find_tool("tool_two") is tool2
        assert engine._find_tool("nonexistent") is None
