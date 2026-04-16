"""Session JSONL store: append-only transcript with resume."""
from __future__ import annotations

import time
from pathlib import Path

from uipath_claude.sessions.store import SessionEvent, SessionStore


def test_append_and_load_roundtrip(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path)
    sid = store.new_session_id()

    store.append(sid, SessionEvent(kind="user", text="hello"))
    store.append(sid, SessionEvent(kind="assistant", text="hi", tokens_in=10, tokens_out=3))
    store.append(sid, SessionEvent(kind="tool", name="write_file", ok=True, text="[OK] wrote"))

    events = store.load(sid)
    assert [e.kind for e in events] == ["user", "assistant", "tool"]
    assert events[1].tokens_in == 10
    assert events[2].name == "write_file" and events[2].ok is True


def test_list_sessions_sorted_newest_first(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path)
    a = store.new_session_id()
    b = store.new_session_id()
    store.append(a, SessionEvent(kind="user", text="a"))
    time.sleep(0.02)
    store.append(b, SessionEvent(kind="user", text="b"))
    ids = [s.session_id for s in store.list_sessions(limit=10)]
    assert ids[0] == b and ids[1] == a
