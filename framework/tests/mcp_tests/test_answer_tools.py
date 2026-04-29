"""Tests for uipath_answer MCP tool."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server.tools import answer_tools
from uipath_claude.query.persona_router import PersonaAnswer


class TestGetAnswerTools:
    def test_exposes_single_tool(self):
        tools = answer_tools.get_answer_tools()
        assert len(tools) == 1
        assert tools[0].name == "uipath_answer"
        schema = tools[0].inputSchema
        assert schema["required"] == ["question"]
        assert set(schema["properties"]["persona"]["enum"]) == {
            "ba",
            "sa",
            "developer",
            "qa",
        }


class TestCallAnswerTool:
    @pytest.mark.asyncio
    async def test_rejects_wrong_tool_name(self):
        with pytest.raises(ValueError):
            await answer_tools.call_answer_tool("nope", {"question": "x"})

    @pytest.mark.asyncio
    async def test_rejects_empty_question(self):
        with pytest.raises(ValueError):
            await answer_tools.call_answer_tool(
                "uipath_answer", {"question": ""}
            )

    @pytest.mark.asyncio
    async def test_rejects_unknown_persona(self):
        with pytest.raises(ValueError):
            await answer_tools.call_answer_tool(
                "uipath_answer", {"question": "hi", "persona": "ceo"}
            )

    @pytest.mark.asyncio
    async def test_routes_to_persona_router(self):
        fake = PersonaAnswer(
            persona="developer",
            final_response="Use try/catch with BusinessRuleException.",
            tool_calls_made=[],
            iterations=3,
            tokens_in=100,
            tokens_out=50,
        )
        with patch.object(
            answer_tools, "answer_question", AsyncMock(return_value=fake)
        ) as mock_ans:
            out = await answer_tools.call_answer_tool(
                "uipath_answer",
                {"question": "How to handle errors?", "persona": "developer"},
            )

        assert out["status"] == "ok"
        assert out["persona"] == "developer"
        assert out["final_response"].startswith("Use try/catch")
        mock_ans.assert_awaited_once()
        _, kwargs = mock_ans.call_args
        assert kwargs["persona"] == "developer"

    @pytest.mark.asyncio
    async def test_defaults_to_sa_persona(self):
        fake = PersonaAnswer(
            persona="sa", final_response="ok", tool_calls_made=[],
            iterations=1, tokens_in=1, tokens_out=1,
        )
        with patch.object(
            answer_tools, "answer_question", AsyncMock(return_value=fake)
        ) as mock_ans:
            out = await answer_tools.call_answer_tool(
                "uipath_answer", {"question": "what is Orchestrator?"}
            )

        assert out["persona"] == "sa"
        _, kwargs = mock_ans.call_args
        assert kwargs["persona"] == "sa"
