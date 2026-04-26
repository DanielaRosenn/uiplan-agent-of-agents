# How to use UiPlan

## Canonical paths

- **Kit:** `templates/uiplan/` at repo root (MCP and `generate-docs` resolve here).
- **Pytest (UiPlan):** `framework/tests/uiplan/`. Example: `uv run pytest framework/tests/uiplan/ -q`.

## Decision table

| I want to… | Use |
| --- | --- |
| Chat-native flow with grounding and review | MCP `uipath_plan_ground`, `uipath_plan_spec_new`, `uipath_plan_plan_new`, `uipath_plan_tasks_new`, `uipath_plan_review` (or `uipath_plan_uiplan_new` for the bundled path). |
| A file-first bundle from templates with local validation | From repo root: `uv run python -m tools.uiplan generate-docs <slug>` (optional `--out`, `--kit`, `--strict`). |
| Slash commands in Cursor | Project command `.cursor/commands/uiplan.md`: `/uiplan` with dispatcher subcommands (`full`, `ground`, `spec`, `plan`, `tasks`, `review`). |
| CLI parity with chat | `uipath-claude plan uiplan …` (see [USER_GUIDE.md](../USER_GUIDE.md)). |

## Paths (folder convention)

- **Drafts (default):** `.cursor/plans/<slug>/` with `spec.md`, `plan.md`, `tasks.md`, `.meta.yaml` (`plan_kind: uiplan`). Draft trees are gitignored like other `.cursor/plans` work.
- **Published:** `docs/plans/<slug>/` after `uipath_plan_accept` + `uipath_plan_publish`.
- **Templates (kit):** [`templates/uiplan/`](../../templates/uiplan/) at the repo root.

## Human approval gate

Do **not** treat `generate-docs` output as approved scope by default.

1. Read the three files for real grounding text (replace `_…_` placeholders).
2. Run `uipath_plan_review` until `"ok": true` when using MCP.
3. Only then run `scaffold-code` or start implementation work.

## Numbered quickstarts

### A) Cursor skill / slash

1. Open the repo in Cursor with skills installed ([INSTALL.md](../INSTALL.md)).
2. Use the project slash command from `.cursor/commands/uiplan.md`:
   `/uiplan full <title>` for the bundled path, or staged routes like
   `/uiplan ground`, `/uiplan spec`, `/uiplan plan`, `/uiplan tasks`, and
   `/uiplan review`.
3. The dispatcher loads `.cursor/skills/uiplan/SKILL.md`, maps to the same
   `uipath_plan_*` MCP tools as the CLI/chat surface, and keeps implementation
   behind review plus human acceptance.

### B) Local Typer CLI (`tools/uiplan`)

```bash
cd <repo-root>
uv sync
uv run python -m tools.uiplan generate-docs 2026-04-23-my-feature
# optional: --out path/to/folder --kit path/to/kit --no-strict
uv run python -m tools.uiplan scaffold-code 2026-04-23-my-feature --max-loops 5
```

### C) MCP (`uipath_plan_*`)

Use when the agent session already has MCP enabled ([MCP_TOOLS.md](../MCP_TOOLS.md)). Prefer `uipath_plan_ground` first, then the `spec` / `plan` / `tasks` stages, then `uipath_plan_review`.

The grounding pack is workspace-aware: it includes `uipath-planner`, matched
specialist skill excerpts, local library search, and the library → AskAI lookup
path when available. `uipath_plan_plan_new` writes those inputs into `plan.md`
so later task generation and review can cite them.
