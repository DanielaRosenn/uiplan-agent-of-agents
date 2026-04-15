"""Tests for planning agent module."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from uipath_claude.tools.skill_execution_tools import get_planning_tools


class TestGetPlanningTools:
    def test_returns_list_of_tools(self):
        tools = get_planning_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_includes_read_only_tools(self):
        tools = get_planning_tools()
        tool_names = {t.name for t in tools}
        assert "read_file" in tool_names
        assert "list_directory" in tool_names
        assert "read_project_json" in tool_names

    def test_excludes_write_tools(self):
        tools = get_planning_tools()
        tool_names = {t.name for t in tools}
        assert "write_file" not in tool_names
        assert "install_package" not in tool_names
        assert "run_workflow" not in tool_names


class TestRunPlannerAgent:
    @pytest.mark.asyncio
    @patch("uipath_claude.query.planner.AgenticExecutor")
    async def test_creates_executor_with_model_params(self, mock_executor_cls):
        from uipath_claude.query.planner import run_planner_agent
        from uipath_claude.query.agentic_executor import AgenticResult

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value=AgenticResult(
                success=True,
                final_response="Plan content here",
                iterations=1,
                tool_calls_made=[],
                files_written=[],
                error=None,
            )
        )
        mock_executor_cls.return_value = mock_executor

        await run_planner_agent(
            "Create a workflow",
            model_name="test-model",
            region="us-east-1",
        )

        mock_executor_cls.assert_called_once_with(
            model_name="test-model", region="us-east-1"
        )

    @pytest.mark.asyncio
    @patch("uipath_claude.query.planner.AgenticExecutor")
    async def test_system_prompt_contains_read_only_constraint(self, mock_executor_cls):
        from uipath_claude.query.planner import run_planner_agent
        from uipath_claude.query.agentic_executor import AgenticResult

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value=AgenticResult(
                success=True,
                final_response="Plan",
                iterations=1,
                tool_calls_made=[],
                files_written=[],
                error=None,
            )
        )
        mock_executor_cls.return_value = mock_executor

        await run_planner_agent(
            "Create a workflow",
            model_name="test-model",
            region="us-east-1",
        )

        call_kwargs = mock_executor.execute.call_args.kwargs
        skill_content = call_kwargs.get("skill_content", "")
        assert "READ-ONLY" in skill_content
        assert "STRICTLY PROHIBITED" in skill_content

    @pytest.mark.asyncio
    @patch("uipath_claude.query.planner.AgenticExecutor")
    async def test_passes_planning_tools_to_executor(self, mock_executor_cls):
        from uipath_claude.query.planner import run_planner_agent
        from uipath_claude.query.agentic_executor import AgenticResult
        from uipath_claude.tools.skill_execution_tools import get_planning_tools

        mock_executor = MagicMock()
        mock_executor.execute = AsyncMock(
            return_value=AgenticResult(
                success=True,
                final_response="Plan",
                iterations=1,
                tool_calls_made=[],
                files_written=[],
                error=None,
            )
        )
        mock_executor_cls.return_value = mock_executor

        await run_planner_agent(
            "Create a workflow",
            model_name="test-model",
            region="us-east-1",
        )

        call_kwargs = mock_executor.execute.call_args.kwargs
        tools = call_kwargs.get("tools", [])
        expected_tools = get_planning_tools()
        assert len(tools) == len(expected_tools)
