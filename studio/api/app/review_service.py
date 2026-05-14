from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

_log = logging.getLogger(__name__)
_run_uiplan_review = None

try:
    from mcp_server.tools.plan_uiplan_review import run_uiplan_review as _imported
    _run_uiplan_review = _imported
except Exception:
    repo_root = Path(__file__).resolve().parents[3]
    framework_path = repo_root / "framework"
    if framework_path.is_dir():
        framework_path_str = str(framework_path)
        if framework_path_str not in sys.path:
            sys.path.insert(0, framework_path_str)
        try:
            from mcp_server.tools.plan_uiplan_review import run_uiplan_review as _imported2
            _run_uiplan_review = _imported2
        except Exception:
            _log.warning("Review framework unavailable; /review/run will return degraded results")


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
    if _run_uiplan_review is None:
        return {
            "ok": False,
            "error": "Review framework is not available (framework/ not found)",
            "findings": [],
            "findings_by_document": {},
            "acceptance_ready": False,
        }

    repo = Path(__file__).resolve().parents[3]
    result = _run_uiplan_review(
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
