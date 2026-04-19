"""CLI: ``library-proposals`` — review and apply proposed library updates."""
from __future__ import annotations

import json

import typer

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.library.apply import apply_proposal, reject_proposal
from uipath_claude.library.proposals import ProposalStore

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
    result = apply_proposal(proposal_id)
    if not result.ok:
        typer.echo(result.message, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)


@library_proposals_app.command("reject")
def reject_cmd(proposal_id: str) -> None:
    """Drop a proposal without applying it."""
    result = reject_proposal(proposal_id)
    if not result.ok:
        typer.echo(result.message, err=True)
        raise typer.Exit(code=1)
    typer.echo(result.message)


def register_library_proposals_command(app: typer.Typer) -> None:
    """Register ``library-proposals`` as a nested Typer on the main CLI app."""
    app.add_typer(library_proposals_app, name="library-proposals")


def _format_list() -> str:
    store = ProposalStore()
    pending = store.list_pending()
    if not pending:
        return "No pending proposals."
    lines = [
        f"{p.proposal_id}  {p.book_id}/{p.chapter_id}/{p.section_id}  "
        f"[{p.kind.value}]  {p.section_title}"
        for p in pending
    ]
    return "\n".join(lines)


def _format_show(proposal_id: str) -> str:
    store = ProposalStore()
    p = store.get(proposal_id)
    if not p:
        return f"Proposal not found: {proposal_id}"
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
    return json.dumps(summary, indent=2) + "\n---\n" + p.content


def register_library_proposals_chat_command(registry: CommandRegistry) -> None:
    """Register the ``/library-proposals`` in-chat slash command.

    Subcommands: ``list`` (default), ``show <id>``, ``approve <id>``,
    ``reject <id>``. Reuses the same ProposalStore + apply/reject helpers
    as the Typer CLI form, so behaviour stays consistent.
    """

    def handle(*args: str) -> str:
        if not args:
            return _format_list()
        sub = args[0].strip().lower()
        rest = args[1:]
        if sub == "list":
            return _format_list()
        if sub == "show":
            if not rest:
                return "Usage: /library-proposals show <proposal_id>"
            return _format_show(rest[0])
        if sub == "approve":
            if not rest:
                return "Usage: /library-proposals approve <proposal_id>"
            result = apply_proposal(rest[0])
            return result.message
        if sub == "reject":
            if not rest:
                return "Usage: /library-proposals reject <proposal_id>"
            result = reject_proposal(rest[0])
            return result.message
        return (
            f"Unknown subcommand: {sub}. "
            "Use list | show <id> | approve <id> | reject <id>."
        )

    registry.register(
        "library-proposals",
        "Review/approve/reject proposed library updates",
        handle,
    )
