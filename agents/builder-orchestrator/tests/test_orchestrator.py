import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import classify_request  # noqa: E402
from main import normalize_state_input  # noqa: E402
from main import prepare_build  # noqa: E402
from main import run_orchestrator  # noqa: E402


def _load_sample_intake() -> dict:
    intake_path = (
        Path(__file__).resolve().parents[3] / "samples" / "invoice-exception" / "intake.json"
    )
    return json.loads(intake_path.read_text(encoding="utf-8"))


def test_classification_is_enterprise_agent_builder() -> None:
    state = run_orchestrator(_load_sample_intake())
    assert state["classification"] == "enterprise_agent_builder"


def test_raw_intake_normalization() -> None:
    raw_input = _load_sample_intake()
    normalized = normalize_state_input(raw_input)
    assert "intake" in normalized
    assert normalized["intake"]["systems"]


def test_generic_classification_fallback() -> None:
    classification = classify_request({"intake": {"businessGoal": 123, "systems": "erp"}})
    assert classification["classification"] == "generic_request"


def test_assignments_cover_required_specialists() -> None:
    state = run_orchestrator(_load_sample_intake())
    phases = {item["phase"] for item in state["agentAssignments"]}
    assert "discovery" in phases
    assert "architecture" in phases
    assert "generation" in phases
    assert "verification" in phases
    assert "deployment evidence" in phases
    assert all("responsibility" in item and item["responsibility"] for item in state["agentAssignments"])


def test_deployment_readiness_blocked_until_verification_passes() -> None:
    blocked = prepare_build({"verificationStatus": "pending_approval"})
    ready = prepare_build({"verificationStatus": "passed"})
    assert blocked["deploymentReadiness"] == "blocked_pending_verification"
    assert ready["deploymentReadiness"] == "ready"


def test_approved_resumed_path_reaches_ready() -> None:
    resumed_state = run_orchestrator({"intake": _load_sample_intake(), "verificationStatus": "passed"})
    assert resumed_state["verificationStatus"] == "passed"
    assert resumed_state["deploymentReadiness"] == "ready"


def test_handoff_contains_evidence_checklist() -> None:
    state = run_orchestrator(_load_sample_intake())
    checklist = state["handoff"]["evidenceChecklist"]
    assert isinstance(checklist, list)
    assert "verification_results" in checklist
    assert "deployment_readiness_report" in checklist
