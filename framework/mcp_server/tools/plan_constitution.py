"""Load constitution gates for UiPlan review (defaults + repo override)."""
from __future__ import annotations

from pathlib import Path
from typing import Any

_DEFAULT_GATES = [
    {
        "id": "modern_experience_only",
        "text": "Modern experience only: C#, Windows, .NET 8. No Classic, no VB.Net.",
    },
    {
        "id": "analyze_gate",
        "text": "Never publish if analyze returns errors; gate CI on analyze.",
    },
    {
        "id": "no_prod_from_assistant",
        "text": "Never deploy to Production from an AI-assistant session.",
    },
    {
        "id": "secrets",
        "text": "Never commit secrets; use Orchestrator assets or env vars.",
    },
    {
        "id": "cli_version_match",
        "text": "Match CLI version to Studio/Orchestrator version.",
    },
]


def load_constitution(repo: Path) -> dict[str, Any]:
    """Return gates list and raw path used."""
    override = repo / "docs" / "plans" / "constitution.md"
    if override.is_file():
        return {
            "source": override.relative_to(repo).as_posix(),
            "gates": _parse_gates_markdown(override.read_text(encoding="utf-8")),
        }
    return {"source": "built-in", "gates": list(_DEFAULT_GATES)}


def _parse_gates_markdown(text: str) -> list[dict[str, str]]:
    gates: list[dict[str, str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        rest = line[2:].strip()
        if not rest:
            continue
        # "- **id**: description" or "- description"
        if rest.startswith("**") and "**:" in rest:
            end = rest.find("**:", 2)
            if end > 0:
                gid = rest[2:end].strip()
                desc = rest[end + 3 :].strip()
                gates.append({"id": gid, "text": desc})
                continue
        gates.append({"id": f"gate_{len(gates)+1}", "text": rest})
    if not gates:
        return list(_DEFAULT_GATES)
    return gates
