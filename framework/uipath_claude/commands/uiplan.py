"""Slash commands for UiPlan artifacts backed by plan MCP tools."""
from __future__ import annotations

import asyncio
from typing import Any

from uipath_claude.commands.registry import CommandRegistry, register_command


def _run_plan_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from mcp_server.tools.plan_tools import call_plan_tool

    return asyncio.run(call_plan_tool(name, arguments))


_SUBCOMMANDS = frozenset(
    {"ground", "spec", "plan", "tasks", "review", "full", "implement"},
)


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


def _extract_flag_value(text: str, flag: str) -> tuple[str, str | None]:
    marker = f" {flag} "
    padded = f" {text.strip()} "
    if marker not in padded:
        return text.strip(), None
    left, right = padded.split(marker, 1)
    right = right.strip()
    if not right:
        return left.strip(), None
    if " --" in right:
        value, remainder = right.split(" --", 1)
        return f"{left.strip()} --{remainder.strip()}".strip(), value.strip()
    return left.strip(), right.strip()


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
        errors = [item for item in findings if isinstance(item, dict) and item.get("severity") == "error"]
        warns = [item for item in findings if isinstance(item, dict) and item.get("severity") == "warn"]
        lines.append(f"Error findings: {len(errors)} | Warning findings: {len(warns)}")
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


def _format_implement_handoff(
    slug: str,
    review: dict[str, Any],
    *,
    run_to_completion: bool = False,
) -> str:
    """Review-first preflight for build handoff (matches uiplan-implement skill)."""
    body = _format_review(review)
    ok = review.get("ok")
    if not ok:
        return (
            f"UiPlan implement (preflight) for `{slug}`\n\n"
            f"{body}\n\n"
            f"Fix error-severity findings, then re-run `/uiplan-implement {slug}`."
        )
    if run_to_completion:
        acc = review.get("acceptance_ready")
        rtc_note = ""
        if acc is False:
            rtc_note = (
                "\n\n**Run-to-completion blocked:** `.meta.yaml` status is not `accepted`. "
                "Run `uipath_plan_accept` / `uipath-claude plan uiplan accept` before executing "
                "the full task loop without pauses."
            )
        mode = (
            "Run-to-completion mode is enabled: execute accepted local tasks in order without "
            "asking for confirmation between tasks. For each task, run the UiPath implementation "
            "loop: plan alignment, source reality snapshot, dependency/tooling check, development, "
            "artifact completeness gate, behavior tests, analyze gate, spec compliance review, "
            "code quality review, and completion ledger. Stop only on hard gates: review errors, "
            "missing acceptance, submodule guard failure, dependency drift, restore/analyze errors, "
            "failing tests, incomplete runtime artifacts, scaffold-only progress, status mismatch, "
            "missing required credentials/tooling, destructive actions, publish, deploy, or "
            "Production."
            + rtc_note
        )
    else:
        mode = (
            "Follow `.cursor/skills/uiplan-implement/SKILL.md`: confirm the user approves build, "
            "then execute `tasks.md` in order using specialist skills, MCP tools, tests, and "
            "the project build loop."
        )
    return (
        f"UiPlan implement (preflight) for `{slug}`\n\n"
        f"{body}\n\n"
        f"Read `spec.md`, `plan.md`, and `tasks.md` in `.cursor/plans/.../{slug}/` (draft folder). "
        f"{mode} Do not deploy or publish without explicit user approval."
    )


