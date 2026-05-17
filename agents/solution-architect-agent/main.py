from __future__ import annotations

from typing import Any

from shared.agent_contracts import ArtifactPlan
from shared.agent_contracts import AutomationIntake


def run_solution_architect(payload: dict[str, Any]) -> ArtifactPlan:
    intake = AutomationIntake.from_payload(payload)
    architecture_summary = (
        "Use a coded orchestrator to coordinate discovery, planning, verification, and deployment "
        "evidence while keeping human approval before deployment."
    )
    if intake.systems:
        architecture_summary += f" Integrate with: {', '.join(intake.systems)}."

    return ArtifactPlan(
        title="Invoice Exception TO-BE Architecture",
        uipath_surfaces=[
            "Coded Agent",
            "Maestro",
            "RPA Workflow",
            "API Workflow",
            "Action Center",
            "Orchestrator Queue",
        ],
        workflow_catalog=[
            "Normalize intake payload",
            "Validate invoice metadata",
            "Route exceptions for human approval",
            "Queue and run non-production smoke tests",
            "Generate deployment handoff package",
        ],
        architecture_summary=architecture_summary,
        notes=[
            "Deployment remains blocked until verification passes.",
            "Action Center is used for human-in-the-loop approval.",
        ],
    )
