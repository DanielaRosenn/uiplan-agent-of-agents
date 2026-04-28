# Smoke Tests

For a **tabular** full-project review (tick each MCP tool and repo gate with PASS/FAIL/BLOCKED and submit results), use [MANUAL_REVIEW_CURSOR_FULL_PROJECT.md](MANUAL_REVIEW_CURSOR_FULL_PROJECT.md). This file stays **scenario-based** (long flows, env tables, step-by-step).

## Model + profile env vars

Optional environment overrides (everything has sensible defaults):

| Variable | Purpose |
|---|---|
| `UIPATH_CLAUDE_MODEL_HEAVY` | Bedrock model for HEAVY tasks (BA, SA, Dev, QA, planner, agentic executor). Default: `anthropic.claude-3-5-sonnet-20241022-v2:0`. |
| `UIPATH_CLAUDE_MODEL_LIGHT` | Bedrock model for LIGHT tasks (distiller, classifiers, short-text rewrites). Default: `anthropic.claude-3-5-haiku-20241022-v1:0`. |
| `UIPATH_CLAUDE_MODEL` | Legacy global override; applies to both tiers unless a per-tier var is set. |
| `UIPATH_CLAUDE_TOOL_PROFILE` | `all` (default), `safe`, or `uipath-dev`. Gates slash commands in `uipath chat`; `safe` and `uipath-dev` use the same SDLC-focused allow-list ([SLASH_COMMANDS.md](SLASH_COMMANDS.md)). |
| `UIPATH_DISTILLER_MODEL` | Explicit override for the skill distiller only (beats the tier router). |

To use Sonnet 4.x when Bedrock has it enabled in your region, you must use a
**cross-region inference profile id** (the `us.` prefix); the raw model id is
not available with on-demand throughput and Bedrock will reject it with
`ValidationException`:

```powershell
$env:UIPATH_CLAUDE_MODEL_HEAVY = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

A customer-created inference-profile ARN (`arn:aws:bedrock:...:inference-profile/...`)
also works. Setting the raw `anthropic.claude-sonnet-4-...` id triggers a
one-time startup warning and a friendly hint on the resulting Bedrock error.

## MCP approval cards (Cursor)

Every tool exposed by the MCP server now ships `ToolAnnotations`
(`readOnlyHint` / `destructiveHint` / `idempotentHint`). Cursor uses
`destructiveHint=true` to surface its native Allow/Deny card before invoking
writers like `uipath_library_approve_proposal`, `uipath_workflow_write_file`,
`uipath_workflow_run`, or `uipath_workflow_deploy`. Read-only tools
(`uipath_library_search`, `uipath_doc_*`, etc.) and staging tools
(`uipath_library_propose_*`, `uipath_skill_insights_add`) run without prompting
once the server is trusted. To smoke-test, trigger
`uipath_library_approve_proposal` from Cursor and confirm the approval card
appears; trigger `uipath_library_search` and confirm it does not.

## Build / verify loop and scaffold guard (Cursor MCP)

Verifies the analyze-debug-fix loop wired into the MCP so Cursor can't mark a
UiPath build "done" without it.

1. From Cursor, ask the agent to build a one-activity project (e.g. a Log
   Message workflow) in a fresh directory. Expect the agent to call:
   - `uipath_workflow_environment_probe` BEFORE picking activity packages.
   - `uipath_workflow_create_project` to scaffold (NOT `write_file` on
     `project.json`).
   - `uipath_workflow_write_file` for `Main.xaml` only.
   - `uipath_workflow_build_and_verify` after the write, until it returns
     `success=true` and `next_action: "none"`.
2. Try to make Cursor hand-write `project.json` directly. Expect
   `uipath_workflow_write_file` to refuse with a message pointing at
   `uipath_workflow_create_project` / `uipath_workflow_install_package`
   unless `allow_scaffold_overwrite=true` is supplied explicitly.
3. Introduce a typo in `Main.xaml` (e.g. break a closing tag). Expect the
   next `uipath_workflow_build_and_verify` call to return `success=false`
   with `phase: "validate"` and the error in `errors[0]`. Confirm Cursor
   applies a single `write_file` fix and re-calls until `success=true`.
4. Pin a mismatched dependency (e.g. add `UiPath.Core.Activities: "[22.10.3]"`
   alongside `UiPath.System.Activities: "[26.2.4]"`) using
   `allow_scaffold_overwrite=true`. Expect
   `uipath_workflow_build_and_verify` to short-circuit with
   `phase: "probe"`, `next_action: "install_packages"`, and the mismatch
   listed in `errors`. Confirm Cursor calls
   `uipath_workflow_install_package` (or `create_project`) instead of
   re-editing `project.json`.

## Studio Designer validation guard

Use this smoke whenever a task creates, copies, or heavily edits a Studio/RPA
project, especially when layering a use case on top of a template.

1. Run Studio-aware per-file validation on every edited `.xaml`:

   ```powershell
   uip rpa get-errors --file-path "<file.xaml>" --project-dir "<projectDir>" --studio-dir "C:\Program Files\UiPath\Studio" --output json
   ```

   Expected result: `No diagnostics found`.

2. Run a full Studio build before pack/deploy:

   ```powershell
   uip rpa build --project-path "<projectDir>" --studio-dir "C:\Program Files\UiPath\Studio" --output json
   ```

   Expected result: `Success: true`.

3. If the build reports that the project is already open in Studio, close it and
   rerun the build:

   ```powershell
   uip rpa close-project --project-dir "<projectDir>" --studio-dir "C:\Program Files\UiPath\Studio" --output json
   ```

4. Only after Studio Designer validation and Studio build pass, run
   `uipcli package analyze`, pack/deploy, and Orchestrator smoke.

Reason: `uipcli package analyze`, solution pack, deployment, and a successful
Orchestrator job can still miss Studio Designer diagnostics. Copied
VisualBasic templates are especially sensitive to missing imports/references
for types such as `Dictionary` and `List`.

Two focused smoke tests that exercise the full surface: knowledge pipeline,
unified Ask AI, library proposals + chapters, book manifests, skills
auto-refresh, upstream scan, harvest, and MCP parity.

## CLI test (PowerShell)

Run from the repo root (`uipath-builder-agent`).

```powershell
# 0. Env: force a fresh session so the new per-session refresh actually triggers
$env:UIPATH_CHAT_SESSION_ID = "smoke-" + (Get-Date -Format "yyyyMMddHHmmss")
$env:UIPATH_SKILLS_AUTO_REFRESH = "1"
# Optional: enable web-search leg of the knowledge pipeline
# $env:UIPATH_WEB_SEARCH_ENABLED = "1"
# $env:TAVILY_API_KEY = "..."   # or SERPAPI_API_KEY

