# UiPath Builder Agent — Claude / CLI user guide

This guide is the **terminal-first** companion to [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md). It covers **Claude Code-style** use of `uipath-claude` from a shell (no Cursor UI, no MCP in the IDE). For command tables, env vars, and deeper workflows, also keep [USER_GUIDE.md](USER_GUIDE.md) open.

For the visual map of every skill family and how Claude/CLI routes work through skills and tools, see [SKILL_VISUAL_GUIDE.md](SKILL_VISUAL_GUIDE.md).

## Quick setup (about 5 minutes)

Use **one assistant per clone**. Quickstart scripts record `.assistant-choice` and block switching unless you pass `-Force` / `--force`.

### 0. Almost zero work (one script)

From repo root after clone:

```powershell
.\ops\scripts\claude-quickstart.ps1
```

```bash
bash ops/scripts/claude-quickstart.sh
```

This runs `git submodule update --init --recursive` and **`uv sync --extra dev`** (see script for exact flags). You need **git** and **uv** on PATH.

If this clone is already configured for Cursor, re-run with `-Force` / `--force` to switch.

### Preflight doctor

Read-only health checks (submodule, hooks, `uip`, MCP doc drift, markdown encoding, library proposals):

```powershell
uipath-claude doctor
```

It does **not** edit files or call Orchestrator.

### 1. Clone and initialize

```powershell
git clone <repo-url>
cd uipath-builder-agent
git submodule update --init --recursive
```

### 2. Install (if you skipped quickstart)

**Recommended:** `uv` at repo root so the same environment is used everywhere:

```powershell
uv sync --extra dev
```

**Alternative:** venv + `pip install -e ".[dev]"` — see [USER_GUIDE.md](USER_GUIDE.md).

### 3. Verify AWS Bedrock

The interactive agent expects Bedrock-backed models (see [INSTALL.md](INSTALL.md) for regions and overrides):

```bash
aws sts get-caller-identity
```

### 4. Start the agent

```bash
uipath-claude chat
```

In the first session, run **`/help`**, **`/status`**, and **`/skills`** to confirm routing and skill discovery.

---

## Complete step-by-step: using `uipath-claude` from a terminal

Follow these steps in order whenever you sit down to work. Skip steps that do not apply (for example, skip `git pull` if you already have the latest).

### 1. Open the right directory

1. Open a terminal (PowerShell, bash, or the integrated terminal in VS Code / Cursor).
2. `cd` to the **repository root** (the folder that contains `pyproject.toml` and `framework/`).

All relative paths (`skills/`, `.cursor/plans/`, `generated/`) assume this is the current working directory unless you pass **`--project-dir`** (see below).

### 2. Sync the repo (when you pulled changes)

```powershell
git pull
git submodule update --init --recursive
```

If `pyproject.toml` or lockfiles changed, refresh Python deps:

```powershell
uv sync --extra dev
```

### 3. Preflight (recommended before demos or after big merges)

```powershell
uipath-claude doctor
```

Fix any **FAIL** lines before starting chat. **WARN** lines are hints (encoding, stale proposals, doc regen suggestions).

### 4. Start interactive chat

Either form starts the same chat loop (Typer default invokes `chat`):

```powershell
uipath-claude
# same as:
uipath-claude chat
```

From a clean tool environment, prefer:

```powershell
uv run uipath-claude chat
```

The banner prints a **session id**. The process tells you: `Type 'exit' or 'quit' to leave.`

### 5. Inside chat: normal work loop

1. Type a **goal** in plain language (include paths, project type, and constraints).
2. Use **slash commands** when you want a fixed operation (`/validate`, `/uiplan-*`, `/uiplan`, `/pdd`, …). See [SLASH_COMMANDS.md](SLASH_COMMANDS.md).
3. Answer **approval prompts** when the agent proposes destructive tools (unless you disabled prompts via `UIPATH_TOOL_APPROVAL` for CI).
4. When finished, type **`exit`** or **`quit`**, or press **Ctrl+C** to abort the current line or stop the session.

### 6. Optional: bind chat to an existing UiPath project folder

If outputs and validators should target a Studio project on disk (instead of only the per-session `generated/chat/...` tree):

```powershell
uipath-claude chat --project-dir "C:\work\MyProcess"
```

That sets **`UIPATH_PROJECT_DIR`** for the process. Use an absolute path.

### 7. Optional: plan and UiPlan **without** staying in chat

Same MCP-backed tools the server uses, invoked from the shell:

```powershell
uipath-claude plan --help
uipath-claude plan uiplan full "Your feature title"
```

Use **`uipath-claude plan uiplan --help`** for staged `ground`, `spec`, `plan`, `tasks`, `review`.

