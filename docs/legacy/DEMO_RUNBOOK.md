# Demo runbook: InvoiceIntake_Demo end to end

Copy-pasteable PowerShell for a single-take demo. You run everything yourself.
You may keep a **reference** copy under this repo; the **authoritative** demo
project for Studio is the OneDrive path below unless you deliberately choose
otherwise.

**Where files must land:** the chat agent writes to the path you pass to
`--project-dir` **and** the absolute path in your build prompt. Those two must
be the **same** folder as your Studio project (below). If you start plain
`uipath-claude chat` with no `--project-dir`, or you paste the repo path
(`...\uipath-builder-agent\InvoiceIntake_Demo`), artifacts go under the repo,
not under OneDrive. Fix: always use the OneDrive path in both places.

Assumes:

- `uipcli` installed at `C:\Users\DanielaRosenstein\.dotnet\tools\uipcli.exe`
  (verified 25.10).
- `uipath` (Python CLI) at
  `C:\Users\DanielaRosenstein\AppData\Local\Programs\Python\Python312\Scripts\uipath.exe`.
- This repo cloned at `c:\Users\DanielaRosenstein\projects\uipath-builder-agent`.
- Target project folder:
  `C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo`.

## 1. One-time machine setup (already done)

Nothing to run. Listed for camera context only:

```powershell
Get-Command uipcli | Select-Object Name, Source
Get-Command uipath | Select-Object Name, Source
```

## 2. Pre-demo smoke (run in this repo)

```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
python ops/scripts/smoke_chat_pipeline.py
```

Expected: `SMOKE OK`. Any other output means **abort the recording**. The
smoke script verifies classifier routing, the `uip design-propose` denylist,
and the design-store round-trip.

Then start a fresh chat session (required so the hardening changes are in the
running process, not just on disk). **Pin the Studio project directory** so
every tool defaults to OneDrive, not the repo:

```powershell
Set-Location c:\Users\DanielaRosenstein\projects\uipath-builder-agent
.\.venv\Scripts\Activate.ps1

$STUDIO_PROJ = "C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo"
uipath-claude chat --project-dir $STUDIO_PROJ
```

Use the same `$STUDIO_PROJ` value in **Prompt 2** (build line). Do not mention
the repo `...\uipath-builder-agent\InvoiceIntake_Demo` path in that line unless
you intentionally want the agent to work there.

## 3. Drive the chat (see section "Chat flow for the demo" below)

When the agent is done, spot-check:

```powershell
Set-Location "C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo"
dir
Get-Content Main.xaml | Select-Object -First 20
```

Expected (minimal invoice intake scope): non-empty `Main.xaml`,
`Workflows\ExtractInvoice.xaml`, `Workflows\ApplyPolicy.xaml`,
`Workflows\WriteResult.xaml`, `Data\Input\`, `Data\Output\`, and `project.json`.
If your approved plan also specified Forms/Models/Tests, those appear too;
they are not required for the baseline demo.

## 4. Analyze and pack via uipcli (25.10+)

`uipcli` takes the path to `project.json` as a **positional** argument (the old
`--projectPath` / `--projectsPath` flags are not used).

```powershell
Set-Location "C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo"

# Optional: cache UiPath cloud creds for future coded-agent work.
# Note: this does NOT deploy a classic RPA project. It's informational only.
uipath auth

# Analyzer gate (writes analyze.json). Tenant policy may require Automation
# Hub URL (ST-USG-034). If that is the only "error" in the log, either set the
# idea URL in Studio Project Settings, or ignore for CI-only checks:
uipcli package analyze ".\project.json" `
  --resultPath ".\analyze.json" `
  --ignoredRules ST-USG-034

# Pack (also restores packages as needed):
uipcli package pack ".\project.json" -o ".\out" --autoVersion