# 1. Launch chat; watch startup banner for "Skills cache: updated ..." or "skipped: ..."
python -m uipath_claude.cli.app chat
```

> Note: `python -m uipath_claude.cli.app` on its own prints "Missing command".
> The app is a Typer multi-command CLI. Use `chat`, `start-project`, or
> `library-proposals`.

Inside the chat REPL, run these slash-commands one by one:

```
/books                     # lists library books + manifest fields (audience, curator, license)
/books --info              # shows MANIFEST.yaml metadata per book
/scan-upstream-skills      # diff of new/removed skills in the skills/ submodule
/library-harvest           # enqueues NEW_SECTION proposals from every upstream SKILL.md
/library-proposals list    # shows queued proposals (from harvest + any chapter proposals)
```

Ask the agent a UiPath question to exercise the knowledge pipeline
(library → Ask AI → optional web search). Expect citations in the answer:

```
How do I schedule a job in UiPath Orchestrator? Cite sources.
```

Approve one harvested proposal end-to-end:

```
/library-proposals list
/library-proposals approve <paste-a-proposal-id>
```

Re-run scan; diff should show no *new* changes this session:

```
/scan-upstream-skills
```

Exit, then re-enter with the SAME session id to prove per-session skip:

```powershell
exit
python -m uipath_claude.cli.app chat
# Banner should show: "Skills cache: skipped: same session"
```

New session id => refresh runs again (force-reset, backup branch on drift):

```powershell
$env:UIPATH_CHAT_SESSION_ID = "smoke-" + (Get-Date -Format "yyyyMMddHHmmss")
python -m uipath_claude.cli.app chat
```

## Full chat test drive: build a real UiPath project

This exercises BA → SA → planner → Dev → QA, the knowledge pipeline, Ask AI,
skills, and Studio integration end-to-end.

1. Sanity checks inside the chat REPL:

   ```
   /books --info
   /scan-upstream-skills
   ```

2. Kick off a project via free-text chat:

   ```
   Build a UiPath attended automation called "InvoiceTriage" that:
    - watches a SharePoint folder for new PDF invoices,
    - extracts vendor, invoice number, total, and due date using Document Understanding,
    - writes the results to a SQL Server table dbo.Invoices,
    - sends a Teams notification on failure.
   Use our library as the primary source and cite sources.
   ```

   Expected flow:
   - BA produces requirements.
   - SA produces a design with citations like `[uipath-docs/...]`.
   - Planner emits a plan; approve it when prompted.
   - Dev writes the project (XAML + `project.json`).
   - QA adds and runs tests.

3. Verify artifacts (in a second PowerShell, same cwd):

   ```powershell
   Get-ChildItem .\InvoiceTriage
   Get-Content .\InvoiceTriage\project.json -TotalCount 40
   ```

4. Non-interactive bootstrap path (second confirmation):

   ```powershell
   python -m uipath_claude.cli.app start-project InvoiceTriage2
   ```

5. Follow-ups inside chat to hit more tools:

   ```
   Ask UiPath AI: difference between attended and unattended robots.
   Look up "retry scope best practices" in the library and cite.
   /library-proposals list
   /library-proposals approve <id>
   ```

### What to verify

- Citations on any knowledge lookup answer.
- `InvoiceTriage/` contains a valid `project.json`, `Main.xaml`, and tests.
- No errors referencing `install_git_hooks`.
- Second chat launch with the same `UIPATH_CHAT_SESSION_ID` prints
  `Skills cache: skipped: same session`.

### What to verify

- Banner prints `Skills cache: updated ...` on first run, `skipped: same session` on the second.
- `/books --info` shows `audience: agent`, `curator: uipath-builder-agent`, etc. for `uipath-docs`.
- `/library-harvest` returns "N proposals enqueued" and `/library-proposals list` shows them.
- The UiPath question answer contains bracketed citations like `[uipath-docs/<chapter>/<section>]` or an Ask-AI source.
- After approve, the target section exists under `data/library/books/uipath-docs/<chapter>/<section>.md`.
- No `post-merge` / `post-checkout` / `post-rewrite` files in `.git/hooks/` (removed).

## Cursor test (MCP tools)

Point Cursor's MCP config at this repo's server (already wired via
`mcp_server/server.py` and `.cursor/mcp.json`). Setup prerequisites are in
the "MCP setup (Cursor)" section of [CONTRIBUTING.md](../CONTRIBUTING.md#mcp-setup-cursor).
In a Cursor chat, run these prompts in order — each one forces a specific
`uipath_library_*` tool and exercises the same surface without the CLI.

> **Why these prompts name the tool explicitly:** Cursor's tool router will
> happily answer "List books" by reading `data/library/catalog.yaml` with
> `Read`/`Glob`/`SemanticSearch`, which bypasses the MCP surface entirely
> and silently passes the test. Each prompt below names the MCP tool and
> forbids raw file reads so the test actually verifies the MCP path. If a
> step still resolves to a file read, that is itself a failure — flag it.

0. **Verify the MCP server is loaded.** In Cursor, open the tool picker (or
   ask the agent: "What MCP tools do you have available? List every tool
   whose name starts with `uipath_`."). Confirm at least
   `uipath_library_list`, `uipath_library_search`, and `query_uipath_docs`
   appear. If they do not, **stop** — fix the MCP wiring per
   [CONTRIBUTING.md](../CONTRIBUTING.md#mcp-setup-cursor) before continuing.
   Every step below assumes those tools are visible; without them the test
   will silently "pass" by falling back to `SemanticSearch`/`Read` and the
   smoke test loses all signal. Two recent transcripts hit exactly this
   failure mode: the agent answered "List books" with a workspace search
   one session and a clarifying question the next, both because no
   `uipath_library_*` tool was actually registered.

1. **List books**
   > "Use the `uipath_library_list` MCP tool to list all UiPath library books with their manifests. Do not read `data/library/catalog.yaml` or scan `data/library/books/` directly."
   Calls `uipath_library_list`; shows audience/curator/license.

2. **TOC**
   > "Use the `uipath_library_toc` MCP tool to show the table of contents for the `uipath-docs` book. Do not read `data/library/books/uipath-docs/book.yaml` directly."
   Calls `uipath_library_toc`.

3. **Search**
   > "Use the `uipath_library_search` MCP tool to search the library for 'orchestrator schedule' and show the top 3 sections. Do not Grep or SemanticSearch `data/library/`."
   Calls `uipath_library_search`.

4. **Read section**
   > "Use the `uipath_library_read_section` MCP tool to read section <paste id from step 3>. Do not read the underlying `.md` file directly."
   Calls `uipath_library_read_section`.

5. **Full knowledge lookup**
   > "Use the `uipath_library_lookup` MCP tool to answer 'how to create an attended robot' using the full knowledge pipeline. Cite sources."
   Calls `uipath_library_lookup` (library → Ask AI → web if enabled). The
   answer always ends in a `SOURCE:` line (`library:`, `askai`, web, or
   `none` on full miss); citations **must** be present whenever any backend
   succeeds.

6. **Propose a chapter**
   > "Use the `uipath_library_propose_chapter` MCP tool to propose a new chapter 'Patterns' in `uipath-docs` with an initial section called 'Retry loops', then call `uipath_library_list_proposals` to confirm it queued."
   Calls `uipath_library_propose_chapter` (and optionally
   `uipath_library_propose_section` for individual sections), then
   `uipath_library_list_proposals`. Verify the proposal shows `kind = new_chapter`.

7. **Approve**
   > "Use the `uipath_library_approve_proposal` MCP tool to approve proposal <id from step 6>."
   Calls `uipath_library_approve_proposal`. Check that
   `data/library/books/uipath-docs/patterns/` now exists with `chapter.yaml`.

8. **Reject**
   > "Use the `uipath_library_reject_proposal` MCP tool to reject proposal <another id>."
   Calls `uipath_library_reject_proposal`; it should disappear from the list.

9. **Unified Ask AI**
   > "Use the `query_uipath_docs` MCP tool to ask UiPath AI: what's the difference between attended and unattended?"
   Invokes `query_uipath_docs` (SDK-first, HTTP fallback). The legacy alias
   `uipath_doc_query` still resolves to the same handler for one release.

   **Step 9 prerequisites (clean clone).** Out of the box this step has no
   backend wired up. Pick one of:

   1. **Production path.** Set `UIPATH_ASKAI_ENDPOINT=<your Ask AI URL>`
      (and `UIPATH_ASKAI_API_KEY` if the endpoint requires it) before
      starting the MCP server. The HTTP fallback above will be used.
   2. **Local-fixture path (for smoke verification only).** Set
      `UIPATH_ASKAI_ENDPOINT=mock://localfixture` before starting the MCP
      server. The tool short-circuits to a deterministic local response
      that includes a `SOURCE: askai-mock` line, which is enough to mark
      the smoke step PASS without provisioning Ask AI.
   3. **Bundled SDK path.** If `skills/skills/uipath-askai/` is installed
      and its `uipath_askai_config.json` is configured, the SDK path is
      preferred over both options above.

