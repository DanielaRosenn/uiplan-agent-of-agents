"""Structured scaffold reports (typed summaries for CLI and tests)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScaffoldReport:
    """Result of a scaffold-code adapter run."""

    project_kind: str
    plan_slug: str
    max_loops: int
    loop_outcome: dict[str, Any]
    hints: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_kind": self.project_kind,
            "plan_slug": self.plan_slug,
            "max_loops": self.max_loops,
            "loop_outcome": self.loop_outcome,
            "hints": list(self.hints),
        }
