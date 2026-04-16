"""LLM-based lesson distiller with offline fallback and semantic dedup."""
from __future__ import annotations

import os
from typing import Iterable

from uipath_claude.skills.insights import SkillInsight

_DISTILL_PROMPT = (
    "You are refining a short UiPath lesson. Rewrite the candidate in one or two "
    "sentences, preserve specific tool / activity names, be imperative, and omit "
    "apology or hedging. If the candidate is semantically the same as any in "
    "EXISTING, output exactly DUPLICATE.\n\n"
    "CANDIDATE:\n{candidate}\n\nEXISTING:\n{existing}\n"
)


def _invoke_llm(prompt: str) -> str:
    from langchain_aws import ChatBedrockConverse

    model = (
        os.environ.get("UIPATH_DISTILLER_MODEL")
        or os.environ.get("UIPATH_MODEL_ID")
        or "anthropic.claude-3-sonnet-20240229-v1:0"
    )
    region = os.environ.get("AWS_REGION") or "us-east-1"
    llm = ChatBedrockConverse(model=model, region_name=region)
    response = llm.invoke(prompt)
    return (
        response.content if isinstance(response.content, str) else str(response.content)
    ).strip()


def distill(
    candidate: SkillInsight,
    existing_top: Iterable[SkillInsight],
) -> SkillInsight | None:
    """Return a rewritten lesson, ``None`` if duplicate; original body on LLM failure."""
    existing_text = "\n".join(f"- {i.content}" for i in existing_top)
    prompt = _DISTILL_PROMPT.format(candidate=candidate.content, existing=existing_text or "(none)")
    try:
        rewritten = _invoke_llm(prompt)
    except Exception:
        return candidate

    if rewritten.strip().upper() == "DUPLICATE":
        return None

    out = SkillInsight(
        skill_name=candidate.skill_name,
        insight_type=candidate.insight_type,
        content=rewritten,
        context=candidate.context,
        source="auto+distilled",
        success_count=candidate.success_count,
        failure_count=candidate.failure_count,
    )
    return out
