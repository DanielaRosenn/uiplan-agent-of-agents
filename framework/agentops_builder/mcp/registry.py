"""Canonical AgentOps MCP tool inventory and phase mapping."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .orchestrator_integration import APPROVAL_GATED_ACTION_WRAPPERS, READ_ONLY_WRAPPERS
from .tool_contracts import (
    ApprovalRequirement,
    DirectCallPolicy,
    MCPToolCategory,
    MCPToolContract,
    ToolRiskLevel,
)


def _inventory() -> list[MCPToolContract]:
    base_tools = [
        MCPToolContract(
            tool_id="uipath_plan_review",
            category=MCPToolCategory.PLAN,
            label="Plan Review",
            risk_level=ToolRiskLevel.LOW,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="structured review findings",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
        MCPToolContract(
            tool_id="uipath_skill_match",
            category=MCPToolCategory.SKILL,
            label="Skill Match",
            risk_level=ToolRiskLevel.LOW,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="ranked skill candidates",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
        MCPToolContract(
            tool_id="uipath_skill_get",
            category=MCPToolCategory.SKILL,
            label="Skill Read",
            risk_level=ToolRiskLevel.LOW,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="selected skill content",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
        MCPToolContract(
            tool_id="uipath_library_lookup",
            category=MCPToolCategory.LIBRARY,
            label="Library Lookup",
            risk_level=ToolRiskLevel.LOW,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="answer + cited source line",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
        MCPToolContract(
            tool_id="uipath_workflow_read_file",
            category=MCPToolCategory.WORKFLOW,
            label="Workflow Read",
            risk_level=ToolRiskLevel.LOW,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="file snapshot",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
        MCPToolContract(
            tool_id="uipath_workflow_build_and_verify",
            category=MCPToolCategory.WORKFLOW,
            label="Workflow Build+Verify",
            risk_level=ToolRiskLevel.MEDIUM,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="build verification verdict and diagnostics",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
        MCPToolContract(
            tool_id="uipath_workflow_session_status",
            category=MCPToolCategory.DEPLOYMENT,
            label="Deployment Readiness",
            risk_level=ToolRiskLevel.MEDIUM,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="gate status and pending blockers",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
        MCPToolContract(
            tool_id="orchestrator.telemetry_readiness",
            category=MCPToolCategory.TELEMETRY,
            label="Orchestrator Telemetry Readiness",
            risk_level=ToolRiskLevel.LOW,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="normalized orchestrator readiness telemetry",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        ),
    ]

    readonly_tools = [
        MCPToolContract(
            tool_id=tool_id,
            category=MCPToolCategory.ORCHESTRATOR_READONLY,
            label=tool_id.replace("orchestrator.", "").replace("_", " ").title(),
            risk_level=ToolRiskLevel.LOW,
            approval_requirement=ApprovalRequirement.NONE,
            evidence_output="redacted orchestrator read-only payload",
            direct_call_policy=DirectCallPolicy.WRAPPER_REQUIRED,
            demo_safe_action=True,
        )
        for tool_id in READ_ONLY_WRAPPERS
    ]

    action_tools = [
        MCPToolContract(
            tool_id=tool_id,
            category=MCPToolCategory.ORCHESTRATOR_ACTION,
            label=tool_id.replace("orchestrator.", "").replace("_", " ").title(),
            risk_level=ToolRiskLevel.HIGH,
            approval_requirement=ApprovalRequirement.EXPLICIT_APPROVAL_GATE,
            evidence_output="redacted action envelope with approval trace",
            direct_call_policy=DirectCallPolicy.DENIED,
            demo_safe_action=False,
        )
        for tool_id in APPROVAL_GATED_ACTION_WRAPPERS
    ]

    return base_tools + readonly_tools + action_tools


REGISTRY: dict[str, MCPToolContract] = {tool.tool_id: tool for tool in _inventory()}

PHASE_TOOL_PLAN_MAPPING: dict[str, tuple[str, ...]] = {
    "discovery": (
        "uipath_skill_match",
        "uipath_skill_get",
        "uipath_library_lookup",
    ),
    "design": (
        "uipath_plan_review",
        "uipath_library_lookup",
    ),
    "build": (
        "uipath_workflow_read_file",
        "uipath_workflow_build_and_verify",
    ),
    "verify": (
        "uipath_workflow_build_and_verify",
        "orchestrator.list_jobs",
        "orchestrator.get_job_logs",
    ),
    "deploy": (
        "uipath_workflow_session_status",
        "orchestrator.telemetry_readiness",
        "orchestrator.start_job",
    ),
}


def iter_contracts() -> Iterable[MCPToolContract]:
    return REGISTRY.values()


def contracts_by_category() -> dict[str, list[MCPToolContract]]:
    grouped: dict[str, list[MCPToolContract]] = defaultdict(list)
    for contract in REGISTRY.values():
        grouped[contract.category.value].append(contract)
    for contracts in grouped.values():
        contracts.sort(key=lambda item: item.tool_id)
    return dict(grouped)


def tools_for_phase(phase: str) -> tuple[str, ...]:
    return PHASE_TOOL_PLAN_MAPPING.get(phase, ())

