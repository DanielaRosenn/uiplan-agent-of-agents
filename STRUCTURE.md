# Repository Structure

Map of the top-level directories in this template, intended for someone
forking it. Read [`CLAUDE.md`](CLAUDE.md) for AI-assistant rules and
[`QUICKSTART.md`](QUICKSTART.md) for the human getting-started flow.

| Path | Owner | Purpose |
|---|---|---|
| `apps/uiplan-studio/` | product | React + Vite frontend for the UiPlan Studio Explorer |
| `services/uiplan-studio-api/` | product | FastAPI backend that indexes projects and serves the explorer graph |
| `framework/uipath_claude/` | product | Python core (CLI, library/skills registries, planning tooling) |
| `extensions/skills/` | product | Project-local overrides on top of the `skills/` submodule |
| `skills/` | upstream submodule (read-only) | Source of truth for UiPath skills - pinned in `.uipath/skills-approved.sha` |
| `templates/` | product | Project starter templates (RPA, agent, solution, etc.) |
| `scaffold/` | product | Lower-level scaffolding helpers used by the templates |
| `examples/` | docs | Worked examples and sample projects used by the docs |
| `data/` | product | Documentation library content (read via `uipath_library_*` MCP tools) |
| `config/` | product | Static configuration shared across apps and services |
| `tools/` | dev | Build, CI, and developer helper scripts |
| `ops/` | dev | Operational scripts (deploy, migration, telemetry) |
| `test-fixtures/` | dev | Cross-cutting fixtures used by multiple test suites |
| `docs/` | docs | All product, architecture, and how-to documentation |
| `docs/uiplan/` | docs | UiPlan Studio (Explorer + planner) docs - start at `docs/uiplan/README.md` |
| `docs/superpowers/` | dev | Specs and plans produced by the brainstorming/writing-plans flow |
| `.cursor/` | dev | Cursor IDE rules, skills, slash commands |
| `.claude/` | dev | Claude Code rules and project context |
| `.uipath/` | dev | Submodule SHA pin and other UiPath-tooling state |
| `.uipath-claude/` | dev | Per-machine state for the `uipath-claude` CLI (gitignored) |
| `.githooks/` | dev | Git hooks the team checks in (run `git config core.hooksPath .githooks`) |
| `.github/` | dev | GitHub Actions workflows |
| `projects/`, `generated/`, `.worktrees/` | scratch | **Gitignored.** Per-developer working areas; never commit |

## Top-level files

| File | Purpose |
|---|---|
| `CLAUDE.md` | Hard rules and decision logic for any AI assistant working in this repo |
| `QUICKSTART.md` | Human getting-started guide |
| `README.md` | High-level intro |
| `CONTRIBUTING.md` | Contribution rules |
| `CHANGELOG.md` | Release notes |
| `VERSION` | Single source of truth for the template version |
| `.env.example` | Template for `.env` (never commit a real `.env`) |
| `pyproject.toml` / `uv.lock` | Python tooling for the framework |
| `langgraph.json` / `run_evals.py` | Local agent + eval glue |

## Where to start by goal

| Goal | Open |
|---|---|
| Use the Explorer in a new project | [`docs/uiplan/EXPLORER_NEW_PROJECT.md`](docs/uiplan/EXPLORER_NEW_PROJECT.md) |
| Understand the Explorer architecture | [`docs/uiplan/EXPLORER.md`](docs/uiplan/EXPLORER.md) |
| Plan a build with UiPlan | [`docs/uiplan/HOW_TO_USE.md`](docs/uiplan/HOW_TO_USE.md) |
| Pick a UiPath paradigm | [`CLAUDE.md`](CLAUDE.md) §1 (project type detection) |
| Run a CLI command | [`docs/uipath-cli.md`](docs/uipath-cli.md) |
| Read the latest review/cleanup notes | [`docs/uiplan/EXPLORER_REVIEW_2026-05-07.md`](docs/uiplan/EXPLORER_REVIEW_2026-05-07.md) |
