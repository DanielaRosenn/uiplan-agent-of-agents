# Manual evaluation and QA checklist

Use this document when you want to **test the product yourself** before or after changes. It combines **fast automated smoke checks**, **copy-paste chat prompts** (with expected behavior), **persona-based full project checks**, and **optional** `run_evals.py` runs (AWS + time).

**How to use**

1. Run [§1 Automated smoke](#1-automated-smoke-run-first-every-time).
2. Start chat with the env block in [§2.0 Session setup](#20-session-setup-copy-once).
3. For each case: copy the **entire** fenced prompt into the chat input, wait for the run to finish, tick **Pass** only if every **Expected** bullet is satisfied, then write notes in **Your feedback**.
4. Add your own rows in [§2.8 Blank template — add more cases](#28-blank-template--add-more-cases).
5. Optionally run [§3 Automated end-to-end evaluation](#3-automated-end-to-end-evaluation-optional-costly) and paste summary into the session log.

---

## Two-stage evaluation (what “expected result” means)

We do **not** yet encode this split everywhere (Excel still has a single **Expected Behavior** column; `run_evals.py` scoring is mostly **Stage 1**). Treat the following as the **definition of done** when you write or review cases.

### Stage 1 — Technical (observable flow and mechanics)

**Question:** Did the system run the **right pipeline** and leave **correct artifacts**?

Pass when you can verify things like:

- **Routing / mode**: e.g. `[PLANNING]` then approval vs direct build; `[ANSWERING]` for question intent; agentic steps when building.
- **Tooling**: expected tools run (or acceptable substitutes), no repeated `Unknown tool`, no crash loops; validation invoked after writes when the case requires it.
- **Filesystem**: files under the intended session/output root; `project.json` / `Main.xaml` (or case-specific paths) exist when the scenario demands them.
- **Quality gates**: `validate_file` outcome matches expectation (0 errors after fix loop when `uip` is available); optional `run_workflow` when the case says so.
- **Deployment** (if in scope): env present, `deploy_to_orchestrator` result JSON or Orchestrator UI matches expectation — not only natural-language “success”.

**Automated overlap:** `run_evals.py` + `uipath_claude/evaluation/evaluators.py` implement **deterministic** checks close to Stage 1: **outcome** (expected files, packages, validation flag) and **trajectory** (tool subsequence). That is **not** an LLM judge; it is rules over captured outputs.

### Stage 2 — Conceptual (response quality and intent)

**Question:** Did the user get the **required answer or explanation** for the task type (clarify, teach, plan-only, build, deploy)?

Pass when:

- The **substance** matches the scenario (e.g. clarification asks the *right* missing questions; a “how does X work?” answer is accurate and scoped; a plan matches constraints).
- **User-visible text** satisfies explicit deliverables in the prompt (e.g. “numbered testing checklist 1–4”, “do not add Outlook”, “short summary at the end”).

**LLM-as-judge:** **Not implemented** in-repo as a standard evaluator today. Options for later: a small rubric prompt (same model or a separate judge) scoring 1–5 on dimensions (correctness, completeness, constraint adherence) with the transcript + expected criteria JSON. Until then, Stage 2 is **manual**: tick Pass only if you agree the answer would satisfy a reasonable user, and note disagreements in **Your feedback**.

### How this maps to existing artifacts

| Artifact | Stage 1 | Stage 2 |
|----------|---------|---------|
| **This doc — “Expected” bullets under each case** | Often covered (panels, tools, files) | Sometimes covered (wording, structure of answer) |
| **`docs/Chat_UX_Test_Cases.xlsx`** — *Expected Behavior* | Should be written as **checkable** bullets where possible | Add separate free-text or columns when you split rubrics |
| **`run_evals.py` / benchmarks** | Primary fit | Partially (only if encoded in reference outputs); no semantic judge |
| **Excel / PowerShell harness runs** | Can log transcripts | Heuristic PASS/FAIL is **unreliable** for Stage 2 (and often Stage 1); see `docs/Test_Runs_Summary_And_Conclusions.md` |

When adding a new case, draft **Expected** as two short lists: **Technical** (Stage 1) and **Conceptual** (Stage 2), then merge or duplicate into Excel if you keep one column.

---

## Prerequisites

From the repository root (after `pip install -e ".[dev]"`):

| Check | Command / action | Pass criteria |
|-------|------------------|---------------|
| Python env | `python --version` | 3.11+ (project target; 3.12 often works) |
| Package on PATH | `uipath-claude --help` | Help prints, no import error |
| AWS (for chat / evals) | `aws sts get-caller-identity` | Valid account identity |
| Optional: UiPath CLI | `uip` in PATH | Needed for `validate_file`, `run_workflow`, and realistic Studio checks |

**Windows PowerShell** examples below; on macOS/Linux use `export VAR=value` instead of `$env:VAR = "value"`.

---

## 1) Automated smoke (run first, every time)

These do **not** call Bedrock for most tests; they catch regressions quickly.

```powershell
cd <REPO_ROOT>\uipath-builder-agent

# Full unit suite (expect mostly green; note any known flaky tests)
pytest tests/unit/ -q --tb=line

# Focused: CLI, commands, planner, library tools
pytest tests/unit/cli/ tests/unit/commands/ tests/unit/query/test_planner.py tests/unit/tools/test_library_tools.py tests/unit/library/ -v --tb=short
```

**Record:** date, git commit (`git rev-parse --short HEAD`), pass/fail, and any failure names.

---

## Reading agentic console output

When `UIPATH_DEBUG_AGENT=1` (default), each **Step n/max** is one **LLM iteration** (think, then optional tools), not a guaranteed successful pipeline stage. The bracket track uses `=` for progress, `>` as the caret, and middle dots (`·`) for the remainder so empty space is not mistaken for a broken bar.

- **Artifact root** prints once at the start of an agentic turn: resolved folder `…/generated/chat/<session-id>/` (or your `UIPATH_CHAT_OUTPUT_DIR`).
- **Agent finished after N iteration(s)** means the model stopped calling tools, **not** that every tool succeeded. The next lines show **tool calls this run: X ok, Y reported errors** when applicable.
- **Failed tool returns** print a **Full output** panel (truncated at a large cap). By default **`UIPATH_DEBUG_VERBOSE=1`**, so successful tools also print full JSON **arguments**; set `UIPATH_DEBUG_VERBOSE=0` for quieter one-line summaries. Set `UIPATH_AGENTIC_FULL_TOOL_OUTPUT=1` to print full **return bodies** for successful tools as well.
- **Finishing line:** If the model already ran tools and then answers with **no further tool calls**, the console prints **Finishing (no more tool calls this turn).** plus an optional one-line **Preview** of the final assistant text (so the last step is not a blank gap after `Thinking...`).
- **`run_workflow` live CLI lines:** set `UIPATH_STREAM_UIP_CLI=1` to copy `uip` stdout/stderr to stderr as lines arrive (still capped; JSON output may be a single line).

The chat transcript also appends **`Artifact root:`** and, if any tool looked like a failure, a short **Tool errors** note above the assistant reply.

---

## 2) Interactive QA — copy-paste prompts

For every case below:

- Send **one user message** containing the full text from the grey box (unless the steps say otherwise).
- Compare the assistant output and session folder against **Expected**.
- Fill **Your feedback** (bugs, wrong tools, missing files, latency, UX).

### 2.0 Session setup (copy once)

```powershell
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"
# Token streaming for non-agentic turns: default on ($env:UIPATH_CHAT_STREAM = "1").
# UIPATH_CHAT_OUTPUT_MODE does not disable deltas; use --no-stream or UIPATH_CHAT_STREAM=0 to turn off.
# Optional: quieter tool logs (default is verbose: full tool args JSON)
# $env:UIPATH_DEBUG_VERBOSE = "0"
# Optional: where artifacts go
# $env:UIPATH_CHAT_OUTPUT_DIR = "<REPO_ROOT>\uipath-builder-agent\generated\chat"

uipath-claude chat
```

Replace `<REPO_ROOT>` with your machine path. Start a **fresh** chat session when switching between major cases if you want a clean artifact folder.

---

### Case A — Plan mode: simple log workflow (default `UIPATH_PLAN_MODE=1`)

**Full prompt (copy everything inside the box):**

```text
Create a UiPath Studio workflow project that logs a single message "Hello from manual QA" to the output panel. Use Main.xaml as the entry workflow. Keep the project minimal: project.json and Main.xaml only unless the tool chain requires otherwise. After writing Main.xaml, validate it with the project's validate step if you have that capability.
```

**Steps after the model replies**

1. If you see a cyan **Implementation Plan** panel, reply exactly: `y` (or use `adjust` / `n` per README if you are testing those paths).
2. Wait until the agent finishes (footer lines about iterations / tool counts).

**Expected**

- You see `[PLANNING]` before the plan when plan mode is on.
- After approval, execution proceeds; you see agentic steps (`Step 1/25`, tools, etc.).
- Under `generated/chat/<session-id>/` (or your output dir): **`project.json`** and **`Main.xaml`** exist; validation did not leave the workflow in an unexplained broken state (if `uip` is installed, prefer **0 validation errors** after fixes).
- Optional: **`.plan.md`** exists for that session when you approved with `y`.

| Pass | Date | Your feedback (what differed from Expected?) |
|------|------|-----------------------------------------------|
| [ ] |      |                                               |

---

### Case B — Skip plan for one session (`--no-plan`)

Start a **new** shell:

```powershell
cd <REPO_ROOT>\uipath-builder-agent
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"
uipath-claude chat --no-plan
```

**Full prompt:**

```text
Create a minimal UiPath workflow that only logs "No plan mode" once in Main.xaml. Use ensure_project_structure if needed, then write and validate.
```

**Expected**

- **No** plan approval panel for this build-style request (goes straight to tool loop or assistant work).
- Artifacts still land under the session folder; `Main.xaml` + `project.json` present when the agent used tools as intended.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case C — Plan mode off via environment

```powershell
$env:UIPATH_PLAN_MODE = "0"
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"
uipath-claude chat
```

**Full prompt:**

```text
Build a tiny RPA project: Main.xaml with one Log Message activity displaying the text "PLAN_MODE_OFF_QA". Scaffold with ensure_project_structure, install only packages you need, write Main.xaml, validate_file.
```

**Expected**

- No planning gate (same category of behavior as B).
- After testing: `Remove-Item Env:UIPATH_PLAN_MODE` (or new shell) so later runs restore default plan behavior.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case D — Slash `/recall`

Have a short conversation (2–3 turns), then run:

```text
/recall <one distinctive word you used earlier>
```

Then:

```text
/recall
```

**Expected**

- First `/recall`: Rich-style table with `#`, `Role`, `Content` (or equivalent columns).
- Second: usage / help when no search term.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case E — Slash `/plan` (on-demand plan)

```text
/plan add a Sequence in Main.xaml that logs the current time using a Log Message activity; keep dependencies minimal and mention validation.
```

Then:

```text
/plan
```

**Expected**

- First: plan text plus guidance to continue / approve as implemented in your branch.
- Second: usage or help when empty.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case F — Ambiguous build: agent should clarify (not invent)

**Full prompt:**

```text
Automate my email.
```

**Expected**

- Assistant asks **ONE clarifying question at a time** (not a batch of 2-3 questions).
- After you answer, it should ask the next most important question.
- When enough information is collected (system, action, inputs/outputs), it should say "Ready to build!" and transition to BUILD.
- The CLI prints **`[CLARIFYING]`** for each question turn.
- **NEW UX:** Single-question loop replaces batch questioning for better conversation flow.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case G — Read-only / advisory (no file generation unless you ask)

**Full prompt:**

```text
Explain in bullet points what belongs in a minimal UiPath Studio project.json for a Windows VB workflow project, and what Main.xaml is for. Do not create or modify files on disk unless I explicitly ask you to in a follow-up message.
```

**Expected**

- Explanatory answer; **no** `write_file` / materialization unless you later ask to build.
- If the agent still writes files, note that under feedback (policy regression).
- **Routing note:** Pure “explain / what is” prompts are classified as **question** intent; the CLI answers with a **no-tools** path (no `[PLANNING]`, no agentic step trace for that turn).

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case H — Excel path (packages + validation discipline)

**Full prompt:**

```text
Create a UiPath workflow that reads range A1:B10 from an Excel file named "Input.xlsx" in the project folder (assume the file will exist next to the project), writes the same data to Sheet2 starting at A1, using UiPath.Excel.Activities. Project dir ".", entry Main.xaml. After writing XAML, run validate_file. List which packages you installed.
```

**Expected**

- `install_package` for Excel activities (or equivalent) appears when needed.
- `validate_file` is attempted after `write_file` for `Main.xaml` (order may vary slightly but validation should not be permanently skipped).
- **CRITICAL:** If validation fails, the agent should **automatically retry fixes** until validation passes (0 errors) or max iterations exhausted. The agent should **NOT** stop with validation errors in simple tasks.
- If `Input.xlsx` is missing at runtime, static validation may still pass; note that in feedback if you care about runtime.
- **Prompt note:** The default chat system prompt tells the agent to call **`ensure_project_structure`** before other tools on build requests so `project.json` exists before packages or XAML writes.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case I — Explicit validation failure recovery (stress)

**Full prompt:**

```text
Create Main.xaml with an intentional placeholder activity tag "ThisIsNotARealUiPathActivity" inside a Sequence so validation fails once. Then fix Main.xaml to a valid minimal Sequence with a single Log Message "fixed", re-validate until validation passes or you hit a clear blocker, and summarize what you changed.
```

**Expected**

- At least one **failed** validation or tool error, then a **fix** and improved outcome (or a clear explanation if CLI cannot validate).
- Good signal for `_tool_return_indicates_success` and agent loop behavior.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Case J — Documentation library (local “book”)

**One-time seed:**

```powershell
python <REPO_ROOT>\uipath-builder-agent\scripts\seed_uipath_docs.py
```

**Full prompt:**

```text
Using only the local UiPath documentation library tools if available: what books exist, and what is one section title you can read back? If the library is empty, say so clearly.
```

**Expected**

- Agent may call `list_library_books` / `search_library` / `read_section` (visible when debug is on).
- `python -c "from uipath_claude.library import LibraryCatalog; c=LibraryCatalog.load(); print(len(c.books))"` prints at least `1` after seed.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

## Persona projects — full build cases (P1–P3)

Use these when you want a **realistic end-to-end** session: persona sets priorities and constraints; you still judge pass/fail from artifacts and explanations.

**How to run:** Paste **Persona + task** as **one** user message (each case is a single block). Approve plan if prompted (`y` unless you are testing `adjust` / `n`). When finished, open the session artifact folder and verify files.

---

### Persona P1 — Finance operations lead (invoice threshold + logging)

**Full prompt (copy entire block):**

```text
You are Jordan Lee, Finance Operations Lead at Contoso EU. You speak precisely and care about auditability.

Persona goals:
- You only approve vendor invoices below €5,000 without a second signature.
- You want automation to READ an Excel sheet "Invoices.xlsx" (assume columns: Vendor, AmountEUR, Status) and for each row: if AmountEUR < 5000 and Status is empty, append one line to a text log file "approvals.log" with Vendor, AmountEUR, and timestamp; if AmountEUR >= 5000, log a different line marking "requires second signature".
- You do NOT want the robot to send email in this first version—logging only.

Technical ask:
- Build a minimal UiPath Studio project under the current chat session (Main.xaml + project.json, relative project_dir ".").
- Use appropriate Excel activities package; validate Main.xaml; if safe and CLI allows, run_workflow is optional—if you skip it, say why.

Deliverables checklist (you should verify on disk after the run):
- project.json with sensible name/entryPoints
- Main.xaml containing Excel read + decision + Log Message or file append pattern consistent with Studio (exact activity names may vary by package version)
- Evidence validate_file was used at least once after a write

After building, summarize what you created in 5 bullet points for a finance reviewer.
```

**Expected**

- Plan (if enabled) reflects Excel + logging + threshold; execution produces **project.json** + **Main.xaml** under the session folder.
- `validate_file` appears in the tool trace after writes (when agentic tools are used).
- Final assistant text includes the **5 bullet** summary.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Persona P2 — Internal IT support (folder watch + incident log)

**Full prompt (copy entire block):**

```text
You are Sam Rivera, Internal IT Support Engineer. You prefer clear logs and defensive automation.

Scenario:
- A shared folder "\\\\fileserver\\drops\\tickets" will receive .txt ticket files (you cannot access that UNC from here—design the workflow as if the path is configurable via a string variable TicketFolderPath defaulting to a subfolder "incoming" under the project directory for local testing).
- When a new .txt file appears, log its file name and size with Log Message activities (polling loop is acceptable for v1—no need for OS-level FileSystemWatcher if too complex).
- Keep the project minimal for QA: Main.xaml + project.json, validate after write.

Constraints:
- Do not claim you cannot use tools; use ensure_project_structure, write_file, validate_file as appropriate.
- If you use packages beyond defaults, install_package and state package names in the final summary.

End with: (1) list of variables you introduced, (2) how an operator would change TicketFolderPath for production.
```

**Expected**

- Project scaffold + **Main.xaml** with a plausible polling or iteration pattern and logging.
- **Variables** section or clear variable names in summary as requested.
- Validation attempted after substantive XAML writes.

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### Persona P3 — Retail operations “citizen developer” (SKU lookup + branch)

**Full prompt (copy entire block):**

```text
You are Alex Morgan, store operations coordinator. You are learning RPA and want readable workflows.

Business need:
- Read "Products.xlsx" (assume columns SKU, Quantity, ReorderLevel in sheet "Stock").
- For each row: if Quantity <= ReorderLevel, log "REORDER SKU=<sku> qty=<qty>" else log "OK SKU=<sku>".
- Use Excel activities; keep names friendly in DisplayName properties when possible.

Technical:
- New UiPath project in this chat session; Main.xaml entry; validate_file after Main.xaml is written.
- In your final message, include a short "Testing checklist" numbered 1–4 that a store manager could follow in Studio or Orchestrator later (even if we only validate locally here).

Do not add Outlook, SQL, or web browsers in this version.
```

**Expected**

- Excel-based loop with **branching** log lines matching the SKU rule (structure may vary by activity API).
- No mail/SQL/browser packages **unless** the agent justified a mistake (note in feedback).
- Final answer includes a **numbered testing checklist** (1–4).

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

### 2.8 Blank template — add more cases

Duplicate this subsection for each new scenario. Use `~~~text` / `~~~` for the prompt so Markdown stays valid.

### Case __ — (short title)

**Full prompt:**

~~~text
<paste exact user message you send>
~~~

**Expected**

- 
- 
- 

| Pass | Date | Your feedback |
|------|------|---------------|
| [ ] |      |               |

---

## 3) Automated end-to-end evaluation (optional, costly)

This runs the **real agent** against the benchmark dataset and needs **Bedrock** access. See also [workflow-benchmarks.md](workflow-benchmarks.md).

```powershell
cd <REPO_ROOT>\uipath-builder-agent

python run_evals.py --max-examples 3 --output evaluation_results_sample.json
python run_evals.py --max-examples 5 --category excel --output eval_excel.json
```

**Record:** command line, wall time, `evaluation_results*.json` path, summary pass rate from console.

---

## 4) Severity rubric (how to score manual runs)

Use when filing issues or comparing builds.

| Severity | Meaning |
|----------|---------|
| **Blocker** | Crash, wrong project path, credentials loop, data loss |
| **Major** | Plan not saved, tools not registered, agentic mode broken |
| **Minor** | UI wording, spinner text, non-critical layout |
| **Cosmetic** | Colors only, typos in docs |

---

## 5) Session log template (full run)

Copy to a ticket or notes file after a QA pass.

```
Date:
Git (short):
Tester:
Build / branch:

Smoke pytest: PASS / FAIL — notes:

Manual — quick cases:
  A Plan + Hello QA:        PASS / FAIL / SKIP
  B --no-plan:              PASS / FAIL / SKIP
  C UIPATH_PLAN_MODE=0:     PASS / FAIL / SKIP
  D /recall:                PASS / FAIL / SKIP
  E /plan:                  PASS / FAIL / SKIP
  F ambiguous email:       PASS / FAIL / SKIP
  G read-only explain:     PASS / FAIL / SKIP
  H Excel read/write:      PASS / FAIL / SKIP
  I validation recovery:   PASS / FAIL / SKIP
  J library seed:          PASS / FAIL / SKIP / N/A

Persona full builds:
  P1 Finance invoice log:   PASS / FAIL / SKIP
  P2 IT folder polling:     PASS / FAIL / SKIP
  P3 Retail SKU reorder:    PASS / FAIL / SKIP

Custom cases (list IDs): _______________________

run_evals: RUN / SKIP — output file:

Top 3 issues / feedback themes:
1)
2)
3)
```

---

## Related docs

- [workflow-benchmarks.md](workflow-benchmarks.md) — canonical `run_evals.py` usage
- [ARCHITECTURE.md](ARCHITECTURE.md) — runtime and modules
- [USER_GUIDE.md](USER_GUIDE.md) — end-user oriented usage (if present in your branch)
