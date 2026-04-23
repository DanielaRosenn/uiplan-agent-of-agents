"""Structured skill invocation with isolated prompt context (forked-style)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from uipath_claude.query.feedback_loop import detect_clarifying_question
from uipath_claude.skills.loader import load_skill_content

_FILE_BLOCK_RE = re.compile(
    r"<<<UIPATH_FILE path=(?P<q>[\"'])(?P<rel>.+?)(?P=q)>>>(?P<body>.*?)<<<END_UIPATH_FILE>>>",
    re.DOTALL,
)


@dataclass
class SkillResult:
    success: bool
    output: str
    artifacts: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    follow_up_required: bool = False
    follow_up_question: str | None = None


@runtime_checkable
class _ModelEngine(Protocol):
    async def run(
        self,
        messages: list[dict[str, str]],
        tools: list[Any],
        system_prompt: str,
    ) -> str: ...


def _artifact_paths_from_response(response: str) -> list[Path]:
    paths: list[Path] = []
    for m in _FILE_BLOCK_RE.finditer(response):
        paths.append(Path(m.group("rel").strip().replace("\\", "/")))
    return paths


def _fork_system_prompt(skill_name: str, skill_body: str, context: dict[str, Any]) -> str:
    extra = context.get("extra_system", "")
    parts = [
        f"You are executing the UiPath agent skill `{skill_name}`.",
        "Follow the skill instructions strictly. Do not claim you ran shell commands unless output is shown.",
        "",
        skill_body,
    ]
    if extra:
        parts.extend(["", "Additional context:", str(extra)])
    return "\n".join(parts)


class SkillTool:
    """Invoke one skill in an isolated message stack (forked-style context)."""

    def __init__(
        self,
        skills: list[dict[str, Any]],
        engine: _ModelEngine,
    ) -> None:
        self._by_name = {str(s.get("name", "")): s for s in skills if s.get("name")}
        self._engine = engine

    def _build_skill_prompt(self, skill: dict[str, Any], content: str, context: dict[str, Any]) -> str:
        return _fork_system_prompt(str(skill.get("name", "")), content, context)

    def _parse_response(self, response: str, _skill: dict[str, Any]) -> SkillResult:
        q = detect_clarifying_question(response)
        arts = _artifact_paths_from_response(response)
        return SkillResult(
            success=True,
            output=response,
            artifacts=arts,
            errors=[],
            follow_up_required=q is not None,
            follow_up_question=q,
        )

    async def invoke(
        self,
        skill_name: str,
        user_request: str,
        context: dict[str, Any] | None = None,
    ) -> SkillResult:
        ctx = context or {}
        skill = self._by_name.get(skill_name)
        if not skill:
            return SkillResult(
                success=False,
                output="",
                artifacts=[],
                errors=[f"Skill not found: {skill_name}"],
                follow_up_required=False,
                follow_up_question=None,
            )
        path = str(skill.get("path", ""))
        content = load_skill_content(path) if path else ""
        if not content.strip():
            return SkillResult(
                success=False,
                output="",
                artifacts=[],
                errors=[f"Skill content empty or unreadable: {skill_name}"],
                follow_up_required=False,
                follow_up_question=None,
            )
        system_prompt = self._build_skill_prompt(skill, content, ctx)
        fork_messages: list[dict[str, str]] = [
            {"role": "user", "content": user_request},
        ]
        try:
            text = await self._engine.run(fork_messages, [], system_prompt=system_prompt)
        except Exception as exc:  # pragma: no cover - network
            return SkillResult(
                success=False,
                output="",
                artifacts=[],
                errors=[str(exc)],
                follow_up_required=False,
                follow_up_question=None,
            )
        return self._parse_response(str(text), skill)


def create_skill_tool(skill_metadata: dict[str, Any], *, engine: _ModelEngine | None = None):
    """
    Build a LangChain tool for optional REPL-style skill calls.

    When ``engine`` is omitted, returns a tool that echoes skill markdown (legacy).
    """
    from langchain_core.tools import tool

    skill_name = skill_metadata["name"]
    skill_description = skill_metadata["description"]
    skill_path = skill_metadata.get("path", "")

    if engine is None or not hasattr(engine, "run"):

        @tool
        def skill_tool(query: str) -> str:
            """Execute skill with given query."""
            content = load_skill_content(skill_path)
            return f"Skill: {skill_name}\n\nContent:\n{content}\n\nQuery: {query}"

        skill_tool.name = skill_name
        skill_tool.description = skill_description
        return skill_tool

    st = SkillTool([skill_metadata], engine)

    @tool
    def skill_tool(query: str) -> str:
        """Execute skill with given query (model-backed)."""
        import asyncio

        result = asyncio.run(st.invoke(skill_name, query, {}))
        if not result.success:
            return "Errors: " + "; ".join(result.errors)
        if result.follow_up_required and result.follow_up_question:
            return result.output + "\n\n[Follow-up suggested: " + result.follow_up_question + "]"
        return result.output

    skill_tool.name = skill_name
    skill_tool.description = skill_description
    return skill_tool
