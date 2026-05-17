from __future__ import annotations

import re
from typing import Any

from shared.agent_contracts import VerificationEvidence


def _gate_status(output: str) -> str:
    text = output.lower()

    if "blocked" in text:
        return "blocked"

    count_matches = re.findall(r"\b(\d+)\s+(failures?|errors?)\b", text)
    if count_matches:
        has_nonzero = any(int(count) > 0 for count, _label in count_matches)
        if has_nonzero:
            return "failed"
        return "passed"

    if re.search(r"\b(fail(?:ed|ure|ures)?|error|errors|exception|exceptions)\b", text):
        return "failed"

    if re.search(r"\b(pass(?:ed)?|ok|success(?:ful)?)\b", text):
        return "passed"

    if re.search(r"\b0\b", text) and re.search(r"\btests?\b", text):
        return "failed"

    return "blocked"


def run_verifier(command_outputs: dict[str, Any]) -> VerificationEvidence:
    checklist = [
        "Run tests",
        "Run analyzer",
        "Run package/build validation",
    ]
    gate_statuses: dict[str, str] = {}
    blocked_reasons: list[str] = []

    for gate_name, raw_output in command_outputs.items():
        status = _gate_status(str(raw_output))
        gate_statuses[gate_name] = status
        if status != "passed":
            blocked_reasons.append(f"{gate_name} is {status}.")

    passed = bool(gate_statuses) and all(status == "passed" for status in gate_statuses.values())
    return VerificationEvidence(
        checklist=checklist,
        gate_statuses=gate_statuses,
        passed=passed,
        blocked_reasons=blocked_reasons,
    )
