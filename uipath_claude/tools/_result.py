"""Structured tool result envelope used by skill execution tools."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class ToolOutcome:
    ok: bool
    message: str
    data: dict[str, Any] | None = None

    def to_text(self) -> str:
        """Render a LangChain-tool-compatible string the LLM can read."""
        status = "OK" if self.ok else "ERROR"
        return f"[{status}] {self.message}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
