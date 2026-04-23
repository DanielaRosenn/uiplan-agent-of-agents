"""Persona-based Q&A router for UiPath Claude Code.

The router takes a user question, a persona key (``ba`` / ``sa`` / ``developer``
/ ``qa`` / ``add`` / ``tdd``), builds a read-only tool surface composed of the
library and activity-documentation MCP tools, and hands the request to the
``AgenticExecutor`` under the persona's system prompt.

Personas are NEVER given write/execute tools from here; answering a general
UiPath question must not mutate the workspace. BUILD-intent requests belong on
``run_planner_agent_with_discovery`` instead.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from uipath_claude.agents.add import ADDAgent
from uipath_claude.agents.ba import BAAgent
from uipath_claude.agents.base import BaseAgent
from uipath_claude.agents.developer import DeveloperAgent
from uipath_claude.agents.qa import QAAgent
from uipath_claude.agents.sa import SAAgent
from uipath_claude.agents.tdd import TDDAgent
from uipath_claude.query.agentic_executor import AgenticExecutor, AgenticResult
from uipath_claude.tools.doc_tools import get_doc_tools
from uipath_claude.tools.library_tools import get_library_tools


_PERSONAS: dict[str, type[BaseAgent]] = {
    "ba": BAAgent,
    "sa": SAAgent,
    "developer": DeveloperAgent,
    "qa": QAAgent,
    "add": ADDAgent,
    "tdd": TDDAgent,
}

DEFAULT_PERSONA = "sa"

_READ_ONLY_GUARDRAIL = (
    "\n\n=== READ-ONLY Q&A MODE ===\n"
    "You are answering a UiPath question. You MUST NOT write files, modify the "
    "workspace, run shell commands, or mutate state. Use only the library and "
    "activity-documentation tools provided. Always cite the library book id / "
    "section id (or activity package + activity name) you drew the answer from."
)


@dataclass
class PersonaAnswer:
    """Return value of ``answer_question``."""

    persona: str
    final_response: str
    tool_calls_made: list[dict[str, Any]]
    iterations: int
    tokens_in: int
    tokens_out: int

    @classmethod
    def from_result(cls, persona: str, result: AgenticResult) -> "PersonaAnswer":
        return cls(
            persona=persona,
            final_response=result.final_response,
            tool_calls_made=list(result.tool_calls_made),
            iterations=result.iterations,
            tokens_in=result.tokens_in,
            tokens_out=result.tokens_out,
        )


def available_personas() -> list[str]:
    return list(_PERSONAS.keys())


def resolve_persona(persona: str | None) -> str:
    if not persona:
        return DEFAULT_PERSONA
    key = persona.lower().strip()
    if key not in _PERSONAS:
        raise ValueError(
            f"Unknown persona '{persona}'. Expected one of: "
            f"{sorted(_PERSONAS)}"
        )
    return key


def build_system_prompt(persona: str) -> str:
    key = resolve_persona(persona)
    agent = _PERSONAS[key]()
    return agent.get_system_prompt() + _READ_ONLY_GUARDRAIL


_WRITE_TOOL_NAMES: frozenset[str] = frozenset(
    {
        "write_file",
        "write_documentation",
        "propose_library_update",
        "propose_library_chapter",
    }
)


def get_qa_tools() -> list:
    """Read-only tool surface for persona Q&A (library + doc tools).

    Proposal / write tools are filtered out so personas answering a question
    can never mutate the library or the workspace.
    """
    all_tools = [*get_library_tools(), *get_doc_tools()]
    return [t for t in all_tools if t.name not in _WRITE_TOOL_NAMES]


async def answer_question(
    user_question: str,
    *,
    persona: str | None = None,
    history: list[dict[str, str]] | None = None,
    executor: AgenticExecutor | None = None,
) -> PersonaAnswer:
    """Answer a UiPath question under a persona, read-only."""
    if not isinstance(user_question, str) or not user_question.strip():
        raise ValueError("'user_question' must be a non-empty string")

    key = resolve_persona(persona)
    system_prompt = build_system_prompt(key)
    exe = executor or AgenticExecutor()

    result = await exe.execute(
        skill_content=system_prompt,
        user_request=user_question,
        tools=get_qa_tools(),
        project_context={
            "selected_skill_names": [f"uipath-persona-{key}"],
            "persona": key,
            "mode": "qa",
        },
        skill_name=f"uipath-persona-{key}",
        prior_messages=history,
    )

    return PersonaAnswer.from_result(key, result)
