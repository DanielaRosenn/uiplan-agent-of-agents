"""Slash commands for UiPlan artifacts backed by plan MCP tools."""
from __future__ import annotations

import asyncio
import json
from typing import Any

from uipath_claude.commands.registry import CommandRegistry, register_command


def _run_plan_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import call_plan_tool

    return asyncio.run(call_plan_tool(name, arguments))


_SUBCOMMANDS = frozenset({"ground", "spec", "plan", "tasks", "review", "full"})


def _json_result(out: dict[str, Any]) -> str:
    return json.dumps(out, indent=2, default=str)


def _parse_title_intent(tail: str) -> tuple[str, str]:
    """Parse ``<title> [--intent ...]`` while allowing multi-word titles."""
    marker = " --intent "
    if marker in tail:
        title, intent = tail.split(marker, 1)
        title = title.strip()
        intent = intent.strip() or title
        return title, intent
    return tail.strip(), tail.strip()


def _dispatch_uiplan(sub: str, tail: str, *, command_name: str = "uiplan") -> str:
    """Dispatch a UiPlan subcommand to its backing MCP plan tool."""
    try:
        if sub == "ground":
            if not tail:
                return f"Usage: /{command_name} <topic>"
            out = _run_plan_tool("uipath_plan_ground", {"topic": tail})
        elif sub == "full":
            if not tail:
                return f"Usage: /{command_name} <title>"
            out = _run_plan_tool(
                "uipath_plan_uiplan_new",
                {"title": tail, "intent": tail},
            )
        elif sub == "spec":
            if not tail:
                return f"Usage: /{command_name} <title> [--intent text]"
            title, intent = _parse_title_intent(tail)
            out = _run_plan_tool(
                "uipath_plan_spec_new",
                {"title": title, "intent": intent},
            )
        elif sub == "plan":
            if not tail:
                return f"Usage: /{command_name} <slug>"
            out = _run_plan_tool("uipath_plan_plan_new", {"slug": tail.split()[0]})
        elif sub == "tasks":
            if not tail:
                return f"Usage: /{command_name} <slug>"
            out = _run_plan_tool("uipath_plan_tasks_new", {"slug": tail.split()[0]})
        elif sub == "review":
            bits = tail.split()
            if not bits:
                return f"Usage: /{command_name} <slug> [all|spec|plan|tasks]"
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
    return _json_result(out)


def _usage() -> str:
    return (
        "Usage:\n"
        "  /uiplan-full <title>                 — ground + spec + plan + tasks + review\n"
        "  /uiplan-ground <topic>               — workspace grounding pack only\n"
        "  /uiplan-spec <title> [--intent text] — create folder + spec.md\n"
        "  /uiplan-plan <slug>                  — write plan.md (after spec)\n"
        "  /uiplan-tasks <slug>                 — write tasks.md (after plan)\n"
        "  /uiplan-review <slug> [all|spec|plan|tasks]\n"
        "Backwards-compatible dispatcher: /uiplan <full|ground|spec|plan|tasks|review> ...\n"
        "CLI: uipath-claude plan uiplan <subcommand> ..."
    )


def register_uiplan_command(registry: CommandRegistry) -> None:
    @register_command(
        registry,
        name="uiplan-ground",
        description="UiPlan ground: run uipath_plan_ground for a topic.",
    )
    def uiplan_ground_command(*parts: str) -> str:
        return _dispatch_uiplan("ground", " ".join(parts).strip(), command_name="uiplan-ground")

    @register_command(
        registry,
        name="uiplan-spec",
        description="UiPlan spec: run uipath_plan_spec_new to create spec.md.",
    )
    def uiplan_spec_command(*parts: str) -> str:
        return _dispatch_uiplan("spec", " ".join(parts).strip(), command_name="uiplan-spec")

    @register_command(
        registry,
        name="uiplan-plan",
        description="UiPlan plan: run uipath_plan_plan_new to write plan.md.",
    )
    def uiplan_plan_command(*parts: str) -> str:
        return _dispatch_uiplan("plan", " ".join(parts).strip(), command_name="uiplan-plan")

    @register_command(
        registry,
        name="uiplan-tasks",
        description="UiPlan tasks: run uipath_plan_tasks_new to write tasks.md.",
    )
    def uiplan_tasks_command(*parts: str) -> str:
        return _dispatch_uiplan("tasks", " ".join(parts).strip(), command_name="uiplan-tasks")

    @register_command(
        registry,
        name="uiplan-review",
        description="UiPlan review: run uipath_plan_review for spec/plan/tasks/all.",
    )
    def uiplan_review_command(*parts: str) -> str:
        return _dispatch_uiplan("review", " ".join(parts).strip(), command_name="uiplan-review")

    @register_command(
        registry,
        name="uiplan-full",
        description="UiPlan full: run uipath_plan_uiplan_new for the full bundle.",
    )
    def uiplan_full_command(*parts: str) -> str:
        return _dispatch_uiplan("full", " ".join(parts).strip(), command_name="uiplan-full")

    @register_command(
        registry,
        name="uiplan",
        description=(
            "UiPlan: spec.md + plan.md + tasks.md under .cursor/plans/<date-slug>/ "
            "(ground -> spec -> plan -> tasks -> review). Prefer first-class "
            "commands: /uiplan-ground, /uiplan-spec, /uiplan-plan, "
            "/uiplan-tasks, /uiplan-review, /uiplan-full."
        ),
    )
    def uiplan_command(*parts: str) -> str:
        raw = " ".join(parts).strip()
        if not raw:
            return _usage()
        tokens = raw.split()
        head = tokens[0].lower()
        if head in _SUBCOMMANDS:
            sub = head
            tail = " ".join(tokens[1:]).strip()
        else:
            sub = "full"
            tail = raw
        return _dispatch_uiplan(sub, tail, command_name=f"uiplan {sub}")
