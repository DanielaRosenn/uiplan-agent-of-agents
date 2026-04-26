"""Canonical UiPlan paradigm scaffolds shared by MCP and file-first CLI."""

from __future__ import annotations

from typing import Final

KNOWN_PARADIGMS: Final[tuple[str, ...]] = (
    "modern-rpa",
    "coded-automation",
    "coded-agent",
    "solution",
    "maestro-flow",
    "coded-app",
    "api-workflow",
    "case-management",
    "library",
    "tests",
    "unknown",
)

_ALIASES: Final[dict[str, str]] = {
    "rpa": "modern-rpa",
    "modern": "modern-rpa",
    "modern-rpa": "modern-rpa",
    "coded-automation": "coded-automation",
    "coded_automation": "coded-automation",
    "coded-agent": "coded-agent",
    "agent": "coded-agent",
    "solution": "solution",
    "maestro": "maestro-flow",
    "flow": "maestro-flow",
    "maestro-flow": "maestro-flow",
    "coded-app": "coded-app",
    "codedapp": "coded-app",
    "api-workflow": "api-workflow",
    "apiworkflow": "api-workflow",
    "case": "case-management",
    "case-management": "case-management",
    "library": "library",
    "test": "tests",
    "tests": "tests",
    "unknown": "unknown",
    "mixed": "unknown",
}


def normalize_paradigm(project_type: str | None) -> str:
    value = (project_type or "").strip().lower().replace(" ", "-")
    return _ALIASES.get(value, "unknown")


def infer_paradigm_from_files(
    *,
    has_project_json: bool,
    has_xaml: bool,
    has_pyproject: bool,
    has_agent_marker: bool,
    has_solution: bool,
    has_coded_app: bool,
    has_case_plan: bool,
    has_api_workflow: bool,
    has_maestro_file: bool,
) -> str:
    if has_case_plan:
        return "case-management"
    if has_solution:
        return "solution"
    if has_coded_app:
        return "coded-app"
    if has_api_workflow:
        return "api-workflow"
    if has_maestro_file:
        return "maestro-flow"
    if has_pyproject and has_agent_marker:
        return "coded-agent"
    if has_project_json and has_xaml:
        return "modern-rpa"
    if has_project_json:
        return "coded-automation"
    return "unknown"


def cli_family(paradigm: str) -> str:
    if paradigm in ("modern-rpa", "coded-automation", "solution", "api-workflow", "library", "tests"):
        return "uipcli"
    if paradigm == "coded-agent":
        return "uipath"
    if paradigm in ("maestro-flow", "coded-app", "case-management"):
        return "uip"
    return "uipcli / uipath / uip (confirm with project discovery)"


def stack_line(paradigm: str) -> str:
    if paradigm in ("modern-rpa", "coded-automation", "library", "tests", "solution", "api-workflow"):
        return "Modern UiPath stack: C# expressions, Windows target, .NET 8."
    if paradigm == "coded-agent":
        return "Python coded agent stack: Python 3.11+, uv-managed dependencies."
    if paradigm in ("maestro-flow", "coded-app", "case-management"):
        return "Studio Web / cloud-first UiPath stack with CLI support."
    return "Confirm stack in project-context before implementation."


def deploy_gate(paradigm: str) -> str:
    if paradigm == "solution":
        return (
            "Automation Cloud only; deploy to personal/dev workspace first. "
            "Never deploy to Production without explicit human approval."
        )
    return (
        "Deploy only after explicit approval, defaulting to personal workspace. "
        "Never deploy to Production from assistant sessions."
    )


