# UiPath Assistant Capability Contract

This is the canonical contract for pragmatic Claude Code-style behavior in this repo.

The goal is **UiPath delivery parity across `uipath-claude` and Cursor + MCP**, not a full Claude Code clone. Both surfaces should support the same UiPath work: skill-guided planning, project/workflow generation, validation and repair, grounded answers, session recall, and guarded destructive actions.

## Supported Surfaces

| Capability | CLI / slash command | MCP tool family | Cursor skill | Notes |
| --- | --- | --- | --- | --- |
| Workspace health | `/doctor`, `uipath-claude doctor` | n/a | n/a | Read-only checks for skills, MCP config, docs, runtime, `uip`, and library health. |
| Status and session context | `/status`, `/resume`, `/recall` | `uipath_memory_*` | n/a | CLI owns chat transcripts; MCP exposes durable memory operations. |
| Skill discovery and routing | `/skills`, `/update-skills` | `uipath_skill_*` | `skills/skills/*`, approved Cursor overlays | `skills/skills` is the upstream source of truth. |
| Structured planning | `/plan`, `/uiplan`, `/uiplan-*`, `uipath-claude plan ...` | `uipath_plan_*` | `uiplan`, `uiplan-*`, `writing-uipath-plans` | UiPlan is the preferred plan-to-build contract for non-trivial work. |
| Full SDLC lifecycle | `/pdd` | `uipath_agent_*`, `uipath_doc_*`, `uipath_workflow_*` | Specialist UiPath skills | BA -> SA -> ADD -> TDD -> Dev -> QA, with publish/deploy gates. |
| Workflow build/edit/validate | `/validate`, chat execution loop | `uipath_workflow_*` | `uipath-rpa` | Destructive write/package/run/publish/deploy tools stay approval-gated. |
| Grounded answers | chat question path, `/books` | `uipath_answer`, `uipath_library_*`, `uipath_doc_*` | Product-specific skills | Prefer reviewed library and docs before inventing answers. |
| **Shared orchestration (NL routing)** | `uipath-claude chat` (non-slash input) | `uipath_assistant_context`, `uipath_assistant_route` | n/a | Natural language is LLM-routed (answer, clarify, docs, UiPlan, planner, execute) with the same core as the CLI. Slash commands stay deterministic. Set `UIPATH_ORCHESTRATION_ROUTER=0` to use legacy keyword intent only. |
| Library learning | `/library-harvest`, `/library-proposals` | `uipath_library_*` proposal tools | n/a | Proposals require human approval before library mutation. |
| Design approval | plan/design gates | `uipath_design_*` | `uiplan` | Used to separate proposal, approval, rejection, and status. |

## Explicit Non-Goals

The repo does not try to recreate Claude Code internals that are not required for UiPath delivery:

- Native TypeScript/Bun/Ink terminal UI.
- Full Claude Code plugin marketplace/runtime.
- LSP tool parity.
- Agent swarms or team-agent management.
- IDE bridge protocol.
- Cron or remote triggers.
- Git worktree isolation.

## LLM Operating Contract

When an AI assistant works in this repo:

- Start with `README.md`, `docs/INSTALL.md`, this contract, and the surface-specific guide (`docs/USER_GUIDE.md` or `docs/CURSOR_USER_GUIDE.md`).
- Use `docs/MCP_TOOLS.md` as generated MCP truth; regenerate it after changing tool registrations.
- Treat `skills/skills` as upstream skill truth; use `extensions/skills` for team-owned overrides.
- Use UiPlan for non-trivial or ambiguous work before destructive changes.
- Do not invent UiPath APIs, package names, activity names, or CLI verbs. Check skills, library tools, generated MCP docs, or UiPath CLI docs first.
- Ask the user only when project intent cannot be discovered from repo files, plans, docs, or safe read-only tool calls.

## Verification

The contract is enforced by tests that:

- Check required slash commands are registered.
- Check all registered MCP tools belong to the UiPath-supported MCP surface.
- Check Cursor skill alignment through `uipath-claude doctor`.
- Check generated MCP docs stay in sync with code.
