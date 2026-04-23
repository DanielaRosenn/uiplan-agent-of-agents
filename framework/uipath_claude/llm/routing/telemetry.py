"""Structured telemetry for model selection + fallback."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class EventSink(Protocol):
    def emit(self, event: str, payload: dict[str, Any]) -> None: ...


class NullSink:
    """No-op sink used by default."""

    def emit(self, event: str, payload: dict[str, Any]) -> None:
        return None


@dataclass
class RecordingSink:
    """In-memory sink for tests and debugging."""

    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def emit(self, event: str, payload: dict[str, Any]) -> None:
        self.events.append((event, dict(payload)))

    def names(self) -> list[str]:
        return [name for name, _ in self.events]
