"""Data types for host-agnostic LLM chat orchestration (CLI, MCP, plain Claude Code)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RouteKind(str, Enum):
    """High-level next step the assistant should take."""

    ANSWER = "answer"
    CLARIFY = "clarify"
    DOCUMENTATION = "documentation"
    UIPLAN = "uiplan"
    PLAN = "plan"
    EXECUTE = "execute"
    COMMAND_HINT = "command_hint"
    REFUSE = "refuse"


class ApprovalLevel(str, Enum):
    """User confirmation needed before side effects."""

    NONE = "none"
    CONFIRM_ROUTE = "confirm_route"
    CONFIRM_WRITE = "confirm_write"
    CONFIRM_DEPLOY = "confirm_deploy"


@dataclass
class OrchestrationContext:
    """Context passed to the LLM router (JSON-serializable as dict if needed)."""

    user_request: str
    project_root: str
    tool_profile: str
    command_names: list[str] = field(default_factory=list)
    history_excerpt: list[dict[str, str]] = field(default_factory=list)
    intent: str = ""
    intent_reason: str = ""
    grounding_pack: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationDecision:
    """Structured router output; validated in orchestration_router."""

    route: RouteKind
    confidence: float
    rationale: str
    approval_level: ApprovalLevel = ApprovalLevel.NONE
    question: str | None = None
    suggested_command: str | None = None
    next_action: str | None = None
    selected_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "approval_level": self.approval_level.value,
            "question": self.question,
            "suggested_command": self.suggested_command,
            "next_action": self.next_action,
            "selected_skills": list(self.selected_skills),
        }
