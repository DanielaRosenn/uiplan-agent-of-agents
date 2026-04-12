"""Bootstrap command implementation."""
import asyncio
from typing import Any, Awaitable, Callable

from uipath_claude.commands.registry import CommandRegistry, register_command


def _preview(text: str, limit: int = 320) -> str:
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."


def register_bootstrap_command(
    registry: CommandRegistry,
    run_bootstrap: Callable[..., Awaitable[dict[str, Any]]],
) -> None:
    """Register the /bootstrap command."""

    @register_command(registry, name="bootstrap", description="Start bootstrap flow")
    def bootstrap_command(*request_parts: str) -> str:
        """Start the bootstrap flow (BA -> SA -> Dev -> QA)."""
        request = " ".join(request_parts).strip()
        if not request:
            return 'Usage: /bootstrap "<project request>"'

        try:
            result = asyncio.run(run_bootstrap(request))
        except Exception as exc:
            return f"Bootstrap failed: {exc}"

        lines: list[str] = ["Bootstrap complete.", ""]
        paths = result.get("paths") or {}
        if paths:
            lines.append("Artifacts written:")
            for key in sorted(paths.keys()):
                lines.append(f"  {key}: {paths[key]}")
            lines.append("")
        lines.extend(
            [
                "Summaries (truncated):",
                f"  PDD: {_preview(result.get('pdd', ''))}",
                f"  SDD: {_preview(result.get('sdd', ''))}",
                f"  Developer: {_preview(result.get('code', ''))}",
                f"  QA: {_preview(result.get('validation', ''))}",
            ]
        )
        return "\n".join(lines)
