"""Pre-demo smoke check for the uipath-builder-agent chat pipeline.

Verifies the three regressions that silently broke the previous demo:

1. Intent classification routes questions and status checks to QUESTION and
   build phrases to BUILD / AMBIGUOUS.
2. ``run_uip_command`` short-circuits hallucinated MCP verbs (``design-propose``
   etc.) with a redirect to the real MCP tool, without spawning a subprocess.
3. The design-gate store round-trips: propose -> has_approved is False ->
   approve -> has_approved becomes True.

Run it before recording a demo:

    python scripts/smoke_chat_pipeline.py

Exit code 0 + ``SMOKE OK`` means the chat pipeline is healthy. Any failure
prints a short diagnostic and returns non-zero; do NOT record on failure.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


def _check_classifier() -> list[str]:
    from uipath_claude.query.intent_classifier import IntentType, classify_intent

    cases: list[tuple[str, IntentType]] = [
        ("what's coreipc?", IntentType.QUESTION),
        ("tell me about orchestrator", IntentType.QUESTION),
        ("did you create the project?", IntentType.QUESTION),
        ("have you built the workflow?", IntentType.QUESTION),
        ("was the project created?", IntentType.QUESTION),
        ("build an invoice processor", IntentType.BUILD),
        ("create the InvoiceIntake_Demo project", IntentType.BUILD),
    ]
    failures: list[str] = []
    for text, expected in cases:
        actual, reason = classify_intent(text)
        if actual is not expected:
            failures.append(
                f"classify_intent({text!r}) -> {actual.value} (reason={reason}); "
                f"expected {expected.value}"
            )
    return failures


def _check_denylist() -> list[str]:
    from uipath_claude.tools import skill_execution_tools

    failures: list[str] = []
    with patch.object(skill_execution_tools.subprocess, "run") as mock_run:
        for verb, mcp in (
            ("design-propose", "uipath_design_propose"),
            ("design-approve", "uipath_design_approve"),
        ):
            result = skill_execution_tools.run_uip_command.func(
                command="rpa",
                command_args=[verb, "--project-dir", "."],
            )
            if mock_run.call_count != 0:
                failures.append(
                    f"run_uip_command('{verb}') spawned subprocess "
                    f"(expected short-circuit)"
                )
            if mcp not in result:
                failures.append(
                    f"run_uip_command('{verb}') result missing redirect to "
                    f"'{mcp}': {result[:160]}"
                )
    return failures


def _check_design_store() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        store_path = Path(tmp) / "design_proposals.json"
        project_dir = Path(tmp) / "proj"
        project_dir.mkdir()
        env_patch = {
            "UIPATH_DESIGN_STORE_PATH": str(store_path),
            "UIPATH_DESIGN_APPROVAL_ENABLED": "1",
        }
        with patch.dict(os.environ, env_patch, clear=False):
            from uipath_claude.tools import design_store

            design_store.reset(in_memory_only=True)
            if design_store.has_approved(str(project_dir)):
                failures.append(
                    "design_store.has_approved returned True on a fresh project"
                )
            proposal, _warnings = design_store.propose(
                project_dir=str(project_dir),
                title="smoke",
                summary="smoke summary",
                body="smoke body",
            )
            if design_store.has_approved(str(project_dir)):
                failures.append(
                    "design_store.has_approved returned True after propose only"
                )
            design_store.approve(proposal.design_id)
            if not design_store.has_approved(str(project_dir)):
                failures.append(
                    "design_store.has_approved returned False after approve"
                )
            design_store.reset(in_memory_only=True)
    return failures


def _check_xaml_tools() -> list[str]:
    """Smoke-check the XAML authoring tool: import, render, validate."""
    failures: list[str] = []
    try:
        from uipath_claude.tools.xaml_tools import (
            create_xaml_workflow,
            render_xaml_workflow,
            validate_xaml,
            validate_xaml_text,
        )
    except Exception as exc:
        failures.append(f"import xaml_tools failed: {type(exc).__name__}: {exc}")
        return failures

    try:
        xaml = render_xaml_workflow(
            relative_path="Workflows/Smoke.xaml",
            arguments=[{"name": "in_FilePath", "direction": "In", "type": "x:String"}],
            variables=[{"name": "rawText", "type": "x:String"}],
            body=[
                {"kind": "LogMessage", "message_expr": '"smoke"'},
                {
                    "kind": "Assign",
                    "to": "rawText",
                    "value_expr": '""',
                },
            ],
        )
    except Exception as exc:
        failures.append(f"render_xaml_workflow raised {type(exc).__name__}: {exc}")
        return failures

    issues = validate_xaml_text(xaml, relative_path="Workflows/Smoke.xaml")
    errs = [i for i in issues if i.level == "error"]
    if errs:
        failures.append(
            "validate_xaml_text reported errors on canonical render: "
            + "; ".join(i.message for i in errs)
        )

    # Confirm tools are @tool-wrapped and exported from skill_execution_tools.
    from uipath_claude.tools.skill_execution_tools import get_skill_execution_tools

    tool_names = {getattr(t, "name", getattr(t, "__name__", "?")) for t in get_skill_execution_tools()}
    for expected in ("create_xaml_workflow", "validate_xaml"):
        if expected not in tool_names:
            failures.append(
                f"{expected} is not exported from get_skill_execution_tools"
            )
    return failures


def main() -> int:
    all_failures: list[str] = []
    for label, fn in (
        ("classifier", _check_classifier),
        ("uip-denylist", _check_denylist),
        ("design-store", _check_design_store),
        ("xaml-tools", _check_xaml_tools),
    ):
        try:
            failures = fn()
        except Exception as exc:
            all_failures.append(f"[{label}] raised {type(exc).__name__}: {exc}")
            continue
        for f in failures:
            all_failures.append(f"[{label}] {f}")

    if all_failures:
        print("SMOKE FAIL", file=sys.stderr)
        for line in all_failures:
            print("  - " + line, file=sys.stderr)
        return 1

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
