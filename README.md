# UiPath Claude Code

**Claude Code for UiPath — an agentic CLI and Cursor integration that builds, validates, and runs RPA workflows.**

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-Internal-lightgrey)
![Built with](https://img.shields.io/badge/built%20with-LangGraph%20%2B%20Bedrock-6f42c1)
![Status](https://img.shields.io/badge/status-v0.2-green)

RPA developers spend hours scaffolding projects, hand-writing XAML, and chasing validator errors that all look alike. UiPath Claude Code runs that loop for you: it scaffolds the project, writes the XAML, runs the UiPath validator, fixes what it breaks, and only stops to ask when a human decision actually matters. It works from the CLI, inside Cursor, and as a full BA → SA → ADD → TDD → Dev → QA pipeline that turns a one-paragraph brief into a validated, packaged, optionally deployed UiPath project.

![demo](docs/assets/demo.gif)

```mermaid
flowchart LR
    User[User prompt] --> Router[Query router]
    Router --> Executor[Agentic ReAct executor]
    Executor --> Tools[Tool registry]
    Tools --> Skills[Skills and Library]
    Tools --> UiPath[UiPath CLI / Analyzer / Orchestrator]
    Tools --> Validator{Validator gate}
    Validator -->|errors| Executor
    Validator -->|ok| Output[Generated project]
    Executor -->|needs approval| Human[HITL approval]
    Human --> Executor
```

---

## Quickstart

### 1. Clone the repo (fresh setup)

```bash
git clone <your-repo-url>
cd uipath-builder-agent
git submodule update --init --recursive
```

The submodule step is required: the official UiPath skills ship under `skills/skills/` as a git submodule.

### 2. Create a virtual environment

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

Pick the extra that matches how you plan to use the project:

| Usage mode             | Install command            |
| ---------------------- | -------------------------- |
| CLI / development      | `pip install -e ".[dev]"`  |
| Cursor + MCP server    | `pip install -e ".[mcp]"`  |
| Both (contributors)    | `pip install -e ".[dev,mcp]"` |

### 4. Verify Bedrock access and run

```bash
aws sts get-caller-identity   # confirm Bedrock creds
uipath-claude chat
```

Full setup (UiPath CLI, Studio 26.2+, Orchestrator auth, AWS region overrides) lives in [docs/INSTALL.md](docs/INSTALL.md).

---

## Choose your setup path

Three supported ways to use the project. Pick one (or combine).

### A. CLI (`uipath-claude chat`) — Claude Code-style agent

The full agentic CLI with auto-fix loop, planner, and BA -> SA -> ADD -> TDD -> Dev -> QA pipeline driven by `/pdd`.

- Requires `pip install -e ".[dev]"` and AWS Bedrock access.
- Run: `uipath-claude chat`
- Day-to-day usage: [docs/USER_GUIDE.md](docs/USER_GUIDE.md)

### B. Cursor (skills-only)

Use the UiPath skills directly inside Cursor without the CLI runtime. Good for quick scaffolding and design questions.

```powershell
# Windows
.\scripts\setup-cursor.ps1
```

```bash
# macOS / Linux
./scripts/setup-cursor.sh
```

Open the repo in Cursor; skills auto-load. Guide: [docs/CURSOR_USER_GUIDE.md](docs/CURSOR_USER_GUIDE.md).

### C. Cursor + MCP (skills + UiPath tool calls)

Adds validation, package install, and run-workflow tools to Cursor via the bundled MCP server.

- Install MCP extras: `pip install -e ".[mcp]"`.
- Run `scripts/setup-cursor.ps1` / `.sh` (writes `.cursor/mcp.json`).
- Open the repo in Cursor — the `uipath-builder-agent` MCP server auto-connects.
- Verify in Cursor: Settings -> MCP -> `uipath-builder-agent` shows connected.
- MCP tool reference and patterns: [docs/CURSOR_USER_GUIDE.md](docs/CURSOR_USER_GUIDE.md#mcp-tools-advanced).

---

## What it does

- **Generate validated UiPath projects from a description.** Describe the automation in plain English; the agent scaffolds the project, writes XAML, runs the UiPath Workflow Analyzer and `uip rpa` validator, and auto-fixes validator errors until the workflow passes both static and runtime checks.
- **Bootstrap end-to-end with the BA → SA → ADD → TDD → Dev → QA pipeline.** `/pdd "InvoiceBot"` turns a one-paragraph brief into a PDD, SDD, ADD, TDD, scaffolded project, validated workflow, and (optionally) a published + deployed Orchestrator process. The legacy four-stage `/bootstrap` flow is still available for quick BA → SA → Dev → QA runs. Full reference: [docs/PDD_LIFECYCLE.md](docs/PDD_LIFECYCLE.md).
- **Works where you work.** Use the CLI (`uipath-claude chat`), drive it from Cursor (the skills register automatically after running `scripts/setup-cursor.ps1`), or call slash commands like `/pdd`, `/bootstrap`, `/skills`, `/analyze`, `/recall`.
- **Learns as you use it.** A layered skills system (user → project → team extensions → official UiPath submodule) plus a library learning loop capture gotchas and edge cases as you hit them, so the agent gets better at your codebase over time.
- **Safe by default.** Tool profiles (`safe`, `uipath-dev`, `all`), per-operation approval gates, and session hooks keep destructive actions behind human review. Nothing touches Orchestrator unless you say so.

---

## A real example

A session driving the auto-fix loop against a real validator error. The full transcript lives in [examples/03-auto-fix-validator/](examples/03-auto-fix-validator/).

```text
> Build me an InvoiceProcessor workflow that reads Sample.xlsx and logs each invoice id.

[Step 1/25] ensure_project_structure(name="InvoiceProcessor")
   -> created InvoiceProcessor/project.json, Main.xaml
[Step 2/25] install_package("UiPath.Excel.Activities")
   -> ok
[Step 3/25] write_file("InvoiceProcessor/Main.xaml", ...)
[Step 4/25] validate_file("InvoiceProcessor/Main.xaml")
   -> ERRORS (2):
      - UiPath.Excel.Activities.ExcelReadRange: 'Range' is required
      - Variable 'dt_Invoices' used before assignment
[Step 5/25] validate_and_fix_loop -> patching...
[Step 6/25] write_file("InvoiceProcessor/Main.xaml", ...)   # revised
[Step 7/25] validate_file("InvoiceProcessor/Main.xaml")
   -> OK (0 errors, 0 warnings)
[Step 8/25] run_workflow("InvoiceProcessor")
   -> OK: processed 14 invoices in 1.2s

Done. Generated at generated/chat/2026-04-18-0a1b/InvoiceProcessor/.
```

What just happened: the model wrote XAML, the UiPath validator rejected it, `validate_and_fix_loop` interpreted the errors, rewrote the file, and only stopped when both the static validator and the runtime `uip rpa run-file` agreed.

---

## Architecture

The chat runtime loads a **skill registry** from several filesystem layers (user, project, team extensions, official UiPath submodule) and exposes them to a ReAct-style executor alongside UiPath tools (CLI, Analyzer, Orchestrator, Ask AI). A validator gate sits inline in the loop: every `write_file` is followed by `validate_file`, and failures feed back into the executor until the workflow passes. Plan mode wraps the executor with a read-only proposal step so you approve the plan before any file is touched.

```mermaid
flowchart LR
    Brief[One-paragraph brief] --> BA[BA: PDD]
    BA --> SA[SA: SDD]
    SA --> ADD[ADD: architecture]
    ADD --> TDD[TDD: tech + test design]
    TDD --> Dev[Developer: scaffold + code + validate]
    Dev -->|auto-fix loop| Dev
    Dev --> QA[QA: review + tests]
    QA --> Done[Generated project]
    Dev -.->|"--deploy"| Publish[Publish + Orchestrator process]
```

The new six-agent flow is driven by the `/pdd` slash command and is documented in [docs/PDD_LIFECYCLE.md](docs/PDD_LIFECYCLE.md). The legacy `/bootstrap` BA → SA → Dev → QA flow is still wired in for short runs (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).

Deeper technical detail: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Docs

- [docs/README.md](docs/README.md) — index of every document in this repo
- [docs/INSTALL.md](docs/INSTALL.md) — full installation (UiPath CLI, Studio, submodules, AWS)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — runtime, executor, validator gate, pipeline
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) — day-to-day CLI usage
- [docs/PDD_LIFECYCLE.md](docs/PDD_LIFECYCLE.md) — full `/pdd` lifecycle: BA → SA → ADD → TDD → Dev → QA → publish → deploy
- [docs/CURSOR_USER_GUIDE.md](docs/CURSOR_USER_GUIDE.md) — using the skills inside Cursor
- [docs/TOOLS.md](docs/TOOLS.md) — tool registry reference
- [docs/SKILL_LAYOUT.md](docs/SKILL_LAYOUT.md) — skill layering and provenance
- [docs/LIBRARY_LEARNING.md](docs/LIBRARY_LEARNING.md) — library learning loop
- [docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md) — end-to-end smoke scenarios
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to add skills, tools, and slash commands
- [CHANGELOG.md](CHANGELOG.md) — release history

---

## Keeping skills up to date

The `skills/` git submodule tracks [UiPath/skills](https://github.com/UiPath/skills). The workspace's `.cursor/skills` is a junction into `skills/skills/`, so any submodule bump is picked up by Cursor immediately. Four paths to stay current:

- **Automatic (server-side, daily):** [.github/workflows/update-skills-submodule.yml](.github/workflows/update-skills-submodule.yml) runs at 06:00 UTC and opens a PR `chore/update-skills-submodule` when upstream moves. Also triggerable from the Actions tab.
- **Automatic (per Cursor session, every 2 days):** [.cursor/hooks.json](.cursor/hooks.json) registers a `sessionStart` hook that runs [.cursor/hooks/check-skills-update.ps1](.cursor/hooks/check-skills-update.ps1) on Windows (or `.sh` on mac/linux). It surfaces a banner in the new chat when updates are available; throttled via `.cursor/hooks/state/last-update-check` (gitignored, per-user). Change `$ThrottleDays` at the top of the script to tune the cadence.
- **Manual in chat:** `/update-skills [--check|--info|--force]` and `/scan-upstream-skills` inside the CLI.
- **Manual in a shell:** `scripts/update-skills.ps1 [-Check] [-Commit]` (or `scripts/update-skills.sh [--check|--commit]`) for one-off pulls outside Cursor.

> Mac/linux teammates: if `pwsh` is not installed, replace the `command` in `.cursor/hooks.json` with `bash .cursor/hooks/check-skills-update.sh`, or place an override at `~/.cursor/hooks.json` (user-scope hooks take precedence over project-scope).

---

## Contributing

Issues and PRs are welcome. The project is extensible along three axes: **skills**, **tools**, and **slash commands**.

### Quick contributor path

```bash
# 1. Fork and clone, then install dev + MCP extras
pip install -e ".[dev,mcp]"
git submodule update --init --recursive

# 2. Make your change on a feature branch
git checkout -b my-change

# 3. Run the core checks
ruff check .
black --check .
mypy uipath_claude
pytest -m "not integration"

# 4. Open a PR against main
```

### Where to contribute

- **Skills** — markdown playbooks under `extensions/skills/` (team-shared) or `.uipath-claude/skills/` (local). Do not edit the `skills/skills/` submodule in place.
- **Tools** — Python functions under [uipath_claude/tools/](uipath_claude/tools/), registered via tool profiles.
- **Slash commands** — small modules under `uipath_claude/commands/` registered on the command registry.
- **Docs** — keep [docs/](docs/) and [CHANGELOG.md](CHANGELOG.md) in sync with user-visible changes.

Full contribution workflow, layering rules, MCP session gate, and review expectations live in [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

Internal use. See `pyproject.toml`.
