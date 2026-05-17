from __future__ import annotations

from typing import Any

from shared.agent_contracts import DeploymentEvidence
from shared.agent_contracts import HandoffPackage
from shared.agent_contracts import VerificationEvidence


def _to_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    return []


def run_deployment_evidence(payload: dict[str, Any]) -> DeploymentEvidence:
    package_versions = _to_string_list(payload.get("packageVersions", []))
    run_ids = _to_string_list(payload.get("runIds", []))
    blockers = _to_string_list(payload.get("blockers", []))
    folder_raw = payload.get("targetFolder", "")
    folder = folder_raw.strip() if isinstance(folder_raw, str) else ""

    summary = (
        f"Prepared handoff for folder '{folder or 'unspecified'}' with "
        f"{len(package_versions)} package version(s) and {len(run_ids)} run id(s)."
    )
    if blockers:
        summary += f" Blockers: {', '.join(blockers)}."

    return DeploymentEvidence(
        package_versions=package_versions,
        target_folder=folder,
        run_ids=run_ids,
        blockers=blockers,
        summary=summary,
    )


def create_handoff_package(
    intake_payload: dict[str, Any],
    verification: VerificationEvidence,
    deployment_payload: dict[str, Any],
) -> HandoffPackage:
    from shared.agent_contracts import AutomationIntake

    return HandoffPackage(
        intake=AutomationIntake.from_payload(intake_payload),
        verification=verification,
        deployment=run_deployment_evidence(deployment_payload),
    )
