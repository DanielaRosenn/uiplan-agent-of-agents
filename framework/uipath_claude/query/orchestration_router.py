"""LLM orchestration router: structured route decision for chat without canned keyword flows."""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Callable

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage

from uipath_claude.llm.invoke import build_chat_model
from uipath_claude.llm.routing.complexity import ComplexitySignals
from uipath_claude.query.orchestration_types import (
    ApprovalLevel,
    OrchestrationContext,
    OrchestrationDecision,
    RouteKind,
)

LOW_CONFIDENCE = 0.55

_ROUTER_SYSTEM = """You are the orchestration router for UiPath Builder Agent.
Return ONLY a single JSON object. No markdown fences, no prose before or after.

Schema (all keys required unless null allowed):
- "route": one of: answer, clarify, documentation, uiplan, plan, execute, command_hint, refuse
- "confidence": number from 0.0 to 1.0
- "rationale": short string, one or two sentences
- "approval_level": one of: none, confirm_route, confirm_write, confirm_deploy
- "question": string or null (required when route is clarify, else null)
- "suggested_command": string or null (slash command to suggest, e.g. /uiplan-spec Title --intent ...; use when route is command_hint or to disambiguate)
- "next_action": string or null (short token like create_spec, review_spec, run_ground, default null)
- "selected_skills": array of zero or more skill name strings (e.g. uiplan, uipath-rpa)

Routing rules:
- "answer": user wants information, definition, or permission check (e.g. can we use uiplan?) without building artifacts.
- "clarify": the request is ambiguous; ask one concrete question in "question".
- "documentation": user wants PDD, SDD, ADD, TDD, or other SDLC documentation.
- "uiplan": user wants a UiPlan bundle (spec/plan/tasks under .cursor/plans) or grounded planning for non-trivial work.
- "plan": user wants a single implementation plan narrative (planner) before execution.
- "execute": user wants the agent to change code, workflows, projects, or run build/pack now.
- "command_hint": best next step is a specific slash command; set suggested_command.
- "refuse": out of scope or cannot proceed; put reason in "rationale".

If confidence is below 0.55, use route "clarify" and set a helpful "question".

The field "deterministic_intent" in the user message is a weak hint from keyword rules, not a command. Prefer the user's full request and the context pack.

Set approval_level to confirm_write before creating specs or files; confirm_deploy only for deploy/publish."""


def _extract_json_object(text: str) -> str | None:
    text = (text or "").strip()
    if not text:
        return None
    m = re.search(r"\{[\s\S]*\}\s*$", text)
    if m:
        return m.group(0).strip()
    return text if text.startswith("{") else None


def parse_orchestration_json(
    text: str,
) -> dict[str, Any] | None:
    raw = _extract_json_object(text)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _parse_route(s: str | None) -> RouteKind | None:
    if not s or not isinstance(s, str):
        return None
    s = s.strip().lower()
    for rk in RouteKind:
        if rk.value == s:
            return rk
    return None


def _parse_approval(s: str | None) -> ApprovalLevel:
    if not s or not isinstance(s, str):
        return ApprovalLevel.NONE
    s = s.strip().lower()
    for a in ApprovalLevel:
        if a.value == s:
            return a
    return ApprovalLevel.NONE


def decision_from_parsed(
    data: dict[str, Any] | None,
    *,
    allowed_routes: set[RouteKind] | None = None,
) -> OrchestrationDecision:
    if not data:
        return OrchestrationDecision(
            route=RouteKind.CLARIFY,
            confidence=0.0,
            rationale="Could not parse router JSON; asking for clarification.",
            approval_level=ApprovalLevel.NONE,
            question="What would you like to do next (answer a question, create a UiPlan spec, or implement a change)?",
        )

    route = _parse_route(data.get("route"))
    if route is None:
        route = RouteKind.CLARIFY
    if allowed_routes and route not in allowed_routes:
        route = RouteKind.CLARIFY
        data["question"] = data.get("question") or "That path is not available in this context. What should we do instead?"

    conf: float
    try:
        conf = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))

    rationale = str(data.get("rationale", "") or "").strip() or "No rationale provided."
    ap = _parse_approval(data.get("approval_level"))
    question = data.get("question")
    if question is not None and not str(question).strip():
        question = None
    elif question is not None:
        question = str(question).strip()

    if conf < LOW_CONFIDENCE and route not in (RouteKind.ANSWER,):
        if not question:
            question = "Can you add a bit more detail (goal, project area, and whether you want docs, a plan, or implementation)?"
        route = RouteKind.CLARIFY
        ap = ApprovalLevel.NONE

    if route == RouteKind.CLARIFY and not question:
        question = "What is the main outcome you want?"

    suggested = data.get("suggested_command")
    if suggested is not None:
        suggested = str(suggested).strip() or None

    next_action = data.get("next_action")
    if next_action is not None:
        next_action = str(next_action).strip() or None

    skills: list[str] = []
    raw_sk = data.get("selected_skills")
    if isinstance(raw_sk, list):
        skills = [str(x) for x in raw_sk if x]

    return OrchestrationDecision(
        route=route,
        confidence=conf,
        rationale=rationale,
        approval_level=ap,
        question=question,
        suggested_command=suggested,
        next_action=next_action,
        selected_skills=skills,
    )


