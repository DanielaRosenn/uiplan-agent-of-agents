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


@dataclass
class AutomationIntake:
    business_goal: str
    industry: str
    systems: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AutomationIntake":
        return cls(
            business_goal=_to_clean_string(payload.get("businessGoal", "")),
            industry=_to_clean_string(payload.get("industry", "")),
            systems=_to_string_list(payload.get("systems", [])),
            constraints=_to_string_list(payload.get("constraints", [])),
            success_criteria=_to_string_list(payload.get("successCriteria", [])),
        )


@dataclass
class AgentAssignment:
    phase: str
    agent: str
    responsibility: str


@dataclass
class ArtifactPlan:
    title: str
    uipath_surfaces: list[str] = field(default_factory=list)
    workflow_catalog: list[str] = field(default_factory=list)
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


@dataclass
class HandoffPackage:
    intake: AutomationIntake
    assignments: list[AgentAssignment] = field(default_factory=list)
    artifact_plan: ArtifactPlan | None = None
    verification: VerificationEvidence | None = None
    deployment: DeploymentEvidence | None = None
