# Full-project manual review (Cursor)

Use this document to **manually exercise** the UiPath Builder Agent surface **through Cursor** (chat + MCP tools + skills), record **PASS / FAIL / BLOCKED / N/A**, and paste the **Results** section into your team’s ticket, PR, or wiki when done.

| Scope | This doc | Other docs |
| --- | --- | --- |
| Post–Phase 4 layout, submodule, quick gates | Rows under **Repo and CLI gates** | [MANUAL_TESTING_POST_PHASE4.md](MANUAL_TESTING_POST_PHASE4.md) |
| Long scripted scenarios (Ask AI, library loop, etc.) | Use **Notes** to point at step IDs | [SMOKE_TESTS.md](SMOKE_TESTS.md) |
| Tool semantics and schemas | **Notes** only; source of truth | [MCP_TOOLS.md](MCP_TOOLS.md) (regenerate with `python ops/scripts/generate_mcp_tools_doc.py` if tools change) |

**Non-goals:** This does not replace `uv run pytest -q`. It does not authorize Production Orchestrator deploy ([CLAUDE.md](../CLAUDE.md)).

---

## Prerequisites

1. **Workspace** — Open the **repository root** as the Cursor folder (not a parent path).
2. **Python / uv** — `uv sync` from repo root; interpreter matches what MCP uses ([.cursor/mcp.json.example](../.cursor/mcp.json.example)).
3. **MCP** — Copy `.cursor/mcp.json.example` → `.cursor/mcp.json` if needed; confirm **Settings → MCP** shows `uipath-builder-agent` connected.
4. **Optional** — AWS Bedrock env for BA/SA/agent tools ([SMOKE_TESTS.md](SMOKE_TESTS.md) “Model + profile env vars”); `uip` on PATH for doc steps 8–9 in the Phase 4 checklist; Studio / tenant only where a row explicitly requires them.
5. **Destructive tools** — When testing writers (`uipath_workflow_write_file`, `uipath_plan_accept`, …), use a **throwaway branch** or temp paths. Click **Allow** in Cursor when exercising destructive MCP tools.

---

## How to run the review

