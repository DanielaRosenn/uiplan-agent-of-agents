# Agent tool surface

The agent loads three sets of LangChain tools:

1. **Planning tools** (BA/SA planner) — `get_planning_tools()`
2. **Skill execution tools** (runtime) — `get_skill_execution_tools()`
3. **Knowledge tools** (shared) — `get_knowledge_tools()`

The MCP server re-exports a subset of these with typed schemas.

## Model routing

Model selection is tier-based (`uipath_claude/llm/router.py`). Each call site
names a task; the router maps task to tier to Bedrock model id.

| Task id | Tier | Default model |
|---|---|---|
| `ba_agent`, `solution_architect`, `developer`, `qa`, `planner`, `agentic_executor` | HEAVY | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| `distiller`, `intent_classifier`, `doc_need_detector`, `rename_summary` | LIGHT | `anthropic.claude-3-5-haiku-20241022-v1:0` |

Overrides, in precedence order: `UIPATH_CLAUDE_MODEL_HEAVY` /
`UIPATH_CLAUDE_MODEL_LIGHT` (per-tier), then `UIPATH_CLAUDE_MODEL`
(legacy global), then the default. Unknown task ids fall back to HEAVY.

## Knowledge pipeline

- `lookup_uipath_knowledge(question, allow_network=True)` — library first, then
  Ask AI (SDK or HTTP), then optional web search. Emits a `SOURCE:` line; when
  it answers from outside the library, also emits a `CAPTURED_SOURCE:` JSON blob
  suitable for turning into a library proposal.
- `web_search(query, max_results=5)` — Tavily / SerpAPI. Gated by
  `UIPATH_WEB_SEARCH_ENABLED` plus a provider key.

## Library tools

- `list_library_books()` — books + chapter counts (now includes manifest tags).
- `browse_book_toc(book_id)` — chapters and sections.
- `read_section(book_id, chapter_id, section_id)` — returns content with an
  inline citation.
- `search_library(query)` — keyword search across sections.
- `propose_library_update(...)` — enqueue a section proposal.
- `propose_library_chapter(...)` — enqueue a chapter proposal.

## Ask AI

- `query_uipath_docs(question)` → unified wrapper around
  `uipath_claude.tools.uipath.askai.query_uipath_documentation`
  (tries the local SDK skill under `skills/skills/uipath-askai`, then falls
  back to `UIPATH_ASKAI_ENDPOINT` HTTP).

## Skills upstream

- Auto-refresh once per chat session (local only) via
  `ensure_fresh_for_session`. The updater force-syncs to `origin/main`; any
  local drift inside the `skills/` submodule is preserved on a
  `backup/local-<timestamp>` branch first. No git hooks — Cursor-driven only.
- `/scan-upstream-skills` — diff new/removed skills and tool packs in the
  `UiPath/skills` submodule.
- `/library-harvest` — enqueue library proposals from every upstream
  `SKILL.md`.

## MCP surface (prefix reference)

| Prefix                       | Source file                                           | Coverage |
| ---------------------------- | ----------------------------------------------------- | -------- |
| `uipath_workflow_*`          | `mcp_server/tools/workflow_tools.py`                  | scaffold, write/read, validate, build_and_verify, run, debug, run_command, deploy, publish, environment_probe, session_status. Deploy/publish follow [ORCHESTRATOR_DEPLOYMENT.md](ORCHESTRATOR_DEPLOYMENT.md). |
| `uipath_skill_*`             | `mcp_server/tools/skill_tools.py`                     | list, get, match, manifest, insights, lessons, check/perform updates |
| `uipath_agent_*`             | `mcp_server/tools/agent_tools.py`                     | bootstrap, plan, execute, classify_intent, ba, sa |
| `uipath_doc_*`               | `mcp_server/tools/doc_tools.py`                       | list_packages/activities, get_activity, get_package_overview, search, find_activity, query, read_template, list_docs, read_doc, write_doc |
| `uipath_memory_*`            | `mcp_server/tools/memory_tools.py`                    | load, save, append |
| `uipath_library_*`           | `mcp_server/tools/library_tools.py`                   | list, toc, read_section, search, lookup, propose_section, propose_chapter, list_proposals, approve_proposal, reject_proposal |
| `uipath_design_*`            | `mcp_server/tools/design_tools.py`                    | propose, approve, reject, list, status |

The full per-tool table (with parameters and examples) lives in [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md). The cross-surface CLI/MCP/skill matrix is [`CAPABILITY_CONTRACT.md`](CAPABILITY_CONTRACT.md). Orchestrator publish/deploy policy lives in [ORCHESTRATOR_DEPLOYMENT.md](ORCHESTRATOR_DEPLOYMENT.md).

## Tests (where to look for regressions)

- **MCP tool contracts and annotations:** `framework/tests/mcp_tests/`
- **UiPlan CLI and docs bundle:** `framework/tests/uiplan/`
- **Full map:** [TESTING.md](TESTING.md)
