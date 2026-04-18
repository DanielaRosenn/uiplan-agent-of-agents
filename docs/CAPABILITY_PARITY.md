# Capability parity (CLI / Cursor / Claude Code / MCP)

High-level comparison of how each surface reaches the agent's capabilities.
CLI is the reference implementation; MCP-backed surfaces (Cursor, Claude Code)
share most of the same tool and resource surface.

| Capability                   | CLI                                      | Cursor (MCP)                      | Claude Code (MCP)                | Notes                                                    |
| ---------------------------- | ---------------------------------------- | --------------------------------- | -------------------------------- | -------------------------------------------------------- |
| Skills (browse, pick)        | `/skills`                                | `uipath_skill_*`                  | `uipath_skill_*`                 | Loaded from `skills/` submodule + local/user sources.    |
| Skills auto-refresh          | Per-session startup refresh, `/update-skills` | Session-start hook                | Session-start hook               | `UIPATH_SKILLS_AUTO_REFRESH=0` to disable. Updater force-resets to `origin/main`; local drift moved to a `backup/local-<ts>` branch. |
| New-skill diff notice        | `/scan-upstream-skills` + startup banner | n/a (CLI-only today)              | n/a (CLI-only today)             | Snapshot at `.skills_refresh_at`/`.upstream_skills_state`.|
| Planner / plan mode          | `/plan`, `UIPATH_PLAN_MODE`              | via `uipath_agent_plan` (pending) | via `uipath_agent_plan` (pending)| MCP plan tool still scoped.                              |
| Clarifier                    | Auto (intent gating)                     | Not exposed directly              | Not exposed directly             | Kept internal to CLI loop.                               |
| Documentation loop (PDD/SDD) | `run_documentation_flow`                 | `uipath_doc_*`                    | `uipath_doc_*`                   | See `uipath_claude/cli/documentation_flow.py`.           |
| RPA generation               | Chat → skill → tools                     | via `uipath_workflow_*`           | via `uipath_workflow_*`          |                                                           |
| Maestro flow                 | Chat → skill                             | via `uipath_workflow_*`           | via `uipath_workflow_*`          |                                                           |
| Coded Agents / Apps          | Chat → skill                             | Partial (typed tools pending)     | Partial                          | Tracked under P6.                                        |
| Orchestrator deploy          | `deploy_to_orchestrator`                 | `uipath_workflow_deploy`          | `uipath_workflow_deploy`         |                                                           |
| Memory                       | `/recall`                                | `uipath_memory_*`                 | `uipath_memory_*`                |                                                           |
| Library (TOC/read/search)    | `/books`, library tools                  | `uipath_library_*`                | `uipath_library_*`               | New in this iteration.                                   |
| Library lookup (browse→askai→web) | `lookup_uipath_knowledge`             | `uipath_library_lookup`           | `uipath_library_lookup`          | Web gated on `UIPATH_WEB_SEARCH_ENABLED`.                |
| Library proposals            | `/library-proposals` + `/library-harvest`| `uipath_library_list/approve/reject_proposal` | same                 | Human approval required; agent never writes directly.    |
| Telemetry                    | `StructuredLogger`                       | Same                              | Same                             |                                                           |

## Env knobs relevant to parity

- `UIPATH_SKILLS_AUTO_REFRESH` (default `1`) — auto-pull `skills/` submodule.
- `UIPATH_TOOL_APPROVAL` (default `1`) — destructive-tool approval prompt.
- `UIPATH_WEB_SEARCH_ENABLED` + `TAVILY_API_KEY` or `SERPAPI_KEY` — enable web.
- `UIPATH_ASKAI_ENDPOINT` / `UIPATH_ASKAI_API_KEY` — Ask AI HTTP fallback.
- `UIPATH_CLAUDE_LIBRARY` — override library root.
- `UIPATH_CLAUDE_LIBRARY_PROPOSALS` — override proposal store root.

## Known parity gaps

- Plan mode is not yet exposed as a first-class MCP tool.
- Clarifier remains an internal CLI stage.
- StudioWeb publish path (P3) is not yet a parity feature across all surfaces.
