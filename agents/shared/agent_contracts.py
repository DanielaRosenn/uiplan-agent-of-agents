from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any


def _to_clean_string(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if value is None:
        return ""
    return str(value).strip()


def _to_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_to_clean_string(item) for item in value if _to_clean_string(item)]
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


def _read_string(payload: dict[str, Any], key: str, default: str = "") -> str:
    value = _to_clean_string(payload.get(key, ""))
    return value if value else default


@dataclass
class BusinessBrief:
    project_name: str
    domain: str
    objective: str
    systems: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    stakeholders: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    output_root: str = ""
    run_id: str = ""
    dry_run: bool = True

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "BusinessBrief":
        return cls(
            project_name=_read_string(payload, "projectName", "agent-of-agents-build"),
            domain=_read_string(payload, "domain", "operations"),
            objective=_read_string(payload, "objective", _read_string(payload, "businessGoal", "")),
            systems=_to_string_list(payload.get("systems", [])),
            constraints=_to_string_list(payload.get("constraints", [])),
            stakeholders=_to_string_list(payload.get("stakeholders", [])),
            success_criteria=_to_string_list(payload.get("successCriteria", [])),
            output_root=_to_clean_string(payload.get("outputRoot", "")),
            run_id=_to_clean_string(payload.get("runId", "")),
            dry_run=bool(payload.get("dryRun", True)),
        )


@dataclass
class AgentAssignment:
    phase: str
    agent: str
    responsibility: str


@dataclass
class GeneratedDocument:
    name: str
    title: str
    path: str
    status: str = "generated"


@dataclass
class BuildArtifact:
    name: str
    kind: str
    path: str
    status: str = "generated"


@dataclass
class ProvisionedResource:
    resource_type: str
    name: str
    status: str
    resource_id: str = ""
    details: str = ""


@dataclass
class ExecutionEvidence:
    run_id: str
    status: str
    output_dir: str
    started_at: str = ""
    ended_at: str = ""
    command_logs: list[str] = field(default_factory=list)
    evidence_files: list[str] = field(default_factory=list)


@dataclass
class HandoffPackage:
    brief: BusinessBrief
    assignments: list[AgentAssignment] = field(default_factory=list)
    generated_documents: list[GeneratedDocument] = field(default_factory=list)
    build_artifacts: list[BuildArtifact] = field(default_factory=list)
    provisioned_resources: list[ProvisionedResource] = field(default_factory=list)
    execution: ExecutionEvidence | None = None
    summary: str = ""
    # Legacy compatibility fields.
    intake: BusinessBrief | None = None
    artifact_plan: ArtifactPlan | None = None
    verification: VerificationEvidence | None = None
    deployment: DeploymentEvidence | None = None


# Backward-compatible legacy contract aliases used by existing agents/tests.
AutomationIntake = BusinessBrief


@dataclass
class ArtifactPlan:
    title: str
    uipath_surfaces: list[str] = field(default_factory=list)
    workflow_catalog: list[str] = field(default_factory=list)
    produced_artifacts: list[str] = field(default_factory=list)
    architecture_summary: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass
class VerificationEvidence:
    checklist: list[str] = field(default_factory=list)
    gate_statuses: dict[str, str] = field(default_factory=dict)
    passed: bool = False
    blocked_reasons: list[str] = field(default_factory=list)


@dataclass
class DeploymentEvidence:
    package_versions: list[str] = field(default_factory=list)
    target_folder: str = ""
    run_ids: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    summary: str = ""
