"""Tests for Solution Architect agent."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from uipath_claude.query.solution_architect_agent import (
    run_solution_architect_agent,
    SA_SYSTEM_PROMPT,
    DocType,
)


class TestSolutionArchitectAgent:
    """Tests for Solution Architect agent."""

    def test_system_prompt_contains_sdd_focus(self):
        """SA agent system prompt should handle SDD/ADD/TDD."""
        assert "SDD" in SA_SYSTEM_PROMPT or "Solution Design" in SA_SYSTEM_PROMPT
        assert "architect" in SA_SYSTEM_PROMPT.lower()

    def test_system_prompt_references_pdd(self):
        """SA agent should reference PDD as input."""
        assert "PDD" in SA_SYSTEM_PROMPT

    def test_doc_type_enum_values(self):
        """DocType enum should have SDD, ADD, TDD."""
        assert DocType.SDD.value == "sdd"
        assert DocType.ADD.value == "add"
        assert DocType.TDD.value == "tdd"

    @pytest.mark.asyncio
    async def test_sa_agent_sdd_mode(self):
        """SA agent should create SDD when requested."""
        with patch("uipath_claude.query.solution_architect_agent.AgenticExecutor") as mock_executor:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.final_response = "Here is the SDD..."
            mock_result.tool_calls = []
            mock_result.iterations = 3
            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = await run_solution_architect_agent(
                user_request="Create an SDD based on the PDD",
                doc_type=DocType.SDD,
                model_name="test-model",
                region="us-east-1",
            )
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_sa_agent_add_mode(self):
        """SA agent should create ADD for agentic projects."""
        with patch("uipath_claude.query.solution_architect_agent.AgenticExecutor") as mock_executor:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.final_response = "Here is the ADD..."
            mock_result.tool_calls = []
            mock_result.iterations = 3
            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = await run_solution_architect_agent(
                user_request="Create an Agent Design Document",
                doc_type=DocType.ADD,
                model_name="test-model",
                region="us-east-1",
            )
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_sa_agent_uses_doc_tools(self):
        """SA agent should have access to documentation tools."""
        with patch("uipath_claude.query.solution_architect_agent.AgenticExecutor") as mock_executor:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.final_response = "SDD created"
            mock_result.tool_calls = [{"name": "read_documentation"}]
            mock_result.iterations = 2
            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            await run_solution_architect_agent(
                user_request="Create SDD",
                doc_type=DocType.SDD,
                model_name="test-model",
                region="us-east-1",
            )
            
            call_kwargs = mock_instance.execute.call_args[1]
            tool_names = [t.name for t in call_kwargs.get("tools", [])]
            assert "read_documentation" in tool_names