def _format_result(sub: str, out: dict[str, Any]) -> str:
    """Return chat-friendly UiPlan output instead of raw MCP JSON."""
    # uipath_plan_review returns {ok, findings, ...} with no top-level status
    if sub == "review":
        return _format_review(out)

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
            f"Plan id: `{slug}`\n"
            f"Folder: `{folder}`"
            f"{_files_line(str(folder) if folder else None)}\n\n"
            "Review/edit next:\n"
            "1. Open `spec.md` and edit requirements/user stories.\n"
            f"2. Run `/uiplan-plan {slug}`\n"
            f"3. Optional spec check: `/uiplan-review {slug} spec`\n"
            "\nTip: in chat, you can type `/uiplan-plan` or `please do` right after this and the CLI will reuse the plan id."
        )

    if sub == "plan":
        slug = out.get("slug")
        path = out.get("path")
        return (
            "UiPlan plan created.\n"
            f"Plan id: `{slug}`\n"
            f"Path: `{path}`"
        )

    if sub == "tasks":
        slug = out.get("slug")
        path = out.get("path")
        return (
            "UiPlan tasks created.\n"
            f"Plan id: `{slug}`\n"
            f"Path: `{path}`\n\n"
            "Next:\n"
            "1. Review/edit `tasks.md`.\n"
            f"2. Run `/uiplan-review {slug} all`.\n"
            "3. Build only after review passes and you approve the bundle."
        )

    if sub == "full":
        slug = out.get("slug")
        folder = out.get("folder")
        review = out.get("review") if isinstance(out.get("review"), dict) else {}
        return (
            "UiPlan bundle created.\n"
            f"Plan id: `{slug}`\n"
            f"Folder: `{folder}`"
            f"{_files_line(str(folder) if folder else None)}\n\n"
            f"{_format_review(review)}\n\n"
            "Review/edit next:\n"
            "1. Open `spec.md`, `plan.md`, and `tasks.md`.\n"
            f"2. Run `/uiplan-review {slug} all` after edits.\n"
            f"3. Build accepted work with `/uiplan-implement {slug}`."
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
            clean_tail, paradigm = _extract_flag_value(tail, "--paradigm")
            out = _run_plan_tool(
                "uipath_plan_uiplan_new",
                {"title": clean_tail, "intent": clean_tail, "paradigm": paradigm},
            )
        elif sub == "spec":
            if not tail:
                return f"Usage: /{command_name} <title> [--intent text]"
            clean_tail, paradigm = _extract_flag_value(tail, "--paradigm")
            title, intent = _maybe_split_natural_spec_request(clean_tail)
            out = _run_plan_tool(
                "uipath_plan_spec_new",
                {"title": title, "intent": intent, "paradigm": paradigm},
            )
        elif sub == "plan":
            if not tail:
                return f"Usage: /{command_name} <slug>"
            clean_tail, paradigm = _extract_flag_value(tail, "--paradigm")
            out = _run_plan_tool(
                "uipath_plan_plan_new",
                {"slug": clean_tail.strip(), "paradigm": paradigm},
            )
        elif sub == "tasks":
            if not tail:
                return f"Usage: /{command_name} <slug>"
            clean_tail, paradigm = _extract_flag_value(tail, "--paradigm")
            out = _run_plan_tool(
                "uipath_plan_tasks_new",
                {"slug": clean_tail.strip(), "paradigm": paradigm},
            )
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
        elif sub == "implement":
            bits = tail.split()
            if not bits:
                return f"Usage: /{command_name} <slug> [--run-to-completion|--yes]"
            run_to_completion = any(
                bit in {"--run-to-completion", "--yes", "--no-stop", "--auto"}
                for bit in bits
            )
            slug_bits = [bit for bit in bits if not bit.startswith("--")]
            if not slug_bits:
                return f"Usage: /{command_name} <slug> [--run-to-completion|--yes]"
            slug = slug_bits[0].strip()
            out = _run_plan_tool(
                "uipath_plan_review",
                {"slug": slug, "stage": "all"},
            )
            return _format_implement_handoff(
                slug,
                out,
                run_to_completion=run_to_completion,
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
        "  /uiplan-spec <title> [--intent text] [--paradigm value] — create folder + spec.md\n"
        "  /uiplan-plan <plan-id> [--paradigm value]               — write plan.md (after spec)\n"
        "  /uiplan-tasks <plan-id> [--paradigm value]              — write tasks.md (after plan)\n"
        "  /uiplan-review <plan-id> [all|spec|plan|tasks]\n"
        "  /uiplan-implement <plan-id> [--run-to-completion|--yes] — build accepted local tasks\n"
        "Backwards-compatible dispatcher: /uiplan <full|ground|spec|plan|tasks|review|implement> ...\n"
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
        name="uiplan-implement",
        description="UiPlan implement: uipath_plan_review(all) preflight, then hand off to uiplan-implement skill flow.",
    )
    def uiplan_implement_command(*parts: str) -> str:
        return _dispatch_uiplan(
            "implement", " ".join(parts).strip(), command_name="uiplan-implement"
        )

    @register_command(
        registry,
        name="uiplan",
        description=(
            "UiPlan: spec.md + plan.md + tasks.md under .cursor/plans/<date-slug>/ "
            "(ground -> spec -> plan -> tasks -> review). Prefer first-class "
            "commands: /uiplan-ground, /uiplan-spec, /uiplan-plan, "
            "/uiplan-tasks, /uiplan-review, /uiplan-full, /uiplan-implement."
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