# Deploy to Personal Workspace (fill in External App creds off-camera):
# uipcli package deploy .\out `
#   -s <ORCHESTRATOR_URL> `
#   -t <TENANT> `
#   -a <ACCOUNT> `
#   --applicationId <CLIENT_ID> `
#   --applicationSecret <CLIENT_SECRET> `
#   --organizationUnitId <PERSONAL_WS_FOLDER_ID>
```

Do not run `uipcli package deploy` on camera without the External App creds
prepared. Keep the placeholder block commented; uncomment only when the
creds are in env vars or a secure store.

## 5. Run from Studio Desktop (fallback / visual)

If Orchestrator is not set up for camera:

1. `File -> Open -> project.json` from the InvoiceIntake_Demo folder.
2. `Manage Packages` -> for the **baseline** invoice demo, **`UiPath.System.Activities`**
   must resolve (per `project.json`). Only install extra packages
   (Mail, OCR, UIAutomation, WebAPI) if your **approved design** added them;
   otherwise do not add unused dependencies.
3. If restore is flaky from Studio, run **`uipcli package pack`** from section 4
   once (it restores as part of the build) or use Studio's **Repair** / restore.
4. Open `Main.xaml`, `F5` to run in attended mode (see **section 6** for inputs
   and expected outputs).

## 6. Test all workflows (finalize before demo)

Do this in **Studio** with the project opened from the **OneDrive** path. Goal:
every `.xaml` compiles (no analyzer **errors**, severity 1) and the end-to-end
path produces an output file.

### 6.1 Analyzer gate (CLI)

From the project folder:

```powershell
Set-Location "C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo"
uipcli package analyze ".\project.json" --resultPath ".\analyze.json" --ignoredRules ST-USG-034
```

Pass criteria: in `analyze.json`, **no entries with `ErrorSeverity` equal to
`1`**. Ignore `ErrorSeverity` `3` (informational stats).

### 6.2 Child workflows (quick compile check)

For each file under `Workflows\`:

1. Double-click the `.xaml` in Studio.
2. If Studio shows **0 errors** in the designer/analyzer panel for that file,
   the workflow compiles. Fix any red errors before continuing.
3. Optional **Run File**: set sensible **Test values** for arguments (e.g.
   `in_InvoiceFilePath` = full path to `Data\Input\sample_invoice.txt`, or a
   short test string for `in_InvoiceData` on `ApplyPolicy`). Confirm no
   fault and output arguments look right.

### 6.3 Main end-to-end (mandatory)

1. Put at least one file in `Data\Input\`:
   - **`.txt`** invoice (plain text, more than 10 characters), and/or
   - **`.pdf`** only if `ExtractInvoice` was implemented with PDF activities
     and the matching package is installed.
2. Open `Main.xaml`, press **F5** (Debug).
3. **Pass:** `Data\Output\` contains a `*_result.txt` whose body references the
   input file name, extracted text, and policy line.
4. **Fail:** no output file, or robot fault — open **Output** panel, read the
   exception, fix XAML or paths, re-run 6.1 then 6.3.

### 6.4 Repo-only regression (optional)

If you maintain a copy under this repository, from repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\ops\scripts\verify_invoice_intake_demo.ps1
```

That regenerates XAML from the deterministic emitter and runs the same style
of analyze gate (ST-USG-034 ignored in the JSON). It does **not** replace
sections 6.2–6.3 in Studio.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| Chat shows `Build is blocked: project has no approved design` banner after a run | The agent didn't finish the propose/approve handshake. See chat flow Prompt 4. |
| `uipcli package analyze` / `analyze.json` looks scary | In JSON, **`ErrorSeverity` 1 = Error** (must fix). **`ErrorSeverity` 3** (e.g. ST-ANA-009 file stats, ST-ANA-003 workflow count) is **information**, not a failing gate. |
| `uipcli package analyze` returns real errors (severity 1) | Fix the workflows, re-run analyze, then pack. Do not deploy on errors. |
| Agent wrote under the repo instead of OneDrive | You skipped `--project-dir` or the build prompt used the repo path. Close chat, restart with section 2 command, retry Prompt 2 with the OneDrive path only. |
| `uipcli package deploy` returns 401 | External App missing scopes. Re-issue the External App with default 25.10 scopes. |
| Studio `Manage Packages` shows red icons | Use **Manage Packages → Restore**, or run **`uipcli package pack`** on `project.json` (section 4) so dependencies restore. |
| Chat shows `SMOKE FAIL` | Read the `[label]` lines. Do not record; fix before continuing. |

---

## Chat flow for the demo

This is the exact sequence to type. Do not improvise. Every prompt has a
green-light signal (continue) and a red-flag signal (stop and fix).

### C1. Ground rules

- One intent per message. Don't combine "what is X" with "build Y".
- End questions with `?`. The classifier uses punctuation to route questions
  vs builds.
- Name the project by absolute path once, then refer to it as "the project".
- If the agent asks a follow-up, answer with a short phrase (`y`, `broader`,
  `ManagerApproval`), not a sentence.
- If you see `[BLOCKED]` or the "Build is blocked" banner, do NOT repeat the
  build prompt. Follow the scripted recovery in section C3.

### C2. Scripted prompt sequence

#### Prompt 1 - sanity check (optional, ~10s)

Type:

    what is a UiPath classic RPA project?

- Expected: streaming prose answer, no plan panel.
- Green light: you see prose, not an "Implementation Plan" box.
- Red flag: plan panel appears -> classifier fix didn't load. Abort, rerun
  `python ops/scripts/smoke_chat_pipeline.py`.

#### Prompt 2 - kick off the build

