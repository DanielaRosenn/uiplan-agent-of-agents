"""Route to appropriate documentation agent based on detected needs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from uipath_claude.tools.doc_tools import list_docs


@dataclass
class DocRouteDecision:
    """Decision about which documentation agent to invoke."""
    
    agent: Literal["ba", "sa", "none"]
    doc_type: str | None
    next_docs: list[str] = field(default_factory=list)
    reason: str = ""
    skip_reason: str | None = None


_DOC_PRIORITY = ["pdd", "sdd", "add", "tdd"]

_DOC_TO_AGENT = {
    "pdd": "ba",
    "sdd": "sa",
    "add": "sa",
    "tdd": "sa",
}


async def route_to_doc_agent(
    user_input: str,
    recommended_docs: list[str],
    project_dir: str | None = None,
) -> DocRouteDecision:
    """
    Route to the appropriate documentation agent.
    
    Args:
        user_input: The user's request
        recommended_docs: List of recommended doc types from detector
        project_dir: Optional project directory
        
    Returns:
        DocRouteDecision with agent type and doc to create
    """
    if not recommended_docs:
        return DocRouteDecision(
            agent="none",
            doc_type=None,
            reason="No documentation needed",
        )
    
    existing = list_docs(project_dir)
    existing_types = {k for k, v in existing.items() if v.get("exists")}
    
    sorted_docs = sorted(
        recommended_docs,
        key=lambda d: _DOC_PRIORITY.index(d) if d in _DOC_PRIORITY else 99,
    )
    
    doc_to_create = None
    skipped = []
    
    for doc in sorted_docs:
        if doc in existing_types:
            skipped.append(doc)
        else:
            doc_to_create = doc
            break
    
    if doc_to_create is None:
        return DocRouteDecision(
            agent="none",
            doc_type=None,
            reason="All recommended documentation already exists",
            skip_reason=f"Skipped existing: {', '.join(skipped)}" if skipped else None,
        )
    
    remaining = [d for d in sorted_docs if d != doc_to_create and d not in existing_types]
    
    agent = _DOC_TO_AGENT.get(doc_to_create, "sa")
    
    skip_msg = None
    if skipped:
        skip_msg = f"Skipped existing: {', '.join(skipped)}"
    
    return DocRouteDecision(
        agent=agent,
        doc_type=doc_to_create,
        next_docs=remaining,
        reason=f"Creating {doc_to_create.upper()} using {agent.upper()} agent",
        skip_reason=skip_msg,
    )
