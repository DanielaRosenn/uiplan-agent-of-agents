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
            "Automation Cloud only; deploy to personal workspace or dev workspace first. "
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
            "`uipcli test run` -> `uipcli package pack` -> documented **smoke run** "
            "(job / `uip rpa run-file`) -> **log assertions** -> optional `uipcli package deploy`\n"
            "- Analyzer gate: stop on any `analyze` errors.\n"
        )
    if paradigm == "solution":
        return (
            "- CLI family: `uipcli` (`solution` verbs)\n"
            "- Build loop: `uipcli solution restore` -> `uipcli solution analyze` -> "
            "`uipcli solution pack` -> `uipcli solution upload-package` -> "
            "documented **smoke run** per sub-project -> **log assertions** -> "
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
        "- [ ] T010 [P] [US1] Add or refine failing tests for the first story at explicit paths from "
        "`plan.md` (for example `tests/test_us1.py` or project test workflows); run the declared test "
        "command and store runtime evidence under `TestResults/`.\n"
    )
    if paradigm == "modern-rpa":
        return base + (
            "- [ ] T011A [US1] Implement the primary RPA workflow entry in `Main.xaml` or a named "
            "`Workflows/*.xaml` artifact from `plan.md` using activities resolved via "
            "`uipath_doc_get_activity`, `uipath_library_search`, and `uipath_library_lookup`; "
            "verify with `uipcli package analyze --resultPath out/analyze-rpa.json`.\n"
            "- [ ] T011B [US1] Implement required queue/asset/config updates in `project.json`, "
            "`Data/*.json`, or binding artifacts named in `plan.md`; verify with tests plus analyze and "
            "record runtime evidence paths.\n"
        )
    if paradigm == "coded-agent":
        return base + (
            "- [ ] T011A [US1] Implement graph/node behavior in `langgraph.json` and agent source files "
            "(for example `main.py` or `agent.py`) using `[skill:uipath-agents]`; verify with "
            "`uv run pytest` and `uipath run` fixture smoke where applicable.\n"
            "- [ ] T011B [US1] Implement host invocation schema and response handling in the artifact "
            "named by `plan.md`; verify request/response contract tests and runtime evidence.\n"
        )
    if paradigm == "solution":
        return base + (
            "- [ ] T011A [US1] Implement Dispatcher/intake surface in "
            "`projects/<Dispatcher>/Main.xaml` using the selected starter template and concrete "
            "connector/queue activities resolved through `uipath_doc_get_activity` plus "
            "`uipath_library_search`/`uipath_library_lookup`; `[skill:uipath-rpa]`; verify with "
            "`uipcli package analyze projects/<Dispatcher>/project.json --resultPath out/analyze-dispatcher.json`.\n"
            "- [ ] T011B [US1] Implement analyzer host surface in "
            "`projects/<AnalyzerRunner>/Main.xaml` (Sequence/Flowchart/Long Running as declared) with "
            "queue transitions, correlation IDs, and agent invocation boundary; "
            "`uipath_library_search`/`uipath_library_lookup`; `[skill:uipath-rpa]` + "
            "`[skill:uipath-agents]`; include `projects/<AnalyzerAgent>/langgraph.json`, entrypoint, and "
            "local run/test command (`uipath run` or `uv run pytest`) for the invocation contract; "
            "verify analyze + fixture tests.\n"
            "- [ ] T011C [US1] Implement coded agent surface in `projects/<AnalyzerAgent>/langgraph.json` "
            "and source nodes under `projects/<AnalyzerAgent>/src/` with explicit graph entrypoint plus "
            "request/response schema; `[skill:uipath-agents]`; verify `uv run pytest` and runtime "
            "classification fixtures.\n"
            "- [ ] T011D [US1] Implement human review surface in "
            "`projects/<HumanReview>/flows/<HumanReview>.flow` (or BPMN path from `plan.md`) with HITL "
            "decision, timeout, and linked queue updates; verify Flow validation and "
            "story-level tests; `uipath_library_search`/`uipath_library_lookup`; "
            "`[skill:uipath-maestro-flow]`.\n"
            "- [ ] T011E [US1] Run solution-level gates on `solution.uipx`: "
            "`uipcli solution restore` -> `uipcli solution analyze --resultPath out/solution-analyze.json` "
            "-> tests -> `uipcli solution pack`; include impacted workflow paths under `projects/`; "
            "`[skill:uipath-platform]`; capture runtime evidence paths and deploy gate notes.\n"
        )
    if paradigm == "coded-app":
        return base + (
            "- [ ] T011A [US1] Implement app/action source in `src/` and update `app.config.json` / "
            "`action-schema.json` as defined by `plan.md`; verify with app tests and `uip codedapp build`.\n"
            "- [ ] T011B [US1] Implement integration/binding updates and smoke validation for the app "
            "surface; capture runtime evidence paths and deployment handoff constraints.\n"
        )
    if paradigm == "case-management":
        return base + (
            "- [ ] T011A [US1] Implement case model changes in `caseplan.json` and related artifacts "
            "from `plan.md`; verify with case schema checks and `uip case` validation commands.\n"
            "- [ ] T011B [US1] Implement stage/task transitions and evidence outputs for the first story; "
            "verify with tests and captured runtime logs.\n"
        )
    if paradigm == "maestro-flow":
        return base + (
            "- [ ] T011A [US1] Implement flow updates in `.flow` / `.bpmn` artifact paths from `plan.md` "
            "with trigger and mapping updates; verify with Studio Web/`uip` validation output.\n"
            "- [ ] T011B [US1] Implement downstream integration and status updates tied to the flow "
            "surface; verify story tests and runtime evidence logs.\n"
        )
    if paradigm == "api-workflow":
        return base + (
            "- [ ] T011A [US1] Implement API workflow source (`.xaml` and descriptor files) from `plan.md`; "
            "resolve activities via `uipath_doc_get_activity`; verify with `uipcli package analyze`.\n"
            "- [ ] T011B [US1] Implement request/response schema handling and failure-path tests for the "
            "API workflow surface; capture analyzer/test evidence paths.\n"
        )
    if paradigm == "library":
        return base + (
            "- [ ] T011A [US1] Implement library activity/code surface in declared source files and "
            "tests; verify with `uipcli package analyze` + `uipcli package pack` evidence.\n"
        )
    if paradigm == "tests":
        return base + (
            "- [ ] T011A [US1] Implement test project source and fixtures defined in `plan.md`; verify "
            "with `uipcli test run` and runtime result artifacts.\n"
        )
    return base + (
        "- [ ] T011A [US1] Implement first-story artifact updates directly from `plan.md` project "
        "surfaces and verify with the declared paradigm build/test commands.\n"
    )