### What to verify in Cursor

- Every step invokes a distinct `uipath_library_*` / `query_uipath_docs` /
  `lookup_uipath_knowledge` tool (visible in the tool-call trace).
- Proposals round-trip: create → list → approve writes files; reject removes them.
- Citations appear on any knowledge lookup answer.
- No errors about git hooks or missing `install_git_hooks` (proves the removal is clean).

If any step fails, grab the tool-call payload from Cursor's trace and the
corresponding log line — that's enough to pinpoint whether the failure is in
the library layer, Ask AI, or the updater.

## Cursor real-project scenarios (gap-finding suite)

These are full-flow exercises designed to be **recorded** so we can grade BA /
SA / Developer / QA persona quality, PDD/SDD/TDD/ADD output, library citation
discipline, and Studio-level fidelity. Run each in a clean folder so artifacts
don't collide.

For each scenario, capture: (1) the chat transcript, (2) the contents of
`docs/` and the generated project, (3) which Cursor tool calls fired
(`uipath_library_*`, `query_uipath_docs`, `lookup_uipath_knowledge`,
`generate_pdd`, `generate_sdd`, etc.), (4) the model id reported by
`/status` for each persona turn (heavy vs light).

### Setup (once per scenario)

```powershell
$dir = "smoke-" + (Get-Date -Format "yyyyMMddHHmm")
New-Item -ItemType Directory $dir | Out-Null
Set-Location $dir
$env:UIPATH_CHAT_SESSION_ID = $dir
python -m uipath_claude.cli.app
```

In the chat, before each scenario: `/status` (record active profile + model
ids) and `/books` (confirm library is reachable).

### Scenario 1 - Simple attended bot (low complexity, no docs expected)

> "Create a small attended automation 'HelloFolder' that pops a dialog with
> the count of files in C:\\Temp. No integrations, no approvals."

Expected:
- Doc-need detector returns `NONE` or `OPTIONAL` (low complexity score).
- BA short PDD section only; no SDD/TDD/ADD.
- Developer emits a `Main.xaml` with `Assign` + `MessageBox` activities,
  `project.json` targets Windows attended.
- QA proposes 1-2 tests max.

