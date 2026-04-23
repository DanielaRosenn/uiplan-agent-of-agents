from __future__ import annotations

from pathlib import Path

from tools.uiplan.scaffold.report import ScaffoldReport
from tools.uiplan.scaffold.adapters.base import ScaffoldAdapter


class ExplicitStubAdapter(ScaffoldAdapter):
    """Explicit not-implemented path (no silent no-op)."""

    def __init__(self, kind: str) -> None:
        self.kind = kind

    def run(self, *, plan_slug: str, repo_root: Path, max_loops: int) -> ScaffoldReport:
        return ScaffoldReport(
            project_kind=self.kind,
            plan_slug=plan_slug,
            max_loops=max_loops,
            loop_outcome={
                "status": "failed",
                "iteration": 1,
                "reason": "not_implemented",
                "result": {
                    "status": "failed",
                    "recoverable": False,
                    "message": (
                        f"scaffold-code adapter not implemented for project kind {self.kind!r}. "
                        "Use generate-docs for UiPlan bundles; see docs/uiplan/SCAFFOLD_CODE.md."
                    ),
                },
            },
            hints=[
                "See docs/uiplan/SCAFFOLD_CODE.md and the runtime restructure design doc §13.",
            ],
        )