**Prerequisite:** you already started chat with `--project-dir` set to the **same**
folder as in the line below (see section 2).

Type (all one line). **Use this exact OneDrive path** — do not substitute the
repo clone path unless you mean to build there on purpose.

    build the InvoiceIntake_Demo project at C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo following the PDD and SDD in its docs folder

If `docs\` under that folder is empty or missing, use this variant instead
(same line shape, still no `?` at the end):

    build the InvoiceIntake_Demo classic RPA project at C:\Users\DanielaRosenstein\OneDrive - Cato Networks\Documents\UiPath\InvoiceIntake_Demo: Main.xaml orchestrates Data\Input and Data\Output, ForEach invoice file with TryCatch, InvokeWorkflowFile ExtractInvoice then ApplyPolicy then WriteResult; ExtractInvoice reads text from in_InvoiceFilePath to out_InvoiceData; ApplyPolicy sets out_PolicyResult from in_InvoiceData length rule; WriteResult writes under Data\Output using the pattern basename plus _result.txt; C# Windows project.json; unique activity DisplayNames and Log Message in each workflow; run uipcli package analyze when done

- Expected, in order:
  1. Dim pre-flight banner: `[DESIGN_GATE] project=...InvoiceIntake_Demo approved=false pending=none -> first write requires uipath_design_propose + uipath_design_approve.`
  2. Implementation Plan panel with `Approve plan? [y/n/edit]`.
- Green light: both appear.
- Red flag: no pre-flight banner -> the hardened executor code isn't loaded.
  Exit chat (`Ctrl+C`), re-open, retry.

#### Prompt 3 - approve the plan

Type:

    y

- Expected: agent runs read-only tools (`list_directory`, `read_project_json`),
  then calls `uipath_design_propose` (forced by the write-intent redirect
  before any write).
- Green light: `[STAGED] design_id=design_xxxxxx` block with a resolutions
  summary.
- Red flag: you see `[TOOL_CALL: run_uip_command]` with `design-propose` in
  args -> denylist didn't load (old process). Exit chat, re-open, retry.

#### Prompt 4 - approve the design

Type (copy the id from the staged block):

    approve design_id=design_xxxxxx

or, if the agent presents a y/n prompt for the design card, just:

    y

- Expected: `[OK] approved design_id=...`, then a stream of
  `[TOOL_CALL: write_file]` and `[TOOL_CALL: ensure_project_structure]`
  entries with `[OK]`.
- Green light: many `+ File created` lines accumulate.
- Red flag: `[REDIRECT] Project ... has no approved design` keeps repeating
  after you approved -> the approval didn't persist. Check
  `%USERPROFILE%\.uipath-builder-agent\design_proposals.json` is writable
  and `UIPATH_DESIGN_STORE_PATH` env isn't overriding to a read-only path.

#### Prompt 5 - wait, do not type

The agent will eventually call `uipath_workflow_build_and_verify` per the
plan's Phase 7. Cold runs take 30-120s. Do not type during this.

- Green light: final message includes `verdict='pass'` with tool call count
  > 15 ok.
- Red flag: the same `verdict='needs_llm_fix'` error appears twice in a row
  -> type `stop, report the last error and the file you tried to write.
  do not retry.` Don't let it loop a third time.

#### Prompt 6 - status check

Type:

    did you create the project?

- Expected: direct prose answer listing specific filenames (at minimum
  `Main.xaml`, `Workflows/ExtractInvoice.xaml`, `Workflows/ApplyPolicy.xaml`,
  `Workflows/WriteResult.xaml`, `project.json`), no new plan.
- Green light: concrete filenames in the response.
- Red flag: an Implementation Plan reappears -> status-question classifier
  fix didn't load. Recovery: exit and restart chat.

### C3. Recovery prompts

Use only when a specific red flag fires.

- Design gate keeps rejecting writes:
  `show the design gate status for <project_dir>`
  (agent should call `uipath_design_status`).
- A tool loops on the same error:
  `stop, summarize the last 3 tool calls and the error, do not retry.`
- Agent goes off-script and invents new phases:
  `return to the approved plan, do not add new phases.`

### C4. What NOT to type during the demo

- Any `?` question while the executor is mid-run (causes re-routing, wasted
  turns).
- "also add X" mid-build (forces re-planning).
- File paths with trailing backslashes on Windows (PowerShell line
  continuation).
- `yes`, `yeah`, `sure` - the plan approval prompt expects `y` exactly.

### C5. Hard stop criteria

Abort the demo and cut the recording if any of these happen twice in one
session:

- Pre-flight banner missing on a BUILD intent.
- `uip rpa design-propose` or `uip rpa design-approve` appears in tool calls.
- Agent finishes a BUILD turn with zero write tool calls and no BLOCKED
  banner.

These are the three symptoms the hardening is designed to eliminate. If they
still fire, the code changes didn't load into the chat process.

---

## Appendix A: Studio terminal one-shot (self-drive)

**Warning:** this appendix writes output under the **repository** tree (or a
subfolder you name there). It is **not** the same as the main runbook, which
targets **OneDrive** via `--project-dir`. Use **Appendix A only** for CI,
quick experiments, or when you explicitly want artifacts in the clone. For a
Studio demo you open from OneDrive, **skip Appendix A** and use sections 2–6
above.

### A.1 Prep

```powershell
Set-Location C:\Users\DanielaRosenstein\projects\uipath-builder-agent

