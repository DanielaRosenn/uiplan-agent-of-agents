from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
_SPEC = importlib.util.spec_from_file_location("deployment_evidence_main", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
run_deployment_evidence = _MODULE.run_deployment_evidence


def _derived_deployment_payload_from_sample() -> dict[str, object]:
    intake_path = (
        Path(__file__).resolve().parents[3] / "samples" / "invoice-exception" / "intake.json"
    )
    payload = json.loads(intake_path.read_text(encoding="utf-8"))
    return {
        "packageVersions": ["AgentOps.Builder.0.1.0", "Invoice.Exception.Workflows.0.1.0"],
        "targetFolder": "Dev/Invoice",
        "runIds": [f"smoke-{len(payload.get('systems', []))}-1"],
        "blockers": [],
    }


def test_deployment_evidence_happy_path_from_derived_fixture() -> None:
    evidence = run_deployment_evidence(_derived_deployment_payload_from_sample())
    assert evidence.package_versions
    assert evidence.target_folder == "Dev/Invoice"
    assert evidence.run_ids
    assert "Prepared handoff" in evidence.summary


def test_deployment_evidence_ignores_non_list_payload_fields() -> None:
    evidence = run_deployment_evidence(
        {
            "packageVersions": None,
            "runIds": 123,
            "blockers": {"reason": "x"},
            "targetFolder": None,
        }
    )
    assert evidence.package_versions == []
    assert evidence.run_ids == []
    assert evidence.blockers == []
    assert evidence.target_folder == ""
