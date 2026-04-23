"""Slash command /uiplan — dispatches to plan MCP tools (spec-kit-style bundle)."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from uipath_claude.commands.registry import CommandRegistry, register_command


def _run_plan_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import call_plan_tool

    return asyncio.run(call_plan_tool(name, arguments))


_SUBCOMMANDS = frozenset({"ground", "spec", "plan", "tasks", "review", "full"})


def register_uiplan_command(registry: CommandRegistry) -> None:
    @register_command(
        registry,
        name="uiplan",
        description=(
            "UiPlan: spec.md + plan.md + tasks.md under .cursor/plans/<date-slug>/ "
            "(ground -> spec -> plan -> tasks -> review). "
            "Usage: /uiplan full <title> | /uiplan ground <topic> | "
            "/uiplan spec <title> [--intent text] | /uiplan plan <slug> | "
            "/uiplan tasks <slug> | /uiplan review <slug> [spec|plan|tasks|all]"
        ),
    )
    def uiplan_command(*parts: str) -> str:
        raw = " ".join(parts).strip()
        if not raw:
            return (
                "Usage:\n"
                "  /uiplan full <title>   — scaffold entire bundle (intent defaults to title)\n"
                "  /uiplan ground <topic> — workspace grounding pack only\n"
                "  /uiplan spec <title> [intent ...] — create folder + spec.md\n"
                "  /uiplan plan <slug>    — write plan.md (after spec)\n"
                "  /uiplan tasks <slug>   — write tasks.md (after plan)\n"
                "  /uiplan review <slug> [all|spec|plan|tasks]\n"
                "CLI: uipath-claude plan uiplan <subcommand> ..."
            )
        tokens = raw.split()
        head = tokens[0].lower()
        if head in _SUBCOMMANDS:
            sub = head
            tail = " ".join(tokens[1:]).strip()
        else:
            sub = "full"
            tail = raw
        try:
            if sub == "ground":
                if not tail:
                    return "Usage: /uiplan ground <topic>"
                out = _run_plan_tool("uipath_plan_ground", {"topic": tail})
            elif sub == "full":
                if not tail:
                    return "Usage: /uiplan full <title>"
                out = _run_plan_tool(
                    "uipath_plan_uiplan_new",
                    {"title": tail, "intent": tail},
                )
            elif sub == "spec":
                if not tail:
                    return "Usage: /uiplan spec <title> [intent words...]"
                bits = tail.split(None, 1)
                title = bits[0]
                intent = bits[1] if len(bits) > 1 else title
                out = _run_plan_tool(
                    "uipath_plan_spec_new",
                    {"title": title, "intent": intent},
                )
            elif sub == "plan":
                if not tail:
                    return "Usage: /uiplan plan <slug>"
                out = _run_plan_tool("uipath_plan_plan_new", {"slug": tail.split()[0]})
            elif sub == "tasks":
                if not tail:
                    return "Usage: /uiplan tasks <slug>"
                out = _run_plan_tool("uipath_plan_tasks_new", {"slug": tail.split()[0]})
            elif sub == "review":
                bits = tail.split()
                if not bits:
                    return "Usage: /uiplan review <slug> [all|spec|plan|tasks]"
                slug = bits[0]
                stage = bits[1] if len(bits) > 1 else "all"
                out = _run_plan_tool(
                    "uipath_plan_review",
                    {"slug": slug, "stage": stage},
                )
            else:
                return f"Unknown subcommand: {sub}"
        except Exception as exc:  # noqa: BLE001
            return f"UiPlan command failed: {exc}"
        return json.dumps(out, indent=2, default=str)
