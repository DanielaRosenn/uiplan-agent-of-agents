"""Build compact context for the LLM orchestration router."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp_server.tools.plan_grounding import build_grounding_pack

from uipath_claude.query.intent_classifier import classify_intent
from uipath_claude.query.orchestration_types import OrchestrationContext


def _history_excerpt(
    history: list[dict[str, str]] | None, *, max_messages: int = 8, max_chars: int = 4000
) -> list[dict[str, str]]:
    if not history:
        return []
    tail = history[-max_messages:]
    out: list[dict[str, str]] = []
    used = 0
    for msg in tail:
        role = str(msg.get("role", ""))
        content = str(msg.get("content", ""))
        if len(content) > 2000:
            content = content[:2000] + "\n...(truncated)"
        line_len = len(role) + len(content) + 4
        if used + line_len > max_chars and out:
            break
        out.append({"role": role, "content": content})
        used += line_len
    return out


def _compact_grounding_pack(pack: dict[str, Any]) -> dict[str, Any]:
    """Remove heavy/duplicate fields; keep what the router needs."""
    if pack.get("status") != "ok":
        return {"status": pack.get("status", "error")}

    matched: list[dict[str, str]] = []
    for s in (pack.get("matched_skills") or [])[:8]:
        if not isinstance(s, dict):
            continue
        name = str(s.get("name") or "")
        if not name:
            continue
        matched.append(
            {
                "name": name,
                "description": (str(s.get("description", "")))[:200],
            }
        )

    src_docs: list[dict[str, str]] = []
    for d in (pack.get("source_documents") or [])[:5]:
        if not isinstance(d, dict):
            continue
        one = {
            "path": str(d.get("path", "")),
            "name": str(d.get("name", "")),
            "kind": str(d.get("kind", "")),
        }
        ex = d.get("excerpt")
        if ex:
            one["excerpt"] = str(ex)[:1200]
        if d.get("error"):
            one["error"] = str(d.get("error"))[:200]
        src_docs.append(one)

    unanswered = list(pack.get("unanswered") or [])[:5]

    return {
        "status": "ok",
        "topic": (pack.get("topic") or "")[:2000],
        "source_documents": src_docs,
        "matched_skills": matched,
        "pdd_candidates": (pack.get("pdd_candidates") or [])[:8],
        "candidate_project_template": pack.get("candidate_project_template") or "",
        "project_context_excerpt": (pack.get("project_context_excerpt") or "")[:1200] if pack.get("project_context_excerpt") else None,
        "claude_md_excerpt": (pack.get("claude_md_excerpt") or "")[:800] if pack.get("claude_md_excerpt") else None,
        "unanswered": unanswered,
    }


def build_orchestration_context(
    user_request: str,
    *,
    project_root: str | Path | None = None,
    command_names: list[str] | None = None,
    tool_profile: str = "all",
    history: list[dict[str, str]] | None = None,
) -> OrchestrationContext:
    """
    Assemble a router context pack. Read-only: loads grounding via ``build_grounding_pack``,
    which may read user-referenced .md files from the request string.
    """
    root = Path(
        str(project_root or os.environ.get("WORKSPACE_ROOT") or "."),
    ).expanduser().resolve()

    intent, intent_reason = classify_intent((user_request or "").strip() or " ")
    pack = build_grounding_pack(root, (user_request or "").strip() or " ")

    return OrchestrationContext(
        user_request=(user_request or "").strip(),
        project_root=str(root),
        tool_profile=tool_profile,
        command_names=sorted(set(command_names or [])),
        history_excerpt=_history_excerpt(history),
        intent=intent.value,
        intent_reason=intent_reason,
        grounding_pack=_compact_grounding_pack(pack),
    )
