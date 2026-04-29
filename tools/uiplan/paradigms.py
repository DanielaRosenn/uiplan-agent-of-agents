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


def _story_visuals_block(paradigm: str) -> str:
    """Mini-diagrams (story flow + sequence + data/queue + activity stub) for embed in tasks."""
    return (
        "\n#### Story flow\n\n"
        "```mermaid\n"
        "flowchart LR\n"
        "  Trigger[Trigger] --> Workflow[Story workflow]\n"
        "  Workflow --> Decision{Outcome?}\n"
        "  Decision -- Success --> Done[Terminal success]\n"
        "  Decision -- Needs review --> HITL[Human review]\n"
        "  classDef start fill:#ECFDF5,stroke:#10B981,color:#065F46\n"
        "  classDef proc fill:#F1F5F9,stroke:#64748B,color:#0F172A\n"
        "  classDef dec fill:#FFFBEB,stroke:#F59E0B,color:#92400E\n"
        "  class Trigger start\n"
        "  class Workflow proc\n"
        "  class Decision dec\n"
        "  linkStyle default stroke:#94A3B8,stroke-width:1.5px\n"
        "```\n\n"
        "#### Workflow interaction\n\n"
        "```mermaid\n"
        "sequenceDiagram\n"
        "  autonumber\n"
        "  participant Trigger\n"
        "  participant Workflow\n"
        "  participant Queue\n"
        "  participant Reviewer\n"
        "  Trigger->>Workflow: invoke\n"
        "  Workflow->>Queue: write item (correlationId)\n"
        "  Workflow-->>Reviewer: request review (when needed)\n"
        "  Reviewer-->>Workflow: decision\n"
        "  Workflow-->>Trigger: outcome\n"
        "  %% classDef participant fill:#F1F5F9,stroke:#64748B,color:#0F172A\n"
        "```\n\n"
        "#### Data / queue contract\n\n"
        "```mermaid\n"
        "flowchart TB\n"
        "  Inputs[Inputs] --> IntakeQ[(Intake queue)]\n"
        "  IntakeQ --> Worker[Worker]\n"
        "  Worker --> ReviewQ[(Review queue)]\n"
        "  Worker --> Output[(Output sink)]\n"
        "  Worker --> Assets[Assets / bindings]\n"
        "  classDef data fill:#ECFEFF,stroke:#0891B2,color:#164E63\n"
        "  class IntakeQ,ReviewQ,Output,Assets data\n"
        "  linkStyle default stroke:#94A3B8,stroke-width:1.5px\n"
        "```\n\n"
    )


