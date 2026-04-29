"""MCP tool ``uipath_answer`` — persona-based Q&A.

Routes a general UiPath question to one of the role personas (BA, SA,
Developer, QA). Agent Design (ADD) and Technical Design (TDD) requests are
handled under the Solution Architect persona with an internal document type,
not as separate persona enum values.

Answers use only the read-only library and activity-documentation tools.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from mcp.types import Tool, ToolAnnotations

from uipath_claude.query.persona_router import (
    answer_question,
    available_personas,
    resolve_persona,
)


def get_answer_tools() -> list[Tool]:
    personas = available_personas()
    return [
        Tool(
            name="uipath_answer",
            description=(
                "Answer a general UiPath question under a role persona "
                "(business analyst, solution architect, developer, or QA). "
                "Agent Design (ADD) and Technical Design (TDD) prompts are "
                "routed through the solution architect persona with the "
                "appropriate document template. "
                "Read-only: the persona can only call the "
                "uipath_library_* and uipath_doc_* tools — it cannot modify "
                "the workspace. For BUILD requests use uipath_plan_build "
                "instead."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The user's UiPath question.",
                    },
                    "persona": {
                        "type": "string",
                        "enum": personas,
                        "description": (
                            "Which persona should answer. Defaults to 'sa' "
                            "(Solution Architect). Use uipath_intent_classify "
                            "to pick a persona automatically."
                        ),
                    },
                },
                "required": ["question"],
            },
            annotations=ToolAnnotations(
                title="Answer a UiPath question (persona-routed, read-only)",
                readOnlyHint=True,
            ),
        ),
    ]


async def call_answer_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name != "uipath_answer":
        raise ValueError(f"Unknown answer tool: {name}")

    question = arguments.get("question", "")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("'question' must be a non-empty string")

    persona_arg = arguments.get("persona")
    if persona_arg is not None and not isinstance(persona_arg, str):
        raise TypeError("'persona' must be a string if provided")

    persona = resolve_persona(persona_arg)
    result = await answer_question(question, persona=persona)
    return {"status": "ok", **asdict(result)}
