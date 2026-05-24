from __future__ import annotations

import json
import shutil
from datetime import UTC
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist" / "agenthack-repo"

COPY_SPEC = [
    ("README.md", "README.md"),
    ("examples/agent-of-agents-e2e", "example/agent-of-agents-e2e"),
    ("examples/05-agenthack-enterprise-intake", "example/05-agenthack-enterprise-intake"),
    ("examples/README.md", "example/README.md"),
    ("samples/agent-of-agents/brief.enterprise-incident.json", "samples/brief.enterprise-incident.json"),
    ("ui/copilotkit", "ui-demo/copilotkit"),
    ("docs/rebuild/COPILOTKIT_ADAPTER_VALIDATION.md", "submission/COPILOTKIT_ADAPTER_VALIDATION.md"),
    ("docs/rebuild/SKILLS_PHASE_MAP.md", "submission/SKILLS_PHASE_MAP.md"),
    ("docs/rebuild/CORE_KEEP_ALLOWLIST.md", "submission/CORE_KEEP_ALLOWLIST.md"),
    ("docs/rebuild/SKILLS_SYNC_PROOF.md", "submission/SKILLS_SYNC_PROOF.md"),
    ("docs/rebuild/TEMPLATE_CONTRACT_DIFF_SUMMARY.md", "submission/TEMPLATE_CONTRACT_DIFF_SUMMARY.md"),
    ("docs/rebuild/ORCHESTRATION_LOOP_TEST_OUTPUTS.md", "submission/ORCHESTRATION_LOOP_TEST_OUTPUTS.md"),
    ("docs/rebuild/DUAL_REPO_STRATEGY.md", "submission/DUAL_REPO_STRATEGY.md"),
    ("docs/rebuild/FINAL_ACCEPTANCE_REPORT.md", "submission/FINAL_ACCEPTANCE_REPORT.md"),
    ("docs/rebuild/VERIFICATION_BUNDLE_INDEX.md", "submission/VERIFICATION_BUNDLE_INDEX.md"),
    ("docs/rebuild/UIPLAN_AGENT_OF_AGENTS_REEVALUATION_ADR.md", "submission/UIPLAN_AGENT_OF_AGENTS_REEVALUATION_ADR.md"),
    ("docs/rebuild/SHIPPED_ARTIFACTS_MANIFEST.json", "submission/SHIPPED_ARTIFACTS_MANIFEST.json"),
    ("docs/rebuild/NON_PROD_DEPLOYMENT_EVIDENCE.md", "submission/NON_PROD_DEPLOYMENT_EVIDENCE.md"),
    ("docs/rebuild/UIPLAN_SHOWCASE.md", "submission/UIPLAN_SHOWCASE.md"),
    ("docs/rebuild/COPILOT_VISUALS_WALKTHROUGH.md", "submission/COPILOT_VISUALS_WALKTHROUGH.md"),
    ("templates/uiplan", "templates/uiplan"),
]


def _latest_run_id() -> str:
    out_root = REPO_ROOT / "agents" / "builder-orchestrator" / "out"
    prefixes = "enterpriseincidentagentbuilder-"
    candidates = [path.name for path in out_root.glob(f"{prefixes}*") if path.is_dir()]
    if not candidates:
        return ""
    return sorted(candidates)[-1]


def _copy_item(src_rel: str, dst_rel: str) -> dict[str, str]:
    src = REPO_ROOT / src_rel
    dst = DIST_ROOT / dst_rel
    if not src.exists():
        return {"source": src_rel, "target": dst_rel, "kind": "missing", "status": "skipped"}

    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
        return {"source": src_rel, "target": dst_rel, "kind": "directory", "status": "copied"}

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"source": src_rel, "target": dst_rel, "kind": "file", "status": "copied"}


def main() -> int:
    if DIST_ROOT.exists():
        shutil.rmtree(DIST_ROOT)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)

    copy_spec = list(COPY_SPEC)
    latest_run = _latest_run_id()
    if latest_run:
        copy_spec.extend(
            [
                (
                    f"agents/builder-orchestrator/out/{latest_run}/ui/run-events.json",
                    "demo/evidence/run-events.json",
                ),
                (
                    f"agents/builder-orchestrator/out/{latest_run}/evidence/execution-evidence.json",
                    "demo/evidence/execution-evidence.json",
                ),
                (
                    f"agents/builder-orchestrator/out/{latest_run}/evidence/simulated-run-output.json",
                    "demo/evidence/simulated-run-output.json",
                ),
                (
                    f"agents/builder-orchestrator/out/{latest_run}/handoff.json",
                    "demo/evidence/handoff.json",
                ),
            ]
        )

    copied = [_copy_item(src, dst) for src, dst in copy_spec]
    copied_count = sum(1 for entry in copied if entry["status"] == "copied")
    skipped_count = sum(1 for entry in copied if entry["status"] == "skipped")

    manifest = {
        "name": "agenthack-export",
        "generatedAt": datetime.now(UTC).isoformat(),
        "sourceRepo": str(REPO_ROOT),
        "targetFolder": str(DIST_ROOT),
        "summary": {
            "copiedCount": copied_count,
            "skippedCount": skipped_count,
            "latestRunId": latest_run or "none",
        },
        "copied": copied,
    }
    (DIST_ROOT / "EXPORT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    print(f"AgentHack export ready at: {DIST_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
