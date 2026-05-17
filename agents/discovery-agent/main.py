from __future__ import annotations

from dataclasses import asdict
from typing import Any

from shared.agent_contracts import AutomationIntake


def run_discovery(payload: dict[str, Any]) -> dict[str, Any]:
    intake = AutomationIntake.from_payload(payload)
    missing_decisions: list[str] = []
    if not intake.business_goal:
        missing_decisions.append("Business goal is missing.")
    if not intake.systems:
        missing_decisions.append("Systems list is missing.")
    if not intake.success_criteria:
        missing_decisions.append("Success criteria are missing.")

    risks = ["No production deployment", "Human approval before deploy"]
    risks.extend(item for item in intake.constraints if item not in risks)

    return {
        "normalizedIntake": asdict(intake),
        "asIsFacts": [
            f"Industry: {intake.industry or 'unspecified'}",
            f"Current systems: {', '.join(intake.systems) if intake.systems else 'unspecified'}",
            "Process currently relies on manual invoice exception triage.",
        ],
        "resources": [
            "Automation developer",
            "Process owner",
            "UiPath Dev folder",
        ],
        "risks": risks,
        "missingDecisions": missing_decisions,
    }
