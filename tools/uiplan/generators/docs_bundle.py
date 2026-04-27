"""Materialize spec.md / plan.md / tasks.md from the UiPlan kit templates."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from tools.uiplan.paradigms import (
    build_loop_block,
    cli_family,
    code_structure_block,
    deploy_gate,
    normalize_paradigm,
    paradigm_task_blocks,
    stack_line,
)
from tools.uiplan.scaffold.project_kind import detect_paradigm

_SPECS = ("_spec-template.md", "spec.md")
_PLANS = ("_plan-template.md", "plan.md")
_TASKS = ("_tasks-template.md", "tasks.md")


def default_kit_dir(repo_root: Path) -> Path:
    return repo_root / "templates" / "uiplan"


def _slug_title(slug: str) -> str:
    cleaned = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug)
    return cleaned.replace("-", " ").strip().title() or slug


def _default_mapping(plan_slug: str, paradigm: str) -> dict[str, str]:
    today = dt.date.today().isoformat()
    title = _slug_title(plan_slug)
    normalized = normalize_paradigm(paradigm)
    return {
        "TITLE": title,
        "DATE": today,
        "FOLDER_NAME": plan_slug,
        "INTENT": f"UiPlan bundle for `{plan_slug}` (fill from product brief).",
        "GROUNDING_CITATIONS": "_Grounding to be filled after `uipath_plan_ground`._",
        "GROUNDING_CONTEXT": "_Run `uipath_plan_ground` or paste grounding excerpts here._",
        "SOURCE_ROUTING_SNIPPET": (
            "- `uipath_library_search` / `uipath_library_lookup` first\n"
            "- `query_uipath_docs` / `[askai:...]` when library coverage is insufficient\n"
            "- `uipath_doc_get_activity` / `uipath_doc_list_packages` before naming activities\n"
        ),
        "PLANNER_HANDOFF": (
            "[skill:uipath-planner] [skill:uipath-rpa] [skill:uipath-agents] [skill:uipath-platform] "
            "[agent:uipath-project-discovery-agent] `.claude/rules/project-context.md` "
            "uipath_library_search uipath_library_lookup uipath_doc_get_activity"
        ),
        "WORKFLOW_SHAPE_BLOCK": (
            "_Name per-project workflow types (Sequence, Flowchart, State Machine, Long Running) "
            "for each `.xaml` entry in `plan.md`._"
        ),
        "LOGGING_VERIFICATION_BLOCK": (
            "`LogMessage` with correlation id per phase; smoke run; assert expected substrings in "
            "robot/job logs."
        ),
        "PLANNER_TASKS": (
            "Re-read `[skill:uipath-planner]` routing in `plan.md` and align `tasks.md` execution order."
        ),
        "SUMMARY": "_One-paragraph summary._",
        "LANG_VERSION": "_e.g. C# / .NET 8 or Python 3.11+_",
        "DEPS": "_Primary packages / services._",
        "STORAGE": "_Queues, DBs, buckets._",
        "TESTING": "_Test framework / harness._",
        "TARGET_PLATFORM": "_Windows / cloud / etc._",
        "PROJECT_TYPE": "_rpa | coded-agent | solution | …_",
        "PARADIGM": normalized,
        "CLI_FAMILY": cli_family(normalized),
        "TARGET_STACK": stack_line(normalized),
        "DEPLOY_GATE": deploy_gate(normalized),
        "PERF": "_Latency / throughput goals._",
        "CONSTRAINTS": "_Org constraints (PII, regions, …)._",
        "SCALE": "_Volumes, tenants, robots._",
        "CONSTITUTION_CHECKLIST": "_Paste constitution gate table or bullets._",
        "SOURCE_TREE": "_Key folders touched (see framework/, ops/, …)._",
        "CODE_STRUCTURE_BLOCK": code_structure_block(normalized),
        "BUILD_LOOP_BLOCK": build_loop_block(normalized),
        "STRUCTURE_DECISION": "_Why this layout._",
        "COMPLEXITY_TABLE": "| Item | Why needed |\n| --- | --- |\n| | |",
        "US1_TITLE": "_User story 1_",
        "US1_BODY": "_As a … I want … so that …_",
        "US1_PRIORITY": "_P1 rationale._",
        "US1_TEST": "_How to verify independently._",
        "US1_GIVEN_1": "_context_",
        "US1_WHEN_1": "_action_",
        "US1_THEN_1": "_outcome_",
        "US2_TITLE": "_User story 2_",
        "US2_BODY": "_…_",
        "US2_PRIORITY": "_P2 rationale._",
        "US2_TEST": "_…_",
        "US2_GIVEN_1": "_…_",
        "US2_WHEN_1": "_…_",
        "US2_THEN_1": "_…_",
        "EDGE_1": "_Edge case._",
        "FR_001": "_requirement 1_",
        "FR_002": "_requirement 2_",
        "FR_003": "_requirement 3_",
        "ENTITY_1": "_Entity_",
        "ENTITY_1_DESC": "_Description._",
        "SC_001": "_Measurable outcome._",
        "ASSUMPTION_1": "_Assumption._",
        "BUILD_ENTRYPOINT": "`tasks.md` after review passes and the bundle is accepted.",
        "IMPLEMENTATION_SCOPE": "_Files/projects/services the build may change._",
        "BUILD_COMMAND": (
            f"`/uiplan-implement {plan_slug}` after review passes and the bundle "
            "is accepted. Use `scaffold-code` only for optional local "
            "runtime/adaptor checks."
        ),
        "QUALITY_GATES": "restore -> analyze -> test -> pack; deploy only with explicit approval.",
        "T001": (
            "Confirm project type from `plan.md` / repo descriptors (`project.json`, `solution.uipx`, "
            "`pyproject.toml`); cite `[skill:uipath-planner]` and `[agent:uipath-project-discovery-agent]`; "
            "record Studio/CLI versions in `docs/` notes."
        ),
        "T002": (
            "Create only directories/files listed in `plan.md` **Structure Decision** (mirror "
            "`projects/` / `tests/` paths); no speculative scaffolding."
        ),
        "US1_GOAL": "_Story goal._",
        "US1_IND_TEST": "_Independent test description._",
        "T010_TEST": (
            "Add failing automated test at `tests/test_us1_placeholder.py` (or `Tests/` per paradigm); "
            "run `uv run pytest tests/test_us1_placeholder.py -q` (or `uipcli test run -a <projectKey> .`); "
            "**Runtime evidence**: pytest JUnit or console log under `TestResults/`."
        ),
        "T011_IMPL": (
            "Implement US1 at the concrete artifact paths in `plan.md` (e.g. `projects/Process/Main.xaml` "
            "or `main.py`); use `[skill:uipath-rpa]` / `[skill:uipath-agents]` per paradigm; "
            "`uipath_library_search` + `uipath_library_lookup` and `uipath_doc_get_activity` before naming "
            "activities; **Verification**: `uipcli package analyze --resultPath out/analyze.json` or "
            "`uv run pytest`; **Runtime evidence**: `out/analyze.json` or pytest report + correlation id "
            "in `LogMessage` smoke logs; personal workspace default; Production requires explicit approval."
        ),
        "PARADIGM_TASK_BLOCKS": paradigm_task_blocks(normalized),
        "T020": "_Polish / docs / telemetry; deploy remains approval-required via docs/ORCHESTRATOR_DEPLOYMENT.md._",
        "DEPENDENCIES_TEXT": "_Story B may start after foundation; otherwise parallel._",
    }


def _apply_placeholders(template: str, mapping: dict[str, str]) -> str:
    out = template
    for key, value in mapping.items():
        out = out.replace("{{" + key + "}}", value)
    return out


def _copy_one(src: Path, dest: Path, mapping: dict[str, str]) -> None:
    tpl = src.read_text(encoding="utf-8")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_apply_placeholders(tpl, mapping), encoding="utf-8", newline="\n")


def generate_docs_bundle(
    *,
    repo_root: Path,
    plan_slug: str,
    output_dir: Path,
    kit_dir: Path | None = None,
    extra_mapping: dict[str, str] | None = None,
    paradigm: str | None = None,
) -> None:
    """Write ``spec.md``, ``plan.md``, and ``tasks.md`` under *output_dir*."""
    kit = kit_dir or default_kit_dir(repo_root)
    detected = normalize_paradigm(paradigm) if paradigm else detect_paradigm(repo_root)
    mapping = _default_mapping(plan_slug, detected)
    if extra_mapping:
        mapping.update(extra_mapping)
    _copy_one(kit / _SPECS[0], output_dir / _SPECS[1], mapping)
    _copy_one(kit / _PLANS[0], output_dir / _PLANS[1], mapping)
    _copy_one(kit / _TASKS[0], output_dir / _TASKS[1], mapping)
