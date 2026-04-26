# Docs index

Landing page for everything under `docs/`. Start with [ARCHITECTURE.md](ARCHITECTURE.md) if you want to understand the system; start with [USER_GUIDE.md](USER_GUIDE.md) if you want to use it.

## Core

- [ARCHITECTURE.md](ARCHITECTURE.md) — runtime, agentic executor, validator gate, `/pdd` and `/bootstrap` pipelines.
- [CAPABILITY_CONTRACT.md](CAPABILITY_CONTRACT.md) — canonical CLI/Cursor/MCP capability contract and explicit Claude Code non-goals.
- [USER_GUIDE.md](USER_GUIDE.md) — day-to-day CLI usage, slash commands, env vars, and Claude quickstart.
- [CLAUDE_USER_GUIDE.md](CLAUDE_USER_GUIDE.md) — terminal / Claude Code: full **`uipath-claude`** step-by-step, flags, sessions, restart/debug, hooks-first policy, and how CLI differs from Cursor + MCP.
- [SKILL_VISUAL_GUIDE.md](SKILL_VISUAL_GUIDE.md) — visual guide to skill families, routing, Cursor flow, Claude flow, and MCP tool families.
- [SLASH_COMMANDS.md](SLASH_COMMANDS.md) — slash command reference, SDLC mapping, `UIPATH_CLAUDE_TOOL_PROFILE`.
- [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md) — the full BA -> SA -> ADD -> TDD -> Dev -> QA -> publish -> deploy flow driven by `/pdd` (includes **Naming: SDD vs lifecycle TDD**).
- [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) — using the UiPath skills + MCP tools from inside Cursor (clone + `uv sync --extra mcp` + `mcp.json`).
- Local setup policy: one assistant per clone via `ops/scripts/cursor-quickstart.*` or `ops/scripts/claude-quickstart.*` (`.assistant-choice`, switch with force).
- [uiplan/README.md](uiplan/README.md) — UiPlan quick start, decision tree, and leverage patterns for `spec.md` + `plan.md` + `tasks.md`.
- [INSTALL.md](INSTALL.md) — full installation: UiPath CLI, Studio 26.2+, submodules, AWS Bedrock.
- [TOOLS.md](TOOLS.md) — reference for every tool the agent can call.
- [MCP_TOOLS.md](MCP_TOOLS.md) — generated catalog of MCP-exposed tools (run `python ops/scripts/generate_mcp_tools_doc.py` after changes).
- [MCP_TOOLS_FINDINGS.md](MCP_TOOLS_FINDINGS.md) — known gaps and recommended fixes for MCP tools.

## Planning (Cursor + agent)

- [PLANNING_FRAMEWORK.md](PLANNING_FRAMEWORK.md) — superpowers-style brainstorm -> draft -> accept -> publish loop, including the optional `UIPATH_PLAN_GATE`.
- [plans/README.md](plans/README.md) — index of git-tracked implementation plans under `docs/plans/`.
- [plans/_TEMPLATE.md](plans/_TEMPLATE.md) — required front matter, Mermaid, tasks, verification.
- Cursor skills: `.cursor/skills/uiplan/SKILL.md` (canonical planning + discovery), `.cursor/skills/writing-uipath-plans/SKILL.md`, `.cursor/skills/mermaid-diagram-builder/SKILL.md`.
- MCP (CRUD): `uipath_plan_save`, `uipath_plan_list` (scope), `uipath_plan_read`, `uipath_plan_status_set`, `uipath_plan_render_mermaid`, `uipath_plan_build`.
- MCP (brainstorm loop): `uipath_plan_new`, `uipath_plan_brainstorm`, `uipath_plan_refine`, `uipath_plan_diff`, `uipath_plan_accept`, `uipath_plan_reject`, `uipath_plan_publish` — see [MCP_TOOLS.md](MCP_TOOLS.md).
- CLI: `uipath plan new|brainstorm|refine|diff|accept|reject|publish|list`.
- Regenerate the plans table: `python ops/scripts/generate_plan_index.py`.
- Formal lifecycle: [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md).

## Skills and library

- [SKILL_LAYOUT.md](SKILL_LAYOUT.md) — how skills are layered (user, project, extensions, submodule, template), and how to keep Cursor in sync with the submodule.
- [SKILL_VISUAL_GUIDE.md](SKILL_VISUAL_GUIDE.md) — how every skill family works, with Mermaid diagrams and routing tables.
- [LIBRARY_AUTHORING.md](LIBRARY_AUTHORING.md) — authoring content for the knowledge library.
- [LIBRARY_LEARNING.md](LIBRARY_LEARNING.md) — the harvest -> propose -> apply learning loop.
- [CAPABILITY_CONTRACT.md](CAPABILITY_CONTRACT.md) — supported pragmatic Claude-Code-style UiPath capabilities and explicit non-goals.

## Evaluation and QA

- [Testing_Guide.md](Testing_Guide.md) — how to run tests.
- [SMOKE_TESTS.md](SMOKE_TESTS.md) — end-to-end smoke scenarios.
- [MANUAL_EVAL_AND_QA.md](MANUAL_EVAL_AND_QA.md) — manual evaluation checklist.
- [workflow-benchmarks.md](workflow-benchmarks.md) — benchmark workflows.

Historical broad manual-review matrices remain in the repo for audit context, but the canonical day-to-day QA path is `uipath-claude doctor`, generated [MCP_TOOLS.md](MCP_TOOLS.md), [TESTING.md](TESTING.md), and [SMOKE_TESTS.md](SMOKE_TESTS.md).

## Deployment

- [DEPLOYMENT_INTEGRATION.md](DEPLOYMENT_INTEGRATION.md) — deployment integration notes.

## Cato discoverability (wiki drafts)

- [wiki/confluence-overview.md](wiki/confluence-overview.md) — Confluence "Overview" page (non-dev audience).
- [wiki/confluence-quickstart.md](wiki/confluence-quickstart.md) — Confluence "Quickstart for developers" page.

## Assets

- [assets/demo.tape](assets/demo.tape) — VHS script for the hero terminal cast.
- [assets/builder-agent-logo.svg](assets/builder-agent-logo.svg) — reusable UiPath Builder Agent logo used by the README and skill visual guide.
- [assets/builder-agent-icon.svg](assets/builder-agent-icon.svg) — compact icon variant for smaller visual surfaces.
- `assets/demo.gif` — rendered terminal cast (generated from `demo.tape`).
