# Full-project manual review (Cursor-first)

Use this document after a **fresh clone** (or any time you need a wide pass) to exercise the builder agent **primarily through Cursor**: natural-language chat, **MCP** tools, and project skills. Record **PASS / FAIL / BLOCKED / N/A** and paste **[Results (copy-paste)](#results-copy-paste)** when done.

**What you are testing**

1. **Intent routing** — You type **everyday language** (no tool IDs). The agent should pick the right MCP tool from **names and descriptions** registered on the server ([MCP_TOOLS.md](MCP_TOOLS.md)).
2. **Repo + UiPlan** — Layout, kit, generated bundles, and docs hang together.
3. **Clone ergonomics** — A new developer following this doc + [CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md) gets a **green MCP** and sensible first prompts.

| Scope | This doc | Other docs |
| --- | --- | --- |
| Phase 4 quick gates | **Fresh clone** + **Repo gates** | [MANUAL_TESTING_POST_PHASE4.md](MANUAL_TESTING_POST_PHASE4.md) |
| Long scripted flows | Notes → step ids | [SMOKE_TESTS.md](SMOKE_TESTS.md) |
| Tool schemas / diagrams | Reference only | [MCP_TOOLS.md](MCP_TOOLS.md) |

**Non-goals:** Does not replace `uv run pytest -q`. No Production Orchestrator deploy ([CLAUDE.md](../CLAUDE.md)).

---

## Cursor Auto (agent handoff)

Use this block when **handing work to Cursor Auto** (or another agent session) so the next run does not lose context.

**Entry files the next agent should open first**

- [CLAUDE.md](../CLAUDE.md) — hard gates and CLI routing.
- [docs/SKILL_LAYOUT.md](SKILL_LAYOUT.md) — where skills live (`skills/`, `extensions/skills/`, `.cursor/skills`).
- [docs/MCP_TOOLS.md](MCP_TOOLS.md) — tool names and one-line purposes (regenerate from code if schemas drift).

**Stop conditions**

- Stop before `uipcli package deploy`, `uipath publish`, or any deploy to non-personal feeds without explicit human confirmation ([CLAUDE.md](../CLAUDE.md) deploy rules).
- Stop if `python -m uipath_claude.skills.submodule_guard` fails until `skills/` matches `.uipath/skills-approved.sha`.

**Example prompts**

- "Continue the wrap-up plan: run submodule guard, full `uv run pytest -q`, then summarize failures with file:line."
- "Implement only the HITL schema change in `<path>`; run `uip flow validate` and paste JSON errors if any."

---

## Almost zero work (onboarding)

Goal: **one terminal command**, then **two clicks** in Cursor.

1. **Prereqs on PATH:** `git`, `uv` ([install uv](https://docs.astral.sh/uv/)).
2. From **repo root** after `git clone`:

```powershell
.\ops\scripts\cursor-quickstart.ps1
```

macOS / Linux:

```bash
bash ops/scripts/cursor-quickstart.sh
```

That runs: `git submodule update --init --recursive` → `uv sync --extra mcp` → creates `.cursor/mcp.json` from [.cursor/mcp.json.example](../.cursor/mcp.json.example) if missing → runs `ops/scripts/setup-cursor.ps1` or `setup-cursor.sh` (skills junction/symlink).

3. In Cursor only: **File → Open Folder** (this repo) → **Settings → MCP** → confirm **uipath-builder-agent** is connected → **Developer: Reload Window** if it was red.

Optional later: Superpowers plugin ([CURSOR_USER_GUIDE.md](CURSOR_USER_GUIDE.md)); use **Agent** mode when you want tools.

If you ran quickstart successfully, you can mark **CC1–CC7** in the table below as **PASS** (or **N/A**) without doing each line by hand.

---

## Cursor checklist (expanded — only if you skipped quickstart)

| Step | Action | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| CC1 | `git clone …` then `cd` into **repo root** | | | |
| CC2 | `git submodule update --init --recursive` | | | |
| CC3 | `uv sync --extra mcp` at repo root | | | |
| CC4 | `Copy-Item .cursor/mcp.json.example .cursor/mcp.json` (or rely on quickstart) | | | |
| CC5 | Run `.\ops\scripts\setup-cursor.ps1` or `./ops/scripts/setup-cursor.sh` | | | |
| CC6 | **File → Open Folder** → **this repo root** | | | |
| CC7 | **Settings → MCP** → `uipath-builder-agent` **connected** | | | |
| CC8 | Optional: `cursor-public/superpowers` | | | |
| CC9 | **Agent** vs **Ask** mode as needed | | | |

**Tip:** If MCP stays red, run from repo root: `uv run python -m mcp_server.server` with `PYTHONPATH` including `framework` — the terminal error is the source of truth ([MANUAL_TESTING_POST_PHASE4.md](MANUAL_TESTING_POST_PHASE4.md) §6).

---

## Prerequisites (review session)

1. Complete **Almost zero work** (quickstart) or the **expanded checklist** above.
2. **Destructive work** — Use a throwaway branch; confirm **Allow** on Cursor prompts for destructive MCP tools.
3. **Optional env** — Bedrock / Ask AI for heavy agents ([SMOKE_TESTS.md](SMOKE_TESTS.md)); `uip` for platform doc steps; Studio only when a scenario requires it.

---

## How to run this review (Cursor)

1. Prefer **natural-language rows** first: paste the **Example user message** into Cursor chat **without** naming MCP tools (e.g. do not write `uipath_library_search`).
2. Watch which tools the agent calls; confirm behavior matches **Expected** (or is an acceptable alternative).
3. Use **Tool / MCP name** rows when you need a **1:1 audit** or regression against a specific tool.
4. Fill **Status** / **Notes** / **Date**; then complete **[Results](#results-copy-paste)**.

**Status legend**

| Value | Meaning |
| --- | --- |
| `PASS` | Correct routing + outcome in Cursor |
| `FAIL` | Wrong tool, error, or unsafe suggestion |
| `BLOCKED` | Missing env, policy, binary |
| `N/A` | Skipped by choice |

---

## Natural-language scenarios (wide intent routing)

Type the **Example user message** in Cursor (Agent mode). Do **not** paste tool names into your prompt unless the row says you may.

| Id | Example user message (copy into Cursor) | Expected (MCP / area) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| NL1 | "List the books in the internal UiPath documentation library and give me one chapter title from any book." | `uipath_library_*` read path | | | |
| NL2 | "Search the docs library for how Orchestrator queues work and quote one sentence with the section id." | `uipath_library_search` or lookup | | | |
| NL3 | "What skills are available in this project for RPA work, and which one best matches building a coded workflow in C#?" | `uipath_skill_list` / `uipath_skill_match` | | | |
| NL4 | "I am planning a small automation: ground a plan from our constitution and repo context, then outline spec sections only—no writes to disk yet." | `uipath_plan_ground`, read-only plan tools | | | |
| NL5 | "Show me the current draft plans under the default scope and the status of each." | `uipath_plan_list`, `uipath_plan_read` | | | |
| NL6 | "Render the Mermaid from my current plan bundle as markdown I can paste into a review." | `uipath_plan_render_mermaid` | | | |
| NL7 | "Classify this request as BUILD vs QUESTION: I need to add a Log Message to Main.xaml in an existing Studio project." | `uipath_intent_classify` or planner path | | | |
| NL8 | "What UiPath activity packages exist for Excel in the bundled activity docs, and list one activity type?" | `uipath_doc_list_packages` / `uipath_doc_get_activity` | | | |
| NL9 | "Find documentation for Retry Scope in the activity reference and summarize constraints in two bullets." | `uipath_doc_search` / `query_uipath_docs` | | | |
| NL10 | "Probe my local Studio environment for installed package versions before we add dependencies." | `uipath_workflow_environment_probe` | | | |
| NL11 | "Read project.json from my UiPath project path and tell me the entry workflow name—read only." | `uipath_workflow_read_project` / read_file | | | |
| NL12 | "We have an approved design: append a short note to session memory under key demo-review." | `uipath_memory_append` / save | | | |
| NL13 | "List pending design proposals for this workspace and whether any are approved." | `uipath_design_list` / `uipath_design_status` | | | |
| NL14 | "What is the MCP session gate status for workflow builds right now?" | `uipath_workflow_session_status` | | | |
| NL15 | "Run a read-only validation on my UiPath project at this path and summarize errors." | `uipath_workflow_validate` | | | |
| NL16 | "Propose a library section update based on a lesson learned from last sprint—staging only, do not approve yet." | `uipath_library_propose_section` (staging) | | | |
| NL17 | "Summarize this answer from the builder agent perspective: why use environment probe before install_package?" | `uipath_answer` | | | |
| NL18 | "Bootstrap a minimal agentic plan JSON for exploration only—use a throwaway output path I will delete." | `uipath_agent_*` (destructive — careful) | | | |
| NL19 | "Generate BA-style product text only from this one paragraph brief—no full lifecycle, single agent." | `uipath_agent_ba` | | | |
| NL20 | "Turn the last BA output into a solution design draft text only—still no scaffold." | `uipath_agent_sa` | | | |
| NL21 | "In 60 seconds, explain this repo's purpose, who should use it, and the safest first workflow for a new user." | README + USER_GUIDE routing clarity | | | |
| NL22 | "I want to leverage everything: give me the exact order from onboarding to UiPlan to validate to manual review." | Cross-doc path (`README` -> `USER_GUIDE` -> `uiplan` -> review docs) | | | |

---

## UiPlan — docs, kit, and MCP alignment

Verify the **human docs** and **templates** are coherent and that both **CLI** and **MCP** paths are described ([HOW_TO_USE.md](uiplan/HOW_TO_USE.md)).

| Id | Check | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| UP0 | In Cursor (natural language): "Explain when to use UiPlan `generate-docs` vs MCP `uipath_plan_uiplan_new`, and where the kit lives." | Agent cites `docs/uiplan/` and `templates/uiplan/` paths | | | |
| UP1 | Read [docs/uiplan/README.md](uiplan/README.md) — links resolve | | | |
| UP2 | Read [docs/uiplan/HOW_TO_USE.md](uiplan/HOW_TO_USE.md) — decision table matches your mental model | | | |
| UP3 | Confirm kit files exist: `templates/uiplan/_spec-template.md`, `_plan-template.md`, `_tasks-template.md`, `_diagram-patterns.md` | | | |
| UP4 | `uv run python -m tools.uiplan generate-docs 2099-12-31-uiplan-review --out (Join-Path $env:TEMP 'uiplan-kit-test')` — **strict** (PowerShell) | Three files + density OK | | | |
| UP5 | Open the three generated files; confirm placeholders and Mermaid fences present | | | |
| UP6 | `uv run python -m tools.uiplan scaffold-code 2099-12-31-uiplan-review` at repo root | Coded-agent checks pass | | | |
| UP7 | Optional: `uv run python -m tools.uiplan validate-mermaid templates/uiplan/_diagram-patterns.md` if `mmdc` installed | | | |

## Onboarding narrative quality (new-user comprehension)

Confirm the docs now answer three first-time questions quickly: **what is this project**, **how do I use it well**, **what should I run first**.

| Id | Check | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| ON1 | README includes clear purpose and "use everything" map | | | |
| ON2 | USER_GUIDE includes practical UiPlan cookbook with decision guidance | | | |
| ON3 | docs/uiplan/README has first-15-min flow and decision tree | | | |

---

## Repo and CLI gates (hybrid — terminal OK)

| Id | Check | Status | Notes | Date |
| --- | --- | --- | --- | --- |
| G1 | `git submodule update --init --recursive` | | | |
| G2 | `uv run python -m uipath_claude.skills.submodule_guard` | | | |
| G3 | `uv run pytest -q` (full suite) | | | |
| G4 | `PYTHONPATH=framework` + `uv run python -c "import mcp_server.server"` | | | |
| G8 | `uv run python -c "from uipath_claude.graph import graph; print(type(graph))"` | | | |
| G9 | `uip --version` (optional) | | | |

---

## Slash commands (CLI only — optional)

`uipath chat` slash commands; not Cursor MCP. See [SLASH_COMMANDS.md](SLASH_COMMANDS.md).

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
| S9 | `/update-skills --check` | | | |
| S10 | `/scan-upstream-skills --dry-run` | | | |
| S11 | `/library-proposals list` | | | |
| S12 | `/library-harvest` | | | |
| S13 | `/books` | | | |
| S14 | `/repair-restore` | | | |
| S15 | `/uiplan` | | | |
| S16 | `/plan` (if planner enabled) | | | |

---

## MCP tools — workflow

| Tool | Hint | Example user message (Cursor — do not name the tool) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_workflow_read_file` | read-only | "Open and show the text of this file inside my UiPath project: …" | | | |
| `uipath_workflow_write_file` | destructive | "After design approval, apply this patch to Main.xaml in my project: …" | | | |
| `uipath_workflow_list_directory` | read-only | "What files are under the Tests folder in my automation project?" | | | |
| `uipath_workflow_read_project` | read-only | "Summarize entry points and dependencies from my Studio project metadata." | | | |
| `uipath_workflow_install_package` | destructive | "Add the official Excel activities package compatible with my Studio install." | | | |
| `uipath_workflow_validate` | read-only | "Run static validation on the project and list blocking issues only." | | | |
| `uipath_workflow_validate_loop` | destructive | "Iterate validate/fix until clean or hit a cap—explain each loop." | | | |
| `uipath_workflow_build_and_verify` | destructive | "Run restore/analyze-style verification after my last XAML edit; say if I can mark done." | | | |
| `uipath_workflow_environment_probe` | read-only | "What Studio package versions does my machine expose for this solution?" | | | |
| `uipath_workflow_create_project` | destructive | "Scaffold a new blank UiPath process in this empty folder using CLI—not hand-written JSON." | | | |
| `uipath_workflow_run` | destructive | "Execute the main workflow locally with safe test inputs." | | | |
| `uipath_workflow_debug` | destructive | "Collect debug info for the last failed run in this project." | | | |
| `uipath_workflow_ensure_project` | read-only | "Confirm this path is a valid UiPath project root and say what is missing if not." | | | |
| `uipath_workflow_run_command` | destructive | "Run this approved diagnostic command in the project context." | | | |
| `uipath_workflow_deploy` | destructive | "Do **not** run against Production; if you must demo deploy, use personal workspace only with explicit OK." | | | |
| `uipath_workflow_publish` | destructive | Same caution as deploy—personal workspace only with human confirmation. | | | |
| `uipath_workflow_session_status` | read-only | "Is the workflow session dirty or blocked after recent edits?" | | | |

---

## MCP tools — skill

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_skill_list` | read-only | "List skills the MCP can see for this workspace." | | | |
| `uipath_skill_get` | read-only | "Show the SKILL.md header and when-to-use for the RPA skill." | | | |
| `uipath_skill_match` | read-only | "Which skill should I use for Orchestrator folder operations?" | | | |
| `uipath_skill_insights_query` | read-only | "Any recorded insights about package version mismatches?" | | | |
| `uipath_skill_insights_add` | staging | "Stage a short insight about a recurring validation error we saw." | | | |
| `uipath_skill_manifest` | read-only | "Show the skill manifest grouping for this session." | | | |
| `uipath_skill_check_updates` | read-only | "Does the skills submodule differ from upstream default branch?" | | | |
| `uipath_skill_update` | destructive | "Update the skills submodule in a throwaway branch only—confirm with me first." | | | |
| `uipath_skill_lessons_list` | read-only | "List pending lesson drafts from the distiller." | | | |
| `uipath_skill_lessons_approve` | destructive | "Approve lesson L123 after human review." | | | |

---

## MCP tools — agent

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_agent_bootstrap` | destructive | "Run a controlled bootstrap of the agent stack to this temp output directory." | | | |
| `uipath_agent_plan` | destructive | "Produce a structured implementation plan JSON for this brief." | | | |
| `uipath_agent_execute` | destructive | "Execute the previously approved plan step list with logging." | | | |
| `uipath_agent_classify_intent` | read-only | "Is this message a build request or a documentation question?" | | | |
| `uipath_agent_ba` | destructive | "Draft a PDD-style product brief from this stakeholder paragraph." | | | |
| `uipath_agent_sa` | destructive | "Turn the product brief into a solution design narrative." | | | |

---

## MCP tools — doc

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_doc_list_packages` | read-only | "What activity packages are indexed for documentation lookup?" | | | |
| `uipath_doc_list_activities` | read-only | "List activities in UiPath.Excel.Activities for quick pick." | | | |
| `uipath_doc_get_activity` | read-only | "Property summary for Use Excel File activity." | | | |
| `uipath_doc_get_package_overview` | read-only | "High-level overview of the System activities package." | | | |
| `uipath_doc_search` | read-only | "Search activity docs for 'queue trigger' snippets." | | | |
| `uipath_doc_find_activity` | read-only | "Find the package that owns 'Set Transaction Status'." | | | |
| `query_uipath_docs` | read-only | "Ask the unified docs endpoint a narrow factual question about Orchestrator folders." | | | |
| `uipath_doc_query` | read-only | "Structured doc query for templates mentioning REFramework." | | | |
| `uipath_doc_read_template` | read-only | "Load the SDD template excerpt for headings only." | | | |
| `uipath_doc_list_docs` | read-only | "List internal markdown docs under docs/ the tool can read." | | | |
| `uipath_doc_read_doc` | read-only | "Open ARCHITECTURE.md and summarize the runtime diagram in three bullets." | | | |
| `uipath_doc_write_doc` | destructive | "Persist this approved doc body to docs/foo.md—only after explicit human OK." | | | |

---

## MCP tools — memory

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_memory_load` | read-only | "Recall what we stored under session key sprint-42." | | | |
| `uipath_memory_save` | destructive | "Replace session memory map with this JSON blob for demo only." | | | |
| `uipath_memory_append` | destructive | "Append a timestamped note to the running session log in memory." | | | |

---

## MCP tools — library

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_library_list` | read-only | "What books exist in the curated library catalog?" | | | |
| `uipath_library_toc` | read-only | "Table of contents for book uipath-docs." | | | |
| `uipath_library_read_section` | read-only | "Fetch section text for orchestrator / queues / overview." | | | |
| `uipath_library_search` | read-only | "Full-text search the library for 'personal workspace'." | | | |
| `uipath_library_lookup` | read-only | "Lookup curated snippets for keyword 'governance'." | | | |
| `uipath_library_propose_section` | staging | "Stage a proposed rewrite for one library section with citations." | | | |
| `uipath_library_propose_chapter` | staging | "Stage a new chapter skeleton for review." | | | |
| `uipath_library_list_proposals` | read-only | "List open library proposals with ids." | | | |
| `uipath_library_approve_proposal` | destructive | "Approve proposal P-… after maintainer review in meeting." | | | |
| `uipath_library_reject_proposal` | destructive | "Reject proposal P-… with reason duplicate content." | | | |

---

## MCP tools — design

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_design_propose` | staging | "Submit a design summary for this small XAML change for human approval." | | | |
| `uipath_design_approve` | destructive | "Record human approval for design D-… so writes unblock." | | | |
| `uipath_design_reject` | destructive | "Reject design D-… and ask for narrower scope." | | | |
| `uipath_design_list` | read-only | "List designs visible for this repo session." | | | |
| `uipath_design_status` | read-only | "Is there an approved design for the project I am editing?" | | | |

---

## MCP tools — intent

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_intent_classify` | read-only | "Classify: 'bump version and publish tonight' vs 'explain queues'." | | | |

---

## MCP tools — plan

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_plan_build` | read-only | "Build the plan markdown from the current draft metadata." | | | |
| `uipath_plan_save` | destructive | "Save this edited plan body to the draft slug I specify." | | | |
| `uipath_plan_list` | read-only | "List plans in scope personal with newest first." | | | |
| `uipath_plan_read` | read-only | "Read plan body for slug 2026-04-23-demo." | | | |
| `uipath_plan_status_set` | staging | "Mark plan status to in_review for slug …" | | | |
| `uipath_plan_render_mermaid` | read-only | "Render diagrams from plan markdown to a preview block." | | | |
| `uipath_plan_new` | staging | "Start a new brainstorm thread id for this feature name." | | | |
| `uipath_plan_brainstorm` | read-only | "Continue brainstorming round 2 with objections addressed." | | | |
| `uipath_plan_refine` | destructive | "Apply refinements from the last review notes to the draft." | | | |
| `uipath_plan_diff` | read-only | "Show diff between draft v1 and v2 for this slug." | | | |
| `uipath_plan_accept` | destructive | "Accept the draft after human sign-off in chat." | | | |
| `uipath_plan_reject` | destructive | "Reject draft and request narrower scope." | | | |
| `uipath_plan_publish` | destructive | "Publish accepted plan to docs/plans after policy check." | | | |
| `uipath_plan_ground` | read-only | "Ground a new plan pack from constitution + skills + optional PDD path." | | | |
| `uipath_plan_spec_new` | destructive | "Materialize spec.md for slug … from grounded context." | | | |
| `uipath_plan_plan_new` | destructive | "Materialize plan.md for slug …" | | | |
| `uipath_plan_tasks_new` | destructive | "Materialize tasks.md with test-before-impl sections." | | | |
| `uipath_plan_review` | read-only | "Run structured review on the three-file bundle; return ok flag." | | | |
| `uipath_plan_uiplan_new` | destructive | "Create the UiPlan three-file bundle via MCP for this slug." | | | |

---

## MCP tools — answer

| Tool | Hint | Example user message (Cursor) | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| `uipath_answer` | read-only | "Answer succinctly: why must analyze pass before pack in our gates?" | | | |

---

## Cursor skills (spot-check)

Use **natural language**; the agent should pick skills via rules / match tools.

| Id | Example user message | Expected | Status | Notes | Date |
| --- | --- | --- | --- | --- | --- |
| C1 | "Following our RPA skill conventions, name the expression language we use for modern projects and cite the skill." | Grounded in `uipath-rpa` or extension | | | |
| C2 | "Using platform guidance, list two ways to authenticate `uip` for tenant operations—no secrets in chat." | `uipath-platform` / docs | | | |

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

- Regenerate [MCP_TOOLS.md](MCP_TOOLS.md) after tool registration changes (`python ops/scripts/generate_mcp_tools_doc.py`), then **add rows** here for new tools (with NL column).
- Keep **NL scenarios** aligned with real product language from BA/SA workshops when possible.