# Do NOT set UIPATH_PROJECT_DIR for this path. Leaving it unset lets the
# agent create a fresh project subfolder directly under the repo root.
Remove-Item Env:UIPATH_PROJECT_DIR -ErrorAction SilentlyContinue

$env:UIPATH_SKIP_AUTH_CHECK         = "1"   # skip cloud auth prompt
$env:UIPATH_TOOL_APPROVAL           = "0"   # don't gate tool calls
$env:UIPATH_DESIGN_APPROVAL_ENABLED = "0"   # one-shot, no propose/approve
$env:PYTHONIOENCODING               = "utf-8"
chcp 65001 | Out-Null
```

### A.2 Run (interactive)

```powershell
uipath-claude chat
```

Prompt to paste (single line, edit scope as needed):

    build an InvoiceIntake_Demo classic RPA UiPath project. C# / .NET 8 / Windows. Four XAML workflows: Main.xaml plus Workflows/ExtractInvoice.xaml, Workflows/ApplyPolicy.xaml, Workflows/WriteResult.xaml. Use create_xaml_workflow for every XAML file and validate_xaml after each. Place outputs under a subdirectory named InvoiceIntake_Demo.

Then `y` at the plan prompt. Wait for the executor to finish (tool-call
stream, then final Assistant message). Type `exit`.

### A.3 Run (non-interactive, one shot)

Same env vars as A.1. Pipe a scripted stdin:

```powershell
$prompt = 'build an InvoiceIntake_Demo classic RPA UiPath project. ' +
          'C# / .NET 8 / Windows. Four XAML workflows: Main.xaml plus ' +
          'Workflows/ExtractInvoice.xaml, Workflows/ApplyPolicy.xaml, ' +
          'Workflows/WriteResult.xaml. Use create_xaml_workflow for every ' +
          'XAML file and validate_xaml after each. Place outputs under a ' +
          'subdirectory named InvoiceIntake_Demo.'
@($prompt, 'n', 'exit') -join "`n" |
  uipath-claude chat --auto-approve-plan 2>&1 |
  Tee-Object -FilePath chat_run.log
```

Note: single-shot pipes are brittle. If iteration budget is exhausted
(look for `Max iterations (35) reached`), rerun interactively.

### A.4 Ground-truth gate (uipcli 25.10+, positional path to project.json)

```powershell
Set-Location .\InvoiceIntake_Demo

uipcli package analyze ".\project.json" --resultPath ".\analyze.json" --ignoredRules ST-USG-034
```

Parse `analyze.json`: **any `ErrorSeverity` of `1` is a hard fail.** Severity
`3` is informational (e.g. ST-ANA-009). Do not record the demo until severity-1
is clean (or you have an explicit human sign-off for a listed rule).

Flags to note for 25.10+:
- `--projectsPath` / `--projectPath` are **gone**. Pass `project.json` as the
  first positional argument to `analyze` / `pack`.
- Standalone `package restore` may require `--restoreFolder` and
  `--nugetConfigFilePath` on your CLI build; **`package pack`** restores as part
  of the build when dependencies are missing — prefer **section 4** for the
  OneDrive copy.

### A.5 Known failure modes seen during the 2026-04-21 run

| Symptom | Likely cause |
|---|---|
| `Could not load Main.xaml ... DynamicActivity ... is null` | Missing xmlns aliases (e.g. `xmlns:s`, `xmlns:scg`) referenced later in the XAML. |
| `BC30512 Option Strict On disallows ...` on a `CSharp` project | Project declares `expressionLanguage: CSharp` but XAML lacks `TextExpression.Language="CSharp"` / the compiler falls back to VB. Regenerate with that attribute on the root `<Activity>`. |
| `BC36637 The '?' character cannot be used here` | Same root cause: C# null-conditional in a workflow being parsed as VB. |
| Agent ends with `Max iterations (35) reached` | Budget exhausted. Re-run; consider raising `UIPATH_MAX_ITER_EXTEND`. |

Treat A.4 as the demo gate. If it fails: the artifacts exist but the
project is **not** demo-ready; do not publish.