### 8. Optional: library proposal queue (CLI)

```powershell
uipath-claude library-proposals list
uipath-claude library-proposals show <id>
uipath-claude library-proposals approve <id>
```

### 9. Optional: one-shot legacy bootstrap (non-chat)

```powershell
uipath-claude start-project "MyAutomationName"
```

Runs the legacy bootstrap flow and writes artifacts under the **current working directory**. Prefer **`/pdd`** or **`/bootstrap`** inside chat for interactive control.

### 10. Discover every Typer flag

```powershell
uipath-claude --help
uipath-claude chat --help
uipath-claude doctor --help
```

---

## `uipath-claude chat` flags you should know

| Flag | When to use it |
| --- | --- |
| `--no-banner` | CI or scripted runs where the ASCII banner is noise. |
| `--no-plan` | Skip the planning phase for BUILD intents (use sparingly). |
| `--auto-approve-plan` | **CI / automation only** — auto-approves plans without prompts. |
| `--project-dir` / `-p` | Point validators and writes at a real UiPath project directory. |
| `--skip-docs` | Skip the PDD/SDD/TDD doc sub-flow when design docs already exist. |
| `--no-stream` | Easier copy/paste logs; disables streaming tokens. Overrides `UIPATH_CHAT_STREAM`. |
| `--no-track-processes` | If Studio process tracking interferes with your machine; see [Testing_Guide.md](Testing_Guide.md) / Studio close guidance. |

Environment variables (`UIPATH_AGENTIC_MODE`, `UIPATH_CLAUDE_TOOL_PROFILE`, Bedrock overrides, etc.) are documented in [USER_GUIDE.md](USER_GUIDE.md) and [SMOKE_TESTS.md](SMOKE_TESTS.md).

---

## Sessions: new chat vs continuing

- Each chat run allocates a **session id** (printed at startup) unless you pre-set **`UIPATH_CHAT_SESSION_ID`**.
- **`/resume`** lists recent sessions and explains how to attach to one: set `UIPATH_CHAT_SESSION_ID` to that id, then **start `uipath-claude chat` again** in a new process so logs and outputs line up with the same session folder.
- For a **fresh** session on the same machine, start chat **without** setting `UIPATH_CHAT_SESSION_ID` (or clear it in the shell before launching).

---

## Best practices for Claude / terminal work

The CLI is best when you want a bounded, repeatable agent run with explicit gates. Use it like a disciplined terminal partner:

```mermaid
flowchart LR
    Preflight[Preflight<br/>doctor + sync] --> Scope[Scope prompt<br/>goal + constraints]
    Scope --> Risk{Risky or multi-file?}
    Risk -->|yes| Plan[/uiplan-* or /pdd]
    Risk -->|no| Chat[Plain chat]
    Plan --> Approve[Human approval]
    Approve --> Implement[Implement]
    Chat --> Implement
    Implement --> Validate[Validate / run]
    Validate -->|fail| Implement
    Validate -->|pass| Learn[Library proposal<br/>if reusable lesson]
    Learn --> Handoff[Summary + next steps]
```

### 1. Start every serious session with a preflight

```powershell
git pull
git submodule update --init --recursive
uv sync --extra dev
uv run uipath-claude doctor
```

If `doctor` reports `FAIL`, fix that first. If it reports library `WARN` rows, you can still work, but consider cleaning the proposal queue before a release or demo.

### 2. Give the agent an operating envelope

Good terminal prompts say what is allowed and what is forbidden:

```text
In project C:\work\InvoiceProcessor, update Main.xaml to create queue items for ready invoices.
Use uipath-rpa patterns, validate after edits, and do not publish or deploy.
```

For read-only analysis:

```text
Review this project for selector fragility and package risks. Read files and run validation only;
do not write files unless I explicitly approve a fix plan.
```

### 3. Use slash commands for fixed workflows

| Need | Prefer |
| --- | --- |
| Full delivery lifecycle | `/pdd` |
| Structured spec/plan/tasks | `/uiplan-full` or staged `/uiplan-spec` … `/uiplan-review`; build with `/uiplan-implement` (see [SLASH_COMMANDS.md](SLASH_COMMANDS.md)) |
| Existing workflow validation | `/validate` or `/analyze` |
| Skill refresh/checks | `/update-skills`, `/scan-upstream-skills` |
| Library proposal review | `/library-proposals` |

Plain chat is good for exploration; slash commands are better for repeatable operations.

### 4. Keep writes behind plans when risk is non-trivial

