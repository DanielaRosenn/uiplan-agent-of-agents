"""Normalized telemetry contracts for MCP tools."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class ToolTelemetryRecord:
    tool_id: str
    category: str
    phase: str
    risk_level: str
    status: str
    approval_required: bool
    evidence_output: str
    started_at: str = field(default_factory=_now_iso)
    completed_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OrchestratorTelemetryReadiness:
    ready: bool
    non_prod_target: bool
    redaction_enabled: bool
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class MCPTelemetryEnvelope:
    tool: ToolTelemetryRecord
    orchestrator: OrchestratorTelemetryReadiness | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

