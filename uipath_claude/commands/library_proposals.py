"""CLI: ``library-proposals`` — review and apply proposed library updates."""
from __future__ import annotations

import json

import typer

from uipath_claude.library.proposals import (
    ProposalKind,
    ProposalStore,
)
from uipath_claude.library.writer import LibraryWriter
from uipath_claude.observability.logger import StructuredLogger

library_proposals_app = typer.Typer(
    help="Review, approve, or reject proposed documentation library updates.",
)


@library_proposals_app.command("list")
def list_cmd() -> None:
    """List pending proposals across all books."""
    store = ProposalStore()
    pending = store.list_pending()
    if not pending:
        typer.echo("No pending proposals.")
        return
    for p in pending:
        typer.echo(
            f"{p.proposal_id}  {p.book_id}/{p.chapter_id}/{p.section_id}  "
            f"[{p.kind.value}]  {p.section_title}"
        )


@library_proposals_app.command("show")
def show_cmd(proposal_id: str) -> None:
    """Show a proposal in full, including the proposed markdown."""
    store = ProposalStore()
    p = store.get(proposal_id)
    if not p:
        typer.echo(f"Proposal not found: {proposal_id}", err=True)
        raise typer.Exit(code=1)
    summary = {
        "proposal_id": p.proposal_id,
        "book_id": p.book_id,
        "chapter_id": p.chapter_id,
        "section_id": p.section_id,
        "section_title": p.section_title,
        "kind": p.kind.value,
        "status": p.status.value,
        "keywords": p.keywords,
        "rationale": p.rationale,
        "created_at": p.created_at,
    }
    typer.echo(json.dumps(summary, indent=2))
    typer.echo("---")
    typer.echo(p.content)


@library_proposals_app.command("approve")
def approve_cmd(proposal_id: str) -> None:
    """Apply a proposal to the library, then remove it from the queue."""
    store = ProposalStore()
    p = store.get(proposal_id)
    if not p:
        typer.echo(f"Proposal not found: {proposal_id}", err=True)
        raise typer.Exit(code=1)

    writer = LibraryWriter()
    if p.kind == ProposalKind.UPDATE_SECTION:
        try:
            writer.update_section(
                book_id=p.book_id,
                chapter_id=p.chapter_id,
                section_id=p.section_id,
                content=p.content,
            )
        except ValueError:
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
    store.remove(proposal_id)
    StructuredLogger().emit(
        event="library_proposal_approved",
        proposal_id=p.proposal_id,
        book_id=p.book_id,
        chapter_id=p.chapter_id,
        section_id=p.section_id,
    )
    typer.echo(f"Applied: {p.book_id}/{p.chapter_id}/{p.section_id}")


@library_proposals_app.command("reject")
def reject_cmd(proposal_id: str) -> None:
    """Drop a proposal without applying it."""
    store = ProposalStore()
    if not store.remove(proposal_id):
        typer.echo(f"Proposal not found: {proposal_id}", err=True)
        raise typer.Exit(code=1)
    StructuredLogger().emit(
        event="library_proposal_rejected",
        proposal_id=proposal_id,
    )
    typer.echo(f"Rejected: {proposal_id}")


def register_library_proposals_command(app: typer.Typer) -> None:
    """Register ``library-proposals`` as a nested Typer on the main CLI app."""
    app.add_typer(library_proposals_app, name="library-proposals")
