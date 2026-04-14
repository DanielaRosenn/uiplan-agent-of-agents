"""Track clarifying questions and user answers for human-in-the-loop turns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class FeedbackState:
    questions_asked: int = 0
    max_questions: int = 2
    awaiting_response: bool = False
    pending_question: str | None = None
    responses: list[tuple[str, str]] = field(default_factory=list)


class FeedbackLoop:
    """Aligns with uipath-planner / uipath-rpa guidance: at most two clarifying questions."""

    def __init__(self, max_questions: int = 2) -> None:
        self.state = FeedbackState(max_questions=max_questions)

    def should_ask_more(self) -> bool:
        return self.state.questions_asked < self.state.max_questions

    def record_question(self, question: str) -> None:
        text = question.strip()
        if not text:
            return
        self.state.questions_asked += 1
        self.state.pending_question = text
        self.state.awaiting_response = True

    def record_response(self, response: str) -> None:
        text = response.strip()
        if self.state.pending_question:
            self.state.responses.append((self.state.pending_question, text))
        self.state.pending_question = None
        self.state.awaiting_response = False

    def get_context_summary(self) -> str:
        if not self.state.responses:
            return ""
        lines = ["Prior clarifications:"]
        for q, a in self.state.responses:
            lines.append(f"Q: {q}")
            lines.append(f"A: {a}")
        return "\n".join(lines)

    def reset(self) -> None:
        self.state = FeedbackState(max_questions=self.state.max_questions)


def detect_clarifying_question(response: str) -> str | None:
    """If the assistant output looks like a clarifying question, return it."""
    if not response or "?" not in response:
        return None
    lower = response.lower()
    soft_markers = (
        "would you",
        "could you",
        "please specify",
        "which option",
        "which ",
        "what ",
        "how should",
        "do you want",
        "clarify",
    )
    if not any(m in lower for m in soft_markers) and not response.rstrip().endswith("?"):
        return None
    parts = re.split(r"(?<=[.!?])\s+", response.strip())
    for segment in reversed(parts):
        seg = segment.strip()
        if "?" in seg:
            return seg
    return None