Use `/uiplan-full "<title>"` when the change touches multiple files, changes architecture, adds Orchestrator behavior, affects credentials/assets/queues, or changes production-facing deployment. Let the plan reach review/acceptance before asking for implementation via `/uiplan-implement <slug>`.

For stricter local enforcement:

```powershell
$env:UIPATH_PLAN_GATE = "1"
uv run uipath-claude chat --project-dir "C:\work\InvoiceProcessor"
```

### 5. Validate in the same session that made the change

After edits, ask for a concrete verification result, not a summary:

```text
Run the relevant validation now and summarize exact errors/warnings. If validation passes,
tell me which command/tool proved it.
```

When Studio or `uip` gets wedged, exit chat, close Studio, run `doctor`, and start a fresh session.

### 6. Use the library deliberately

- Ask the CLI to search the library before answering policy, architecture, or recurring UiPath questions.
- When a fix teaches a reusable rule, ask it to stage a library proposal instead of burying the lesson in logs.
- Review proposals with `uipath-claude library-proposals list/show/approve/reject` before relying on them as approved guidance.

### 7. Prefer one assistant per clone

Use a Cursor-configured clone for IDE/MCP work and a Claude-configured clone for terminal runs when possible. If you intentionally switch a clone, use the quickstart `-Force` / `--force` flag so `.assistant-choice`, hooks, and local expectations stay honest.

---

## How the CLI session differs from Cursor

| Concern | Cursor (+ optional MCP) | CLI (`uipath-claude chat`) |
| --- | --- | --- |
| Skills text | Loaded as Cursor skills / rules | Resolved from `skills/` + extensions; injected into the chat system prompt |
| UiPath tool calls (`uip rpa`, pack, validate) | Often via **MCP** tools | Via **slash commands** and agent tools wired in LangGraph (same policies, no IDE MCP) |
| Superpowers plugin | Available in Cursor | **Not** loaded; use repo skills and `/pdd` / planning docs instead |
| Session memory | Thread / project context | Persistent session store (see [ARCHITECTURE.md](ARCHITECTURE.md)) |

**When to prefer CLI:** headless machines, CI-style drive, or you live in **Claude Code** / terminal and want the same slash surface without opening Cursor.

---

## Slash commands (in-chat)

All commands are typed at the prompt starting with `/`. Full table, SDLC mapping, and **`UIPATH_CLAUDE_TOOL_PROFILE`**: [SLASH_COMMANDS.md](SLASH_COMMANDS.md).

High-signal defaults:

| You want | Command |
| --- | --- |
| Full BA → SA → ADD → TDD → Dev → QA (+ optional publish/deploy) | `/pdd` |
| Lighter legacy flow | `/bootstrap` |
| Structured spec / plan / tasks | `/uiplan-*` commands (see [uiplan/README.md](uiplan/README.md), [SLASH_COMMANDS.md](SLASH_COMMANDS.md)) |
| Static validation | `/validate`, `/analyze` |
| Skills hygiene | `/update-skills`, `/scan-upstream-skills` |
| Library learning | `/library-harvest`, `/library-proposals`, `/books` |

**CLI outside chat:** `uipath-claude plan …`, `uipath-claude doctor`, and other Typer subcommands — [USER_GUIDE.md](USER_GUIDE.md).

---

## Skills in the CLI

- Official skills live in the **`skills/`** submodule (`skills/skills/<id>/SKILL.md`).
- Project overlays live under **`.cursor/skills/`** (junction / copy-on-write layout — [SKILL_LAYOUT.md](SKILL_LAYOUT.md)).
- The agent picks skills using the same heuristics as documented for Cursor; you do **not** type `@skill` in the terminal — describe the task and the router + skill text do the rest.

---

## Hooks and scheduled work (no GitHub Actions in-repo)

**GitHub Actions workflows under `.github/workflows/` are intentionally removed** from this branch so nothing runs on GitHub’s timer without you turning it back on.

Use these instead:

1. **Session start (Cursor / compatible hosts):** [`.cursor/hooks.json`](../.cursor/hooks.json) runs skills update checks and related setup (see [README.md](../README.md) “Keeping skills up to date”).
2. **Official UiPath session hook pattern:** `skills/hooks/hooks.json` and `skills/hooks/ensure-uip.sh` (submodule) — follow [CLAUDE.md](../CLAUDE.md) §0a.
3. **Timed automation you control:** OS **Task Scheduler** / **cron** calling `ops/scripts/update-skills.ps1 -Check` (or your own wrapper), or re-add a minimal workflow when you are ready to enable Actions again.

Manual always works: `/update-skills` in chat or `ops/scripts/update-skills.ps1` / `.sh` from a shell (see README).

---

## Workflow patterns (terminal)

### Pattern 1: Quick generation

