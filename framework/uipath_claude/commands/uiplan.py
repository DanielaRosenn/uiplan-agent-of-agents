"""Slash commands for UiPlan artifacts backed by plan MCP tools."""
from __future__ import annotations

import asyncio
from typing import Any

from uipath_claude.commands.registry import CommandRegistry, register_command


def _run_plan_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import call_plan_tool

    return asyncio.run(call_plan_tool(name, arguments))


_SUBCOMMANDS = frozenset({"ground", "spec", "plan", "tasks", "review", "full"})


def _parse_title_intent(tail: str) -> tuple[str, str]:
    """Parse ``<title> [--intent ...]`` while allowing multi-word titles."""
    marker = " --intent "
    if marker in tail:
        title, intent = tail.split(marker, 1)
        title = title.strip()
        intent = intent.strip() or title
        return title, intent
    return tail.strip(), tail.strip()


def _maybe_split_natural_spec_request(tail: str) -> tuple[str, str]:
    """Support ``/uiplan-spec Title can you base...`` without making title huge."""
    text = tail.strip()
    if " --intent " in text:
        return _parse_title_intent(text)
    parts = text.split(maxsplit=1)
    if len(parts) == 2:
        rest_lower = parts[1].lower()
        looks_like_context = (
            " pdd" in f" {rest_lower}"
            or " sdd" in f" {rest_lower}"
            or ".md" in rest_lower
            or ":\\" in parts[1]
            or rest_lower.startswith(("can ", "could ", "please ", "base ", "from "))
        )
        if looks_like_context:
            return parts[0], text
    return text, text


def _files_line(folder: str | None) -> str:
    if not folder:
        return ""
    return (
        "\nFiles:\n"
        f"- `{folder}\\spec.md`\n"
        f"- `{folder}\\plan.md`\n"
        f"- `{folder}\\tasks.md`"
    )


def _format_review(review: dict[str, Any]) -> str:
    ok = review.get("ok")
    next_action = review.get("next_action")
    findings = review.get("findings") or []
    lines = [f"Review: {'pass' if ok else 'needs edits'}"]
    if next_action:
        lines.append(f"Next action: `{next_action}`")
    if findings:
        lines.append("Findings:")
        for item in findings[:8]:
            if isinstance(item, dict):
                severity = item.get("severity", "info")
                message = item.get("message") or item.get("text") or str(item)
                location = item.get("location") or item.get("path")
                suffix = f" ({location})" if location else ""
                lines.append(f"- {severity}: {message}{suffix}")
            else:
                lines.append(f"- {item}")
        if len(findings) > 8:
            lines.append(f"- ... {len(findings) - 8} more")
    return "\n".join(lines)


def _format_result(sub: str, out: dict[str, Any]) -> str:
    """Return chat-friendly UiPlan output instead of raw MCP JSON."""
    status = out.get("status", "unknown")
    if status != "ok":
        message = out.get("message") or out.get("reason") or str(out)
        return f"UiPlan {sub} returned `{status}`: {message}"

    if sub == "ground":
        topic = out.get("topic", "")
        skills = out.get("matched_skills") or []
        lines = [f"UiPlan grounding complete for: {topic}"]
        if skills:
            lines.append("Matched skills:")
            for skill in skills[:5]:
                if isinstance(skill, dict) and skill.get("name"):
                    lines.append(f"- `{skill['name']}`")
        lines.append("Next: `/uiplan-spec <title> --intent <grounded goal>`")
        return "\n".join(lines)

    if sub == "spec":
        folder = out.get("relative") or out.get("path")
        slug = out.get("slug")
        return (
            "UiPlan spec created.\n"
            f"Slug: `{slug}`\n"
            f"Folder: `{folder}`"
            f"{_files_line(str(folder) if folder else None)}\n\n"
            "Review/edit next:\n"
            "1. Open `spec.md` and edit requirements/user stories.\n"
            f"2. Run `/uiplan-plan {slug}` when the spec looks right.\n"
            f"3. Run `/uiplan-review {slug} spec` to check the spec."
        )

    if sub == "plan":
        slug = out.get("slug")
        path = out.get("path")
        return (
            "UiPlan plan created.\n"
            f"Slug: `{slug}`\n"
            f"Path: `{path}`\n\n"
            "Next:\n"
            "1. Review/edit `plan.md`.\n"
            f"2. Run `/uiplan-tasks {slug}`.\n"
            f"3. Run `/uiplan-review {slug} plan`."
        )

    if sub == "tasks":
        slug = out.get("slug")
        path = out.get("path")
        return (
            "UiPlan tasks created.\n"
            f"Slug: `{slug}`\n"
            f"Path: `{path}`\n\n"
            "Next:\n"
            "1. Review/edit `tasks.md`.\n"
            f"2. Run `/uiplan-review {slug} all`.\n"
            "3. Accept only after review passes and you approve the bundle."
        )

    if sub == "review":
        return _format_review(out)

    if sub == "full":
        slug = out.get("slug")
        folder = out.get("folder")
        review = out.get("review") if isinstance(out.get("review"), dict) else {}
        return (
            "UiPlan bundle created.\n"
            f"Slug: `{slug}`\n"
            f"Folder: `{folder}`"
            f"{_files_line(str(folder) if folder else None)}\n\n"
            f"{_format_review(review)}\n\n"
            "Review/edit next:\n"
            "1. Open `spec.md`, `plan.md`, and `tasks.md`.\n"
            f"2. Re-run `/uiplan-review {slug} all` after edits.\n"
            "3. Accept/publish only after review passes and you approve it."
        )

    return str(out)


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
            title, intent = _maybe_split_natural_spec_request(tail)
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
    return _format_result(sub, out)


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
