# 2026-04-19 InvoiceQueueProcessor — `ErrorType` namespace + stale `get-errors`

## Project

`examples/InvoiceQueueProcessor` — first unattended robot example with a
coded workflow that dequeues `Invoices`, validates fields, and inserts valid
items into SQL Server.

## Timeline

1. Agent scaffolded the project, wrote `ProcessInvoices.cs` with
   `using UiPath.Core;` and `errorType: ErrorType.BusinessException`.
2. `uip rpa get-errors` returned `"No diagnostics found."` on the first call.
3. Agent reported `verdict='pass'`. User opened the project in Studio and
   saw 6 compile errors:
   - `The name 'ErrorType' does not exist in the current context`
   - …or, with `using UiPath.Core.Activities;`,
     `'ErrorType' does not contain a definition for 'BusinessException'`.
4. Re-running `get-errors` from a shell produced the errors immediately.

## Root causes

- **Wrong namespace.** `ErrorType` lives in `UiPath.Core.Activities`, not in
  `UiPath.Core` or `UiPath.Orchestrator.Client.Models`.
- **Wrong enum members.** The actual members are `Business` / `Application`,
  not `BusinessException` / `ApplicationException` (the doc snippets in
  `skills/.../25.10/coded/examples.md` are misleading).
- **Stale `get-errors`.** The Studio IPC behind `get-errors` returned a
  stale "no diagnostics" snapshot for the first call after the file write.
- **Verify-gate trusted a single pass.** The agent's pipeline accepted one
  clean `get-errors` result without re-validating, so the false negative
  propagated to `verdict='pass'`.

## Fixes shipped in this round

1. `examples/InvoiceQueueProcessor/ProcessInvoices.cs`: switched to
   `using UiPath.Core.Activities;` and `ErrorType.Business` /
   `ErrorType.Application`. Added a typed `Execute(string sqlConnectionString,
   string? orchestratorFolder = null)` entry point.
2. Re-introduced `Main.xaml` that invokes `ProcessInvoices.cs` via
   `ui:InvokeWorkflowFile`, restored `project.json -> main: "Main.xaml"`.
3. Hardened `uipath_claude/tools/uipath/cli_runner.run_uip_rpa_get_errors`:
   `--min-severity error`, `passes=2`, structured + textual diagnostics
   parsing, `studio_available()` probe, audit emit per call.
4. Updated `uipath_claude/validation/pipeline.py` and the
   `validate_file` / `build_and_verify_workflow` tools to use the new
   defaults (two passes, error-only severity).
5. Tightened the verify-gate prompt strings in
   `uipath_claude/query/agentic_executor.py` so the agent will not call a
   project done without two clean validation passes plus a headless run
   (and an attached Studio debug pass when Studio is detected).
6. Added per-project append-only `BUILD_LOG.md` audit trail
   (`uipath_claude/audit/`) and seeded this lessons-learned book.

## Detection rules going forward

- A `verdict='pass'` from `build_and_verify_workflow` MUST report
  `passes_run >= 2` for the validation step.
- `BUILD_LOG.md` for a project that ever recorded an `outcome=needs_llm_fix`
  should eventually be followed by an entry in
  `99-incidents/` (or an explicit "no incident — root cause known" note).

---

# 2026-04-19 InvoiceQueueProcessor — activities-first regression (round 2)

## Project

Same project as the round-1 incident above.

## Timeline

1. After round-1 fixes shipped, the user observed that the project was still a
   `CodedWorkflow`-driven build even though the planner skill says
   "RPA workflows are XAML by default" (`skills/skills/uipath-planner/SKILL.md`
   rules 10-11) and the RPA decision tree confirms it
   (`skills/skills/uipath-rpa/references/coded-vs-xaml-guide.md` lines 9-21).
2. User feedback: "this should be planned as activities first because it is
   easier to adjust." The original C# `ProcessInvoices.cs` was technically
   correct after round 1 but violated the activities-first design policy.

## Root causes

- **Policy existed, enforcement did not.** The XAML-first rule was documented
  in two places but neither the planner nor the developer agent had a
  programmatic gate. The agent could ship coded with no challenge.
- **Coded-vs-XAML decision was made by the LLM at write-time, not at plan-
  time.** Once the developer agent picked `CodedWorkflow`, `write_file`
  accepted it without question.
- **No audit signal differentiated "we deliberately chose coded" from
  "we drifted to coded".** Reviewers had no way to tell the two apart in
  `BUILD_LOG.md`.

## Fixes shipped in this round

1. `examples/InvoiceQueueProcessor/ProcessInvoices.cs` removed.
2. `examples/InvoiceQueueProcessor/Main.xaml` rewritten as a real activities
   sequence (`DatabaseConnect` -> `DoWhile` { `WaitQueueItem` ->
   `Invoke Code` (validation) -> `If` -> `ExecuteNonQuery` +
   `SetTransactionStatus` } -> `DatabaseDisconnect`).
3. `examples/InvoiceQueueProcessor/project.json` updated via
   `install_package` to add `UiPath.Database.Activities` 2.0.0 and switched
   `expressionLanguage` to `VisualBasic` (so `[bracket]` expressions work
   without `<CSharpValue>` ceremony).
4. `uipath_claude/tools/skill_execution_tools.py` `write_file`: added
   activities-first guard. The first `CodedWorkflow` `.cs` in a XAML
   project is soft-blocked unless a `justification` is passed. The
   justification is logged into `BUILD_LOG.md` under `notes`.
5. `uipath_claude/query/bootstrap.py`: developer-agent prompt now requires
   either an explicit user request or a written justification citing
   `coded-vs-xaml-guide.md` before emitting a coded workflow.
6. `skills/skills/uipath-planner/SKILL.md` rule 11: added an enforcement
   sentence stating that an unrequested coded workflow is a planning
   regression and must re-route to XAML.
7. New `data/library/books/lessons-learned/chapters/00-design-choices/`
   chapter created with the design rule and decision tree.

## Detection rules going forward

- For any new project that ends up coded, `BUILD_LOG.md` MUST contain a
  `write_file` event whose `notes` start with `activities-first override:
  justification=` (or the project must be coded-only by user request from
  step 1).
- A `BUILD_LOG.md` that contains a `CodedWorkflow` write without that
  override note is a regression and should be re-planned as XAML.

