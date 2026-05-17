"""Safe wrapper contracts for external Orchestrator operations."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .telemetry_contracts import OrchestratorTelemetryReadiness

_REDACT_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "password",
    "secret",
    "client_secret",
    "api_key",
}

READ_ONLY_WRAPPERS: tuple[str, ...] = (
    "orchestrator.list_folders",
    "orchestrator.list_processes",
    "orchestrator.list_jobs",
    "orchestrator.list_queues",
    "orchestrator.get_job_logs",
)

APPROVAL_GATED_ACTION_WRAPPERS: tuple[str, ...] = (
    "orchestrator.start_job",
    "orchestrator.retry_job",
    "orchestrator.create_queue_item",
    "orchestrator.set_asset",
)


@dataclass(frozen=True, slots=True)
class WrappedOrchestratorCall:
    action: str
    payload: dict[str, Any]
    approval_required: bool
    readiness: OrchestratorTelemetryReadiness


def redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact known secret-bearing keys."""

    def _scrub(value: Any, key: str | None = None) -> Any:
        if key and key.lower() in _REDACT_KEYS:
            return "***REDACTED***"
        if isinstance(value, dict):
            return {k: _scrub(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [_scrub(item) for item in value]
        return value

    return _scrub(payload)  # type: ignore[return-value]


def is_non_prod_target(folder: str | None) -> bool:
    candidate = (folder or "").strip().lower()
    if not candidate:
        return False
    # Explicit non-prod markers should always pass.
    if re.search(r"\bnon[\W_]*prod(?:uction)?\b", candidate):
        return True

    tokens = re.findall(r"[a-z0-9]+", candidate)
    if not tokens:
        return False

    prod_tokens = {"prod", "production", "preprod"}
    return not any(token in prod_tokens for token in tokens)


def readiness_for_target(folder: str | None) -> OrchestratorTelemetryReadiness:
    non_prod = is_non_prod_target(folder)
    if non_prod:
        return OrchestratorTelemetryReadiness(
            ready=True,
            non_prod_target=True,
            redaction_enabled=True,
            blocked_reason=None,
        )
    return OrchestratorTelemetryReadiness(
        ready=False,
        non_prod_target=False,
        redaction_enabled=True,
        blocked_reason="Target folder is missing or production-like.",
    )


def wrap_read_only_call(action: str, payload: dict[str, Any]) -> WrappedOrchestratorCall:
    if action not in READ_ONLY_WRAPPERS:
        raise ValueError(f"Unsupported read-only action: {action}")
    return WrappedOrchestratorCall(
        action=action,
        payload=redact_payload(payload),
        approval_required=False,
        readiness=OrchestratorTelemetryReadiness(
            ready=True,
            non_prod_target=True,
            redaction_enabled=True,
            blocked_reason=None,
        ),
    )


def wrap_action_call(
    action: str,
    payload: dict[str, Any],
    *,
    folder: str | None,
    approved: bool,
) -> WrappedOrchestratorCall:
    if action not in APPROVAL_GATED_ACTION_WRAPPERS:
        raise ValueError(f"Unsupported approval-gated action: {action}")
    readiness = readiness_for_target(folder)
    if not approved:
        readiness = OrchestratorTelemetryReadiness(
            ready=False,
            non_prod_target=readiness.non_prod_target,
            redaction_enabled=True,
            blocked_reason="Explicit approval is required for orchestrator actions.",
        )
    return WrappedOrchestratorCall(
        action=action,
        payload=redact_payload(payload),
        approval_required=True,
        readiness=readiness,
    )