def _context_payload(ctx: OrchestrationContext) -> str:
    payload = {
        "user_request": ctx.user_request,
        "project_root": ctx.project_root,
        "tool_profile": ctx.tool_profile,
        "command_names": ctx.command_names,
        "deterministic_intent": ctx.intent,
        "deterministic_intent_reason": ctx.intent_reason,
        "history_excerpt": ctx.history_excerpt,
        "grounding": ctx.grounding_pack,
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _fallback_decision_from_context(
    ctx: OrchestrationContext,
    *,
    allowed_routes: set[RouteKind] | None = None,
) -> OrchestrationDecision:
    """Use deterministic intent when the LLM router returns malformed text."""
    lower = ctx.user_request.lower()
    route = RouteKind.CLARIFY
    approval = ApprovalLevel.NONE
    question: str | None = (
        "What would you like to do next (answer a question, create a UiPlan spec, "
        "or implement a change)?"
    )
    suggested: str | None = None
    rationale = "Router JSON was malformed; used deterministic intent fallback."

    if "uiplan" in lower:
        route = RouteKind.COMMAND_HINT
        question = None
        approval = ApprovalLevel.NONE
        suggested = "/uiplan-spec <title> --intent <goal>"
        rationale = "Request mentions UiPlan; suggesting the deterministic UiPlan command."
    elif ctx.intent == "question":
        route = RouteKind.ANSWER
        question = None
    elif ctx.intent == "documentation":
        route = RouteKind.DOCUMENTATION
        question = None
        approval = ApprovalLevel.CONFIRM_WRITE
    elif ctx.intent == "build":
        route = RouteKind.EXECUTE
        question = None
        approval = ApprovalLevel.CONFIRM_WRITE

    if allowed_routes and route not in allowed_routes:
        route = RouteKind.CLARIFY
        approval = ApprovalLevel.NONE
        question = "That path is not available in this context. What should we do instead?"
        suggested = None

    return OrchestrationDecision(
        route=route,
        confidence=0.56 if route != RouteKind.CLARIFY else 0.0,
        rationale=rationale,
        approval_level=approval,
        question=question,
        suggested_command=suggested,
        selected_skills=["uiplan"] if "uiplan" in lower else [],
    )


async def route_user_request(
    ctx: OrchestrationContext,
    *,
    model_name: str | None = None,
    region: str | None = None,
    allowed_routes: list[str] | None = None,
    invoke_model: Callable[..., Any] | None = None,
) -> OrchestrationDecision:
    """
    Call the LLM to classify the next orchestration step.

    ``allowed_routes`` is an optional list of route strings; if set, the decision is
    clamped to that set (or clarify).

    In unit tests, pass ``invoke_model`` as an async function returning an AIMessage or str.
    """
    allowed: set[RouteKind] | None = None
    if allowed_routes:
        allowed = set()
        for s in allowed_routes:
            rk = _parse_route(s)
            if rk is not None:
                allowed.add(rk)
        if not allowed:
            allowed = None

    user_body = "Context (JSON):\n" + _context_payload(ctx) + "\n\nReturn only the JSON object for your routing decision."

    if invoke_model is not None:
        response = await invoke_model(
            [SystemMessage(content=_ROUTER_SYSTEM), HumanMessage(content=user_body)]
        )
        if hasattr(response, "content"):
            text = str(getattr(response, "content", "") or "")
        else:
            text = str(response)
    else:
        chat = build_chat_model(
            task_id="planner",
            region=region,
            signals=ComplexitySignals(intent="ambiguous"),
            chat_cls=ChatBedrockConverse,
        )
        messages = [SystemMessage(content=_ROUTER_SYSTEM), HumanMessage(content=user_body)]
        r = await chat.ainvoke(messages)
        text = str(r.content) if r else ""

    data = parse_orchestration_json(text)
    if data is None:
        return _fallback_decision_from_context(ctx, allowed_routes=allowed)
    return decision_from_parsed(data, allowed_routes=allowed)


def context_to_public_dict(ctx: OrchestrationContext) -> dict[str, Any]:
    """JSON-safe dict for MCP ``uipath_assistant_context`` (no dataclass dependency for callers)."""
    d = asdict(ctx)
    return d
