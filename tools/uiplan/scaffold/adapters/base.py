"""Adapter contract for `scaffold-code`."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from tools.uiplan.scaffold.report import ScaffoldReport


class ScaffoldAdapter(ABC):
    """Runs gate-oriented scaffold checks for one project kind."""

    kind: str

    @abstractmethod
    def run(self, *, plan_slug: str, repo_root: Path, max_loops: int) -> ScaffoldReport:
        """Execute scaffold loop for this adapter."""
