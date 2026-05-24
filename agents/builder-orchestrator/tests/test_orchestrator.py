import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import assign_agents  # noqa: E402
from main import generate_design_docs  # noqa: E402
from main import normalize_state_input  # noqa: E402
from main import provision_resources  # noqa: E402
from main import run_orchestrator  # noqa: E402


def _load_sample_brief() -> dict:
    brief_path = (
        Path(__file__).resolve().parents[3]
        / "samples"
        / "agent-of-agents"
        / "brief.enterprise-incident.json"
    )
    return json.loads(brief_path.read_text(encoding="utf-8"))


def test_orchestrator_generates_expected_sections() -> None:
    state = run_orchestrator(_load_sample_brief())
    assert state["handoff"]["status"] == "completed"
    assert len(state["handoff"]["generatedDocuments"]) == 3
    assert len(state["handoff"]["buildArtifacts"]) >= 2
    assert len(state["handoff"]["provisionedResources"]) == 2


def test_raw_intake_normalization() -> None:
    raw_input = _load_sample_brief()
    normalized = normalize_state_input(raw_input)
    assert "brief" in normalized
    assert normalized["brief"]["systems"]
    assert normalized["runId"]
    assert normalized["outputDir"]


def test_assignments_cover_required_specialists() -> None:
    assignments = assign_agents({})["agentAssignments"]
    phases = {item["phase"] for item in assignments}
    assert "brief-intake" in phases
    assert "design-doc-generation" in phases
    assert "uipath-artifact-generation" in phases
    assert "resource-provisioning" in phases
    assert "execution-evidence" in phases


def test_generate_design_docs_creates_files(tmp_path: Path) -> None:
    normalized = normalize_state_input({**_load_sample_brief(), "outputRoot": str(tmp_path), "runId": "test-run"})
    generated = generate_design_docs(normalized)
    human_docs = generated["generatedDocuments"]
    ui_plan_files = generated["uiPlanFiles"]
    assert len(human_docs) == 3
    assert len(ui_plan_files) == 3
    assert all(Path(item["path"]).exists() for item in human_docs)
    assert all(Path(item["path"]).exists() for item in ui_plan_files)
    assert sorted(item["name"] for item in ui_plan_files) == ["plan", "spec", "tasks"]


def test_provision_resources_in_dry_run_mode() -> None:
    normalized = normalize_state_input(_load_sample_brief())
    provisioned = provision_resources(normalized)["provisionedResources"]
    assert {item["status"] for item in provisioned} == {"simulated"}


def test_provision_resources_requires_commands_in_real_mode() -> None:
    payload = {**_load_sample_brief(), "dryRun": False}
    normalized = normalize_state_input(payload)
    provisioned = provision_resources(normalized)["provisionedResources"]
    assert len(provisioned) == 2
    assert {item["status"] for item in provisioned} == {"failed"}
    assert "required" in provisioned[0]["details"]


def test_handoff_contains_evidence_checklist() -> None:
    state = run_orchestrator(_load_sample_brief())
    checklist = state["handoff"]["evidenceChecklist"]
    assert isinstance(checklist, list)
    assert "pdd_sdd_add" in checklist
    assert "provisioned_queue_and_asset" in checklist


def test_handoff_contains_execution_evidence() -> None:
    state = run_orchestrator(_load_sample_brief())
    execution = state["handoff"]["executionEvidence"]
    assert execution["status"] == "completed"
    assert execution["evidenceFiles"]
    assert state["handoff"]["phaseHistory"]
    assert state["handoff"]["hitlDecisions"]


def test_run_writes_handoff_file_structure() -> None:
    state = run_orchestrator(_load_sample_brief())
    out_dir = Path(state["outputDir"])
    assert (out_dir / "docs" / "PDD.md").exists()
    assert (out_dir / "docs" / "SDD.md").exists()
    assert (out_dir / "docs" / "ADD.md").exists()
    assert (out_dir / "artifacts" / "generated-flow.json").exists()
    assert (out_dir / "evidence" / "execution-evidence.json").exists()
    assert (out_dir / "ui" / "run-events.json").exists()


def test_build_loop_escalates_when_budget_exhausted() -> None:
    payload = {
        **_load_sample_brief(),
        "maxBuildIterations": 2,
        "forceBuildFailures": 2,
    }
    state = run_orchestrator(payload)
    assert state["handoff"]["status"] == "failed"
    assert state["handoff"]["escalation"]["reason"] == "build_loop_budget_exhausted"
