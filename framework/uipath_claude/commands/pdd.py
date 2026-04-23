"""/pdd command - run the full PDD->deploy lifecycle."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

from uipath_claude.commands.registry import CommandRegistry, register_command


def _preview(text: str, limit: int = 240) -> str:
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= limit:
        return t
    return t[: limit - 3] + "..."


def _parse_flags(parts: list[str]) -> tuple[dict[str, Any], str]:
    """Pull --project-type / --deploy / --no-deploy / --folder out of parts."""
    opts: dict[str, Any] = {
        "project_type": "process",
        "deploy": False,
        "folder": "Shared",
    }
    rest: list[str] = []
    i = 0
    while i < len(parts):
        tok = parts[i]
        if tok.startswith("--project-type=") or tok.startswith("--type="):
            opts["project_type"] = tok.split("=", 1)[1]
        elif tok in ("--project-type", "--type") and i + 1 < len(parts):
            opts["project_type"] = parts[i + 1]
            i += 1
        elif tok == "--deploy":
            opts["deploy"] = True
        elif tok == "--no-deploy":
            opts["deploy"] = False
        elif tok.startswith("--folder="):
            opts["folder"] = tok.split("=", 1)[1]
        elif tok == "--folder" and i + 1 < len(parts):
            opts["folder"] = parts[i + 1]
            i += 1
        else:
            rest.append(tok)
        i += 1
    return opts, " ".join(rest).strip()


def register_pdd_command(
    registry: CommandRegistry,
    run_lifecycle: Callable[..., Awaitable[dict[str, Any]]],
) -> None:
    """Register the ``/pdd`` slash command."""

    @register_command(
        registry,
        name="pdd",
        description="Run full PDD->SDD->ADD->TDD->scaffold->validate->run->publish->deploy lifecycle",
    )
    def pdd_command(*request_parts: str) -> str:
        opts, request = _parse_flags(list(request_parts))
        if not request:
            return (
                'Usage: /pdd "<project request>" '
                "[--project-type process|maestro] [--deploy] [--folder <name>]"
            )

        try:
            result = asyncio.run(
                run_lifecycle(
                    request,
                    project_type=opts["project_type"],
                    deploy=opts["deploy"],
                    folder=opts["folder"],
                )
            )
        except Exception as exc:
            return f"PDD lifecycle failed: {exc}"

        lines: list[str] = []
        if result.get("status") == "ok":
            lines.append("PDD lifecycle: OK")
        else:
            lines.append(
                f"PDD lifecycle: FAILED at {result.get('failed_at')}: {result.get('error', '')}"
            )

        stages = result.get("stages") or {}
        for stage_name, payload in stages.items():
            status = payload.get("status", "?") if isinstance(payload, dict) else "?"
            extra = ""
            if isinstance(payload, dict):
                if "error" in payload and payload.get("status") == "failed":
                    extra = f" - {_preview(payload['error'], 120)}"
                elif "result" in payload and isinstance(payload["result"], str):
                    extra = f" - {_preview(payload['result'], 80)}"
            lines.append(f"  {stage_name:10s}: {status}{extra}")

        paths = result.get("paths") or {}
        if paths:
            lines.append("")
            lines.append("Artifacts:")
            for key in sorted(paths):
                lines.append(f"  {key}: {paths[key]}")

        return "\n".join(lines)
