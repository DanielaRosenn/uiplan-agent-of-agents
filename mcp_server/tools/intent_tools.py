"""MCP tools for intent classification and downstream tool routing."""
from __future__ import annotations

from typing import Any

from mcp.types import Tool, ToolAnnotations

from uipath_claude.query.intent_classifier import IntentType, classify_intent


_PERSONA_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ba", ("requirement", "stakeholder", "process map", "business process", "interview")),
    ("sa", ("architecture", "architect", "design", "trade-off", "tradeoff", "pattern")),
    ("qa", ("test", "testing", "validation", "regression", "acceptance")),
    ("add", ("agent design", "add doc", "agent design doc", "agent design document")),
    ("tdd", ("tdd", "technical design", "technical design document")),
    ("developer", ("implement", "implementation", "code", "bug", "refactor")),
)


_LIBRARY_HINT_KEYWORDS: tuple[str, ...] = (
    "retry",
    "reframework",
    "rethrow",
    "dispatcher",
    "performer",
    "queue",
    "orchestrator",
    "maestro",
    "bpmn",
    "dmn",
    "action center",
    "hitl",
    "coded workflow",
    "coded agent",
    "langgraph",
    "llamaindex",
    "bindings",
    "solution",
    "analyzer",
    "pack",
    "deploy",
    "eval",
)


def _pick_persona(text: str, intent: IntentType) -> str | None:
    """Best-effort persona hint based on keywords.

    Returns ``None`` for BUILD intent (the planner picks personas itself).
    """
    if intent == IntentType.BUILD:
        return None
    lower = text.lower()
    for persona, keywords in _PERSONA_KEYWORDS:
        if any(k in lower for k in keywords):
            return persona
    if intent == IntentType.DOCUMENTATION:
        # Default documentation author is the Solution Architect.
        return "sa"
    if intent == IntentType.QUESTION:
        return "sa"
    return None


def _library_hints(text: str) -> list[str]:
    lower = text.lower()
    hits = [kw for kw in _LIBRARY_HINT_KEYWORDS if kw in lower]
    # De-duplicate while preserving order.
    seen: set[str] = set()
    return [h for h in hits if not (h in seen or seen.add(h))]


def _recommended_next_tool(intent: IntentType) -> str:
    mapping = {
        IntentType.BUILD: "uipath_plan_build",
        IntentType.QUESTION: "uipath_answer",
        IntentType.DOCUMENTATION: "uipath_answer",
        IntentType.AMBIGUOUS: "uipath_intent_classify",
    }
    return mapping[intent]


def classify(text: str, project_root: str | None = None) -> dict[str, Any]:
    """Classify free-form text and return the structured intent payload.

    Pure function (``project_root`` is accepted for forward-compat and
    logging only). The payload is exactly what ``uipath_intent_classify``
    emits from MCP.
    """
    intent, reason = classify_intent(text or "")
    return {
        "intent": intent.value,
        "reason": reason,
        "recommended_next_tool": _recommended_next_tool(intent),
        "persona": _pick_persona(text or "", intent),
        "library_hints": _library_hints(text or ""),
        "project_root": project_root,
    }


def get_intent_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_intent_classify",
            description=(
                "Classify a free-form user message into a UiPath build/question/"
                "documentation/ambiguous intent and return the recommended next "
                "MCP tool, a suggested persona, and library-search hints. This "
                "is the single entry point MCP clients should call first when a "
                "user says something that might be either a question or a build "
                "request in a UiPath workspace."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The raw user message to classify.",
                    },
                    "project_root": {
                        "type": "string",
                        "description": (
                            "Optional absolute path of the UiPath project root "
                            "the user is working in; logged alongside the "
                            "classification for traceability."
                        ),
                    },
                },
                "required": ["text"],
            },
            annotations=ToolAnnotations(
                title="Classify UiPath intent",
                readOnlyHint=True,
            ),
        ),
    ]


async def call_intent_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name != "uipath_intent_classify":
        raise ValueError(f"Unknown intent tool: {name}")
    text = arguments.get("text", "")
    project_root = arguments.get("project_root")
    if not isinstance(text, str):
        raise TypeError("'text' must be a string")
    return classify(text, project_root=project_root)
