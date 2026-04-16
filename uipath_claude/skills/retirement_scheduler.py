"""Run skill-insight retirement at most once per 24h (project layer only)."""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

_INTERVAL_SEC = 24 * 3600
_LOG = logging.getLogger(__name__)


def _read_marker_ts(marker: Path) -> int:
    try:
        if not marker.is_file():
            return 0
        return int(marker.read_text(encoding="utf-8").strip() or "0")
    except (ValueError, OSError):
        return 0


def maybe_run_retirement_scheduled() -> None:
    """Best-effort: prune project ``.uipath-claude/skill-insights/*.json`` when due.

    Uses a marker file ``<project>/.uipath-claude/.retirement_at`` (per project root),
    so each repo has its own 24h cadence. The marker is updated only when every
    ``*.json`` file is read and written without error (or there are no files).
    """
    if os.environ.get("UIPATH_SKIP_RETIREMENT_SCHEDULE", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        return
    try:
        project_root = Path(os.environ.get("UIPATH_PROJECT_ROOT") or os.getcwd()).resolve()
        state_dir = project_root / ".uipath-claude"
        marker = state_dir / ".retirement_at"
        state_dir.mkdir(parents=True, exist_ok=True)
        last = _read_marker_ts(marker)
        if time.time() - last <= _INTERVAL_SEC:
            return
        insights_root = state_dir / "skill-insights"
        failures = 0
        if insights_root.is_dir():
            from uipath_claude.skills.insights import SkillInsightsFile
            from uipath_claude.skills.retirement import retire

            for path in insights_root.glob("*.json"):
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                    data = SkillInsightsFile.from_dict(raw)
                    retired = retire(data, min_confidence=0.3, min_samples=3)
                    path.write_text(
                        json.dumps(retired.to_dict(), indent=2),
                        encoding="utf-8",
                    )
                except Exception:
                    failures += 1
                    _LOG.debug("retirement skipped for %s", path, exc_info=True)
                    continue
        if failures == 0:
            marker.write_text(str(int(time.time())), encoding="utf-8")
    except Exception:
        _LOG.debug("scheduled retirement aborted", exc_info=True)