Gaps to watch: persona over-producing docs for a trivial brief; Developer
defaulting to cross-platform target; QA inventing infra it doesn't need.

### Scenario 2 - Orchestrator queue processor (REFramework-shaped)

> "Build a UiPath unattended robot 'InvoiceQueueProcessor' that dequeues from
> Orchestrator queue 'Invoices', validates fields (Vendor, Amount, DueDate),
> writes valid items to SQL Server table dbo.Invoices, and posts business
> exceptions back to Orchestrator. Use the UiPath library for design
> guidance and cite sources."

Expected:
- BA produces a PDD with inputs/outputs, business exceptions, SLAs.
- SA produces an SDD that names REFramework, Get Transaction Item, retries,
  business vs system exception split. Citations like `[uipath-docs/...]` for
  each design choice.
- Developer scaffolds a REFramework-style project (states / TransactionItem
  argument / `Process.xaml`).
- QA covers: invalid row, queue retry, SQL outage.
- `lookup_uipath_knowledge` should fire at least once during SA stage.

Gaps to watch: missing REFramework reference, no business-exception
handling, no idempotency/duplicate-key consideration, no citations.

### Scenario 3 - Document Understanding + SharePoint + Teams

> "Build attended automation 'InvoiceTriage' that watches a SharePoint folder
> for new PDFs, extracts vendor/invoiceNumber/total/dueDate via UiPath
> Document Understanding, writes results to SQL Server dbo.Invoices, and
> posts a Teams message on failure. Cite sources from our library."

Expected:
- Doc-need = `RECOMMENDED` or `REQUIRED` (multi-system + integrations).
- PDD + SDD + TDD generated; ADD only if AI/agentic phrasing used.
- SDD lists: SharePoint trigger, DU taxonomy/extractor, validation station
  (HITL) decision, SQL connector, Teams webhook.
- Developer scaffolds workflow files and `project.json`; references DU and
  SharePoint activity packages.
- QA includes: missing field, low-confidence extraction, SQL down, Teams
  webhook 4xx.

Gaps to watch: HITL/validation station not mentioned, missing taxonomy
file, no retry/backoff, generic answer with no library citations.

### Scenario 4 - Build from an existing PDD (no BA stage)

Pre-create `docs/pdd.md` with a 1-page brief in the current folder, then:

> "I already wrote a PDD at `docs/pdd.md`. Read it, skip the BA stage, and
> have SA + Developer + QA produce the rest. Reference my PDD verbatim
> where relevant."

Expected:
- BA stage is skipped or merely echoes the existing PDD.
- SDD references PDD section ids/headings.
- No re-derivation of process steps from scratch.

Gaps to watch: BA persona ignores the file and rewrites a PDD; SDD doesn't
cite the PDD; conflicting facts vs the PDD.

### Scenario 5 - Build from an existing SDD (Developer + QA only)

Pre-create `docs/sdd.md` with target architecture and component list, then:

> "Use my `docs/sdd.md` as the source of truth. Generate the implementation
> and the test plan only."

Expected: Developer + QA fire; BA/SA produce nothing new (or only deltas).

Gaps to watch: persona scope creep (BA/SA re-running), Developer ignoring
the SDD's component names.

### Scenario 6 - Persona swap mid-conversation

After Scenario 2 finishes, in the same chat:

> "As the QA persona only, add 5 more negative-path tests covering
> Orchestrator outage and queue poisoning."

Expected: only QA-style output (test cases, given/when/then, no PDD/SDD
re-generation). Model router should still route this to the heavy tier
(`qa`).

Gaps to watch: agent silently switches to BA voice; output drifts into
prose; model routing log shows light tier.

### Scenario 7 - Library-driven design choice

> "I need a retry strategy for a flaky HTTP API call inside an attended bot.
> Search our library, then propose the pattern with code skeleton. Cite the
> exact section ids."

Expected: `uipath_library_search` -> `uipath_library_read_section` ->
answer cites `book/chapter/section`. If nothing matches in the library, the
agent should call `lookup_uipath_knowledge` and offer to enqueue a new
library section via `propose_library_update`.

Gaps to watch: agent answers from training data with no tool call; no
citation; no proposal when the library lacked the topic.

### Scenario 8 - Bedrock model swap mid-session

```
You: /status
You: (pick the model id printed for HEAVY)
```

Then exit, set `$env:UIPATH_CLAUDE_MODEL_HEAVY="us.anthropic.claude-sonnet-4-5-20250929-v1:0"`,
re-enter chat, run Scenario 2 again. Compare PDD/SDD verbatim.

Gaps to watch: regression on Sonnet 4.5 (e.g. less library tool usage,
worse XAML), or the opposite (no quality lift, paying more for nothing).

### Scenario 9 - Cursor MCP-only flow (no CLI)

In Cursor (not the CLI), prompt:

> "Use only `uipath_library_*` and `query_uipath_docs` tools. Build a PDD
> and SDD for an unattended bot that reconciles two CSVs and emails the
> diff. Quote the library section ids you used."

Expected: every claim is backed by a tool call visible in Cursor's trace.

Gaps to watch: hallucinated section ids, prose answer with no tool calls,
or Cursor loses the MCP server connection.

### Scenario 10 - Failure modes / negative paths

Run each in isolation; the agent should degrade gracefully:

| Trigger | Expected behavior |
|---|---|
| Disconnect network, ask Scenario 7 | `lookup_uipath_knowledge` falls back to library only; no crash; `web_search` reports disabled. |
| `UIPATH_TOOL_PROFILE=safe`, then `/library-harvest` | Blocked with the profile message. |
| Pre-create a corrupt `data/library/books/uipath-docs/MANIFEST.yaml` | `/books --info` recovers, shows empty manifest fields, no traceback. |
| Set `UIPATH_CLAUDE_MODEL_HEAVY=does-not-exist` and run Scenario 1 | Bedrock error surfaces in chat, not a Python crash. |
| Kill UiPath Studio mid-Developer-stage | Developer stage reports the failure and continues writing files; QA still runs. |

### Recording checklist (per scenario)

