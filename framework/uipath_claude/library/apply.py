"""Shared logic for applying and rejecting library proposals.

Used by both the CLI (`library-proposals approve/reject`) and the MCP
surface so both paths stay consistent in behaviour and observability.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from uipath_claude.library.proposals import (
    LibraryProposal,
    ProposalKind,
    ProposalStore,
)
from uipath_claude.library.writer import LibraryWriter
from uipath_claude.observability.logger import StructuredLogger


@dataclass
class ApplyResult:
    ok: bool
    message: str
    proposal: LibraryProposal | None = None


def apply_proposal(proposal_id: str, *, store: ProposalStore | None = None) -> ApplyResult:
    """Apply a pending proposal by id. Emits structured log on success."""
    store = store or ProposalStore()
    p = store.get(proposal_id)
    if not p:
        return ApplyResult(ok=False, message=f"Proposal not found: {proposal_id}")

    writer = LibraryWriter()
    try:
        if p.kind == ProposalKind.NEW_CHAPTER:
            try:
                meta = json.loads(p.content) if p.content else {}
            except json.JSONDecodeError:
                return ApplyResult(ok=False, message="Invalid proposal content JSON.", proposal=p)
            writer.create_chapter(
                book_id=p.book_id,
                chapter_id=p.chapter_id,
                chapter_title=p.section_title,
                order=meta.get("order"),
                initial_sections=meta.get("initial_sections"),
            )
        elif p.kind == ProposalKind.UPDATE_SECTION:
            try:
                writer.update_section(
                    book_id=p.book_id,
                    chapter_id=p.chapter_id,
                    section_id=p.section_id,
                    content=p.content,
                )
            except ValueError as e:
                if "section does not exist" not in str(e).lower():
                    return ApplyResult(ok=False, message=str(e), proposal=p)
                writer.create_section(
                    book_id=p.book_id,
                    chapter_id=p.chapter_id,
                    section_id=p.section_id,
                    section_title=p.section_title,
                    content=p.content,
                    keywords=p.keywords,
                )
        else:
            writer.create_section(
                book_id=p.book_id,
                chapter_id=p.chapter_id,
                section_id=p.section_id,
                section_title=p.section_title,
                content=p.content,
                keywords=p.keywords,
            )
    except ValueError as e:
        return ApplyResult(ok=False, message=str(e), proposal=p)

    store.remove(proposal_id)
    StructuredLogger().emit(
        event="library_proposal_approved",
        proposal_id=p.proposal_id,
        book_id=p.book_id,
        chapter_id=p.chapter_id,
        section_id=p.section_id,
    )
    return ApplyResult(
        ok=True,
        message=f"Applied: {p.book_id}/{p.chapter_id}/{p.section_id}",
        proposal=p,
    )


def reject_proposal(proposal_id: str, *, store: ProposalStore | None = None) -> ApplyResult:
    """Drop a pending proposal. Emits structured log on success."""
    store = store or ProposalStore()
    if not store.remove(proposal_id):
        return ApplyResult(ok=False, message=f"Proposal not found: {proposal_id}")
    StructuredLogger().emit(event="library_proposal_rejected", proposal_id=proposal_id)
    return ApplyResult(ok=True, message=f"Rejected: {proposal_id}")
