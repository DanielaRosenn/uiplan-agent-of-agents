"""Tests for /uiplan-* slash commands and MCP tool dispatch."""
from __future__ import annotations

import pytest

from uipath_claude.commands.registry import CommandRegistry
from uipath_claude.commands.uiplan import register_uiplan_command


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> tuple[CommandRegistry, list[tuple[str, dict]]]:
    calls: list[tuple[str, dict]] = []

    def fake_run_plan_tool(name: str, arguments: dict) -> dict:
        calls.append((name, arguments))
        if name == "uipath_plan_ground":
            return {
                "status": "ok",
                "topic": arguments.get("topic", ""),
                "matched_skills": [{"name": "uiplan"}],
            }
        if name == "uipath_plan_spec_new":
            return {
                "status": "ok",
                "slug": "my-feature",
                "relative": ".cursor\\plans\\2026-04-26-my-feature",
            }
        if name == "uipath_plan_plan_new":
            return {"status": "ok", "slug": arguments["slug"], "path": "plan.md"}
        if name == "uipath_plan_tasks_new":
            return {"status": "ok", "slug": arguments["slug"], "path": "tasks.md"}
        if name == "uipath_plan_review":
            return {
                "status": "ok",
                "ok": True,
                "findings": [],
                "next_action": "accept",
                "acceptance_ready": True,
                "meta_status": "accepted",
                "routing_metadata": {"slug": arguments.get("slug", ""), "acceptance_ready": True},
            }
        if name == "uipath_plan_uiplan_new":
            return {
                "status": "ok",
                "slug": "one-shot-title",
                "folder": ".cursor\\plans\\2026-04-26-one-shot-title",
                "review": {"status": "ok", "ok": True, "findings": []},
            }
        return {"status": "ok"}

    monkeypatch.setattr(
        "uipath_claude.commands.uiplan._run_plan_tool",
        fake_run_plan_tool,
    )
    reg = CommandRegistry()
    register_uiplan_command(reg)
    return reg, calls


def test_uiplan_commands_registered() -> None:
    reg = CommandRegistry()
    register_uiplan_command(reg)
    for name in (
        "uiplan",
        "uiplan-ground",
        "uiplan-spec",
        "uiplan-plan",
        "uiplan-tasks",
        "uiplan-review",
        "uiplan-full",
        "uiplan-implement",
    ):
        assert name in reg.commands


def test_uiplan_ground_dispatches(registry: tuple) -> None:
    reg, calls = registry
    out = reg.execute("uiplan-ground", "queues", "and", "assets")
    assert calls == [("uipath_plan_ground", {"topic": "queues and assets"})]
    assert "UiPlan grounding complete" in out
    assert "`uiplan`" in out


def test_uiplan_spec_title_and_intent(registry: tuple) -> None:
    reg, calls = registry
    out = reg.execute(
        "uiplan-spec",
        "My",
        "Feature",
        "--intent",
        "harden",
        "retries",
    )
    assert calls == [
        (
            "uipath_plan_spec_new",
            {"title": "My Feature", "intent": "harden retries", "paradigm": None},
        ),
    ]
    assert "UiPlan spec created" in out
    assert "Plan id: `my-feature`" in out
    assert "Run `/uiplan-plan my-feature`" in out
    assert "Copy/paste" not in out
    assert "/uiplan-plan my-feature" in out


def test_uiplan_spec_natural_pdd_request_uses_short_title(registry: tuple) -> None:
    reg, calls = registry
    out = reg.execute(
        "uiplan-spec",
        "zipMailBox",
        "can",
        "you",
        "base",
        "the",
        "spec",
        "on",
        "this",
        "pdd?",
        r"C:\work\pdd.md",
    )
    assert calls == [
        (
            "uipath_plan_spec_new",
            {
                "title": "zipMailBox",
                "intent": r"zipMailBox can you base the spec on this pdd? C:\work\pdd.md",
                "paradigm": None,
            },
        ),
    ]
    assert "UiPlan spec created" in out
    assert "grounding_pack" not in out


