# Contributing

This project is extensible along three axes: **skills**, **tools**, and **slash commands**. The official UiPath skills live in a git submodule (`skills/skills/`) and should not be edited in-place - always override from a higher-priority layer. See [docs/SKILL_LAYOUT.md](docs/SKILL_LAYOUT.md) for the full layering model.

**Submodule vs `.cursor/skills`:** The submodule tree is the **source of truth** for full skill content (`SKILL.md`, references, assets). Files under `.cursor/skills/<name>/` are **gap-fill only** - add missing snippets that are not upstream yet; **do not** duplicate upstream filenames (e.g. a second `SKILL.md`) or you silently override the submodule and break Task Navigation. See template policy in companion repos: `docs/ops/skills-submodule-compliance.md` (UiPath Spec Project Template).

### Every UiPath build ends with a developer report

For non-trivial automation work in a real `project.json` repo, close the session with **validation evidence** (`uip rpa get-errors`) and a short report under `<project>/docs/reports/<YYYY-MM-DD>-<feature>-dev-report.md`. Rules, R/Y/G status, and the report skeleton are canonical in the **UiPath Spec Project Template** submodule at `agent/skills/skills/uipath-rpa/references/validation-and-reporting.md` (also summarized in `uipath-rpa` rules 28-32). This repo consumes that submodule - do not fork the reporting doc into `skills/skills/` here; update upstream in the template and pull the submodule.

## Add a skill

Skills are markdown playbooks (`SKILL.md`) with YAML frontmatter. The loader merges multiple roots; first source wins when two folders define the same skill `name`.

**Where to put a new skill**

| Intent | Location | In git? |
|---|---|---|
| Personal experiment | `~/.cursor/skills/<skill-name>/SKILL.md` | No |
| Per-checkout override | `.uipath-claude/skills/<skill-name>/SKILL.md` | No (gitignored) |
| Team-shared | `extensions/skills/<skill-name>/SKILL.md` | Yes |
| Official UiPath skill | `skills/skills/<skill-name>/SKILL.md` | Submodule - do not edit here |

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

Validate your skill registered: `uipath-claude chat` -> `/skills`. The origin column shows the layer you added it to.

## Add a tool

Tools live under [framework/uipath_claude/tools/](framework/uipath_claude/tools/). Each tool is a Python function registered in a tool group. Follow the pattern in [framework/uipath_claude/tools/skill_execution_tools.py](framework/uipath_claude/tools/skill_execution_tools.py):

1. Add the function with a typed signature and a docstring (the docstring becomes the model-visible description).
2. Register it in the relevant tool group / profile in `uipath_claude/tools/profiles.py`.
3. If the tool performs a potentially destructive operation, gate it through `uipath_claude/tools/uipath/approval.py`.
4. Add a unit test under `framework/tests/unit/tools/`.

Profiles (`safe`, `uipath-dev`, `all`) control which tools the agent sees. Default to `uipath-dev` or `all` only if the tool is clearly side-effect-free or gated.

## Add a slash command

Slash commands live under `framework/uipath_claude/commands/`. Each command is a small module exposing a `run(session, args)` function and registered on the command registry:

1. Create `framework/uipath_claude/commands/my_command.py` with a `run` function (or use the `@register_command` decorator from `framework/uipath_claude/commands/registry.py`).
2. Register it on the active `CommandRegistry` (most commands are registered when the chat session boots; see `framework/uipath_claude/cli/app.py` for `/bootstrap` and `/pdd`).
3. Document the command in `README.md` and [docs/USER_GUIDE.md](docs/USER_GUIDE.md).
4. Add a unit test under `framework/tests/unit/commands/`.

Slash commands call into the same Python packages as the CLI, so keep business logic in `query/` or `tools/` and keep the command thin.

Real-world examples:

- [`framework/uipath_claude/commands/pdd.py`](framework/uipath_claude/commands/pdd.py) - `/pdd`, parses `--project-type` / `--deploy` / `--folder` and delegates to `run_pdd_lifecycle` (full BA -> SA -> ADD -> TDD -> Dev -> QA + publish + deploy). See [docs/PDD_LIFECYCLE.md](docs/PDD_LIFECYCLE.md).
- [`framework/uipath_claude/commands/bootstrap.py`](framework/uipath_claude/commands/bootstrap.py) - `/bootstrap`, the legacy four-stage flow.

## UiPlan templates

- **Kit:** [templates/uiplan/](templates/uiplan/) (`_spec-template.md`, `_plan-template.md`, `_tasks-template.md`, `_diagram-patterns.md`).
- **UiPlan smoke:** `uv run pytest framework/tests/uiplan/test_generate_docs.py framework/tests/uiplan/test_cli_entrypoints.py -q`
- **Skills submodule:** do not advance `skills/` without updating `.uipath/skills-approved.sha` and running `uv run python -m uipath_claude.skills.submodule_guard`.

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
- `pytest framework/tests/unit/<path>` to iterate on a single area.
- Run evaluations before merging anything that touches the executor, planner, or skill registry.