Describe the automation in plain language; include project path and constraints. The agent will use `uipath-rpa` patterns and validators when tools are allowed.

### Pattern 2: Plan before build

For multi-file or risky work, run **`/uiplan-full "<title>"`** (or staged `/uiplan-ground` … `/uiplan-review`), get human acceptance, then implement from `tasks.md` with `/uiplan-implement <slug>`.

### Pattern 3: Full SDLC artifact trail

**`/pdd`** with flags documented in [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md).

### Pattern 4: Read-only triage

**`uipath-claude doctor`** before demos or after pulling a large branch.

---

## Debugging, restart, and recovery

### Restart the application (most common fix)

`uipath-claude` is a **short-lived CLI process**: each `uipath-claude` / `uipath-claude chat` is a new Python interpreter. There is no separate daemon to “restart” beyond exiting and launching again.

1. **Leave chat** — type `exit` or `quit`, or **Ctrl+C** (twice if the loop is busy).
2. **Optional — new session identity** — open a **new** terminal tab or run `Remove-Item Env:UIPATH_CHAT_SESSION_ID` (PowerShell) / `unset UIPATH_CHAT_SESSION_ID` (bash) so the next chat does not inherit an old id.
3. **Re-sync deps** (after `git pull` or branch switch): `uv sync --extra dev`.
4. **Run doctor**: `uipath-claude doctor`.
5. **Start again**: `uv run uipath-claude chat` (or `uipath-claude chat` from an activated venv).

If **Studio** was opened by validation runs, close it before the next agentic loop (see [Testing_Guide.md](Testing_Guide.md) and repo `CLAUDE.md` Studio guidance).

### Hung chat, partial output, or “nothing happens”

| Symptom | What to try |
| --- | --- |
| Output buffered in a pipe | Prefer `uv run uipath-claude chat` in a real TTY; for scripts use `--no-stream`. |
| Windows crash at the auth prompt with `UnicodeEncodeError` / `cp1252` | The auth prompt must be ASCII-safe (`! UiPath CLI Authentication Required`). Pull the latest fix, then run the smoke test below. |
| Token stream too noisy | `--no-stream` or set `UIPATH_CHAT_STREAM=0`. |
| Tool loop hard to understand | Set `UIPATH_DEBUG_AGENT=1` before chat (see [USER_GUIDE.md](USER_GUIDE.md) Agentic Mode). |
| Studio locks or extra processes | `uipath-claude chat --no-track-processes` for that session; then close Studio. |
| Stale skills content | `/update-skills` in chat or `ops/scripts/update-skills.ps1` from the shell. |

Startup smoke test on Windows:

```powershell
@'
2
/status
/skills
exit
'@ | .\.venv\Scripts\uipath-claude.exe chat
```

Expected: the chat starts, option `2` skips Orchestrator auth for that session,
`/status` prints model/region/session details, `/skills` lists loaded skills, and
the process exits cleanly.

### Import errors (`mcp_server`, `uipath_claude`)

Run from **repo root** with the framework on `PYTHONPATH`:

```powershell
$env:PYTHONPATH = ".;framework"
uipath-claude doctor
```

`uv run` sets the project layout correctly when invoked from the root with a synced env.

### Bedrock / AWS / model errors

1. `aws sts get-caller-identity`
2. Region and model env vars from [INSTALL.md](INSTALL.md)
3. Retry with a smaller request; confirm quotas in AWS console

### `skills/skills` missing

```bash
git submodule update --init --recursive
```

### Validator or `uip` not found

Install UiPath **`uip`** CLI per [INSTALL.md](INSTALL.md); `doctor` reports PATH status.

### Same repo, switching from Cursor

Re-run the opposite quickstart with **`-Force`** so `.assistant-choice` and expectations stay consistent.

### Still blocked

1. Capture **`uipath-claude doctor`** text output.
2. Re-run with **`uipath-claude chat --no-banner --no-stream`** once to simplify logs.
3. Open an issue with OS, `uv run uipath-claude --version` (or `pip show uipath-claude-code`), and the last 30 lines of the trace.

---

## Further reading

- [USER_GUIDE.md](USER_GUIDE.md) — day-to-day CLI reference, env vars, cookbook
- [CAPABILITY_CONTRACT.md](CAPABILITY_CONTRACT.md) — canonical CLI/Cursor/MCP parity contract and explicit Claude Code non-goals
- [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) — Cursor + MCP tool surface
- [SLASH_COMMANDS.md](SLASH_COMMANDS.md) — slash command matrix and tool profiles
- [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md) — `/pdd` stages and outputs
- [README.md](../README.md) — project pitch, setup paths, skills update policy
