"""Orchestrates scaffold-code across project-kind adapters."""

from __future__ import annotations

import json
from pathlib import Path

from tools.uiplan.scaffold.registry import get_scaffold_adapter


def run_scaffold(*, plan_slug: str, repo_root: Path, max_loops: int) -> dict:
    adapter = get_scaffold_adapter(repo_root)
    report = adapter.run(plan_slug=plan_slug, repo_root=repo_root, max_loops=max_loops)
    return report.as_dict()


def format_scaffold_stdout(payload: dict) -> str:
    """Human-readable multi-line summary for Typer."""
    lines = [
        f"project_kind: {payload['project_kind']}",
        f"plan_slug: {payload['plan_slug']}",
        f"effective_max_loops: {payload['max_loops']}",
        f"loop: {json.dumps(payload['loop_outcome'], indent=2, sort_keys=True)}",
    ]
    if payload.get("hints"):
        lines.append("hints:")
        for h in payload["hints"]:
            lines.append(f"  - {h}")
    return "\n".join(lines) + "\n"