- [ ] Scenario id + commit sha (`git rev-parse HEAD`).
- [ ] `/status` output before run.
- [ ] Full chat transcript.
- [ ] Final `tree` (or `Get-ChildItem -Recurse`) of the project folder.
- [ ] `docs/pdd.md`, `docs/sdd.md`, `docs/tdd.md`, `docs/add.md` (whichever exist).
- [ ] Cursor tool-call list (which tools fired, and the input args of each).
- [ ] Subjective quality grade per persona (1-5) with one-line note.
- [ ] One concrete gap or improvement idea.

Drop the recordings in `docs/recordings/<date>-<scenario-id>/` and we'll
post-process them into persona/prompt/library improvements.

## End-to-end deploy scenarios (build -> test -> publish to UiPath Cloud)

These two scenarios go all the way: chat builds the project, the agent runs
the project's tests, then **publishes a package to Orchestrator** in UiPath
Cloud and triggers one run. They're the highest-signal smoke tests because
they fail loudly on auth, packaging, or activity-version drift.

### Prerequisites (once)

1. UiPath Automation Cloud account with an Orchestrator tenant + folder you
   can publish to.
2. The `uipath` CLI installed and on PATH (`uipath --version` works).
3. `.env` filled in (see `.env.example`):

   ```env
   UIPATH_ORCHESTRATOR_URL=https://cloud.uipath.com/<account>/<tenant>/orchestrator_
   UIPATH_TENANT_NAME=<tenant>
   UIPATH_FOLDER_PATH=Shared
   # pick ONE auth mode:
   UIPATH_PAT=<personal-access-token>
   # or
   # UIPATH_CLIENT_ID=...
   # UIPATH_CLIENT_SECRET=...
   ```
4. Authenticate the CLI once outside the chat so the chat's deploy step has
   a token cache to reuse:

   ```powershell
   uipath auth login
   uipath auth tenant set "$env:UIPATH_TENANT_NAME"
   ```
5. **Use a non-production folder.** Both scenarios will publish a real
   package and start a real job.

### Scenario 11 - RPA project: build, test, publish, run on Orchestrator

Goal: classic attended/unattended UiPath project, packaged and shipped to
Cloud Orchestrator end-to-end from chat.

```powershell
$dir = "deploy-rpa-" + (Get-Date -Format "yyyyMMddHHmm")
New-Item -ItemType Directory $dir | Out-Null
Set-Location $dir
$env:UIPATH_CHAT_SESSION_ID = $dir
python -m uipath_claude.cli.app
```

Prompt (single message, in chat):

> "Build an unattended UiPath RPA project named `SmokeReconBot` that reads
> `input.csv` from the project root, filters rows where column `Status` =
> `Open`, and writes the result to `output.csv`. Cite library sections you
> use. Then:
> 1. Generate `input.csv` with 5 sample rows (3 Open, 2 Closed).
> 2. Run the project's tests locally with `uipath run` (or the test runner
>    the skill recommends) and show me the output.
> 3. Pack the project with `uipath pack`.
> 4. Publish the .nupkg to Orchestrator using my `.env` credentials
>    (`uipath publish`) into folder `Shared`.
> 5. Create/refresh a process for it and start one job (`uipath run` against
>    Orchestrator, or `Jobs.StartJobs`).
> 6. Print: package id + version, process key, job id, and final job state.
> Stop and ask before any destructive action (deleting prior versions,
> changing folder permissions)."

Expected:
- Files produced: `project.json`, `Main.xaml` (or coded equivalent), at
  least one test workflow under `Tests/`, generated `input.csv`, and a
  populated `output.csv` after the local test run.
- The chat shows three distinct CLI invocations: `uipath pack`,
  `uipath publish`, `uipath run` (or REST equivalent).
- Final summary contains a real package version (e.g. `1.0.0`), a non-empty
  job id, and a terminal state (`Successful` ideally; `Faulted` is also a
  valid signal as long as it's reported, not hidden).

Gaps to watch:
- Agent fakes the publish step (returns plausible-looking ids without
  calling `uipath publish`). Cross-check by running `uipath orchestrator
  packages list` after the run and confirming the version is there.
- Activity package versions in `project.json` don't match the tenant's
  available versions - publish succeeds, job faults at start.
- Auth flow not picked up from `.env` (agent re-prompts for credentials in
  chat - never paste them; abort and check env loading).
- No QA stage / no tests generated; only happy path executed.
- Missing `output.csv` assertion in tests, so a silent no-op would pass.

Cleanup:

```powershell
uipath orchestrator packages delete --name SmokeReconBot --version <ver>
```

### Scenario 12 - Maestro flow: build, validate, publish, run

Goal: same loop, but for a Maestro `.flow` project. Use the
`uipath-maestro-flow` skill's canary as the shape reference.

```powershell
$dir = "deploy-maestro-" + (Get-Date -Format "yyyyMMddHHmm")
New-Item -ItemType Directory $dir | Out-Null
Set-Location $dir
$env:UIPATH_CHAT_SESSION_ID = $dir
python -m uipath_claude.cli.app
```

Prompt (single message):

> "Build a UiPath Maestro flow project named `SmokeWeatherFlow` that takes
> a `city` input, calls a public weather API (e.g. open-meteo, no key
> required), and outputs `temperature_c` and `condition`. Use the
> `uipath-maestro-flow` skill from our library; cite the section ids you
> rely on. Then:
> 1. Validate the `.flow` file with the skill's `flow_check` (or the
>    Maestro CLI validator).
> 2. Run the canary / unit check locally and show the output.
> 3. Pack and publish to my UiPath Cloud tenant
>    (`UIPATH_ORCHESTRATOR_URL`, folder `Shared`).
> 4. Trigger one execution with input `city=London` and report the run id +
>    final outputs.
> Ask before overwriting any existing flow with the same name."

Expected:
- A real `.flow` file gets generated (not just a YAML stub) with at least
  one HTTP node and one output node.
- Library citations point at `skills/skills/uipath-maestro-flow/...` (e.g.
  `references/flow-commands.md`).
