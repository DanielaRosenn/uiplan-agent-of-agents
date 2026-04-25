# UiPath Builder Agent — Claude / CLI user guide

This guide is the **terminal-first** companion to [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md). It covers **Claude Code-style** use of `uipath-claude` from a shell (no Cursor UI, no MCP in the IDE). For command tables, env vars, and deeper workflows, also keep [USER_GUIDE.md](USER_GUIDE.md) open.

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
| Structured spec / plan / tasks | `/uiplan` (see [uiplan/README.md](uiplan/README.md)) |
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

For multi-file or risky work, run **`/uiplan full "<title>"`** (or staged `ground|spec|plan|tasks|review`), get human acceptance, then implement from `tasks.md`.

### Pattern 3: Full SDLC artifact trail

**`/pdd`** with flags documented in [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md).

### Pattern 4: Read-only triage

**`uipath-claude doctor`** before demos or after pulling a large branch.

---

## Troubleshooting

### `skills/skills` missing

```bash
git submodule update --init --recursive
```

### Bedrock / AWS errors

Confirm `aws sts get-caller-identity` and region overrides in [INSTALL.md](INSTALL.md).

### Validator or `uip` not found

Install UiPath **`uip`** CLI per [INSTALL.md](INSTALL.md); `doctor` reports PATH status.

### Same repo, switching from Cursor

Re-run the opposite quickstart with **`-Force`** so `.assistant-choice` and expectations stay consistent.

---

## Further reading

- [USER_GUIDE.md](USER_GUIDE.md) — day-to-day CLI reference, env vars, cookbook
- [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) — Cursor + MCP tool surface (parity reference)
- [SLASH_COMMANDS.md](SLASH_COMMANDS.md) — slash command matrix and tool profiles
- [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md) — `/pdd` stages and outputs
- [README.md](../README.md) — project pitch, setup paths, skills update policy
