from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.agent_contracts import AgentAssignment  # noqa: E402
from shared.agent_contracts import BuildArtifact  # noqa: E402
from shared.agent_contracts import BusinessBrief  # noqa: E402
from shared.agent_contracts import ExecutionEvidence  # noqa: E402
from shared.agent_contracts import GeneratedDocument  # noqa: E402
from shared.agent_contracts import HandoffPackage  # noqa: E402
from shared.agent_contracts import ProvisionedResource  # noqa: E402


def _load_sample_brief() -> dict:
    brief_path = (
        Path(__file__).resolve().parents[3]
        / "samples"
        / "agent-of-agents"
        / "brief.enterprise-incident.json"
    )
    return json.loads(brief_path.read_text(encoding="utf-8"))


def test_contract_models_build_handoff_from_sample() -> None:
    brief = BusinessBrief.from_payload(_load_sample_brief())
    assignment = AgentAssignment(
        phase="design-doc-generation",
        agent="solution-architect-agent",
        responsibility="Generate PDD, SDD, and ADD documents from brief.",
    )
    generated_doc = GeneratedDocument(
        name="pdd",
        title="Process Design Document",
        path="out/sample/docs/PDD.md",
    )
    build_artifact = BuildArtifact(
        name="generated_flow_spec",
        kind="flow_spec",
        path="out/sample/artifacts/generated-flow.json",
    )
    provisioned_resource = ProvisionedResource(
        resource_type="queue",
        name="Q_AGENT_OF_AGENTS_WORK",
        status="simulated",
        resource_id="dry-run-queue",
    )
    execution = ExecutionEvidence(
        run_id="run-001",
        status="completed",
        output_dir="out/sample",
        command_logs=["flowRunCommand skipped because dryRun=true"],
        evidence_files=["out/sample/evidence/simulated-run-output.json"],
    )

    handoff = HandoffPackage(
        brief=brief,
        assignments=[assignment],
        generated_documents=[generated_doc],
        build_artifacts=[build_artifact],
        provisioned_resources=[provisioned_resource],
        execution=execution,
    )

    assert handoff.brief.project_name
    assert handoff.assignments[0].agent == "solution-architect-agent"
    assert handoff.generated_documents and handoff.generated_documents[0].name == "pdd"
    assert handoff.build_artifacts and handoff.build_artifacts[0].kind == "flow_spec"
    assert handoff.provisioned_resources and handoff.provisioned_resources[0].status == "simulated"
    assert handoff.execution is not None and handoff.execution.status == "completed"


def test_intake_normalization_keeps_none_values_empty() -> None:
    brief = BusinessBrief.from_payload(
        {
            "projectName": None,
            "domain": None,
            "objective": None,
            "systems": [None, "ERP", ""],
            "constraints": None,
            "stakeholders": None,
            "successCriteria": [None],
        }
    )
    assert brief.project_name == "agent-of-agents-build"
    assert brief.domain == "operations"
    assert brief.objective == ""
    assert brief.systems == ["ERP"]
    assert brief.constraints == []
    assert brief.stakeholders == []
    assert brief.success_criteria == []
