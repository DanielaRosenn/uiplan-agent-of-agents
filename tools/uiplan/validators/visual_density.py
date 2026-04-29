"""UiPlan visual contract: minimum Mermaid counts + Pro Standard heuristics."""

from __future__ import annotations

import re
from pathlib import Path

_MERMAID_BLOCKS = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)

_MIN_BLOCKS = {
    "spec.md": 2,
    "plan.md": 2,
    "tasks.md": 1,
}


def _mermaid_bodies(text: str) -> list[str]:
    return [m.group(1) for m in _MERMAID_BLOCKS.finditer(text)]


def _pro_standard_issues(body: str) -> list[str]:
    issues: list[str] = []
    lowered = body.lower()
    is_seq = "sequencediagram" in lowered
    is_state = "statediagram" in lowered
    if not (is_seq or is_state) and "classDef" not in body:
        issues.append("missing classDef")
    if not (is_seq or is_state) and "linkStyle" not in body:
        issues.append("missing linkStyle (expected on flowchart / graph diagrams)")
    if not is_seq and not is_state:
        flowish = "flowchart" in body or "\ngraph " in body.lower() or body.lower().lstrip().startswith("graph ")
        if flowish and body.count("\n") > 12 and "subgraph" not in body:
            issues.append("flowchart with many lines should include a subgraph")
    return issues


def validate_uiplan_docs(
    output_dir: Path,
    *,
    strict: bool = True,
) -> list[str]:
    """Return human-readable issues; empty means OK. When *strict* is False, log-style only."""
    errors: list[str] = []
    for name, minimum in _MIN_BLOCKS.items():
        path = output_dir / name
        if not path.is_file():
            errors.append(f"Missing {name} under {output_dir}")
            continue
        text = path.read_text(encoding="utf-8")
        bodies = _mermaid_bodies(text)
        if len(bodies) < minimum:
            errors.append(
                f"{name}: need at least {minimum} ```mermaid``` blocks, found {len(bodies)}",
            )
        for i, body in enumerate(bodies):
            for msg in _pro_standard_issues(body):
                errors.append(f"{name} block {i + 1}: {msg}")
    if not strict:
        return errors
    return errors
