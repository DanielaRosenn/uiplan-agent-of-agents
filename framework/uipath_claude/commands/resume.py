"""/resume command: list or describe prior JSONL sessions."""
from __future__ import annotations

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.sessions.store import SessionStore


def register_resume_command(registry: CommandRegistry) -> None:
    store = SessionStore()

    def handle_resume(*args: str) -> str:
        if not args:
            lines = ["Recent sessions:"]
            for s in store.list_sessions(limit=10):
                lines.append(f"  {s.session_id}")
            lines.append("Usage: /resume <session-id>")
            return "\n".join(lines)

        session_id = args[0]
        events = store.load(session_id)
        if not events:
            return f"No session found for id: {session_id}"
        return (
            f"Loaded {len(events)} events from {session_id}. "
            f"Set UIPATH_CHAT_SESSION_ID={session_id} and restart chat to continue that file."
        )

    registry.register("resume", "Resume a prior chat session (list transcripts)", handle_resume)