- Validation output is shown verbatim, not summarized away.
- Publish + run use the Maestro endpoints (the agent should pick the
  Maestro-flavored publish, not the RPA `uipath pack`).
- Final summary shows run id + the parsed outputs (`temperature_c`,
  `condition`).

Gaps to watch:
- Agent treats this as an RPA project and tries `uipath pack` on a `.flow`
  - that's a clear persona/skill-routing miss.
- No mention of the `uipath-maestro-flow` skill in the answer (means
  library lookup didn't fire).
- Validation skipped; agent jumps straight to publish.
- HTTP node hardcodes a key-required API instead of the keyless one
  requested.
- Run completes but outputs aren't extracted into the chat summary.

Cleanup: delete the published flow from the Maestro UI in your tenant.

### Recording additions for Scenarios 11 & 12

In addition to the standard recording checklist, capture:

- [ ] Output of `uipath --version` and `uipath auth whoami`.
- [ ] `Get-Content .env | Select-String '^UIPATH_'` (redact tokens) to prove
      what env the agent saw.
- [ ] Each CLI command the agent ran, with full stdout/stderr (Cursor /
      terminal scrollback).
- [ ] Orchestrator screenshot or `uipath orchestrator packages list`
      output showing the new version.
- [ ] Job/run id + final state from Orchestrator UI.
- [ ] Time from "send prompt" to "job state reported" (end-to-end latency).

## MCP debug-loop enforcement

Verifies that the Cursor MCP cannot mark a UiPath project "done" without a
real analyze/debug/fix cycle. Three scripted checks against the
`uipath-builder-agent` MCP server.

### Setup

```powershell
$env:UIPATH_MCP_GATE_ENABLED = "1"
$dir = "$env:TEMP\uipath-gate-smoke-$(Get-Date -Format yyyyMMddHHmmss)"
New-Item -ItemType Directory $dir | Out-Null
Set-Location $dir
```

From Cursor, ask the agent to scaffold a one-activity project (Log Message)
into `$dir` via `uipath_workflow_create_project`. Confirm it auto-verifies
and `uipath_workflow_session_status` reports `status=verified`.

### Check 1 - Dirty state blocks run/deploy

1. Edit `Main.xaml` via `uipath_workflow_write_file` (introduce a typo such
   as a missing `</Sequence>` close).
2. Without calling `uipath_workflow_build_and_verify`, ask the agent to
   call `uipath_workflow_run`.
3. Expected: the run tool returns `[BLOCKED] Project '<dir>' has unverified
   changes (Main.xaml). Call uipath_workflow_build_and_verify ...`.
4. `uipath_workflow_session_status { project_dir: $dir }` shows
   `status=dirty` and lists `Main.xaml` in `last_dirty_files`.
5. Same expectation for `uipath_workflow_deploy`,
   `uipath_workflow_install_package`, `uipath_workflow_debug`, and
   `uipath_workflow_run_command`.

### Check 2 - build_and_verify captures headless and Studio results

1. Fix the typo via `uipath_workflow_write_file`.
2. Call `uipath_workflow_build_and_verify` with `run_after_validate=true`
   and default `studio_debug_after_run=true`.
3. Expected payload contains:
   - `verdict: "pass"` and `success: true`.
   - `headless_log` non-empty.
   - When UiPath Studio is running on the host: `studio_debug_log`
     non-empty and the `phase` reaches `studio_debug`.
   - When Studio is not running: `studio_debug_skipped_reason` explains the
     skip and `headless_log` alone justifies the pass.
4. `uipath_workflow_session_status` flips back to `status=verified`.

### Check 3 - Status transitions dirty -> verified -> dirty

1. After Check 2, write a no-op edit (add a comment) via
   `uipath_workflow_write_file`.
2. Expected: `uipath_workflow_session_status` reports `status=dirty` again
   with the new file in `last_dirty_files`.
3. Override path: ask the agent to call `uipath_workflow_run` with
   `allow_unverified=true`. Expected: the run executes (gate bypass
   honored) but `status` stays `dirty`. This proves the override is an
   explicit one-shot human escape, not a permanent gate disable.
4. Disable path: set `UIPATH_MCP_GATE_ENABLED=0`, restart the MCP, and
   confirm gated tools no longer return `[BLOCKED]` even while
   `status=dirty`. Re-enable for normal operation.

### Recording additions

- [ ] Full payload of `uipath_workflow_build_and_verify` from Check 2,
      including `headless_log` and `studio_debug_log`.
- [ ] `uipath_workflow_session_status` output before and after each check.
- [ ] Screenshot of the `[BLOCKED]` error from Check 1.

## MCP design-approval enforcement

Verifies that the Cursor MCP requires a human-approved design before any
file is written into a UiPath project.

### Setup

```powershell
$env:UIPATH_DESIGN_APPROVAL_ENABLED = "1"
$env:UIPATH_DESIGN_STORE_PATH = Join-Path $env:TEMP "design_proposals_smoke.json"
Remove-Item $env:UIPATH_DESIGN_STORE_PATH -ErrorAction SilentlyContinue
$dir = "$env:TEMP\uipath-design-smoke-$(Get-Date -Format yyyyMMddHHmmss)"
New-Item -ItemType Directory $dir | Out-Null
```

Scaffold a fresh project into `$dir` via `uipath_workflow_create_project`.

### Check 1 - Write blocked without an approved design

1. Without proposing or approving, ask the agent to call
   `uipath_workflow_write_file` on a new file under `$dir`.
2. Expected: `[BLOCKED] Project '<dir>' has no approved design. Use
   uipath_design_propose ...`.
3. Same expectation for `uipath_workflow_install_package`.

### Check 2 - Propose then approve unblocks writes

1. Agent calls `uipath_design_propose` with a short summary describing the
   architecture choices (e.g. REFramework + queue + SQL writer for the
   InvoiceQueueProcessor scenario). Capture the returned `design_id`.
2. `uipath_design_status { project_dir: $dir }` reports
   `has_approved_design=false` and surfaces the pending proposal.
3. Human runs `uipath_design_approve { design_id: <id>, note: 'looks good' }`.
4. Re-run `uipath_workflow_write_file`. Expected: the write succeeds.
5. `uipath_design_status` now reports `has_approved_design=true`.

### Check 3 - Reject keeps the project locked

1. Propose a second design via `uipath_design_propose` (same project).
2. Reject it via `uipath_design_reject` with a note.
3. Expected: `uipath_design_status` shows the project still has a prior
   approved design, but `uipath_design_list` records the rejected entry.
4. Reset and try the override: with `UIPATH_DESIGN_APPROVAL_ENABLED=0`
   confirm `uipath_workflow_write_file` no longer returns `[BLOCKED]` even
   without an approved design. Re-enable for normal operation.

### Recording additions

- [ ] Output of `uipath_design_propose` (with `design_id`).
- [ ] `uipath_design_status` before approval, after approval, after reject.
- [ ] Screenshot of the `[BLOCKED]` error from Check 1.

## MCP mandatory Studio debug + out-of-band sweep

Verifies that the verify gate cannot silently mark a project verified
without a Studio debug pass, and that edits made outside
`uipath_workflow_write_file` still flip the project dirty.

### Check 1 - Verify refuses pass when Studio is unavailable

1. Stop UiPath Studio if it is running.
2. On a project with at least one valid `.xaml`, call
   `uipath_workflow_build_and_verify { project_dir: <dir> }` (defaults).
3. Expected: `success=false`, `verdict='needs_human'`,
   `next_action='start_studio_or_waive'`, and `studio_debug_skipped_reason`
   names "No running UiPath Studio instance detected; headless run only."
4. Re-call with `require_studio_debug=false`. Expected: behaves as before,
   `verdict='pass'` allowed when headless run succeeds.

### Check 2 - Out-of-band edits are caught on the next gated call

1. Run `uipath_workflow_build_and_verify` to completion (`verdict='pass'`)
   with Studio attached. Confirm `uipath_workflow_session_status` reports
   `verified` for that project.
2. Edit any `.xaml` under `project_dir` directly (e.g. `notepad Main.xaml`,
   or any IDE save - do NOT call `uipath_workflow_write_file`).
3. Call any gated tool (`uipath_workflow_run` is the cheapest).
4. Expected: `[BLOCKED] ... has unverified changes (...Main.xaml)`. The
   session status now reports `dirty` with that file in `last_dirty_files`.

### Recording additions

- [ ] Full payload from Check 1 (showing `verdict='needs_human'`).
- [ ] Status snapshot before/after Check 2.
- [ ] Note in the report whether Studio was started or
      `require_studio_debug=false` was used to clear Check 1.


## InvoiceQueueProcessor (unattended queue performer)

Project: `examples/InvoiceQueueProcessor`. Validates the full
write -> two-pass static validation -> headless run -> attached Studio
debug pipeline introduced by the standardized verify gate.
See [`docs/build-logs/README.md`](build-logs/README.md) for the audit
schema captured at every step.

### Prerequisites

- Orchestrator queue named `Invoices` exists in the robot's mapped folder.
- SQL Server reachable; table created via
  `examples/InvoiceQueueProcessor/Database/CreateInvoicesTable.sql`.
- Local UiPath CLI (`uip`) installed and authenticated.
- A valid SQL connection string available; pass it as the
  `sqlConnectionString` workflow argument (do **not** hard-code it).

### Commands

```powershell
cd examples/InvoiceQueueProcessor

# 1) Two clean validation passes (the gate requires both).
uip rpa get-errors --min-severity error --output json
uip rpa get-errors --min-severity error --output json

# 2) Headless run.
uip rpa run-file `
  --file-path Main.xaml `
  --command StartExecution `
  --output json `
  --input-arguments '{"sqlConnectionString":"<your-connection-string>"}'

# 3) Optional but enforced when Studio is detected by the agent:
#    attached Studio debug. Open the project in UiPath Studio first.
uip rpa run-file `
  --file-path Main.xaml `
  --command StartDebugging `
  --use-studio `
  --output json `
  --input-arguments '{"sqlConnectionString":"<your-connection-string>"}'
```

### Expected results

- `BUILD_LOG.md` in the project root grows by one event per command
  above (`get_errors` x2, `run_file`, optional `start_debugging`).
- One row inserted into `dbo.Invoices` per valid queue item.
- One Failed transaction with `ErrorType.Business` per invalid payload
  (missing `Vendor`, non-numeric `Amount`, unparseable `DueDate`).
- All four steps return `Result: Success` / exit 0; if any pass returns
  diagnostics, do not declare the project verified.

### Recording additions

- [ ] BUILD_LOG.md diff covering all commands.
- [ ] Snapshot of the inserted `dbo.Invoices` rows.
- [ ] Orchestrator queue tab showing one Successful + one Failed item.

## Post-fix smoke matrix (defect fixes 1-5)

Run after applying the smoke-driven defect fixes (`fix-path-resolution`,
`fix-studio-enforcement`, `fix-create-project-postcheck`,
`fix-session-status-oob`, `fix-askai-mock`). The MCP server should be
launched with `UIPATH_MCP_GATE_ENABLED=1`,
`UIPATH_DESIGN_APPROVAL_ENABLED=1`, and
`UIPATH_ASKAI_ENDPOINT=mock://localfixture`.

| Check | Expected | 2026-04-19 |
| --- | --- | --- |
| design-gate blocks absolute write into a project with no approval | `[BLOCKED]` text returned, project not modified | PASS |
| design-gate blocks relative write that resolves into an unapproved project | `[BLOCKED]` text returned, file not created | PASS |
| approved design unblocks a write and the dirty marker fires on the resolved path | `[OK]` returned and `session_gate.status(project).status == "dirty"` | PASS |
| `build_and_verify { run_after_validate: false, require_studio_debug: true }` | `verdict='needs_human'`, `next_action='start_studio_or_waive'` | PASS |
| `session_status` after an out-of-band edit | status flips to `dirty` (real-time `detect_out_of_band_changes`) | PASS |
| `query_uipath_docs` with `UIPATH_ASKAI_ENDPOINT=mock://localfixture` | answer body contains `SOURCE: askai-mock` | PASS |

Reproduce locally by running `uv run pytest framework/tests/unit/tools/test_write_file_paths.py
framework/tests/unit/tools/test_session_gate_integration.py
framework/tests/unit/tools/test_build_and_verify_studio_gate.py
framework/tests/unit/tools/test_create_project_postcheck.py
framework/tests/unit/tools/uipath/test_askai.py`; the same checks above are encoded
as deterministic unit tests.

## Scenario 13 - Ambiguity triage

Grades whether the agent asks **batched, residue-only** questions when the
user's brief is genuinely vague, and whether the question-asking contract
(planner > BA > design-gate) holds end-to-end without re-asking resolved
items. None of Scenarios 1-12 grade this: they all start from well-formed
briefs, so the planner's batching and BA's hand-off behavior are never
exercised.

This scenario assumes the overlay at
`extensions/skills/uipath-planner/SKILL.md` is active (it wins over the
submodule per [docs/SKILL_LAYOUT.md](SKILL_LAYOUT.md) merge order) and the
updated `BA_SYSTEM_PROMPT` in
[uipath_claude/query/ba_agent.py](../uipath_claude/query/ba_agent.py) is in
use.

### Setup

```powershell
$dir = "ambig-" + (Get-Date -Format "yyyyMMddHHmm")
New-Item -ItemType Directory $dir | Out-Null
Set-Location $dir
$env:UIPATH_CHAT_SESSION_ID = $dir
$env:UIPATH_DESIGN_APPROVAL_ENABLED = "1"
python -m uipath_claude.cli.app chat
```

### Prompt (deliberately vague)

> "Build a bot that processes invoices and sends them somewhere."

### Expected flow

1. Planner fires and makes **one** consolidated `AskUserQuestion` call
   covering only the residue it cannot default or infer. The batch contains
   items from Step 1 (approach / autonomy / PDD / test coverage - only the
   unresolved subset) plus Step 1.5 (attended vs unattended, source system,
   destination system, Orchestrator folder, deploy-or-not). It does **not**
   ask about expression language, project-name casing, XAML vs C#, or
   cross-platform target on Windows (safe defaults).
2. After the user answers, the planner writes a plan file under
   `docs/plans/YYYY-MM-DD-<name>.md` with a populated `## Resolutions`
   section echoing every answered and every defaulted item.
3. `/pdd` runs BA. BA reads the plan file first (no `AskUserQuestion` call
   for anything the plan already answered) and proceeds directly to PDD
   drafting, citing the plan path in the PDD's `Inputs` section.
4. Developer calls `uipath_design_propose` with a populated `resolutions`
   object. `uipath_design_status { project_dir: <dir> }` surfaces
   `latest_pending_resolutions` with the structured keys
   (`attended_unattended`, `external_systems`, `orchestrator_folder`,
   `deploy`, `open_questions_residue`, etc.).
5. Human approves. `uipath_design_status` now shows
   `latest_approved_resolutions` populated.

### Pass criteria

- **One planner question card.** `AskUserQuestion` is called exactly once
  during the planner stage (or zero times if Step 1 + 1.5 were both fully
  resolved from context, which is not expected for this prompt).
- **No re-asks in BA.** BA stage makes zero `AskUserQuestion` calls for
  items present in the plan's `## Resolutions` section.
- **`resolutions` object populated.** `uipath_design_propose` returns no
  `[WARN] resolutions field is empty` line (or the one-off deprecation
  warning does appear, and the next proposal corrects it).
- **`uipath_design_status` surfaces structured resolutions.** The JSON
  payload includes `latest_pending_resolutions` (then
  `latest_approved_resolutions` after approval) with at least
  `attended_unattended`, `deploy`, and the relevant external systems.
- **Total question budget respected.** Steps 1 + 1.5 + 4 together stay at
  or under 5 questions (anti-pattern 3 in the overlay planner SKILL).
- **Project-shape safe defaults applied silently.** The plan header shows
  `Expression language: VB.NET`, a sensible `Project type`, and does not
  ask the user about either.

### Fail signals

| Signal | Why it fails |
|---|---|
| Agent answers silently with no questions at all. | Invented answers to attended/unattended, source, destination - the defaulted choices will usually be wrong. |
| Agent asks one question, waits, asks the next (3+ turns before the plan lands). | Violates Step 1 / Step 1.5 / anti-pattern 19 in the overlay. Batching is the whole point. |
| Agent asks about items with safe defaults (expression language, project-name format, XAML vs C#, cross-platform vs Windows on Windows). | Violates anti-pattern 10 / 11 / 18 in the overlay. Burns the 5-question budget on noise. |
| BA re-asks attended-vs-unattended (or any other item already in `## Resolutions`). | `BA_SYSTEM_PROMPT` context hand-off is not being applied or the plan file is not being read. |
| `uipath_design_propose` call omits the `resolutions` argument. | Design card shows free-text summary only; approver cannot see the structured triage outcome. Tool returns a `[WARN]` line. |
| `uipath_design_status` does not show `latest_pending_resolutions` or `latest_approved_resolutions`. | MCP extension missing or server not reloaded. |
| `propose_library_update` never fires when a residue item ("what retry pattern for flaky HTTP?") is clearly library-answerable. | BA is asking the user instead of calling `lookup_uipath_knowledge` first - bucket 2 of the triage is being skipped. |

### Recording checklist

- [ ] Full transcript of the planner stage showing the single batched
      `AskUserQuestion` call and its option list.
- [ ] The generated plan file, especially the `## Resolutions` section.
- [ ] BA stage transcript showing zero `AskUserQuestion` calls for plan-
      resolved items.
- [ ] `uipath_design_propose` request arguments (full `resolutions` object).
- [ ] `uipath_design_status` output before and after approval.
- [ ] Question count across the whole scenario (must be <= 5).

