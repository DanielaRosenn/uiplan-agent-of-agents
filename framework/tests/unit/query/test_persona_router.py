"""Tests for persona_router."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from uipath_claude.query import persona_router
from uipath_claude.query.agentic_executor import AgenticResult


class TestPersonaResolution:
    def test_default_is_sa(self):
        assert persona_router.resolve_persona(None) == "sa"
        assert persona_router.resolve_persona("") == "sa"

    def test_all_personas_resolvable(self):
        for p in persona_router.available_personas():
            assert persona_router.resolve_persona(p) == p
            assert persona_router.resolve_persona(p.upper()) == p

    def test_unknown_persona_raises(self):
        with pytest.raises(ValueError):
            persona_router.resolve_persona("ceo")


class TestSystemPrompt:
    @pytest.mark.parametrize("persona", ["ba", "sa", "developer", "qa", "add", "tdd"])
    def test_includes_readonly_guardrail(self, persona: str):
        prompt = persona_router.build_system_prompt(persona)
        assert "READ-ONLY Q&A MODE" in prompt
        assert "MUST NOT write files" in prompt

    def test_prompt_differs_per_persona(self):
        ba = persona_router.build_system_prompt("ba")
        sa = persona_router.build_system_prompt("sa")
        assert ba != sa
        assert "Business Analyst" in ba
        assert "Solution Architect" in sa


class TestQATools:
    def test_is_read_only(self):
        tools = persona_router.get_qa_tools()
        names = {t.name for t in tools}
        for forbidden in (
            "write_file",
            "write_documentation",
            "propose_library_update",
            "propose_library_chapter",
        ):
            assert forbidden not in names, f"{forbidden} must not be in QA tools"
        assert "search_library" in names
        assert "read_section" in names
        assert "read_documentation" in names


class TestAnswerQuestion:
    @pytest.mark.asyncio
    async def test_rejects_empty_question(self):
        with pytest.raises(ValueError):
            await persona_router.answer_question("")

    @pytest.mark.asyncio
    async def test_uses_persona_prompt_and_readonly_tools(self):
        exe = MagicMock()
        exe.execute = AsyncMock(
            return_value=AgenticResult(success=True, final_response="ANS")
        )

        result = await persona_router.answer_question(
            "How does REFramework handle business exceptions?",
            persona="qa",
            executor=exe,
        )

        assert result.persona == "qa"
        assert result.final_response == "ANS"
        exe.execute.assert_awaited_once()
        _, kwargs = exe.execute.call_args
        assert "QA Engineer" in kwargs["skill_content"]
        assert "READ-ONLY Q&A MODE" in kwargs["skill_content"]
        tool_names = {t.name for t in kwargs["tools"]}
        assert "write_file" not in tool_names
        assert kwargs["skill_name"] == "uipath-persona-qa"
        assert kwargs["project_context"]["persona"] == "qa"

    @pytest.mark.asyncio
    async def test_defaults_to_sa(self):
        exe = MagicMock()
        exe.execute = AsyncMock(
            return_value=AgenticResult(success=True, final_response="A")
        )
        result = await persona_router.answer_question("what is maestro?", executor=exe)
        assert result.persona == "sa"