def test_uiplan_plan_tasks_review_full(registry: tuple) -> None:
    reg, calls = registry
    reg.execute("uiplan-plan", "2026-04-26-my-slug")
    reg.execute("uiplan-tasks", "2026-04-26-my-slug")
    reg.execute("uiplan-review", "2026-04-26-my-slug", "plan")
    out = reg.execute("uiplan-full", "One shot title")
    assert calls == [
        ("uipath_plan_plan_new", {"slug": "2026-04-26-my-slug", "paradigm": None}),
        ("uipath_plan_tasks_new", {"slug": "2026-04-26-my-slug", "paradigm": None}),
        (
            "uipath_plan_review",
            {"slug": "2026-04-26-my-slug", "stage": "plan"},
        ),
        (
            "uipath_plan_uiplan_new",
            {"title": "One shot title", "intent": "One shot title", "paradigm": None},
        ),
    ]
    assert "UiPlan bundle created" in out
    assert "Review/edit next" in out
    assert "Copy/paste" not in out
    assert "Plan id:" in out
    assert "/uiplan-implement" in out


def test_uiplan_plan_keeps_full_folder_path(registry: tuple) -> None:
    reg, calls = registry
    folder = (
        r"C:\Users\DanielaRosenstein\projects\uipath-builder-agent"
        r"\.cursor\plans\2026-04-27-zip-email-automation-uiplan-build"
    )
    out = reg.execute("uiplan-plan", folder)
    assert calls == [("uipath_plan_plan_new", {"slug": folder, "paradigm": None})]
    assert "UiPlan plan created" in out
    assert "Copy/paste" not in out
    assert "/uiplan-tasks" not in out


def test_uiplan_review_defaults_stage_all(registry: tuple) -> None:
    reg, calls = registry
    reg.execute("uiplan-review", "slug-only")
    assert calls[-1] == (
        "uipath_plan_review",
        {"slug": "slug-only", "stage": "all"},
    )


def test_uiplan_dispatcher_subcommands(registry: tuple) -> None:
    reg, calls = registry
    reg.execute("uiplan", "ground", "topic", "here")
    assert calls[-1] == ("uipath_plan_ground", {"topic": "topic here"})


def test_uiplan_dispatcher_defaults_to_full(registry: tuple) -> None:
    reg, calls = registry
    reg.execute("uiplan", "implicit", "full", "title")
    assert calls[-1] == (
        "uipath_plan_uiplan_new",
        {"title": "implicit full title", "intent": "implicit full title", "paradigm": None},
    )


def test_uiplan_usage_when_empty(registry: tuple) -> None:
    reg, calls = registry
    out = reg.execute("uiplan")
    assert "/uiplan-spec" in out
    assert "/uiplan-full" in out
    assert "/uiplan-implement" in out
    assert not calls


def test_uiplan_paradigm_flag_forwarded(registry: tuple) -> None:
    reg, calls = registry
    reg.execute("uiplan-spec", "Invoice Bot", "--paradigm", "coded-agent")
    assert calls[-1] == (
        "uipath_plan_spec_new",
        {"title": "Invoice Bot", "intent": "Invoice Bot", "paradigm": "coded-agent"},
    )


def test_uiplan_implement_preflight(registry: tuple) -> None:
    reg, calls = registry
    out = reg.execute("uiplan-implement", "my-2026-04-26-slug")
    assert calls == [
        ("uipath_plan_review", {"slug": "my-2026-04-26-slug", "stage": "all"}),
    ]
    assert "UiPlan implement (preflight)" in out
    assert "pass" in out


def test_uiplan_implement_run_to_completion_handoff(registry: tuple) -> None:
    reg, calls = registry
    out = reg.execute("uiplan-implement", "my-2026-04-26-slug", "--yes")
    assert calls == [
        ("uipath_plan_review", {"slug": "my-2026-04-26-slug", "stage": "all"}),
    ]
    assert "Run-to-completion mode is enabled" in out
    assert "without asking for confirmation between tasks" in out
    assert "plan alignment, source reality snapshot" in out
    assert "artifact completeness gate" in out
    assert "behavior tests" in out
    assert "spec compliance review" in out
    assert "code quality review" in out
    assert "completion ledger" in out
    assert "scaffold-only progress" in out
    assert "Do not deploy or publish without explicit user approval" in out


def test_uiplan_implement_run_to_completion_warns_when_not_accepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict]] = []

    def fake_run_plan_tool(name: str, arguments: dict) -> dict:
        calls.append((name, arguments))
        return {
            "ok": True,
            "findings": [],
            "next_action": "accept",
            "acceptance_ready": False,
            "meta_status": "draft",
        }

    monkeypatch.setattr(
        "uipath_claude.commands.uiplan._run_plan_tool",
        fake_run_plan_tool,
    )
    reg = CommandRegistry()
    register_uiplan_command(reg)
    out = reg.execute("uiplan-implement", "draft-slug", "--yes")
    assert "Run-to-completion blocked" in out
    assert "uipath_plan_accept" in out