def code_structure_block(paradigm: str) -> str:
    if paradigm == "modern-rpa":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  project.json\n"
            "  Main.xaml\n"
            "  Framework/\n"
            "  Data/\n"
            "  Tests/\n"
            "  uipath.policy.default.json\n"
            "```\n"
            "- Descriptor files: `project.json`, `Main.xaml`, `uipath.policy.default.json`\n"
            "- Expected package artifact: `<Org>.<Domain>.<Process>.<version>.nupkg`\n"
        )
    if paradigm == "coded-automation":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  project.json\n"
            "  Workflows/\n"
            "    *.cs\n"
            "  Tests/\n"
            "    *.cs\n"
            "  uipath.policy.default.json\n"
            "```\n"
            "- Descriptor files: `project.json`, C# workflow sources, test project files\n"
            "- Expected package artifact: `<Org>.<Domain>.<Process>.<version>.nupkg`\n"
        )
    if paradigm == "coded-agent":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  pyproject.toml\n"
            "  uv.lock\n"
            "  langgraph.json | agent_framework.json | llama_index.json\n"
            "  main.py | agent.py\n"
            "  .uipath/\n"
            "  uipath.json\n"
            "  bindings.json\n"
            "  .env.example\n"
            "  tests/\n"
            "  evals/\n"
            "```\n"
            "- Descriptor files: `pyproject.toml`, graph/framework descriptor, `uipath.json`\n"
            "- Expected package artifact: `<Org>.<Domain>.<Process>.<version>.nupkg`\n"
        )
    if paradigm == "solution":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  solution.uipx\n"
            "  projects/\n"
            "    Process.Alpha/\n"
            "    Agent.Beta/\n"
            "    Library.Shared/\n"
            "  bindings/\n"
            "    dev.json\n"
            "    test.json\n"
            "    prod.json\n"
            "```\n"
            "- Descriptor files: `solution.uipx`, `bindings/*.json`\n"
            "- Expected package artifact: solution package or project `.nupkg` outputs\n"
        )
    if paradigm == "maestro-flow":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  flows/\n"
            "    *.flow | *.bpmn\n"
            "  solution.uipx (optional)\n"
            "```\n"
            "- Descriptor files: `.flow`/`.bpmn`, optional `solution.uipx`\n"
            "- Expected package artifact: solution-managed package where applicable\n"
        )
    if paradigm == "coded-app":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  app.config.json\n"
            "  action-schema.json\n"
            "  src/\n"
            "  package.json\n"
            "```\n"
            "- Descriptor files: `app.config.json`, `action-schema.json`\n"
            "- Expected package artifact: app bundle from coded-app build/deploy flow\n"
        )
    if paradigm == "api-workflow":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  api-workflow.json\n"
            "  project.json (if included in solution)\n"
            "  Workflows/\n"
            "```\n"
            "- Descriptor files: `api-workflow.json`\n"
            "- Expected package artifact: `<Org>.<Domain>.<Process>.<version>.nupkg`\n"
        )
    if paradigm == "case-management":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  caseplan.json\n"
            "  docs/\n"
            "```\n"
            "- Descriptor files: `caseplan.json`\n"
            "- Expected artifact: case plan deployment package/config\n"
        )
    if paradigm == "library":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  project.json\n"
            "  Activities/\n"
            "  Tests/\n"
            "```\n"
            "- Descriptor files: `project.json` (Library type)\n"
            "- Expected package artifact: `<Org>.<Domain>.<Library>.<version>.nupkg`\n"
        )
    if paradigm == "tests":
        return (
            "```text\n"
            "<repo-root>/\n"
            "  Tests/\n"
            "    *.xaml | *.cs\n"
            "  project.json\n"
            "```\n"
            "- Descriptor files: test project descriptors and test assets\n"
            "- Expected artifact: test execution report (JUnit/JSON) and optional package\n"
        )
    return (
        "<!-- paradigm: unknown -->\n"
        "```text\n"
        "<repo-root>/\n"
        "  Confirm project structure with project discovery.\n"
        "```\n"
        "- Descriptor files: unknown, must be discovered before implementation.\n"
        "- Expected package artifact: unknown until paradigm is confirmed.\n"
    )


def build_loop_block(paradigm: str) -> str:
    if paradigm in ("modern-rpa", "coded-automation", "library", "tests"):
        return (
            "- CLI family: `uipcli`\n"
            "- Build loop: `uipcli package restore` -> `uipcli package analyze` -> "
            "`uipcli test run` -> `uipcli package pack` -> optional `uipcli package deploy`\n"
            "- Analyzer gate: stop on any `analyze` errors.\n"
        )
    if paradigm == "solution":
        return (
            "- CLI family: `uipcli` (`solution` verbs)\n"
            "- Build loop: `uipcli solution restore` -> `uipcli solution analyze` -> "
            "`uipcli solution pack` -> `uipcli solution upload-package` -> "
            "optional `uipcli solution deploy` / `deploy-activate`\n"
            "- Analyzer gate: stop on any `analyze` errors.\n"
        )
    if paradigm == "coded-agent":
        return (
            "- CLI family: `uipath`\n"
            "- Build loop: `uv sync` -> `uipath run` / `pytest` -> `uipath pack` -> "
            "optional `uipath publish` / `uipath deploy`\n"
            "- Analyzer/test gate: stop on failing tests or packaging errors.\n"
        )
    if paradigm == "maestro-flow":
        return (
            "- CLI family: `uip` (+ solution packaging when needed)\n"
            "- Build loop: validate flow in Studio Web -> sync via `uip` -> "
            "package/deploy via solution pipeline where applicable.\n"
            "- Gate: stop when flow validation or solution analyze fails.\n"
        )
    if paradigm == "coded-app":
        return (
            "- CLI family: `uip`\n"
            "- Build loop: `uip codedapp build` -> app tests/smoke -> "
            "optional `uip codedapp deploy` (approval required).\n"
            "- Gate: stop when build/smoke checks fail.\n"
        )
    if paradigm == "api-workflow":
        return (
            "- CLI family: `uipcli` (or solution commands)\n"
            "- Build loop: restore -> analyze -> test -> pack -> optional deploy.\n"
            "- Analyzer gate: stop on any `analyze` errors.\n"
        )
    if paradigm == "case-management":
        return (
            "- CLI family: `uip`\n"
            "- Build loop: validate `caseplan.json` -> `uip case` operations -> optional deploy.\n"
            "- Gate: stop when schema/validation checks fail.\n"
        )
    return (
        "- CLI family: unknown\n"
        "- Build loop: run project discovery before any build command.\n"
    )