def paradigm_task_blocks(paradigm: str) -> str:
    visuals = _story_visuals_block(paradigm)
    base = (
        f"{visuals}"
        "- [ ] T010 [P] [US1] Add or refine failing tests for the first story at explicit paths from "
        "`plan.md` (for example `tests/test_us1.py` or project test workflows); run the declared test "
        "command and store runtime evidence under `TestResults/`. "
        "[skill:uipath-test] [library:uipath_library_search]\n"
    )
    if paradigm == "modern-rpa":
        return base + (
            "- [ ] T011A [US1] Scaffold the Studio project from `plan.md` Project Inventory using "
            "`uip rpa create-project --studio-dir <path>` with the chosen starter template "
            "(Dispatcher / Performer / Long Running / Sequence / Flowchart / State Machine). "
            "Record `project.json`, generated `Main.xaml`, and template provenance. "
            "[skill:uipath-rpa] [agent:uipath-project-discovery-agent] [subagent:explore]\n"
            "- [ ] T011B [US1] Implement the primary workflow body in `Main.xaml` (or named "
            "`Workflows/*.xaml`) using **UiPath activities** resolved through "
            "`uipath_doc_get_activity` + `uipath_library_search` / `uipath_library_lookup` "
            "(modern stack: C# expressions, Windows, .NET 8). For each activity row in `plan.md` "
            "Activity Inventory, wire inputs/outputs/connections and add a LogMessage with "
            "`correlationId`. Verify with `uipcli package analyze --resultPath out/analyze-rpa.json`. "
            "[skill:uipath-rpa] [library:uipath_doc_get_activity]\n"
            "- [ ] T011C [US1] Implement queue/asset/config wiring in `project.json`, `Data/*.json`, "
            "or `bindings/dev.json` per `plan.md` Bindings table. Verify with tests + analyze; record "
            "runtime evidence paths. [skill:uipath-platform] [library:uipath_library_lookup]\n"
        )
    if paradigm == "coded-agent":
        return base + (
            "- [ ] T011A [US1] Implement graph entry + nodes in `langgraph.json` and `main.py` (or "
            "`agent.py`) per `plan.md` Code Module Inventory. Use the UiPath LLM Gateway via "
            "`uipath_langchain.chat.UiPathChat`; declare request/response schema. Verify with "
            "`uv run pytest` and `uipath run` fixture. [skill:uipath-agents] "
            "[library:uipath_library_search] [askai:query_uipath_docs]\n"
            "- [ ] T011B [US1] Implement host invocation schema and response handling per "
            "`plan.md` Workflow Catalog; verify request/response contract tests and runtime evidence. "
            "[skill:uipath-agents] [subagent:generalPurpose]\n"
        )
    if paradigm == "solution":
        return base + (
            "- [ ] T011A [US1] Scaffold each Studio project listed in `plan.md` Project Inventory "
            "with `uip rpa create-project --studio-dir <path>` using the matched starter template "
            "(see [`templates/uiplan/_workflow-catalog.md`](../../templates/uiplan/_workflow-catalog.md)). "
            "For any named template, copy/export or scaffold it into `projects/<Project>/`, then read "
            "the copied workflows, config, arguments, variables, dependencies, and extension points "
            "before customization. Record `projects/<Project>/project.json`, generated "
            "`projects/<Project>/Main.xaml`, preserved runtime shape, and template provenance for each. "
            "[skill:uipath-rpa] [library:uipath_library_search] [subagent:explore]\n"
            "- [ ] T011B [US1] Implement Dispatcher/intake surface in `projects/<Dispatcher>/Main.xaml` "
            "inside the copied dispatcher host shell. Read/update `Data/Config.json`, `Process.xaml`, "
            "`Logical/*`, queue payload mapping, idempotency/cursor logic, connector boundary, and "
            "correlationId LogMessage using **UiPath activities** from `plan.md` Activity Inventory "
            "(resolved via `uipath_doc_get_activity`). Verify `uipcli package analyze "
            "projects/<Dispatcher>/project.json "
            "--resultPath out/analyze-dispatcher.json`. [skill:uipath-rpa] "
            "[library:uipath_doc_get_activity] [library:uipath_library_search]\n"
            "- [ ] T011C [US1] Implement AnalyzerRunner as a Long Running Workflow host in "
            "`projects/<AnalyzerRunner>/Main.xaml` using the copied/scaffolded template from "
            "`plan.md` Workflow Catalog. Read the template's wait/resume structure, then customize "
            "Get Queue Item, Invoke Coded Agent (host boundary; declare request/response schema), "
            "response mapping, Set Status/status transitions, timeout/error paths, and "
            "correlation-aware logging inside that shell. "
            "[skill:uipath-rpa] [skill:uipath-agents] [library:uipath_library_search]\n"
            "- [ ] T011D [US1] Implement coded agent in `projects/<AnalyzerAgent>/langgraph.json` and "
            "graph nodes under `projects/<AnalyzerAgent>/src/`; declare request/response schema; verify "
            "with `uv run pytest` plus local agent run evidence. If deployed acceptance is in scope, "
            "run `uip codedagent init`, `uip codedagent run <ENTRYPOINT> '<safe-json>'`, push with "
            "`UIPATH_PROJECT_ID` when Studio Web project binding is required, deploy with "
            "`uip codedagent deploy --my-workspace`, and invoke the deployed entrypoint with "
            "`uip codedagent invoke <ENTRYPOINT> '<safe-json>'`. [skill:uipath-agents] "
            "[library:uipath_library_search] [askai:query_uipath_docs]\n"
            "- [ ] T011E [US1] Implement HumanReview / HITL surface in "
            "`projects/<HumanReview>/Main.xaml` or the accepted `.flow` canvas using the named HITL "
            "template from `plan.md`. Copy/export or scaffold the template, read the copied review "
            "schema/control-flow structure, then customize review inputs, outcomes, "
            "timeout/escalation behavior, return path, and downstream queue/process updates. "
            "Verify completed, cancelled, and timeout/error routing unless the accepted plan defers "
            "a path. [skill:uipath-human-in-the-loop] [skill:uipath-rpa] "
            "[skill:uipath-maestro-flow] [library:uipath_library_search]\n"
            "- [ ] T011F [US1] Run solution-level gates on `solution.uipx` across `projects/`: "
            "`uipcli solution restore` -> `uipcli solution analyze --resultPath out/solution-analyze.json` "
            "-> tests -> `uipcli solution pack`. Capture runtime evidence and deploy-gate notes. "
            "[skill:uipath-platform] [skill:uipath-diagnostics] [subagent:shell]\n"
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
