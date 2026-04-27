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
        "- [ ] T001 [P] [US1] Confirm paradigm and descriptor files from `plan.md`; "
        "cite `[skill:uipath-planner]` and `[agent:uipath-project-discovery-agent]`; "
        "verify by listing detected descriptors under `projects/` or repo root.\n"
        "- [ ] T002 [US1] Map each workflow row in `plan.md` **Per-project workflow** table to concrete "
        "`projects/**/*.xaml` (or `.cs` / `langgraph.json`) entry points; run `uipath_library_search` + "
        "`uipath_library_lookup` (and `query_uipath_docs` when library coverage is thin) for every "
        "uncertain queue/mail/binding/CLI call; record `[library:...]` / `[askai:...]` citations in tasks.\n"
    )
    if paradigm == "modern-rpa":
        return base + (
            "- [ ] T003 [US1] Create the Studio template decision matrix for the RPA project: selected "
            "starter template/scaffold source, workflow type, generated structure to preserve, "
            "`uip rpa create-project` / Studio evidence, and discovery/question item if the template "
            "cannot be inferred from `spec.md` / `plan.md`; `[skill:uipath-rpa]` + "
            "`uipath_library_search`; **Done when**: matrix is explicit before any `Main.xaml` edits.\n"
            "- [ ] T010 [P] [US1] Add failing test in `Tests/InvoiceFlowTests.xaml`; "
            "verify with `uipcli test run`.\n"
            "- [ ] T011A [P] [US1] **Scaffold-only (explicit):** `Workflows/ProcessInvoice.xaml` — "
            "named `LogMessage` steps + correlation id variable only; **Done when**: analyze green "
            "except documented org rules. **Follow-up:** T011B.\n"
            "- [ ] T011B [US1] **Build `Workflows/ProcessInvoice.xaml` (RPA use case):** replace scaffolds "
            "with queue/mail (and other) activities only after `uipath_doc_get_activity` / "
            "`uipath_library_lookup`; use `[skill:uipath-rpa]` + `uipcli package analyze`; record workflow type "
            "per `plan.md`; **Done when**: analyze + `uipcli test run` + smoke logs match spec (no "
            "LogMessage-only completion for this line). `[HANDOFF:OrchestratorDeploy]` / "
            "`[HANDOFF:RobotSmoke]` only for publish or physical robot, not for skipping activities.\n"
        )
    if paradigm == "coded-agent":
        return base + (
            "- [ ] T010 [P] [US1] Add failing test `tests/test_us1_flow.py`; run `uv run pytest tests/test_us1_flow.py`.\n"
            "- [ ] T011 [US1] Implement node logic in `main.py` or `agent.py` and update "
            "`langgraph.json|agent_framework.json`; verify with `uipath run` and pytest.\n"
        )
    if paradigm == "solution":
        return base + (
            "- [ ] T003 [US1] Create the Studio template decision matrix for every RPA project in the "
            "Solution: Dispatcher/scheduled intake template for mailbox polling and enqueue, "
            "Performer/queue-worker or Long Running host template for `AnalyzerRunner`, Long Running "
            "Workflow/HITL template for `HumanReviewHandler`, plus each `projects/ZipEmail.*/project.json` "
            "/ `project.uiproj` scaffold source, workflow type, generated structure to preserve, "
            "`uip rpa create-project` or Studio evidence, and a question/discovery item if any template "
            "is not knowable; `[skill:uipath-rpa]` + `uipath_library_search`; **Done when**: no generic "
            "hand-written `Main.xaml` can be treated as complete without template remediation.\n"
            "- [ ] T010 [P] [US1] Add failing binding/schema test `tests/test_zipemail_bindings.py`; "
            "run `uv run pytest tests/test_zipemail_bindings.py -q`; **Runtime evidence**: "
            "pytest JUnit XML under `TestResults/` or console log path.\n"
            "- [ ] T011A [P] [US1] **Supporting slice (same story, not a substitute for XAML):** align "
            "`bindings/*.json`, `tests/**`, and `projects/ZipEmail.AnalyzerAgent/**` with `spec.md` / "
            "`plan.md` until Independent Test behaviors pass in pytest (mocks/stubs for queues, Graph, "
            "Slack as needed); extend `langgraph.json` graph to exercise pipeline logic. **Done when**: "
            "listed `uv run pytest` commands green; document any analyzer policy exceptions in the task.\n"
            "- [ ] T011B [P] [US1] **Scaffold-only (explicit):** per `plan.md` workflow rows, add **named** "
            "`LogMessage` phase markers + `CorrelationId` in each `projects/ZipEmail.*/Main.xaml` **only** "
            "where Studio wiring is not yet done; **Done when**: `uipcli package analyze` on each RPA "
            "project produces no Error severity except documented org rules (e.g. Automation Hub URL). "
            "**Follow-up:** T011C1–T011F.\n"
            "- [ ] T011C1 [US1] **Dispatcher Studio/tooling preflight for "
            "`projects/ZipEmail.Dispatcher/Main.xaml` (RPA/Studio):** verify the Dispatcher/scheduled "
            "intake starter template or add a template remediation task before Graph wiring; discover "
            "or record Studio path / `uip rpa` integration, install/confirm Graph/mail + queue packages after "
            "`uipath_doc_get_activity`, and capture default-activity-XAML or Studio evidence; "
            "`[skill:uipath-rpa]` + `uipath_library_search` / `uipath_library_lookup`; **Done when**: "
            "template/scaffold provenance is recorded, generated control-flow structure is preserved or "
            "remediated, and `uipcli package restore projects/ZipEmail.Dispatcher/project.json "
            "--restoreFolder packages --nugetConfigFilePath NuGet.Config` succeeds.\n"
            "- [ ] T011C2 [US1] **Dispatcher Graph read in `projects/ZipEmail.Dispatcher/Main.xaml` "
            "(RPA/Studio):** replace `ReadMailboxMessages` scaffold with Graph/Office365 mail activity "
            "using `MicrosoftGraph` connection and mailbox config assets; `uipath_doc_get_activity` + "
            "`uipath_library_search` / `uipath_library_lookup`; **Done when**: no LogMessage substitute "
            "remains for Graph read and `uipcli package analyze projects/ZipEmail.Dispatcher/project.json "
            "--resultPath out/analyze-dispatcher-graph.json` validates except documented tenant policy findings.\n"
            "- [ ] T011C3 [US1] **Dispatcher cursor and duplicate control in "
            "`projects/ZipEmail.Dispatcher/Main.xaml` (RPA/Studio):** implement `LoadMailboxCursor`, "
            "`CheckDuplicate`, and `AdvanceMailboxCursor` with asset/queue reference strategy "
            "(`InternetMessageId` / `CorrelationId`); `uipath_doc_get_activity` + `[skill:uipath-rpa]`; "
            "**Done when**: fixture smoke logs cursor phases and duplicate path without a second "
            "`ZipEmailIntakeQueue` item.\n"
            "- [ ] T011C4 [US1] **Dispatcher intake queue payload in "
            "`projects/ZipEmail.Dispatcher/Main.xaml` (RPA/Studio):** map Graph metadata into "
            "`AddQueueItem` / `ZipEmailIntakeQueue` required fields from `bindings/dev.json`; "
            "`uipath_doc_get_activity` + `uipath_library_lookup`; **Done when**: analyzer JSON has no "
            "XAML validation errors and smoke evidence shows `EmailMessageId`, `InternetMessageId`, "
            "`SourceMailbox`, and `CorrelationId` populated from a test message.\n"
            "- [ ] T011D1 [US1] **Analyzer engine in `projects/ZipEmail.AnalyzerAgent/langgraph.json` "
            "(coded agent / LangGraph):** build/extend graph nodes from `plan.md` and verify with "
            "`uv run pytest tests projects/ZipEmail.AnalyzerAgent/tests -q`; `[skill:uipath-agents]`; "
            "**Done when**: graph smoke returns structured result for invoice, non-invoice, and "
            "human-review fixtures.\n"
            "- [ ] T011D2 [US1] **AnalyzerRunner Invoke Agent boundary in "
            "`projects/ZipEmail.AnalyzerRunner/Main.xaml` (RPA + agent invocation):** verify the "
            "Performer/queue-worker or Long Running host starter template and preserve generated "
            "transaction/error handling structure before activity wiring; implement queue "
            "transaction retrieval, request JSON build, `uipath run` / Invoke Agent command or activity, "
            "structured response parse, and pre/post audit; `uipath_doc_get_activity`, "
            "`[skill:uipath-rpa]`, `[skill:uipath-agents]`; **Done when**: fixture smoke invokes the "
            "agent path and `uipcli package analyze projects/ZipEmail.AnalyzerRunner/project.json "
            "--resultPath out/analyze-analyzer-runner.json` validates except documented tenant policy findings.\n"
            "- [ ] T011D3 [US1] **AnalyzerRunner queue status updates in "
            "`projects/ZipEmail.AnalyzerRunner/Main.xaml` (RPA/Studio):** update "
            "`ZipEmailIntakeQueue`, create `ZipEmailHumanReviewQueue` when review is required, and "
            "handle retry/exception statuses from `bindings/dev.json`; `uipath_doc_get_activity` + "
            "`uipath_library_search` / `uipath_library_lookup`; **Done when**: fixture smoke covers "
            "`InvoiceForwarded`, `NonInvoiceArchived`, `NeedsHumanReview`, and `Exception` with "
            "correlation id logs.\n"
            "- [ ] T011E1 [US1] **HumanReviewHandler Slack HITL setup in "
            "`projects/ZipEmail.HumanReviewHandler/Main.xaml` (RPA/Studio):** verify the Long Running "
            "Workflow/HITL starter template and persistence/wait-resume structure before Slack wiring; "
            "use Studio/default XAML "
            "for Slack notification/outcome activity or approved Integration Service pattern, with "
            "`NotificationTargets.FinanceReview` from `bindings/dev.json`; `uipath_doc_get_activity`, "
            "`uipath_library_search` / `uipath_library_lookup`, `[skill:uipath-rpa]`; **Done when**: "
            "`PostSlackReviewRequest` and `WaitForSlackOutcome` are real activities/validated placeholders "
            "with tenant-only connection fields documented.\n"
            "- [ ] T011E2 [US1] **HumanReviewHandler review/intake queue updates in "
            "`projects/ZipEmail.HumanReviewHandler/Main.xaml` (RPA/Studio):** implement `GetReviewItems`, "
            "`ApplyApprovalOrRejection`, `UpdateReviewQueue`, `UpdateLinkedIntakeQueue`, and "
            "`EscalateExpiredReview`; `uipath_doc_get_activity` + `[skill:uipath-rpa]`; **Done when**: "
            "fixture smoke updates both `ZipEmailHumanReviewQueue` and linked `ZipEmailIntakeQueue` statuses "
            "and `uipcli package analyze projects/ZipEmail.HumanReviewHandler/project.json "
            "--resultPath out/analyze-human-review.json` validates except documented tenant policy findings.\n"
            "- [ ] T011F [US1] **Solution-wide verification for `solution.uipx` (solution):** run "
            "`uipcli solution restore . --restoreFolder packages --nugetConfigFilePath NuGet.Config`, "
            "`uipcli solution analyze . --resultPath out/sln-analyze.json`, RPA package analyzes, and "
            "`uv run pytest tests projects/ZipEmail.AnalyzerAgent/tests -q`; **Runtime evidence**: "
            "`out/sln-analyze.json`, per-project analyzer JSON, pytest output, and package path if packed; "
            "`[skill:uipath-platform]` + `uipath_library_search`; personal workspace default; "
            "Production requires explicit approval.\n"
        )
    if paradigm == "coded-app":
        return base + (
            "- [ ] T010 [P] [US1] Add failing test `tests/test_coded_app.py`; "
            "run `uv run pytest tests/test_coded_app.py -q`.\n"
            "- [ ] T011 [US1] Implement `src/actions/checkout.ts` and `action-schema.json`; "
            "`[skill:uipath-coded-apps]`; `uipath_library_search` + `uipath_library_lookup`; "
            "`uip codedapp build`; **Runtime evidence**: build log under `out/build.log`; "
            "personal workspace default; Production requires explicit approval.\n"
        )
    if paradigm == "case-management":
        return base + (
            "- [ ] T010 [P] [US1] Add `tests/test_caseplan_transitions.py`; "
            "run `uv run pytest tests/test_caseplan_transitions.py -q`.\n"
            "- [ ] T011 [US1] Implement case stages in `caseplan.json`; `uip case` validate; "
            "`uipath_library_search` + `uipath_library_lookup`; **Runtime evidence**: validation log; "
            "personal workspace default; Production requires explicit approval.\n"
        )
    if paradigm == "maestro-flow":
        return base + (
            "- [ ] T010 [P] [US1] Add validation scenario for `flows/sample.flow` in `tests/test_maestro_flow.py`; "
            "run `uv run pytest tests/test_maestro_flow.py -q`; **Runtime evidence**: pytest JUnit path.\n"
            "- [ ] T011 [US1] Implement flow updates in `flows/sample.flow` and integration bindings in "
            "`bindings/dev.json`; `[skill:uipath-maestro-flow]`; `uipath_library_search` + "
            "`uipath_library_lookup`; **Verification**: `uip` sync + plan smoke; **Runtime evidence**: "
            "flow validation export; personal workspace default; Production requires explicit approval.\n"
        )
    if paradigm == "api-workflow":
        return base + (
            "- [ ] T010 [P] [US1] Add `tests/test_api_workflow_contract.py`; "
            "run `uv run pytest tests/test_api_workflow_contract.py -q`.\n"
            "- [ ] T011 [US1] Implement `Workflows/Inbound.xaml` and `api-workflow.json`; "
            "`[skill:uipath-rpa]`; `uipath_doc_get_activity` for HTTP activities; "
            "`uipath_library_search` + `uipath_library_lookup`; `uipcli package analyze --resultPath out/aw.json`; "
            "personal workspace default; Production requires explicit approval.\n"
        )
    if paradigm == "library":
        return base + (
            "- [ ] T010 [P] [US1] Add failing library test `Tests/LibrarySmoke.xaml`; "
            "verify with `uipcli test run -a <projectKey> .`.\n"
            "- [ ] T011 [US1] Implement `Activities/MyActivity.cs` referencing "
            "`[activity:UiPath.System.Activities:LogMessage]`; `uipath_library_lookup`; "
            "`uipcli package pack`; **Runtime evidence**: `.nupkg` path; "
            "personal workspace default; Production requires explicit approval.\n"
        )
    if paradigm == "tests":
        return base + (
            "- [ ] T010 [P] [US1] Add failing test set `Tests/ProcessRegression.xaml`; "
            "`uipcli test run -a <projectKey> .`.\n"
            "- [ ] T011 [US1] Implement minimal source in `Tests/Support.xaml` to pass tests; "
            "`uipath_library_lookup`; verify JUnit output under `TestResults/`; "
            "personal workspace default; Production requires explicit approval.\n"
        )
    return base + (
        "- [ ] T010 [P] [US1] Add `tests/test_paradigm_placeholder.py`; "
        "run `uv run pytest tests/test_paradigm_placeholder.py -q`.\n"
        "- [ ] T011 [US1] Document discovery outcomes in `README.md` using `project.json` as anchor; "
        "`uipath_library_search` + `uipath_library_lookup`; personal workspace default; "
        "Production requires explicit approval.\n"
    )
