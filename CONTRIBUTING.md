# Contributing

This project is extensible along three axes: **skills**, **tools**, and **slash commands**. The official UiPath skills live in a git submodule (`skills/skills/`) and should not be edited in-place — always override from a higher-priority layer. See [docs/SKILL_LAYOUT.md](docs/SKILL_LAYOUT.md) for the full layering model.

## Add a skill

Skills are markdown playbooks (`SKILL.md`) with YAML frontmatter. The loader merges multiple roots; first source wins when two folders define the same skill `name`.

**Where to put a new skill**

| Intent | Location | In git? |
|---|---|---|
| Personal experiment | `~/.cursor/skills/<skill-name>/SKILL.md` | No |
| Per-checkout override | `.uipath-claude/skills/<skill-name>/SKILL.md` | No (gitignored) |
| Team-shared | `extensions/skills/<skill-name>/SKILL.md` | Yes |
| Official UiPath skill | `skills/skills/<skill-name>/SKILL.md` | Submodule — do not edit here |

**Minimum SKILL.md**

```markdown
---
name: my-skill
description: One sentence on what this skill teaches the agent.
triggers:
  - "when user mentions X"
  - "when building Y"
---

# My Skill

Procedure, constraints, examples. Keep it short; the whole file is injected into the model context when the skill matches.
```

Validate your skill registered: `uipath-claude chat` → `/skills`. The origin column shows the layer you added it to.

## Add a tool

Tools live under [uipath_claude/tools/](uipath_claude/tools/). Each tool is a Python function registered in a tool group. Follow the pattern in [uipath_claude/tools/skill_execution_tools.py](uipath_claude/tools/skill_execution_tools.py):

1. Add the function with a typed signature and a docstring (the docstring becomes the model-visible description).
2. Register it in the relevant tool group / profile in `uipath_claude/tools/profiles.py`.
3. If the tool performs a potentially destructive operation, gate it through `uipath_claude/tools/uipath/approval.py`.
4. Add a unit test under `tests/unit/tools/`.

Profiles (`safe`, `uipath-dev`, `all`) control which tools the agent sees. Default to `uipath-dev` or `all` only if the tool is clearly side-effect-free or gated.

## Add a slash command

Slash commands live under `uipath_claude/commands/`. Each command is a small module exposing a `run(session, args)` function and registered on the command registry:

1. Create `uipath_claude/commands/my_command.py` with a `run` function.
2. Register it in `uipath_claude/commands/registry.py` (or wherever the project currently centralizes registrations).
3. Document the command in `README.md` and [docs/USER_GUIDE.md](docs/USER_GUIDE.md).
4. Add a unit test under `tests/unit/commands/`.

Slash commands call into the same Python packages as the CLI, so keep business logic in `query/` or `tools/` and keep the command thin.

## Dev loop

```bash
# Install dev deps (once)
pip install -e ".[dev]"

# Lint + type + tests
ruff check .
black --check .
mypy uipath_claude
pytest

# Evaluations (longer running)
python run_evals.py
```

- `pytest -m "not integration"` to skip integration tests locally.
- `pytest tests/unit/<path>` to iterate on a single area.
- Run evaluations before merging anything that touches the executor, planner, or skill registry.

## MCP design-approval gate

Before the first write to a project the agent must propose a design and the
user must approve it. This stops the agent from racing into XAML before the
human has signed off on the architectural choices (REFramework vs simple
sequence, which packages, queue-driven vs synchronous, etc.).

Flow:

1. Agent gathers user intent. When trade-offs exist it asks the user (e.g.
   via Cursor's `AskQuestion`) to confirm the choices.
2. Agent calls `uipath_design_propose` with `project_dir`, `title`,
   `summary`, `body`, optional `rationale`, and `citations`. The MCP returns
   a `design_id` and the project remains write-locked.
3. Human reviews the summary and runs `uipath_design_approve` (or
   `uipath_design_reject`) with that `design_id`.
4. Once approved, `uipath_workflow_write_file` and
   `uipath_workflow_install_package` accept calls for that project.

Inspect status via `uipath_design_status` or list every proposal with
`uipath_design_list`.

Overrides:

- `UIPATH_DESIGN_APPROVAL_ENABLED=0` disables the design gate entirely
  (default `1`).
- `UIPATH_DESIGN_STORE_PATH=...` overrides the storage location (default
  `~/.uipath-builder-agent/design_proposals.json`).
- Per-call `allow_unapproved=true` on `uipath_workflow_write_file` /
  `uipath_workflow_install_package` bypasses for one call. Use only when
  the user explicitly waives the design step.

## MCP session gate

The `uipath-builder-agent` MCP server enforces an analyze/debug/fix loop on
every UiPath project it touches via a per-project session gate (see
[uipath_claude/tools/session_gate.py](uipath_claude/tools/session_gate.py)).
Behavior:

- Any successful `uipath_workflow_write_file` to a `.xaml`, `.cs`,
  `.json`, or `.uiproj` file marks the owning project (nearest ancestor
  with a `project.json`) as `dirty`.
- A successful `uipath_workflow_install_package` also marks `dirty`.
- While `dirty`, the gated tools `uipath_workflow_run`,
  `uipath_workflow_debug`, `uipath_workflow_install_package`,
  `uipath_workflow_run_command`, and `uipath_workflow_deploy` return
  `[BLOCKED] ...` instead of executing.
- The only way to clear `dirty` -> `verified` is
  `uipath_workflow_build_and_verify` returning `success=true` with
  `verdict=pass`. That tool runs the full loop server-side: probe -> auto
  install (when possible) -> `uip rpa get-errors` -> headless run -> Studio
  debug. With the default `require_studio_debug=true`, the Studio debug
  step is mandatory: when no Studio instance is detected, the call returns
  `verdict='needs_human'` with `next_action='start_studio_or_waive'` and
  the project stays `dirty`. The gate refuses to silently downgrade to a
  static-only "pass".
- Inspect state any time with `uipath_workflow_session_status`.
- The gate also detects out-of-band writes: every time a gated tool runs,
  the gate sweeps the project's tracked files (`.xaml`, `.cs`, `.json`,
  `.uiproj`) and flips to `dirty` when any mtime is newer than
  `last_verify_at`. This catches manual saves, IDE edits, and any
  `ApplyPatch`-style writes that bypass `uipath_workflow_write_file`.

Overrides:

- `UIPATH_MCP_GATE_ENABLED=0` disables the gate process-wide. Set to `1`
  (default) for normal operation.
- Per-call `allow_unverified=true` bypasses the gate for one tool call.
  Use only when the user explicitly asks; the gate state itself is not
  cleared by an override.
- Per-call `require_studio_debug=false` on `uipath_workflow_build_and_verify`
  waives the mandatory Studio debug step. Use only when the user explicitly
  asks (e.g. CI host with no Studio installed).
- `unknown` (no writes observed in this MCP process yet) is a soft pass so
  server restarts don't deadlock honest users; only `dirty` blocks. The
  out-of-band sweep does run from `unknown`, so a project that was edited
  before the MCP started will still be detected as `dirty` on the first
  gated call.

## Commit hygiene

- Keep diffs minimal; do not refactor unrelated code in the same PR.
- Update [CHANGELOG.md](CHANGELOG.md) under `## [Unreleased]` for any user-visible change.
- If you touch a skill or tool, verify `/skills` and `/status` still render cleanly.

## Review

Open a PR against `main`. A maintainer will run the evaluation framework and a manual smoke test (`uipath-claude start-project "InvoiceBot"` end-to-end) before merge.
