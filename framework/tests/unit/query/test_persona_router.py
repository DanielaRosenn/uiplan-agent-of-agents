"""Tests for persona_router."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from uipath_claude.query import persona_router
from uipath_claude.query.agentic_executor import AgenticResult
from uipath_claude.query.intent_classifier import IntentType
from uipath_claude.query.persona_selection import select_persona_for_text


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
    @pytest.mark.parametrize("persona", ["ba", "sa", "developer", "qa"])
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

    def test_sa_with_add_document_type_uses_add_template(self):
        prompt = persona_router.build_system_prompt("sa", document_type="ADD")
        assert "Architecture Design Document (ADD)" in prompt
        assert "READ-ONLY Q&A MODE" in prompt

    def test_sa_with_tdd_document_type_uses_tdd_template(self):
        prompt = persona_router.build_system_prompt("sa", document_type="TDD")
        assert "Technical Design Document (TDD)" in prompt
        assert "READ-ONLY Q&A MODE" in prompt


class TestPersonaSelectionDocumentTypes:
    def test_agent_design_keywords_resolve_to_sa_and_add(self):
        p, reason, doc = select_persona_for_text(
            "Write an agent design document for my support agent.",
            IntentType.QUESTION,
        )
        assert p == "sa"
        assert doc == "ADD"
        assert reason == "agent_design_document"

    def test_technical_design_keywords_resolve_to_sa_and_tdd(self):
        p, reason, doc = select_persona_for_text(
            "I need a technical design document for Excel validation.",
            IntentType.QUESTION,
        )
        assert p == "sa"
        assert doc == "TDD"
        assert reason == "technical_design_document"


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
    def test_rejects_empty_question(self):
        with pytest.raises(ValueError):
            asyncio.run(persona_router.answer_question(""))

    def test_uses_persona_prompt_and_readonly_tools(self):
        exe = MagicMock()
        exe.execute = AsyncMock(
            return_value=AgenticResult(success=True, final_response="ANS")
        )

        result = asyncio.run(
            persona_router.answer_question(
                "How does REFramework handle business exceptions?",
                persona="qa",
                executor=exe,
            )
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

    def test_defaults_to_sa(self):
        exe = MagicMock()
        exe.execute = AsyncMock(
            return_value=AgenticResult(success=True, final_response="A")
        )
        result = asyncio.run(persona_router.answer_question("what is maestro?", executor=exe))
        assert result.persona == "sa"
        assert result.persona_reason == "question_default"

    def test_auto_selects_qa_for_validation_question(self):
        exe = MagicMock()
        exe.execute = AsyncMock(
            return_value=AgenticResult(success=True, final_response="A")
        )
        result = asyncio.run(
            persona_router.answer_question(
                "What validation strategy should I use for this workflow?",
                executor=exe,
            )
        )
        assert result.persona == "qa"
        assert result.persona_reason == "quality/testing keyword"

    def test_auto_selects_sa_add_and_passes_document_type_context(self):
        exe = MagicMock()
        exe.execute = AsyncMock(
            return_value=AgenticResult(success=True, final_response="A")
        )
        result = asyncio.run(
            persona_router.answer_question(
                "Draft an Agent Design Document for a support triage agent.",
                executor=exe,
            )
        )
        assert result.persona == "sa"
        assert result.document_type == "ADD"
        _, kwargs = exe.execute.call_args
        assert kwargs["project_context"]["document_type"] == "ADD"
        assert kwargs["project_context"]["selected_document_type"] == "ADD"
        assert kwargs["project_context"]["selected_skill_names"] == ["uipath-persona-sa"]

    def test_explicit_persona_override_wins(self):
        exe = MagicMock()
        exe.execute = AsyncMock(
            return_value=AgenticResult(success=True, final_response="A")
        )
        result = asyncio.run(
            persona_router.answer_question(
                "What validation strategy should I use?",
                persona="developer",
                executor=exe,
            )
        )
        assert result.persona == "developer"
        assert result.persona_reason == "explicit"
