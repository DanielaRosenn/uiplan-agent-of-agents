# Activities-first, then coded fallback

## Rule

For any new UiPath project, the workflow body is **XAML/activities** by default. A `.cs` `CodedWorkflow` is only emitted when one of the following holds, and the choice is recorded in `BUILD_LOG.md`:

1. The user explicitly asked for a coded workflow ("coded workflow", "C# workflow", "create a .cs file").
2. The project is already coded-only (matching the project's existing mode is the right default — see `skills/skills/uipath-rpa/references/coded-vs-xaml-guide.md` step 1).
3. The implementation requires a UiPath SDK API or .NET library call that has no equivalent activity (`coded-vs-xaml-guide.md` rules 3-6).
4. The user has waived the activities-first guard with an explicit `justification` argument to `write_file`.

## Why this lives in lessons-learned, not in a brand-new policy doc

The XAML-first policy already existed in `skills/skills/uipath-planner/SKILL.md` (rules 10-11) and `skills/skills/uipath-rpa/references/coded-vs-xaml-guide.md` (decision tree, lines 9-21). What was missing was **enforcement at the developer-agent layer**: the planner could correctly say "build this in XAML", and the developer agent could still hand back a `CodedWorkflow` with no challenge. The 2026-04-19 `InvoiceQueueProcessor` round was a clean example — see the incident note at `chapters/99-incidents/2026-04-19-invoice-queue-processor.md`.

## How the guard works

The `write_file` tool (`uipath_claude/tools/skill_execution_tools.py`) refuses to write the FIRST `CodedWorkflow` `.cs` file into an otherwise-XAML project unless the caller passes a non-empty `justification`. The check is:

- The destination path ends with `.cs`.
- The content matches the regex `:\s*CodedWorkflow\b` (the C# inheritance line `: CodedWorkflow`).
- Walking up to the nearest `project.json`, no other `.cs` file in the project (excluding `.codedworkflows/`, `.local/` scaffolding) already declares a `CodedWorkflow`.

When the guard triggers and `justification` is empty, the tool returns a `[ERROR]` payload telling the agent to either write a `.xaml` file instead or re-call with a `justification` citing a `coded-vs-xaml-guide.md` rule. When `justification` is provided, the write proceeds and the justification text is recorded in the project's `BUILD_LOG.md` under `notes`. This means a reviewer can always answer the question "why is there a coded workflow in this project?" by reading `BUILD_LOG.md`, without spelunking through chat history.

## Worked example: InvoiceQueueProcessor

Original (regression) build: a single `ProcessInvoices.cs` `CodedWorkflow` doing dequeue, validation, SQL insert, and `SetTransactionStatus`. Wrapper `Main.xaml` did nothing but `InvokeWorkflowFile` into the `.cs`. Symptoms:

- The whole queue loop lived in C#, so non-developer reviewers could not adjust the validation rules without editing C# and recompiling.
- The SQL insert used `System.Data.SqlClient` directly — adding a hard `.NET` dependency that has no surface in Studio's package manager.
- The planner skill said "XAML by default" but the developer agent shipped coded anyway because nothing prevented it.

Activities-first rebuild: `Main.xaml` is the workflow body — `DatabaseConnect` -> `DoWhile` { `WaitQueueItem` -> validate (one `InvokeCode` block) -> `If` (insert via `ExecuteNonQuery` and `SetTransactionStatus`/Successful, else `SetTransactionStatus`/Failed/Business) } -> `DatabaseDisconnect`. The `UiPath.Database.Activities` 2.0.0 package was added via `install_package` (which writes `project.json` correctly without hand-pinning) so the SQL insert is a real activity, parameter-bound. The validation logic stays as VB inside a single `Invoke Code` activity because (a) UiPath does not provide per-field validation activities and (b) VB inside a single `Invoke Code` is still readable and adjustable in Studio's expression editor — it is not a `CodedWorkflow`.

The end result: a reviewer who wants to add a fourth required field opens `Main.xaml` in Studio, edits the `InvokeCode` block, and re-validates. No C# project file, no build dependency, no `.cs` to keep in sync.

## Cross-references

- `skills/skills/uipath-planner/SKILL.md` rules 10-11 — XAML-first planner policy.
- `skills/skills/uipath-rpa/references/coded-vs-xaml-guide.md` — decision tree with numbered fallback rules.
- `skills/skills/uipath-rpa/SKILL.md` "Project Type Detection" section — how the RPA skill decides existing-project mode.
- `chapters/02-coded-workflows/` — narrow operational gotchas that apply once you are inside a coded workflow (kept distinct from the design choice).
- `chapters/99-incidents/2026-04-19-invoice-queue-processor.md` — the regression that motivated this chapter.