def paradigm_task_blocks(paradigm: str) -> str:
    base = (
        "- [ ] T001 [P] [US1] Confirm paradigm and descriptor files from `plan.md`; "
        "cite `[skill:uipath-planner]` and `[agent:uipath-project-discovery-agent]`; "
        "verify by listing detected descriptors.\n"
        "- [ ] T002 [US1] Run documentation grounding (`uipath_library_lookup` and, when needed, "
        "`query_uipath_docs`) for every uncertain activity/SDK/CLI call; record citations in tasks.\n"
    )
    if paradigm == "modern-rpa":
        return base + (
            "- [ ] T010 [P] [US1] Add failing test in `Tests/InvoiceFlowTests.xaml`; "
            "verify with `uipcli test run`.\n"
            "- [ ] T011 [US1] Implement `Workflows/ProcessInvoice.xaml` using "
            "`[activity:UiPath.System.Activities:LogMessage]` and required package activities; "
            "verify analyze + tests are green.\n"
        )
    if paradigm == "coded-agent":
        return base + (
            "- [ ] T010 [P] [US1] Add failing test `tests/test_us1_flow.py`; run `uv run pytest tests/test_us1_flow.py`.\n"
            "- [ ] T011 [US1] Implement node logic in `main.py` or `agent.py` and update "
            "`langgraph.json|agent_framework.json`; verify with `uipath run` and pytest.\n"
        )
    if paradigm == "solution":
        return base + (
            "- [ ] T010 [P] [US1] Add binding validation test for `bindings/dev.json`; "
            "verify with `uipcli solution download-config` checks.\n"
            "- [ ] T011 [US1] Implement project changes under `projects/` and update binding keys; "
            "verify with `uipcli solution analyze` and `uipcli solution pack`.\n"
        )
    if paradigm == "coded-app":
        return base + (
            "- [ ] T010 [P] [US1] Add failing app action test for `src/actions/*.ts`; "
            "verify with project test runner.\n"
            "- [ ] T011 [US1] Implement `src/actions/` and `action-schema.json` updates; "
            "verify with `uip codedapp build` and smoke run.\n"
        )
    if paradigm == "case-management":
        return base + (
            "- [ ] T010 [P] [US1] Add validation checks for `caseplan.json` transitions.\n"
            "- [ ] T011 [US1] Implement case stages/tasks in `caseplan.json`; verify with `uip case` validation commands.\n"
        )
    if paradigm == "maestro-flow":
        return base + (
            "- [ ] T010 [P] [US1] Add validation scenario for `flows/*.flow|*.bpmn` in test notes.\n"
            "- [ ] T011 [US1] Implement flow updates and integration bindings; verify in Studio Web and sync.\n"
        )
    if paradigm == "api-workflow":
        return base + (
            "- [ ] T010 [P] [US1] Add failing API workflow test for request/response contract.\n"
            "- [ ] T011 [US1] Implement API workflow in `Workflows/` with `api-workflow.json` updates; "
            "verify analyze + tests.\n"
        )
    if paradigm == "library":
        return base + (
            "- [ ] T010 [P] [US1] Add failing library test in `Tests/`.\n"
            "- [ ] T011 [US1] Implement activity/library code in `Activities/`; verify pack output path.\n"
        )
    if paradigm == "tests":
        return base + (
            "- [ ] T010 [P] [US1] Add/refresh failing test set in `Tests/`.\n"
            "- [ ] T011 [US1] Implement minimal source changes required to make tests pass; "
            "verify JUnit/JSON output.\n"
        )
    return base + (
        "- [ ] T010 [P] [US1] Add failing test with exact path once paradigm is confirmed.\n"
        "- [ ] T011 [US1] Implement minimal fix using confirmed artifacts and CLI family.\n"
    )