## MCP setup (Cursor)

Copy `.cursor/mcp.json.example` to `.cursor/mcp.json` (the latter is gitignored), **or** run `ops/scripts/cursor-quickstart.ps1` / `cursor-quickstart.sh` from repo root to create it and sync deps in one step.
The example registers the `uipath-builder-agent` MCP server (stdio transport,
`uv run python -m mcp_server.server` with `PYTHONPATH` including `framework/`).
Cursor will only pick it up when three conditions are met:

1. **Python deps installed in a venv on PATH.** Run `pip install -e ".[dev]"`
   inside an active venv, then make sure `python` resolves to that venv when
   Cursor is launched (Windows: confirm with `where python`; macOS/Linux:
   `which python`). The MCP entry uses bare `python` so it follows whatever
   venv is active for the Cursor process.
2. **Open `uipath-builder-agent/` as the Cursor workspace root.** Not a
   parent like `c:\Users\<you>\projects\`. Project-scoped `.cursor/mcp.json`
   and `.cursor/rules/library-tools.mdc` only load when the workspace root
   matches this folder.
3. **Verify in Cursor.** Settings -> MCP should list `uipath-builder-agent`
   with a green status. If it is red, run `python -m mcp_server.server` in a
   terminal from the repo root - the import or startup error will surface
   there. The most common failures are a wrong venv (missing the `mcp`
   package) and a missing `pip install -e .` (so `mcp_server`/`uipath_claude`
   aren't importable).

Smoke-test the wiring by following the "Cursor test (MCP tools)" section in
[docs/SMOKE_TESTS.md](docs/SMOKE_TESTS.md), starting at Step 0.

### Assistant choice policy (local clone)

This repo supports both Cursor and Claude integrations, but contributors should use one assistant per clone.

- Cursor setup: `ops/scripts/cursor-quickstart.ps1` or `bash ops/scripts/cursor-quickstart.sh`
- Claude setup: `ops/scripts/claude-quickstart.ps1` or `bash ops/scripts/claude-quickstart.sh`

Quickstart writes `.assistant-choice` (gitignored) and blocks switching unless you pass `-Force` / `--force`.

Step 9 (`query_uipath_docs`) needs an Ask AI backend. For a clean clone the
fastest way to mark Step 9 PASS is to set
`UIPATH_ASKAI_ENDPOINT=mock://localfixture` before launching the MCP
server; the tool then returns a deterministic local fixture that includes
`SOURCE: askai-mock`. For real answers, point `UIPATH_ASKAI_ENDPOINT` at
your Ask AI URL (and set `UIPATH_ASKAI_API_KEY` if the endpoint requires
it) or install the bundled `skills/skills/uipath-askai/` SDK and configure
its `uipath_askai_config.json`.

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

## Model routing and fallback

Chat-facing LLM calls go through `uipath_claude.llm.invoke.build_chat_model`,
which resolves the model id via `uipath_claude.llm.router.select_model_for_task`
and wraps `invoke`/`ainvoke`/`stream`/`astream` so a single-shot fallback to the
tier's fallback model fires on model-related provider errors (model not found,
unsupported throughput, access denied).

Both routing flags default to **on** as of this change:

- `UIPATH_CLAUDE_ROUTING_DYNAMIC=1` (default) - pick HEAVY/LIGHT from
  caller-supplied `ComplexitySignals`. Set to `0` for the legacy static
  tier-only behavior.
- `UIPATH_CLAUDE_FALLBACK_ENABLED=1` (default) - retry once with the tier's
  fallback model id when a provider error is classified as model-related.
  Set to `0` to disable and surface the original error.

Model id overrides (unchanged):
`UIPATH_CLAUDE_MODEL_HEAVY`, `UIPATH_CLAUDE_MODEL_LIGHT`,
`UIPATH_CLAUDE_MODEL_FALLBACK_HEAVY`, `UIPATH_CLAUDE_MODEL_FALLBACK_LIGHT`,
`UIPATH_CLAUDE_MODEL` (global override). See
[uipath_claude/llm/routing/config.py](uipath_claude/llm/routing/config.py) for
precedence.

Routing telemetry (model selection, fallback triggers, fallback results) is
emitted as NDJSON via `StructuredLogger` to `~/.uipath-claude/logs/events.log`
under `event=llm_routing.*`. Disable with `UIPATH_CLAUDE_ROUTING_TELEMETRY=0`.

## Commit hygiene

- Keep diffs minimal; do not refactor unrelated code in the same PR.
- Update [CHANGELOG.md](CHANGELOG.md) under `## [Unreleased]` for any user-visible change.
- If you touch a skill or tool, verify `/skills` and `/status` still render cleanly.

## Review

Open a PR against `main`. A maintainer will run the evaluation framework and a manual smoke test (`uipath-claude start-project "InvoiceBot"` end-to-end) before merge.
