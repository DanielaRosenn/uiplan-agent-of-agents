"""AgentOps demo orchestration endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, ValidationInfo, field_validator


router = APIRouter(prefix="/agentops", tags=["agentops"])


class DemoIntakeRequest(BaseModel):
    businessGoal: str
    industry: str | None = None
    systems: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    successCriteria: list[str] = Field(default_factory=list)

    @field_validator("businessGoal")
    @classmethod
    def validate_business_goal(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("businessGoal is required")
        return normalized

    @field_validator("systems", "constraints", "successCriteria", mode="before")
    @classmethod
    def validate_string_lists(cls, value: Any, info: ValidationInfo) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"{info.field_name} must be a list of strings")
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError(f"{info.field_name} must contain only strings")
            item_value = item.strip()
            if item_value:
                normalized.append(item_value)
        return normalized


class SourceLink(BaseModel):
    path: str
    anchor: str | None = None


class SpecialistAssignment(BaseModel):
    agent: str
    role: str
    status: str


class AsIsHandoff(BaseModel):
    id: str
    from_actor: str
    to_actor: str
    channel: str
    artifact: str
    sla: str
    pain: str
    sequence: int


class AsIsPainPoint(BaseModel):
    label: str
    description: str
    related_handoff_ids: list[str] = Field(default_factory=list)


class AsIsViewModel(BaseModel):
    swimlanes: list[str]
    handoffs: list[AsIsHandoff]
    pain_points: list[AsIsPainPoint]
    sources: list[SourceLink]
    systems: list[str] = Field(default_factory=list)


class ToBeBucket(BaseModel):
    id: str
    label: str
    bucket_type: str
    node_ids: list[str]


class ToBeWorkflowStep(BaseModel):
    id: str
    label: str
    shape: str


class ToBeWorkflow(BaseModel):
    id: str
    label: str
    bucket: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    internal_steps: list[ToBeWorkflowStep] = Field(default_factory=list)


class ToBeIntegration(BaseModel):
    id: str
    label: str
    system: str
    used_by_workflow_ids: list[str]


class ToBeOrchestratorResource(BaseModel):
    id: str
    label: str
    resource_type: str
    used_by_workflow_ids: list[str]


class ToBeHitl(BaseModel):
    id: str
    label: str
    channel: str
    actor: str
    callback_contract: str


class RuntimeSequenceStep(BaseModel):
    from_participant: str
    to_participant: str
    label: str
    sequence: int
    is_return: bool


class ToBeViewModel(BaseModel):
    buckets: list[ToBeBucket]
    workflows: list[ToBeWorkflow]
    integrations: list[ToBeIntegration]
    orchestrator: list[ToBeOrchestratorResource]
    hitl: list[ToBeHitl]
    runtime_sequence: list[RuntimeSequenceStep]
    sources: list[SourceLink]


class BuildQueueItem(BaseModel):
    id: str
    title: str
    status: str
    phase: str | None = None


class VerificationGate(BaseModel):
    gate: str
    status: str
    owner: str | None = None


class OrchestratorState(BaseModel):
    current_phase: str
    status: str
    active_workflow: str | None = None
    blocked: bool = False


class DeploymentReadinessStatus(BaseModel):
    status: str
    deployed: bool
    blocker: str | None = None
    target: str | None = None


class HandoffSummary(BaseModel):
    summary: str
    next_action: str | None = None
    owner: str | None = None


class DemoRunResponse(BaseModel):
    orchestrator_state: OrchestratorState
    specialist_assignments: list[SpecialistAssignment]
    as_is_view_model: AsIsViewModel
    to_be_view_model: ToBeViewModel
    build_queue: list[BuildQueueItem]
    verification_checklist: list[VerificationGate]
    deployment_readiness_status: DeploymentReadinessStatus
    handoff_summary: HandoffSummary


@router.post("/demo/run", response_model=DemoRunResponse)
async def run_agentops_demo(payload: DemoIntakeRequest) -> DemoRunResponse:
    systems_list = payload.systems
    response_payload: dict[str, Any] = {
        "orchestrator_state": {
            "current_phase": "Verification",
            "status": "in_progress",
            "active_workflow": "InvoiceExceptionOrchestrator",
            "blocked": True,
        },
        "specialist_assignments": [
            {"agent": "discovery-agent", "role": "Intake analysis", "status": "done"},
            {"agent": "solution-architect-agent", "role": "TO-BE design", "status": "done"},
            {"agent": "builder-orchestrator", "role": "Template clone + deltas", "status": "in_progress"},
            {"agent": "verifier-agent", "role": "Gate verification", "status": "pending"},
            {"agent": "deployment-evidence-agent", "role": "Readiness evidence", "status": "pending"},
        ],
        "as_is_view_model": {
            "swimlanes": ["Finance analyst", "Approver", "Automation operator"],
            "handoffs": [
                {
                    "id": "as-is-1",
                    "from_actor": "Finance analyst",
                    "to_actor": "Approver",
                    "channel": "email",
                    "artifact": "Invoice exception packet",
                    "sla": "4h",
                    "pain": "Manual follow-up and missing context",
                    "sequence": 1,
                },
                {
                    "id": "as-is-2",
                    "from_actor": "Approver",
                    "to_actor": "Automation operator",
                    "channel": "meeting",
                    "artifact": "Approval decision notes",
                    "sla": "2h",
                    "pain": "Non-standard handoff format",
                    "sequence": 2,
                },
            ],
            "pain_points": [
                {
                    "label": "Manual triage",
                    "description": "Exception requests are routed manually across teams.",
                    "related_handoff_ids": ["as-is-1", "as-is-2"],
                }
            ],
            "sources": [{"path": "samples/invoice-exception/intake.json", "anchor": "businessGoal"}],
            "systems": systems_list,
        },
        "to_be_view_model": {
            "buckets": [
                {"id": "bucket-intake", "label": "Intake", "bucket_type": "intake", "node_ids": ["wf-intake"]},
                {"id": "bucket-processing", "label": "Processing", "bucket_type": "processing", "node_ids": ["wf-routing"]},
                {"id": "bucket-evidence", "label": "Evidence", "bucket_type": "evidence", "node_ids": ["orch-evidence"]},
            ],
            "workflows": [
                {
                    "id": "wf-intake",
                    "label": "Normalize exception intake",
                    "bucket": "intake",
                    "inputs": ["inbox message", "invoice metadata"],
                    "outputs": ["normalized payload"],
                    "internal_steps": [{"id": "step-1", "label": "Parse input", "shape": "activity"}],
                },
                {
                    "id": "wf-routing",
                    "label": "Route to specialist",
                    "bucket": "processing",
                    "inputs": ["normalized payload"],
                    "outputs": ["assignment + checklist"],
                    "internal_steps": [{"id": "step-2", "label": "Assign agent", "shape": "gateway"}],
                },
            ],
            "integrations": [
                {
                    "id": "integration-action-center",
                    "label": "Action Center",
                    "system": systems_list[2] if len(systems_list) > 2 else "UiPath Action Center",
                    "used_by_workflow_ids": ["wf-routing"],
                }
            ],
            "orchestrator": [
                {
                    "id": "orch-evidence",
                    "label": "Deployment evidence queue",
                    "resource_type": "queue",
                    "used_by_workflow_ids": ["wf-routing"],
                }
            ],
            "hitl": [
                {
                    "id": "hitl-approval",
                    "label": "Invoice exception approval",
                    "channel": "Action Center",
                    "actor": "Finance approver",
                    "callback_contract": "approval_result_v1",
                }
            ],
            "runtime_sequence": [
                {
                    "from_participant": "Inbox",
                    "to_participant": "Intake workflow",
                    "label": "New exception request",
                    "sequence": 1,
                    "is_return": False,
                }
            ],
            "sources": [{"path": "samples/invoice-exception/intake.json", "anchor": "successCriteria"}],
        },
        "build_queue": [
            {"id": "queue-1", "title": "Clone base Studio template", "status": "done", "phase": "Build"},
            {"id": "queue-2", "title": "Apply generated workflows", "status": "in_progress", "phase": "Build"},
            {"id": "queue-3", "title": "Run local verification script", "status": "pending", "phase": "Verification"},
        ],
        "verification_checklist": [
            {"gate": "AS-IS captured", "status": "passed", "owner": "discovery-agent"},
            {"gate": "TO-BE mapped", "status": "passed", "owner": "solution-architect-agent"},
            {"gate": "Tests green", "status": "pending", "owner": "verifier-agent"},
            {"gate": "Evidence complete", "status": "pending", "owner": "deployment-evidence-agent"},
        ],
        "deployment_readiness_status": {
            "status": "blocked",
            "deployed": False,
            "blocker": "Verification gates are still pending.",
            "target": "personal-workspace",
        },
        "handoff_summary": {
            "summary": "Template clone completed. Generated deltas are ready for verification.",
            "next_action": "Complete verification gates and package deployment evidence.",
            "owner": "builder-orchestrator",
        },
    }
    return DemoRunResponse.model_validate(response_payload)
