"""Typed view of chat graph state (plain dict at runtime)."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    messages: list[dict[str, str]]
    phase: str
    selected_skill_names: list[str]
    assistant_response: str
    pending_question: str | None
    project_path: str | None
    generated_files: list[str]
    validation_errors: list[dict[str, Any]]
    fix_attempts: int
    user_response: str | None
    session_id: str
