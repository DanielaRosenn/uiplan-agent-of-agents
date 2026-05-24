from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "agents"))
    sys.path.insert(0, str(repo_root / "agents" / "builder-orchestrator"))

    from main import run_orchestrator  # noqa: PLC0415

    brief_path = repo_root / "samples" / "agent-of-agents" / "brief.enterprise-incident.json"
    payload = json.loads(brief_path.read_text(encoding="utf-8"))
    state = run_orchestrator(payload)

    output_path = Path(state["outputDir"]) / "handoff.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(state["handoff"], indent=2), encoding="utf-8")

    print(f"run_id={state['runId']}")
    print(f"output_dir={state['outputDir']}")
    print(f"handoff_file={output_path}")
    print(f"status={state['handoff'].get('status', 'unknown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
