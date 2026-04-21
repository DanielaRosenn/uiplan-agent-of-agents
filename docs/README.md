# Docs index

Landing page for everything under `docs/`. Start with [ARCHITECTURE.md](ARCHITECTURE.md) if you want to understand the system; start with [USER_GUIDE.md](USER_GUIDE.md) if you want to use it.

## Core

- [ARCHITECTURE.md](ARCHITECTURE.md) — runtime, agentic executor, validator gate, `/pdd` and `/bootstrap` pipelines.
- [USER_GUIDE.md](USER_GUIDE.md) — day-to-day CLI usage, slash commands, env vars.
- [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md) — the full BA -> SA -> ADD -> TDD -> Dev -> QA -> publish -> deploy flow driven by `/pdd`.
- [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) — using the UiPath skills + MCP tools from inside Cursor.
- [INSTALL.md](INSTALL.md) — full installation: UiPath CLI, Studio 26.2+, submodules, AWS Bedrock.
- [TOOLS.md](TOOLS.md) — reference for every tool the agent can call.
- [MCP_TOOLS.md](MCP_TOOLS.md) — generated catalog of MCP-exposed tools (run `python scripts/generate_mcp_tools_doc.py` after changes).
- [MCP_TOOLS_FINDINGS.md](MCP_TOOLS_FINDINGS.md) — known gaps and recommended fixes for MCP tools.

## Planning (Cursor + agent)

- [plans/README.md](plans/README.md) — index of git-tracked implementation plans under `docs/plans/`.
- [plans/_TEMPLATE.md](plans/_TEMPLATE.md) — required front matter, Mermaid, tasks, verification.
- Cursor skills: `.cursor/skills/writing-uipath-plans/SKILL.md`, `.cursor/skills/mermaid-diagram-builder/SKILL.md`.
- MCP: `uipath_plan_save`, `uipath_plan_list`, `uipath_plan_read`, `uipath_plan_status_set`, `uipath_plan_render_mermaid`, plus `uipath_plan_build` (discovery-fronted) — see [MCP_TOOLS.md](MCP_TOOLS.md).
- Regenerate the plans table: `python scripts/generate_plan_index.py`.
- Formal lifecycle: [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md).

## Skills and library

- [SKILL_LAYOUT.md](SKILL_LAYOUT.md) — how skills are layered (user, project, extensions, submodule, template), and how to keep Cursor in sync with the submodule.
- [LIBRARY_AUTHORING.md](LIBRARY_AUTHORING.md) — authoring content for the knowledge library.
- [LIBRARY_LEARNING.md](LIBRARY_LEARNING.md) — the harvest -> propose -> apply learning loop.
- [CAPABILITY_PARITY.md](CAPABILITY_PARITY.md) — feature parity tracker vs. Claude Code.

## Evaluation and QA

- [Testing_Guide.md](Testing_Guide.md) — how to run tests.
- [SMOKE_TESTS.md](SMOKE_TESTS.md) — end-to-end smoke scenarios.
- [MANUAL_EVAL_AND_QA.md](MANUAL_EVAL_AND_QA.md) — manual evaluation checklist.
- [workflow-benchmarks.md](workflow-benchmarks.md) — benchmark workflows.

## Deployment

- [DEPLOYMENT_INTEGRATION.md](DEPLOYMENT_INTEGRATION.md) — deployment integration notes.

## Cato discoverability (wiki drafts)

- [wiki/confluence-overview.md](wiki/confluence-overview.md) — Confluence "Overview" page (non-dev audience).
- [wiki/confluence-quickstart.md](wiki/confluence-quickstart.md) — Confluence "Quickstart for developers" page.

## Assets

- [assets/demo.tape](assets/demo.tape) — VHS script for the hero terminal cast.
- `assets/demo.gif` — rendered terminal cast (generated from `demo.tape`).
