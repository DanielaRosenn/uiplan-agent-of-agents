from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

try:
    from mcp_server.tools.plan_uiplan_review import run_uiplan_review
except ModuleNotFoundError:
    repo_root = Path(__file__).resolve().parents[3]
    framework_path = repo_root / "framework"
    if framework_path.is_dir():
        framework_path_str = str(framework_path)
        if framework_path_str not in sys.path:
            sys.path.insert(0, framework_path_str)
    from mcp_server.tools.plan_uiplan_review import run_uiplan_review


def map_review_findings(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        document = str(
            finding.get("document")
            or finding.get("where")
            or finding.get("source")
            or "unknown"
        )
        grouped[document].append(finding)
    return dict(grouped)


def run_review(
    *,
    spec: str,
    plan: str,
    tasks: str,
    stage: str = "all",
    gate_ids: list[str] | None = None,
    slug: str | None = None,
) -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[3]
    result = run_uiplan_review(
        spec=spec,
        plan=plan,
        tasks=tasks,
        stage=stage,
        gate_ids=gate_ids or [],
        repo=repo,
        slug=slug,
    )
    findings = result.get("findings", [])
    findings_by_document = map_review_findings(findings)
    acceptance_ready = bool(result.get("ok")) and not any(
        str(finding.get("severity", "")).lower() == "error" for finding in findings
    )
    return {
        **result,
        "findings_by_document": findings_by_document,
        "acceptance_ready": acceptance_ready,
    }
