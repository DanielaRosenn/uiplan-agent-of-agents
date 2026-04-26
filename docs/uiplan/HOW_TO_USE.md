# How to use UiPlan

## Canonical paths

- **Kit:** `templates/uiplan/` at repo root (MCP and `generate-docs` resolve here).
- **Pytest (UiPlan):** `framework/tests/uiplan/`. Example: `uv run pytest framework/tests/uiplan/ -q`.

## Decision table

| I want to… | Use |
| --- | --- |
| Chat-native flow with grounding and review | MCP `uipath_plan_ground`, `uipath_plan_spec_new`, `uipath_plan_plan_new`, `uipath_plan_tasks_new`, `uipath_plan_review` (or `uipath_plan_uiplan_new` for the bundled path). |
| A file-first bundle from templates with local validation | From repo root: `uv run python -m tools.uiplan generate-docs <slug>` (optional `--out`, `--kit`, `--strict`, `--paradigm`). |
| Slash commands in Cursor | Separate skill commands: `/uiplan-full`, `/uiplan-ground`, `/uiplan-spec`, `/uiplan-plan`, `/uiplan-tasks`, `/uiplan-review`, and `/uiplan-implement`. |
| CLI parity with chat | `uipath-claude plan uiplan …` (see [USER_GUIDE.md](../USER_GUIDE.md)). |

## Paths (folder convention)

- **Drafts (default):** `.cursor/plans/<slug>/` with `spec.md`, `plan.md`, `tasks.md`, `.meta.yaml` (`plan_kind: uiplan`). Draft trees are gitignored like other `.cursor/plans` work.
- **Published:** `docs/plans/<slug>/` after `uipath_plan_accept` + `uipath_plan_publish`.
- **Templates (kit):** [`templates/uiplan/`](../../templates/uiplan/) at the repo root.

## Human approval gate

Do **not** treat `generate-docs` output as approved scope by default.

1. Read the three files for real grounding text (replace `_…_` placeholders).
2. Confirm `spec.md` includes **Development Handoff**, `plan.md` includes
   **Development execution contract**, and `tasks.md` includes
   **Build, Verify, and Handoff**.
3. Run `uipath_plan_review` until `"ok": true` when using MCP.
4. Only then accept the bundle and run `scaffold-code` or start implementation
   work from `tasks.md`.

## Numbered quickstarts

### A) Cursor skill / slash

1. Open the repo in Cursor with skills installed ([INSTALL.md](../INSTALL.md)).
2. Use `/uiplan-full <title>` for the bundled path, or staged commands:
   `/uiplan-ground`, `/uiplan-spec`, `/uiplan-plan`, `/uiplan-tasks`, and
   `/uiplan-review`.
3. After review passes and you approve the build, use `/uiplan-implement <slug>`
   to execute from `tasks.md` with the relevant skills, MCP tools, subagents,
   library/AskAI lookup, CLI commands, tests, and build gates.
4. The command wrappers point back to `.cursor/skills/uiplan/SKILL.md`, map to
   the same `uipath_plan_*` MCP tools as the CLI/chat surface, and keep
   implementation behind review plus human approval.

### B) Local Typer CLI (`tools/uiplan`)

```bash
cd <repo-root>
uv sync
uv run python -m tools.uiplan generate-docs 2026-04-23-my-feature
# optional: --out path/to/folder --kit path/to/kit --no-strict --paradigm coded-agent
uv run python -m tools.uiplan scaffold-code 2026-04-23-my-feature --max-loops 5
```

### C) MCP (`uipath_plan_*`)

Use when the agent session already has MCP enabled ([MCP_TOOLS.md](../MCP_TOOLS.md)). Prefer `uipath_plan_ground` first, then the `spec` / `plan` / `tasks` stages, then `uipath_plan_review`.

The grounding pack is workspace-aware: it includes the `uipath-planner` route,
the `uipath-project-discovery-agent` handoff, matched specialist skill excerpts,
local library search, and the library → AskAI lookup path when available.
`uipath_plan_plan_new` writes those inputs into `plan.md` so later task
generation, implementation, and review can cite them.

`uipath_plan_tasks_new` is the build handoff. Its final phase should drive the
accepted implementation loop. In Cursor, `/uiplan-implement <slug>` reads the
planner/specialist handoff, reviews first, asks before building, executes tasks
in order, runs restore -> analyze -> test -> pack, and stops before any
approval-required deploy.

`uipath_plan_review` now includes feasibility checks for declared paradigm,
code-structure descriptors, CLI-family consistency, artifact-rich tasks, and
deploy gates.
