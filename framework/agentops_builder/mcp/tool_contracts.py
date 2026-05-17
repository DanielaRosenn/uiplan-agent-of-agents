"""Tool contract models for AgentOps Builder MCP inventory."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class MCPToolCategory(StrEnum):
    PLAN = "plan"
    SKILL = "skill"
    LIBRARY = "library"
    WORKFLOW = "workflow"
    DEPLOYMENT = "deployment"
    ORCHESTRATOR_READONLY = "orchestrator_readonly"
    ORCHESTRATOR_ACTION = "orchestrator_action"
    TELEMETRY = "telemetry"


class ToolRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalRequirement(StrEnum):
    NONE = "none"
    USER_CONFIRMATION = "user_confirmation"
    EXPLICIT_APPROVAL_GATE = "explicit_approval_gate"


class DirectCallPolicy(StrEnum):
    ALLOWED = "allowed"
    WRAPPER_REQUIRED = "wrapper_required"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class MCPToolContract:
    tool_id: str
    category: MCPToolCategory
    label: str
    risk_level: ToolRiskLevel
    approval_requirement: ApprovalRequirement
    evidence_output: str
    direct_call_policy: DirectCallPolicy
    demo_safe_action: bool = False

    def __post_init__(self) -> None:
        if not self.tool_id.strip():
            raise ValueError("tool_id must be non-empty")
        if not self.label.strip():
            raise ValueError("label must be non-empty")
        if not self.evidence_output.strip():
            raise ValueError("evidence_output must be non-empty")

