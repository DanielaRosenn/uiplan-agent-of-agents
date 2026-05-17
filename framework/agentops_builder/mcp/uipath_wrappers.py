"""Agent-facing wrapper definitions for prioritized MCP operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .telemetry_contracts import ToolTelemetryRecord


@dataclass(frozen=True, slots=True)
class WrappedToolRequest:
    tool_id: str
    arguments: dict[str, Any] = field(default_factory=dict)
    phase: str = "unknown"
    status: str = "ready"
    approval_required: bool = False


def _telemetry(
    *,
    tool_id: str,
    category: str,
    phase: str,
    risk_level: str,
    approval_required: bool,
    evidence_output: str,
    status: str = "ready",
) -> ToolTelemetryRecord:
    return ToolTelemetryRecord(
        tool_id=tool_id,
        category=category,
        phase=phase,
        risk_level=risk_level,
        status=status,
        approval_required=approval_required,
        evidence_output=evidence_output,
    )


def wrap_plan_review(plan_text: str, phase: str = "design") -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="uipath_plan_review",
        arguments={"stage": "all", "plan_text": plan_text},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="plan",
        phase=phase,
        risk_level="low",
        approval_required=False,
        evidence_output="review findings json",
    )


def wrap_skill_match(user_input: str, phase: str = "discovery") -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="uipath_skill_match",
        arguments={"user_input": user_input, "top_k": 5},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="skill",
        phase=phase,
        risk_level="low",
        approval_required=False,
        evidence_output="ranked skill matches",
    )


def wrap_skill_get(skill_name: str, phase: str = "discovery") -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="uipath_skill_get",
        arguments={"skill_name": skill_name},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="skill",
        phase=phase,
        risk_level="low",
        approval_required=False,
        evidence_output="skill markdown body",
    )


def wrap_library_lookup(question: str, phase: str = "design") -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="uipath_library_lookup",
        arguments={"question": question, "allow_network": False},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="library",
        phase=phase,
        risk_level="low",
        approval_required=False,
        evidence_output="lookup answer with source",
    )


def wrap_workflow_read(file_path: str, phase: str = "build") -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="uipath_workflow_read_file",
        arguments={"file_path": file_path},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="workflow",
        phase=phase,
        risk_level="low",
        approval_required=False,
        evidence_output="workflow source snapshot",
    )


def wrap_workflow_build_verify(
    project_dir: str, phase: str = "verify"
) -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="uipath_workflow_build_and_verify",
        arguments={"project_dir": project_dir, "run_after_validate": True},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="workflow",
        phase=phase,
        risk_level="medium",
        approval_required=False,
        evidence_output="verify verdict and diagnostics",
    )


def wrap_deployment_readiness(
    project_dir: str, phase: str = "deploy"
) -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="uipath_workflow_session_status",
        arguments={"project_dir": project_dir},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="deployment",
        phase=phase,
        risk_level="medium",
        approval_required=False,
        evidence_output="session gate and readiness status",
    )


def wrap_orchestrator_telemetry_readiness(
    folder: str, phase: str = "deploy"
) -> tuple[WrappedToolRequest, ToolTelemetryRecord]:
    request = WrappedToolRequest(
        tool_id="orchestrator.telemetry_readiness",
        arguments={"folder": folder},
        phase=phase,
    )
    return request, _telemetry(
        tool_id=request.tool_id,
        category="telemetry",
        phase=phase,
        risk_level="low",
        approval_required=False,
        evidence_output="orchestrator telemetry readiness object",
    )

