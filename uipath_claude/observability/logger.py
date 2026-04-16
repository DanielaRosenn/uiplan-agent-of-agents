"""JSON-line structured logger for agentic runs."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


class StructuredLogger:
    def __init__(self, path: Path | None = None) -> None:
        default = Path.home() / ".uipath-claude" / "logs" / "events.log"
        raw = os.environ.get("UIPATH_EVENT_LOG", "")
        self.path = Path(path or (raw if raw else default))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, **fields: Any) -> None:
        record = {"ts": time.time(), **fields}
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
