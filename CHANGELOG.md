# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Canonical UiPath assistant capability contract in `docs/CAPABILITY_CONTRACT.md`, backed by runtime constants and tests, documenting pragmatic Claude-Code-style parity across CLI, Cursor MCP, and approved skill overlays.
- Doctor checks for Cursor skill drift and reproducible MCP launch configuration, plus `/doctor` and `/resume` coverage in the in-chat slash command surface.
- Library book `MANIFEST.yaml` metadata for UiPath CLI, Agents, Maestro, Data Fabric, and Diagnostics books so `uipath-claude doctor` can validate the catalog cleanly.

### Changed
- Cursor skill setup now generates `.cursor/skills` from the official UiPath skills submodule plus team overlays from `extensions/skills`.
- [docs/CLAUDE_USER_GUIDE.md](docs/CLAUDE_USER_GUIDE.md) and [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) now include clearer visual flow coverage for the Claude terminal loop and current `framework/` runtime/MCP paths.
- [docs/CURSOR_USER_GUIDE.md](docs/CURSOR_USER_GUIDE.md) and [docs/CLAUDE_USER_GUIDE.md](docs/CLAUDE_USER_GUIDE.md) now include practical best practices for Cursor MCP usage, prompt shape, tool selection by risk, context hygiene, safety rules, CLI preflight, slash-command selection, validation, and library learning.
- [README.md](README.md) — refreshed as the project front door with a stronger visual overview, Cursor/CLI/library entry points, current skill routing (`uipath-rpa` vs `uipath-interact`), doctor preflight instructions, library learning links, and corrected `framework/` contribution paths.
- [docs/CLAUDE_USER_GUIDE.md](docs/CLAUDE_USER_GUIDE.md) — terminal / Claude Code guide: step-by-step `uipath-claude` usage, `chat` flags, session ids, Typer commands, hooks vs Actions, and debugging/restart; [docs/USER_GUIDE.md](docs/USER_GUIDE.md) and [docs/CURSOR_USER_GUIDE.md](docs/CURSOR_USER_GUIDE.md) cross-link it.

### Removed
- Root **`.github/workflows/`** jobs (`mermaid-validate`, `update-skills-submodule`); use local `ops/scripts`, Cursor session hooks, or OS scheduling until you re-enable Actions.

### Changed
- UiPlan template kit paths are consistently **`templates/uiplan/`** in contributor docs, superpowers records, and Phase 4 checklists.

### Fixed
- Mermaid diagrams render reliably in GitHub and strict viewers: `ops/scripts/generate_mcp_tools_doc.py` no longer injects `%%{init}%%`, `classDef`, or `linkStyle` into generated `docs/MCP_TOOLS.md` charts; UiPlan kit templates (`templates/uiplan/_diagram-patterns.md`, `_spec-template.md`) and `docs/uiplan/README.md` drop unsupported sequence-diagram styling. Regenerate MCP docs with `python ops/scripts/generate_mcp_tools_doc.py` after tool changes.

