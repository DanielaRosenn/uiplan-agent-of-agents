from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_MODULE_PATH = Path(__file__).resolve().parents[1] / "main.py"
_SPEC = importlib.util.spec_from_file_location("verifier_agent_main", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
run_verifier = _MODULE.run_verifier


def _derived_command_outputs_from_sample() -> dict[str, str]:
    intake_path = (
        Path(__file__).resolve().parents[3] / "samples" / "invoice-exception" / "intake.json"
    )
    payload = json.loads(intake_path.read_text(encoding="utf-8"))
    return {
        "pytest": "passed - sample intake loaded",
        "analyze": f"passed - validated constraints count={len(payload.get('constraints', []))}",
        "pack": "success - package generated",
    }


def test_verifier_happy_path_marks_all_gates_passed() -> None:
    evidence = run_verifier(_derived_command_outputs_from_sample())
    assert evidence.passed
    assert evidence.gate_statuses["pytest"] == "passed"
    assert not evidence.blocked_reasons


def test_verifier_treats_zero_failures_and_errors_as_passed() -> None:
    evidence = run_verifier(
        {
            "pytest": "collected 12 items - 0 failures, 0 errors",
            "analyze": "success: 0 errors",
        }
    )
    assert evidence.passed
    assert evidence.gate_statuses["pytest"] == "passed"


def test_verifier_marks_nonzero_failures_failed() -> None:
    evidence = run_verifier({"pytest": "3 failures, 1 error"})
    assert not evidence.passed
    assert evidence.gate_statuses["pytest"] == "failed"


def test_verifier_mixed_counts_zero_failures_one_error_is_failed() -> None:
    evidence = run_verifier({"pytest": "0 failures, 1 error"})
    assert not evidence.passed
    assert evidence.gate_statuses["pytest"] == "failed"


def test_verifier_mixed_counts_one_failure_zero_errors_is_failed() -> None:
    evidence = run_verifier({"pytest": "1 failure, 0 errors"})
    assert not evidence.passed
    assert evidence.gate_statuses["pytest"] == "failed"
