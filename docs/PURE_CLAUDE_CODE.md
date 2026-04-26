# Pure Claude Code usage

This guide is for [Anthropic Claude Code](https://docs.anthropic.com/en/docs/claude-code) (`claude` in a terminal) in a cloned **UiPath Builder Agent** repo: read `CLAUDE.md`, edit files, and run local commands, **without** the Cursor UI and **without** this repo’s `uipath-claude chat` entrypoint (unless you choose to use it).

| Topic | In this doc |
| --- | --- |
| What pure Claude is | Direct `claude` session at repo root |
| What is different | No Cursor skills UI, no built-in `uipath-claude` slash registry unless you wire MCP/CLI |
| How to get parity | Skill files + optional MCP + optional `uv run uipath-claude` |

## What this is not

- **Anthropic login** (Claude Code) is separate from **AWS** (used by this repo’s Bedrock-backed `uipath-claude` runtime and by some local flows) and from **UiPath** (`uipath` / `uip` / `uipath-claude` Orchestrator features).
- Pure `claude` does **not** run the LangGraph + Bedrock `uipath-claude chat` REPL. For that, use `uv run uipath-claude chat` and see [CLAUDE_USER_GUIDE.md](CLAUDE_USER_GUIDE.md).

## Prerequisites

| Requirement | Notes |
| --- | --- |
| Git, Git for Windows (native Windows) | [Advanced setup](https://docs.anthropic.com/en/docs/claude-code/setup) |
| Claude Code installed | e.g. PowerShell: `irm https://claude.ai/install.ps1 | iex`, then `claude --version` |
| Python 3.11+ and `uv` | Repo: `uv sync --extra dev` from root |
| Submodule | `git submodule update --init --recursive` (official UiPath `skills/`) |
| `skills/` approved SHA | `python -m uipath_claude.skills.submodule_guard` must be OK after clone/pull |
| AWS (optional) | Only for `uipath-claude chat` and Bedrock-backed flows: `aws sts get-caller-identity` |
| UiPath CLIs (optional) | `uipcli` / `uipath` / `uip` on PATH as needed; see [uipath-cli.md](uipath-cli.md) for exact flags |

## Quick start

From a fresh clone at **repo root** (folder with `pyproject.toml` and `framework/`):

```powershell
git submodule update --init --recursive
uv sync --extra dev
python -m uipath_claude.skills.submodule_guard
claude
```

First turn in `claude`, keep scope explicit (example):

```text
Read CLAUDE.md, then .cursor/skills/uiplan/SKILL.md. Detect project type from
pyproject.toml and langgraph.json. Do not edit without summarizing the plan. For
UiPath product facts, use MCP uipath_library_search / uipath_doc_get_activity
if configured, not raw reads of data/library/.
```

## Project discovery (Studio / RPA on disk)

If the user is building against a real UiPath process tree, follow root `CLAUDE.md`: if `.claude/rules/project-context.md` is missing before build work, run the workflow from `skills/agents/uipath-project-discovery-agent.md` (or ask the user for path + consent). This repo root is a **Python/LangGraph agent** workspace, not a Studio `project.json` at root.

## Optional: MCP in Claude Code (parity with Cursor)

The same MCP server this repo uses in Cursor can be added to Claude Code. Official syntax (stdio, options before the server name) is documented under [Claude Code MCP](https://docs.anthropic.com/en/docs/claude-code/mcp/).

From repo root (adjust name and scope; prefer **local** for experimental servers):

```bash
claude mcp add --transport stdio uipath-builder --scope local -- uv run python -m mcp_server.server
```

- Tool catalog: [MCP_TOOLS.md](MCP_TOOLS.md) (regenerate after tool changes: repo ops in [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) or project scripts, if you change server code).
- In-session check: use `/mcp` in Claude Code per product docs.
- `PYTHONPATH`: `uv run` with `-m mcp_server.server` from the repo that contains `framework/` is usually enough; if not, set env in the MCP `claude mcp add --env` flags.

## Optional: repo CLI from pure Claude (no `chat` required)

For deterministic, scriptable plan tools:

```powershell
uv run uipath-claude doctor
uv run uipath-claude plan uiplan full "Your feature title"
uv run uipath-claude plan uiplan accept "your-plan-id"
uv run uipath-claude plan uiplan implement "your-slug"
uv run pytest -q
```

`uipath-claude plan uiplan accept <plan-id>` marks the reviewed UiPlan bundle
accepted. `uipath-claude plan uiplan implement <plan-id>` runs
`uipath_plan_review` with `stage=all` and prints JSON (build preflight). Chat
uses a friendly handoff; see [SLASH_COMMANDS.md](SLASH_COMMANDS.md).

Use `uipath-claude chat` only if you want this project’s custom Bedrock+LangGraph REPL, slash command registry, session store, and orchestration router. Otherwise stay in `claude` and use skills + optional MCP/CLI as above.

## What works in pure `claude`

- Reads [CLAUDE.md](CLAUDE.md), [.cursor/rules/](.cursor/rules/), [docs/](docs/README.md), `.cursor/skills/`, and `extensions/skills/` as normal files.
- Runs any shell tool you allow: `uv run pytest`, `dotnet`, `uipath-claude` subcommands, `uipcli`, `uip` when installed.
- Edits `.cursor/plans/.../spec.md`, `plan.md`, `tasks.md`, and source under your approval policy.

## What is different: Cursor, `uipath-claude chat`, and pure `claude`

| | Cursor + skills | `uipath-claude chat` | Pure `claude` |
| --- | --- | --- | --- |
| Native `/uiplan-*` UI | Yes (skill entries) | Yes (slash commands) | No: name skill file or use MCP/CLI |
| `UIPATH_CLAUDE_TOOL_PROFILE` | N/A in IDE | Enforced | Not enforced; prompt for approvals or use `chat` |
| Session `/resume` / store | N/A / MCP | Yes | No built-in: start new or use `uip`/`uipath-claude` |
| LLM for router | N/A / MCP | Bedrock in-process | Your Claude Code model |

### Slash and skill parity (prompts)

| Cursor / chat command | In pure `claude`, ask (or open the skill) |
| --- | --- |
| `/doctor` | "Run a read-only health pass: `uv run uipath-claude doctor`" |
| `/status` / `/skills` | "Summarize from repo: loaded skills, env; no hidden session" or start `uipath-claude chat` briefly for `/status` |
| `/pdd`, `/bootstrap` | Open `.cursor/skills/...` or follow [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md) + slash mapping in [SLASH_COMMANDS.md](SLASH_COMMANDS.md) |
| `/validate`, `/analyze` | See [uipath-cli.md](uipath-cli.md) for exact `uipcli` flags; or `/validate`-style command via `uipath-claude chat` |
| `/books` | If MCP: `uipath_library_list` / `uipath_library_search`; else follow library rules in `.cursor/rules/library-tools.mdc` in Cursor, or use CLI paths documented in [USER_GUIDE.md](USER_GUIDE.md) |
| `/uiplan-full <title>` | "Follow `.cursor/skills/uiplan-full/SKILL.md`" or `uv run uipath-claude plan uiplan full "<title>"` |
| `/uiplan-implement <slug>` | "Follow `.cursor/skills/uiplan-implement/SKILL.md`" or `uv run uipath-claude plan uiplan implement <slug>` + agentic execution after human approval |
| `/resume` / `/recall` | Use `uipath-claude chat` for session history, or use git + `docs/`; no 1:1 in pure `claude` alone |

## UiPlan lifecycle (three-file bundle)

Canonical contract: [.cursor/skills/uiplan/SKILL.md](.cursor/skills/uiplan/SKILL.md) (drafts under `.cursor/plans/`, review, accept, optional publish to `docs/plans/`). Implement only after review + explicit acceptance: see `.cursor/skills/uiplan-implement/SKILL.md` in the repo.

## Safety and gates

- Do not deploy or publish without explicit user approval. Never target Production from an AI-only session; follow root `CLAUDE.md`.
- For UiPath CLI, read [uipath-cli.md](uipath-cli.md) before non-trivial invocations.
- Build loop: restore to analyze to test to pack. Do not commit `.env` or credentials.

## Related

- [CLAUDE_USER_GUIDE.md](CLAUDE_USER_GUIDE.md) — `uipath-claude` terminal session
- [CAPABILITY_CONTRACT.md](CAPABILITY_CONTRACT.md) — what each surface is supposed to cover
- [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) — Cursor + MCP