### Added
- [docs/SKILL_VISUAL_GUIDE.md](docs/SKILL_VISUAL_GUIDE.md) with diagrams for the skill runtime loop, skill families, every UiPath skill, Cursor flow, Claude/CLI flow, MCP tool families, and an end-to-end sequence.
- [docs/assets/builder-agent-logo.svg](docs/assets/builder-agent-logo.svg) and [docs/assets/builder-agent-icon.svg](docs/assets/builder-agent-icon.svg), now used by the README and visual docs as the project-level robot/AI visual identity.
- UiPlan docs and onboarding refresh: README now has a clear purpose section and a "how to use everything" map; `docs/USER_GUIDE.md` includes a practical UiPlan cookbook and end-to-end workflow; `docs/uiplan/README.md` adds a first-15-min path, decision tree, and leverage patterns; `docs/MANUAL_REVIEW_CURSOR_FULL_PROJECT.md` adds onboarding-comprehension checks and extra NL routing prompts; docs index links updated; new logo asset at `docs/assets/uiplan-logo.svg`.
- `ops/scripts/claude-quickstart.ps1` and `ops/scripts/claude-quickstart.sh` for near-zero-touch Claude onboarding (`git submodule update --init --recursive` + `uv sync --extra dev` + first-run checks).
- Local assistant-selection lock for onboarding: Cursor and Claude quickstart scripts now write `.assistant-choice` (gitignored) and require `-Force` / `--force` to switch the same clone to the other assistant.
- Ambiguity-triage contract across the build pipeline: `extensions/skills/uipath-planner/SKILL.md` overlay batches Step 1 questions into a single `AskUserQuestion` card, adds a new Step 1.5 residue card (attended/unattended, source/destination systems, Orchestrator folder, deploy-or-not), and adds anti-patterns 18 and 19 ("don't ask items the planner / library / filesystem can answer", "don't ask one-at-a-time"). BA persona (`uipath_claude/query/ba_agent.py` `BA_SYSTEM_PROMPT`) now reads the planner's plan file first and refuses to re-ask resolved items. `uipath_design_propose` accepts a structured `resolutions` object (`project_type`, `attended_unattended`, `external_systems`, `orchestrator_folder`, `deploy`, `destructive_actions`, `open_questions_residue`, etc.) that `uipath_design_status` surfaces as `latest_pending_resolutions` / `latest_approved_resolutions` so the approval card shows the triage outcome verbatim; omitting the field is deprecated but still accepted with a warning. New Scenario 13 in `docs/SMOKE_TESTS.md` grades the whole contract end-to-end. New "Question-asking contract" section in `docs/ARCHITECTURE.md`.
- `docs/PDD_LIFECYCLE.md` documenting the full `/pdd` flow (BA -> SA -> ADD -> TDD -> Dev -> QA -> publish -> deploy), stages, sub-agent invocation model, output layout, and failure semantics.
- README, `docs/ARCHITECTURE.md`, and `docs/USER_GUIDE.md` updated to cover the six-agent pipeline, `/pdd` flags (`--project-type`, `--deploy`, `--folder`), and the legacy `/bootstrap` four-stage flow.
- `docs/CURSOR_USER_GUIDE.md` now lists every registered MCP tool, including `uipath_workflow_create_project` / `_publish` / `_session_status` / `_environment_probe` / `_build_and_verify`, all `uipath_doc_*` authoring tools, the full `uipath_library_*` surface, and a new `uipath_design_*` section.
- `docs/TOOLS.md` MCP-prefix table now lists per-prefix coverage and adds the `uipath_design_*` prefix.
- `docs/LIBRARY_LEARNING.md` and `docs/LIBRARY_AUTHORING.md` now provide explicit MCP tool-name mappings for browse/search/proposal flows.
- `CONTRIBUTING.md` references `/pdd` and `/bootstrap` as worked slash-command examples.
- README rewritten as a layered pitch deck with Mermaid architecture and pipeline diagrams.
- `docs/README.md` as a single landing page indexing every doc.
- `docs/INSTALL.md` long-form installation guide.
- `CONTRIBUTING.md` covering the extension model (skills, tools, slash commands).
- `examples/` folder with four runnable scenarios including a Confluence-publisher dogfooding example.
- `ops/scripts/publish_confluence.py` + PowerShell wrapper for publishing docs to the Cato RPA Confluence space. Auth proxies through the UiPath Integration Service Atlassian Confluence connection; no standalone Atlassian API token is held on the developer machine.
- `docs/wiki/` drafts for the Confluence overview and quickstart pages.
- `docs/assets/demo.tape` VHS script + `ops/scripts/record-demo.ps1` for reproducible terminal casts.

### Removed
- Stale and historical docs: `README_DEPLOYMENT.md`, `IMPLEMENTATION_COMPLETE.md`, `docs/UIPATH_CLAUDE_CODE_IMPLEMENTATION.md`, `docs/sprint-1-summary.md`, `docs/CLEANUP_PLAN.md`, `docs/EVALUATION_RESULTS.md`, `docs/CLAUDE_CODE_FEATURE_RELEVANCE_MATRIX.md`, `docs/wiki/azure-devops-landing.md`, the two `docs/plans/2026-04-14-*.md` files, and the entire `docs/superpowers/plans/` and `docs/superpowers/specs/` directories.

## [0.2.0] — 2026-04

### Added
- Agentic ReAct executor (`uipath_claude/query/agentic_executor.py`) with configurable iteration cap.
- Two-stage validation: static (`validate_file`) plus runtime (`run_workflow`) with `validate_and_fix_loop`.
- Plan mode with read-only proposal and approval gate before build.
- BA / SA / Developer / QA personas sharing one engine via prompt and tool filtering.
- Bootstrap flow (`uipath-claude start-project`) producing PDD → SDD → Code → QA artifacts.
- Multi-source skill registry with provenance (user, project, team extensions, UiPath submodule, templates) and first-source-wins resolution.
- Skill insights storage with user / project / shared layers and summary merging.
- Library learning loop: harvest → propose → apply knowledge content.
- Memory system (global `~/.uipath-claude/memory.md` and per-project).
- Session recall via `/recall` backed by session JSONL store.
- Hooks system (session start, tool use, file changes).
- Tool profiles (`safe`, `uipath-dev`, `all`) and per-operation approval gates.
- Evaluation framework with datasets and composite evaluators.
- Cursor integration via `ops/scripts/setup-cursor.ps1` / `.sh` linking skills into `.cursor/skills/`.
- Slash commands: `/help`, `/status`, `/skills`, `/analyze`, `/bootstrap`, `/chat`, `/recall`, `/repair-restore`, `/validate`.
- UiPath integrations: CLI runner, Workflow Analyzer, Orchestrator REST API, Ask AI, Integration Service smoke check.
- MCP server entrypoint (`mcp_server/`) for Model Context Protocol clients.

## [0.1.0] — 2026-04

### Added
- Initial project layout: `uipath_claude/` package with CLI, query engine, tools, skills, commands, and graph nodes.
- Conversational chat against AWS Bedrock (Anthropic Claude) with streaming.
- Basic UiPath CLI wrapper and project scaffolding tools.
- Official UiPath skills pulled in as a git submodule under `skills/`.
- `QUICKSTART.md` and initial `README.md`.