1. Work **section by section** (or one long session), asking the agent in Cursor to invoke the named MCP tool with **minimal safe arguments** (read-only first).
2. For each row: set **Status** to `PASS`, `FAIL`, `BLOCKED` (missing creds/Studio/binary), or `N/A` (not applicable to your environment). Fill **Notes** with the error string, ticket id, or “see SMOKE_TESTS §…”.
3. Copy **Date** when you touched that row (or once per section if you prefer).
4. When finished, fill **[Results (copy-paste)](#results-copy-paste)** at the bottom and submit per your team process.

**Status legend**

| Value | Meaning |
| --- | --- |
| `PASS` | Observed success through Cursor |
| `FAIL` | Invoked but incorrect / error |
| `BLOCKED` | Cannot run (env, policy, missing install) — explain in Notes |
| `N/A` | Deliberately skipped (not in scope for this reviewer) |

---

## Repo and CLI gates (non-MCP or hybrid)

| Id | Check | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| G1 | `git submodule update --init --recursive` | | | |
| G2 | `uv run python -m uipath_claude.skills.submodule_guard` | | | |
| G3 | `uv run pytest -q` (full suite) | | | |
| G4 | `PYTHONPATH=framework` + `uv run python -c "import mcp_server.server"` | | | |
| G5 | `uv run python -m tools.uiplan generate-docs 2099-12-31-review --out %TEMP%\uiplan-review` | | | |
| G6 | `uv run python -m tools.uiplan scaffold-code 2099-12-31-review` (repo root) | | | |
| G7 | `uv run python -m tools.uiplan validate-mermaid` on one kit file (optional; `BLOCKED` if no `mmdc`) | | | |
| G8 | `uv run python -c "from uipath_claude.graph import graph; print(type(graph))"` | | | |
| G9 | `uip --version` (optional) | | | |

---

## Slash and chat commands (when exposed)

These are documented for the **CLI / embedded chat** profile ([USER_GUIDE.md](USER_GUIDE.md)). In **Cursor**, most automation is via **MCP**; still verify any slash surface your deployment exposes.

| Id | Command | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| S1 | `/help` | | | |
| S2 | `/status` | | | |
| S3 | `/skills` | | | |
| S4 | `/pdd "<brief>"` (no deploy) | | | |
| S5 | `/bootstrap "<brief>"` | | | |
| S6 | `/analyze` | | | |
| S7 | `/validate` | | | |
| S8 | `/recall <term>` | | | |

---

## MCP tools — workflow

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_workflow_read_file` | read-only | | | |
| `uipath_workflow_write_file` | destructive | | | |
| `uipath_workflow_list_directory` | read-only | | | |
| `uipath_workflow_read_project` | read-only | | | |
| `uipath_workflow_install_package` | destructive | | | |
| `uipath_workflow_validate` | read-only | | | |
| `uipath_workflow_validate_loop` | destructive | | | |
| `uipath_workflow_build_and_verify` | destructive | | | |
| `uipath_workflow_environment_probe` | read-only | | | |
| `uipath_workflow_create_project` | destructive | | | |
| `uipath_workflow_run` | destructive | | | |
| `uipath_workflow_debug` | destructive | | | |
| `uipath_workflow_ensure_project` | read-only | | | |
| `uipath_workflow_run_command` | destructive | | | |
| `uipath_workflow_deploy` | destructive | | | |
| `uipath_workflow_publish` | destructive | | | |
| `uipath_workflow_session_status` | read-only | | | |

---

## MCP tools — skill

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_skill_list` | read-only | | | |
| `uipath_skill_get` | read-only | | | |
| `uipath_skill_match` | read-only | | | |
| `uipath_skill_insights_query` | read-only | | | |
| `uipath_skill_insights_add` | staging | | | |
| `uipath_skill_manifest` | read-only | | | |
| `uipath_skill_check_updates` | read-only | | | |
| `uipath_skill_update` | destructive | | | |
| `uipath_skill_lessons_list` | read-only | | | |
| `uipath_skill_lessons_approve` | destructive | | | |

---

## MCP tools — agent

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_agent_bootstrap` | destructive | | | |
| `uipath_agent_plan` | destructive | | | |
| `uipath_agent_execute` | destructive | | | |
| `uipath_agent_classify_intent` | read-only | | | |
| `uipath_agent_ba` | destructive | | | |
| `uipath_agent_sa` | destructive | | | |

---

## MCP tools — doc

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_doc_list_packages` | read-only | | | |
| `uipath_doc_list_activities` | read-only | | | |
| `uipath_doc_get_activity` | read-only | | | |
| `uipath_doc_get_package_overview` | read-only | | | |
| `uipath_doc_search` | read-only | | | |
| `uipath_doc_find_activity` | read-only | | | |
| `query_uipath_docs` | read-only | | | |
| `uipath_doc_query` | read-only | | | |
| `uipath_doc_read_template` | read-only | | | |
| `uipath_doc_list_docs` | read-only | | | |
| `uipath_doc_read_doc` | read-only | | | |
| `uipath_doc_write_doc` | destructive | | | |

---

## MCP tools — memory

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_memory_load` | read-only | | | |
| `uipath_memory_save` | destructive | | | |
| `uipath_memory_append` | destructive | | | |

---

## MCP tools — library

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_library_list` | read-only | | | |
| `uipath_library_toc` | read-only | | | |
| `uipath_library_read_section` | read-only | | | |
| `uipath_library_search` | read-only | | | |
| `uipath_library_lookup` | read-only | | | |
| `uipath_library_propose_section` | staging | | | |
| `uipath_library_propose_chapter` | staging | | | |
| `uipath_library_list_proposals` | read-only | | | |
| `uipath_library_approve_proposal` | destructive | | | |
| `uipath_library_reject_proposal` | destructive | | | |

---

## MCP tools — design

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_design_propose` | staging | | | |
| `uipath_design_approve` | destructive | | | |
| `uipath_design_reject` | destructive | | | |
| `uipath_design_list` | read-only | | | |
| `uipath_design_status` | read-only | | | |

---

## MCP tools — intent

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_intent_classify` | read-only | | | |

---

## MCP tools — plan

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_plan_build` | read-only | | | |
| `uipath_plan_save` | destructive | | | |
| `uipath_plan_list` | read-only | | | |
| `uipath_plan_read` | read-only | | | |
| `uipath_plan_status_set` | staging | | | |
| `uipath_plan_render_mermaid` | read-only | | | |
| `uipath_plan_new` | staging | | | |
| `uipath_plan_brainstorm` | read-only | | | |
| `uipath_plan_refine` | destructive | | | |
| `uipath_plan_diff` | read-only | | | |
| `uipath_plan_accept` | destructive | | | |
| `uipath_plan_reject` | destructive | | | |
| `uipath_plan_publish` | destructive | | | |
| `uipath_plan_ground` | read-only | | | |
| `uipath_plan_spec_new` | destructive | | | |
| `uipath_plan_plan_new` | destructive | | | |
| `uipath_plan_tasks_new` | destructive | | | |
| `uipath_plan_review` | read-only | | | |
| `uipath_plan_uiplan_new` | destructive | | | |

---

## MCP tools — answer

| Tool | Side-effect hint | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| `uipath_answer` | read-only | | | |

---

## Cursor skills (spot-check)

Manually ask the agent to follow **at least two** project skills (e.g. `uipath-rpa`, `uipath-platform`) on a trivial question and confirm answers ground in skill paths.

| Id | Check | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| C1 | Skill A (name): | | | |
| C2 | Skill B (name): | | | |

---

## Results (copy-paste)

Fill after completing the tables above. **Submit-to** lines are placeholders only.

```
## Manual review results — UiPath Builder Agent

Reviewer name: 
Machine OS: 
Cursor version: (Help → About)
Git SHA: (output of `git rev-parse HEAD`)
Review window (dates): 

Submit to (placeholder — fill as you prefer):
  Ticket / issue URL: 
  PR / wiki link: 

Summary counts:
  PASS: 
  FAIL: 
  BLOCKED: 
  N/A: 

Top failures / blockers (bullet list):
  - 

Follow-ups:
  - 
```

---

## Maintainer note

When MCP tools are added or renamed, update the **module tables** in this file to match the **Index** table in [MCP_TOOLS.md](MCP_TOOLS.md) (lines under `## Index (all tool names)`).
