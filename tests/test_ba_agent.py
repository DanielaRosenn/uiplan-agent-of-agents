"""Tests for Business Analyst agent."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from uipath_claude.query.ba_agent import (
    run_ba_agent,
    BA_SYSTEM_PROMPT,
)


class TestBAAgent:
    """Tests for BA agent."""

    def test_system_prompt_contains_pdd_focus(self):
        """BA agent system prompt should focus on PDD creation."""
        assert "PDD" in BA_SYSTEM_PROMPT or "Process Definition" in BA_SYSTEM_PROMPT
        assert "business" in BA_SYSTEM_PROMPT.lower()

    def test_system_prompt_has_questioning_strategy(self):
        """BA agent should have strategy for gathering requirements."""
        assert "question" in BA_SYSTEM_PROMPT.lower() or "ask" in BA_SYSTEM_PROMPT.lower()

    @pytest.mark.asyncio
    async def test_ba_agent_returns_result(self):
        """BA agent should return AgenticResult."""
        with patch("uipath_claude.query.ba_agent.AgenticExecutor") as mock_executor:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.final_response = "Here is the PDD..."
            mock_result.tool_calls = []
            mock_result.iterations = 3
            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            result = await run_ba_agent(
                user_request="Create a PDD for invoice processing",
                model_name="test-model",
                region="us-east-1",
            )
            
            assert result is not None
            mock_instance.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_ba_agent_uses_doc_tools(self):
        """BA agent should have access to documentation tools."""
        with patch("uipath_claude.query.ba_agent.AgenticExecutor") as mock_executor:
            mock_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.final_response = "PDD created"
            mock_result.tool_calls = [{"name": "write_documentation"}]
            mock_result.iterations = 2
            mock_instance.execute = AsyncMock(return_value=mock_result)
            mock_executor.return_value = mock_instance
            
            await run_ba_agent(
                user_request="Create a PDD",
                model_name="test-model",
                region="us-east-1",
            )
            
            call_kwargs = mock_instance.execute.call_args[1]
            tool_names = [t.name for t in call_kwargs.get("tools", [])]
            assert "write_documentation" in tool_names or "read_doc_template" in tool_names
