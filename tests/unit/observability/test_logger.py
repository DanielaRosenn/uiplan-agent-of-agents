"""JSON-line structured logger."""
from __future__ import annotations

import json
from pathlib import Path

from uipath_claude.observability.logger import StructuredLogger


def test_writes_jsonl(tmp_path: Path) -> None:
    log = tmp_path / "events.log"
    logger = StructuredLogger(path=log)
    logger.emit(session_id="s1", skill="uipath-automation", iteration=1, tool="write_file", ok=True, ms=42)
    logger.emit(
        session_id="s1",
        skill="uipath-automation",
        iteration=1,
        tool=None,
        ok=None,
        ms=None,
        event="iteration_end",
    )

    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    a = json.loads(lines[0])
    assert a["session_id"] == "s1"
    assert a["tool"] == "write_file"
    assert a["ok"] is True
    assert a["ms"] == 42
