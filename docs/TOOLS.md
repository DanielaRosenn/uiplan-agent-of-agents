# Agent tool surface

The agent loads three sets of LangChain tools:

1. **Planning tools** (BA/SA planner) — `get_planning_tools()`
2. **Skill execution tools** (runtime) — `get_skill_execution_tools()`
3. **Knowledge tools** (shared) — `get_knowledge_tools()`

The MCP server re-exports a subset of these with typed schemas.

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

| Prefix                       | Source file                                           |
| ---------------------------- | ----------------------------------------------------- |
| `uipath_workflow_*`          | `mcp_server/tools/workflow_tools.py`                  |
| `uipath_skill_*`             | `mcp_server/tools/skill_tools.py`                     |
| `uipath_agent_*`             | `mcp_server/tools/agent_tools.py`                     |
| `uipath_doc_*`               | `mcp_server/tools/doc_tools.py`                       |
| `uipath_memory_*`            | `mcp_server/tools/memory_tools.py`                    |
| `uipath_library_*`           | `mcp_server/tools/library_tools.py`                   |

See [`CAPABILITY_PARITY.md`](CAPABILITY_PARITY.md) for the cross-surface matrix.
