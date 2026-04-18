# Changelog

All notable changes to this project are documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- README rewritten as a layered pitch deck with Mermaid architecture and pipeline diagrams.
- `docs/README.md` as a single landing page indexing every doc.
- `docs/INSTALL.md` long-form installation guide.
- `CONTRIBUTING.md` covering the extension model (skills, tools, slash commands).
- `examples/` folder with four runnable scenarios including a Confluence-publisher dogfooding example.
- `scripts/publish_confluence.py` + PowerShell wrapper for publishing docs to the Cato RPA Confluence space.
- `docs/wiki/` drafts for Azure DevOps landing copy and Confluence pages.
- `docs/assets/demo.tape` VHS script + `scripts/record-demo.ps1` for reproducible terminal casts.
- BA → SA → Dev → QA pipeline Mermaid diagram in `docs/ARCHITECTURE.md`.

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
- Cursor integration via `scripts/setup-cursor.ps1` / `.sh` linking skills into `.cursor/skills/`.
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
