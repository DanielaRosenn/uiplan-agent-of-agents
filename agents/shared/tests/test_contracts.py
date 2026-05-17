from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.agent_contracts import AgentAssignment  # noqa: E402
from shared.agent_contracts import ArtifactPlan  # noqa: E402
from shared.agent_contracts import AutomationIntake  # noqa: E402
from shared.agent_contracts import DeploymentEvidence  # noqa: E402
from shared.agent_contracts import HandoffPackage  # noqa: E402
from shared.agent_contracts import VerificationEvidence  # noqa: E402


def _load_sample_intake() -> dict:
    intake_path = (
        Path(__file__).resolve().parents[3] / "samples" / "invoice-exception" / "intake.json"
    )
    return json.loads(intake_path.read_text(encoding="utf-8"))


def test_contract_models_build_handoff_from_sample() -> None:
    intake = AutomationIntake.from_payload(_load_sample_intake())
    assignment = AgentAssignment(
        phase="discovery",
        agent="discovery-agent",
        responsibility="Normalize intake and produce AS-IS facts.",
    )
    plan = ArtifactPlan(
        title="Invoice Exception Target Design",
        uipath_surfaces=["Coded Agent", "Maestro", "API Workflow"],
        workflow_catalog=["Intake Validation", "Queue Processing", "Exception Routing"],
        architecture_summary="Coordinate intake, approvals, and exception handling.",
    )
    verification = VerificationEvidence(
        checklist=["Run tests", "Run analyze", "Review blockers"],
        gate_statuses={"pytest": "passed", "analyze": "passed"},
        passed=True,
    )
    deployment = DeploymentEvidence(
        package_versions=["AgentOps.Builder.0.1.0"],
        target_folder="Dev/Invoice",
        run_ids=["job-1234"],
        summary="Ready for dev smoke run.",
    )

    handoff = HandoffPackage(
        intake=intake,
        assignments=[assignment],
        artifact_plan=plan,
        verification=verification,
        deployment=deployment,
    )

    assert handoff.intake.business_goal
    assert handoff.assignments[0].agent == "discovery-agent"
    assert handoff.artifact_plan is not None
    assert handoff.verification is not None and handoff.verification.passed
    assert handoff.deployment is not None and handoff.deployment.target_folder == "Dev/Invoice"


def test_intake_normalization_keeps_none_values_empty() -> None:
    intake = AutomationIntake.from_payload(
        {
            "businessGoal": None,
            "industry": None,
            "systems": [None, "ERP", ""],
            "constraints": None,
            "successCriteria": [None],
        }
    )
    assert intake.business_goal == ""
    assert intake.industry == ""
    assert intake.systems == ["ERP"]
    assert intake.constraints == []
    assert intake.success_criteria == []
