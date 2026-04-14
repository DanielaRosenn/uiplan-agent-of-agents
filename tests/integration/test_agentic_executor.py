"""Integration tests for agentic executor."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uipath_claude.query.agentic_executor import AgenticExecutor, AgenticResult


class MockToolCallResponse:
    """Mock LLM response with tool calls."""
    
    def __init__(self, tool_calls: list[dict], content: str = ""):
        self.tool_calls = tool_calls
        self.content = content


class MockFinalResponse:
    """Mock LLM response without tool calls (final answer)."""
    
    def __init__(self, content: str):
        self.tool_calls = []
        self.content = content


@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""
    from langchain_core.tools import tool
    
    @tool
    def read_file(file_path: str) -> str:
        """Read a file."""
        return f"Contents of {file_path}"
    
    @tool
    def write_file(file_path: str, content: str) -> str:
        """Write a file."""
        # Return message that matches what the executor looks for
        return f"Successfully wrote {len(content)} bytes to {file_path}"
    
    @tool
    def validate_file(project_dir: str, file_path: str) -> str:
        """Validate a file."""
        return "Validation passed: 0 errors"
    
    return [read_file, write_file, validate_file]


@pytest.mark.asyncio
async def test_agentic_executor_single_tool_call(mock_tools):
    """Test executor handles single tool call then final response."""
    executor = AgenticExecutor(
        model_name="test-model",
        region="us-east-1",
    )
    
    # Mock LLM responses: first calls a tool, then gives final answer
    call_count = 0
    
    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockToolCallResponse(
                tool_calls=[{
                    "name": "read_file",
                    "args": {"file_path": "test.txt"},
                    "id": "call_1",
                }],
            )
        return MockFinalResponse("Done! I read the file and here's the result.")
    
    with patch.object(executor, "_get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.ainvoke = mock_ainvoke
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm
        
        result = await executor.execute(
            skill_content="Test skill instructions",
            user_request="Read test.txt",
            tools=mock_tools,
        )
    
    assert result.success
    assert "Done!" in result.final_response
    assert len(result.tool_calls_made) == 1
    assert result.tool_calls_made[0]["name"] == "read_file"
    assert result.iterations == 2


@pytest.mark.asyncio
async def test_agentic_executor_multiple_tool_calls(mock_tools):
    """Test executor handles multiple sequential tool calls."""
    executor = AgenticExecutor(
        model_name="test-model",
        region="us-east-1",
    )
    
    call_count = 0
    
    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockToolCallResponse(
                tool_calls=[{
                    "name": "write_file",
                    "args": {"file_path": "Main.xaml", "content": "<Activity/>"},
                    "id": "call_1",
                }],
            )
        elif call_count == 2:
            return MockToolCallResponse(
                tool_calls=[{
                    "name": "validate_file",
                    "args": {"project_dir": ".", "file_path": "Main.xaml"},
                    "id": "call_2",
                }],
            )
        return MockFinalResponse("Created and validated Main.xaml successfully!")
    
    with patch.object(executor, "_get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.ainvoke = mock_ainvoke
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm
        
        result = await executor.execute(
            skill_content="Create and validate workflow",
            user_request="Create Main.xaml",
            tools=mock_tools,
        )
    
    assert result.success
    assert len(result.tool_calls_made) == 2
    assert result.tool_calls_made[0]["name"] == "write_file"
    assert result.tool_calls_made[1]["name"] == "validate_file"
    assert result.iterations == 3


@pytest.mark.asyncio
async def test_agentic_executor_no_tool_calls_immediate_answer(mock_tools):
    """Test executor handles LLM giving immediate answer without tools."""
    executor = AgenticExecutor(
        model_name="test-model",
        region="us-east-1",
    )
    
    async def mock_ainvoke(messages):
        return MockFinalResponse("I can help with that! Here's the answer directly.")
    
    with patch.object(executor, "_get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.ainvoke = mock_ainvoke
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm
        
        result = await executor.execute(
            skill_content="Answer questions",
            user_request="What is UiPath?",
            tools=mock_tools,
        )
    
    assert result.success
    assert "Here's the answer directly" in result.final_response
    assert len(result.tool_calls_made) == 0
    assert result.iterations == 1


@pytest.mark.asyncio
async def test_agentic_executor_max_iterations():
    """Test executor stops at max iterations."""
    executor = AgenticExecutor(
        model_name="test-model",
        region="us-east-1",
    )
    executor.MAX_ITERATIONS = 3  # Lower for testing
    
    from langchain_core.tools import tool
    
    @tool
    def infinite_tool(query: str) -> str:
        """A tool that always gets called."""
        return "Result"
    
    async def mock_ainvoke(messages):
        return MockToolCallResponse(
            tool_calls=[{
                "name": "infinite_tool",
                "args": {"query": "test"},
                "id": "call",
            }],
        )
    
    with patch.object(executor, "_get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.ainvoke = mock_ainvoke
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm
        
        result = await executor.execute(
            skill_content="Test",
            user_request="Loop forever",
            tools=[infinite_tool],
        )
    
    assert not result.success
    assert "Max iterations" in result.error
    assert result.iterations == 3


@pytest.mark.asyncio
async def test_agentic_executor_tool_error_handling(mock_tools):
    """Test executor handles tool execution errors gracefully."""
    executor = AgenticExecutor(
        model_name="test-model",
        region="us-east-1",
    )
    
    from langchain_core.tools import tool
    
    @tool
    def failing_tool(arg: str) -> str:
        """A tool that fails."""
        raise ValueError("Tool failed!")
    
    call_count = 0
    
    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockToolCallResponse(
                tool_calls=[{
                    "name": "failing_tool",
                    "args": {"arg": "test"},
                    "id": "call_1",
                }],
            )
        return MockFinalResponse("I encountered an error with the tool.")
    
    with patch.object(executor, "_get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.ainvoke = mock_ainvoke
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm
        
        result = await executor.execute(
            skill_content="Test",
            user_request="Use failing tool",
            tools=[failing_tool],
        )
    
    assert result.success  # Executor should complete even if tool fails
    assert len(result.tool_calls_made) == 1


@pytest.mark.asyncio
async def test_agentic_executor_tracks_written_files(mock_tools):
    """Test executor tracks files written via write_file tool."""
    executor = AgenticExecutor(
        model_name="test-model",
        region="us-east-1",
    )
    
    call_count = 0
    
    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockToolCallResponse(
                tool_calls=[{
                    "name": "write_file",
                    "args": {"file_path": "Main.xaml", "content": "<Activity/>"},
                    "id": "call_1",
                }],
            )
        elif call_count == 2:
            return MockToolCallResponse(
                tool_calls=[{
                    "name": "write_file",
                    "args": {"file_path": "Helper.xaml", "content": "<Activity/>"},
                    "id": "call_2",
                }],
            )
        return MockFinalResponse("Created two workflow files.")
    
    with patch.object(executor, "_get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.ainvoke = mock_ainvoke
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm
        
        result = await executor.execute(
            skill_content="Create workflows",
            user_request="Create Main.xaml and Helper.xaml",
            tools=mock_tools,
        )
    
    assert result.success
    assert "Main.xaml" in result.files_written
    assert "Helper.xaml" in result.files_written


@pytest.mark.asyncio
async def test_agentic_executor_callbacks(mock_tools):
    """Test executor fires callbacks for tool calls and results."""
    tool_calls_logged = []
    tool_results_logged = []
    
    def on_tool_call(name, args):
        tool_calls_logged.append((name, args))
    
    def on_tool_result(name, result):
        tool_results_logged.append((name, result))
    
    executor = AgenticExecutor(
        model_name="test-model",
        region="us-east-1",
        on_tool_call=on_tool_call,
        on_tool_result=on_tool_result,
    )
    
    call_count = 0
    
    async def mock_ainvoke(messages):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MockToolCallResponse(
                tool_calls=[{
                    "name": "read_file",
                    "args": {"file_path": "test.txt"},
                    "id": "call_1",
                }],
            )
        return MockFinalResponse("Done!")
    
    with patch.object(executor, "_get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_bound = MagicMock()
        mock_bound.ainvoke = mock_ainvoke
        mock_llm.bind_tools.return_value = mock_bound
        mock_get_llm.return_value = mock_llm
        
        await executor.execute(
            skill_content="Test",
            user_request="Read file",
            tools=mock_tools,
        )
    
    assert len(tool_calls_logged) == 1
    assert tool_calls_logged[0][0] == "read_file"
    assert len(tool_results_logged) == 1
