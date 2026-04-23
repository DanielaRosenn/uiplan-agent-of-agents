"""Append-only JSONL session store under ``~/.uipath-claude/sessions/``."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class SessionEvent:
    kind: str
    text: str = ""
    name: str | None = None
    ok: bool | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    ts: float = field(default_factory=time.time)


@dataclass
class SessionSummary:
    session_id: str
    path: Path
    mtime_ns: int


class SessionStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or (Path.home() / ".uipath-claude" / "sessions"))
        self.root.mkdir(parents=True, exist_ok=True)

    def new_session_id(self) -> str:
        return time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]

    def _path(self, session_id: str) -> Path:
        return self.root / f"{session_id}.jsonl"

    def append(self, session_id: str, event: SessionEvent) -> None:
        line = json.dumps(asdict(event), ensure_ascii=False)
        with self._path(session_id).open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def load(self, session_id: str) -> list[SessionEvent]:
        p = self._path(session_id)
        if not p.exists():
            return []
        events: list[SessionEvent] = []
        for raw in p.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            events.append(SessionEvent(**json.loads(raw)))
        return events

    def list_sessions(self, limit: int = 20) -> list[SessionSummary]:
        items: list[SessionSummary] = []
        for p in self.root.glob("*.jsonl"):
            try:
                st = p.stat()
                items.append(
                    SessionSummary(
                        session_id=p.stem,
                        path=p,
                        mtime_ns=getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)),
                    )
                )
            except OSError:
                continue
        items.sort(key=lambda s: (s.mtime_ns, s.session_id), reverse=True)
        return items[:limit]
