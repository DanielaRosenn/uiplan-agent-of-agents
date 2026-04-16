"""Optional CLI hint after capability-style questions about building."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


def maybe_print_capability_build_hint(console: Console, user_input: str) -> None:
    """After a streamed QA answer, nudge the user how to trigger real plan/build."""
    lower = user_input.strip().lower()
    looks_buildy = any(
        w in lower
        for w in (
            " build ",
            " create ",
            " make ",
            " generate ",
            " implement ",
        )
    )
    openers = (
        "can you ",
        "could you ",
        "would you ",
        "will you ",
        "are you able to ",
        "is it possible to ",
        "how would you ",
    )
    if looks_buildy and any(lower.startswith(p) for p in openers):
        console.print(
            "[dim]Tip: to actually build it, try an imperative like "
            '"build a project from this SDD" or paste the SDD and say '
            '"implement this".[/dim]'
        )
