---
slug: uiplan-framework
title: /uiplan framework (spec-kit-style, grounded in workspace)
date: 2026-04-21
status: accepted
owner: daniela
project_type: mixed
linked_pdd: ""
supersedes: null
accepted_at: 2026-04-21T00:00:00Z
accepted_by: daniela
rejection_reason: null
published_at: null
---

# /uiplan framework (spec-kit-style, grounded in workspace)

> Follow-up update: paradigm-aware scaffolds and feasibility review gates were
> added in a later implementation pass (`uiplan_skills_detail_5ad4aff8`).
> This file remains a historical accepted plan.

> For agentic workers: implement task-by-task; checkboxes below track progress.
> Use `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans`.

**Goal:** Add a `/uiplan` command that produces a spec-kit-style three-file
build-ready bundle (spec + plan + tasks), grounded in this workspace's
project-context, skills, library, PDD templates, and project templates,
with a dedicated review tool that enforces spec coverage, constitution
gates, TDD pairing, and citation resolution.

**Why now:** The earlier single-file `_UIPLAN_TEMPLATE.md` sketched vague
"Phase N" checklists without atomic steps or re-evaluation. Spec-kit
(github/spec-kit) and Superpowers both separate **what / how / atoms**
and both have an explicit self-review pass. Matching that shape turns
`/uiplan` from a template into an executable workflow.

## Architecture

Three linked Markdown files per slug:

```
.cursor/plans/<YYYY-MM-DD>-<slug>/     # draft (git-ignored)
  spec.md         # user stories, FRs, SCs, assumptions
  plan.md         # tech context, structure, constitution check
  tasks.md        # phase-grouped atomic steps with code blocks
  .meta.yaml      # single source of truth for status / stage / timestamps
```

On `uipath_plan_publish`, the whole folder moves to `docs/plans/<slug>/`.
Back-compat: existing single-file plans (e.g. `2026-04-21-invoice-routing.md`)
continue to work; folder plans and single-file plans are distinguished by
filesystem shape.

### Five new MCP tools

| Tool | Annotation | Purpose |
|---|---|---|
| `uipath_plan_ground` | read-only | Produce a grounding pack (project-context, matched skills, library hits, similar PDDs, candidate project template, constitution) |
| `uipath_plan_spec_new` | destructive | Write `spec.md` seeded from grounding pack |
| `uipath_plan_plan_new` | destructive | Write `plan.md` with constitution check + structure decision |
| `uipath_plan_tasks_new` | destructive | Write `tasks.md` with atomic TDD-paired steps, `[P]` + `[USn]` markers |
| `uipath_plan_review` | read-only | Return structured findings per stage or cross-doc |
| `uipath_plan_uiplan_new` | destructive | Orchestrator: ground -> spec -> plan -> tasks -> review, with stop gates |

### CLI + slash surface

- `uipath-claude plan uiplan <topic>` (full loop) /
  `... plan uiplan {ground|spec|plan|tasks|review} [args]` (staged)
- First-class slash: `/uiplan-ground`, `/uiplan-spec`, `/uiplan-plan`,
  `/uiplan-tasks`, `/uiplan-review`, `/uiplan-full`, `/uiplan-implement`
- Back-compat: `/uiplan` dispatcher (`/uiplan full …`, `/uiplan spec …`, …)

### Grounding strategy (the key differentiator)

Every stage consults the workspace before generating:

| Stage | Sources |
|---|---|
| `ground` / `spec_new` | `.claude/rules/project-context.md` (or triggers `uipath-project-discovery-agent`), `CLAUDE.md` hard gates, existing `docs/PDD/*.md` |
| `plan_new` | `uipath-planner` skill match -> matched specialist skills (via `uipath_skill_get`); `uipath_library_search` for each capability; `scaffold/template/` (dispatcher/long-running/performer) for project shell; `framework/uipath_claude/templates/sdd.md` for structure |
| `tasks_new` | Drafted `plan.md` structure; `uipath_doc_get_activity` for activities; skill SKILL.md capability sections; `framework/uipath_claude/templates/tdd.md` for test patterns; project template file layouts |
| `review` | `CLAUDE.md` hard gates as constitution, optional `docs/plans/constitution.md` override; cross-doc consistency; existing plans for duplicate/supersede detection |

Every generated section gets inline citations (`[skill:uipath-rpa]`,
`[library:uipath-docs/orchestrator/queues]`, `[template:long-running]`).
`uipath_plan_review` verifies citations resolve.

### Review findings (what re-evaluation actually enforces)

| Stage | Rules |
|---|---|
| `spec` | No `[NEEDS CLARIFICATION: ...]` left; >=1 P1 story with Given/When/Then; all FRs start with `System MUST` / `Users MUST`; >=1 measurable SC |
| `plan` | Tech context has no NEEDS CLARIFICATION; Structure Decision set; constitution gates pass OR have Complexity Tracking entries |
| `tasks` | Every task has exact file path; every task has `[USn]` matching a spec story; no superpowers "No Placeholders" phrases; TDD pairing (every impl task preceded by test task in same story); `[P]` only when files distinct from the immediately preceding non-`[P]` task |
| `cross` | Task file paths appear in plan.md Project Structure; every FR has >=1 task; every user story has >=1 task per phase it participates in; no duplicate/superseded plans for the same topic |

Output shape: `{ok, stage, findings[], next_action}`.

## Tech Stack

- Python 3.11, existing `uv` workspace
- `pyyaml` for `.meta.yaml`
- Existing MCP plumbing in `framework/mcp_server/tools/plan_tools.py`
- Existing `uipath_library_search`, `uipath_doc_get_activity`,
  `uipath_skill_get`, `uipath_plan_brainstorm`
- Existing templates under `framework/uipath_claude/templates/` and `scaffold/template/`

---

## File Structure

### New files

```
.cursor/skills/uiplan/SKILL.md
templates/uiplan/_spec-template.md
templates/uiplan/_plan-template.md
templates/uiplan/_tasks-template.md
docs/plans/constitution.md                          # seeded from CLAUDE.md
framework/uipath_claude/commands/uiplan.md        # /uiplan slash command
framework/tests/mcp_tests/test_uiplan_tools.py
framework/tests/mcp_tests/test_uiplan_review.py
framework/tests/mcp_tests/test_plan_grounding.py
```

### Modified files

```
framework/mcp_server/tools/plan_tools.py            # +6 tools, folder-plan helpers
framework/uipath_claude/cli/app.py                  # add `plan uiplan` subcommand group
framework/tests/mcp_tests/test_plan_tools.py              # extend TestGetPlanTools
framework/tests/mcp_tests/test_tool_annotations.py        # classify new tools
framework/tests/mcp_tests/test_tool_descriptions.py       # descriptions for new params
ops/scripts/mcp_tools_doc_diagrams.py                   # diagrams for new tools
docs/PLANNING_FRAMEWORK.md                          # /uiplan section with grounding diagram
README.md                                           # link /uiplan from SDLC section
.gitignore                                          # ensure .cursor/plans/**/ is still covered
```

---

## Task Breakdown

### Task 1: meta + folder-plan helpers

**Files:**

- Create: `framework/mcp_server/tools/plan_folder.py`
  (`load_meta(slug) -> dict`, `save_meta(slug, meta)`, `is_folder_plan(path)`,
  `resolve_slug(root, slug)` returns a `PlanLocation` that is either a single
  file path or a directory path)
- Modify: `framework/mcp_server/tools/plan_tools.py:_find_plan_path`
  (delegate to `plan_folder.resolve_slug`)
- Test: `framework/tests/mcp_tests/test_plan_folder.py`

Steps:

- [ ] **Step 1:** Write `framework/tests/mcp_tests/test_plan_folder.py` covering:
  `resolve_slug` returns file for legacy single-file plan and directory for
  folder plan; `load_meta`/`save_meta` roundtrips; `is_folder_plan` true for
  dir with `.meta.yaml`.
- [ ] **Step 2:** Run; expect FAIL.
- [ ] **Step 3:** Implement `plan_folder.py`.
- [ ] **Step 4:** Re-run; expect PASS.
- [ ] **Step 5:** Patch `_find_plan_path` and any `uipath_plan_read` / `list`
  / `accept` / `reject` / `publish` call sites; re-run full `framework/tests/mcp_tests`.
- [ ] **Step 6:** Commit: `feat(plan): folder-plan helpers + back-compat`.

### Task 2: constitution seeding

**Files:**

- Create: `docs/plans/constitution.md` (seeded from CLAUDE.md hard gates)
- Create: `framework/mcp_server/tools/plan_constitution.py`
  (`load_constitution(root) -> list[Gate]`)
- Test: `framework/tests/mcp_tests/test_plan_constitution.py`

Steps as above (test-first, minimal impl, commit).

### Task 3: `uipath_plan_ground`

**Files:**

- Modify: `framework/mcp_server/tools/plan_tools.py` (+ tool definition + handler)
- New helper: `framework/mcp_server/tools/plan_grounding.py` orchestrating
  `project-context` read, `uipath-planner` skill match, `library_search`
  fan-out, `doc_get_activity` fetches, template picker.
- Test: `framework/tests/mcp_tests/test_plan_grounding.py` (library hits via `search_library.invoke`);
  `framework/tests/mcp_tests/test_uiplan_tools.py` (`test_uiplan_ground_smoke`).

Tests cover: missing project-context path, skills matched by intent keywords,
library hits returned with citations, similar-PDD detection, constitution
load.

### Task 4: templates

Create `templates/uiplan/_spec-template.md`, `_plan-template.md`,
`_tasks-template.md`, each adapted from spec-kit with UiPath-specific
sections (project type, orchestrator folder, coded-vs-XAML, HITL surface).
Each template includes inline citation block headers like
`> Grounding: [...]` that the tools fill in.

Tests: `framework/tests/uiplan/test_generate_docs.py` exercises template copy and
visual-density on generated bundles.

### Task 5: `uipath_plan_spec_new`

Writes `spec.md` using `_spec-template.md`, fills front matter + meta yaml,
consumes grounding pack, injects `[NEEDS CLARIFICATION]` where grounding
had `unanswered[]`.

Tests: roundtrip, grounding required, NEEDS CLARIFICATION present when
grounding had gaps.

### Task 6: `uipath_plan_plan_new`

Requires accepted spec stage (no unresolved NEEDS CLARIFICATION when
`strict=true`). Writes `plan.md` using `_plan-template.md`, fills
Tech Context, Structure Decision (from chosen template), Constitution Check.

### Task 7: `uipath_plan_tasks_new`

Writes `tasks.md` with phase-grouped atomic steps. Enforces TDD pairing at
generation time (each impl task gets a preceding test task in the same
story). Resolves activity citations via `uipath_doc_get_activity` and
records them.

### Task 8: `uipath_plan_review`

Input: `{project_root, slug, stage?: "spec"|"plan"|"tasks"|"all"}`.
Output: `{ok, stage, findings[], next_action}`.

Each rule in a pluggable `REVIEW_RULES: dict[str, list[Rule]]` map so new
rules can be added without touching the tool handler.

Tests: negative cases - inject a `[NEEDS CLARIFICATION]` in spec, a missing
`[USn]` in tasks, a bad `[P]`, a missing TDD pairing, an unresolvable
citation; each must surface as a finding with the correct `rule` id.

### Task 9: `uipath_plan_uiplan_new` orchestrator

Chains `ground -> spec_new -> plan_new -> tasks_new -> review(stage=all)`.
Returns `{slug, directory, review}`. Stops on review errors and returns the
findings so the caller can refine.

### Task 10: CLI + slash

Add `uipath-claude plan uiplan` Typer subcommand dispatching to each tool.
Add `framework/uipath_claude/commands/uiplan.md` so `/uiplan` works in Cursor chat.

### Task 11: skill

Write `.cursor/skills/uiplan/SKILL.md`. Hard gate: no implementation skill
or code change until `uipath_plan_review` returns `{ok: true}` and the user
explicitly accepts the plan via `uipath_plan_accept`.

### Task 12: docs + regen

Add a `/uiplan` section to `docs/PLANNING_FRAMEWORK.md` with a Mermaid
diagram of the grounding flow. Add a short reference in `README.md`
pointing from the existing "SDLC planning" section to `/uiplan`.
Regenerate `docs/MCP_TOOLS.md` and `docs/plans/README.md`.

### Task 13: full-loop test + annotations

- `framework/tests/mcp_tests/test_uiplan_tools.py` (`test_uiplan_full_scaffold`): full ground -> ... -> review green
  roundtrip against a fixture repo.
- Update `test_tool_annotations.py` to classify the six new tools.
- Update `test_tool_descriptions.py` for new params.

### Task 14: final run + commit

```bash
uv run python ops/scripts/generate_mcp_tools_doc.py; uv run python ops/scripts/generate_plan_index.py
uv run pytest framework/tests/mcp_tests framework/tests/unit -q
```

If green, commit in one logical push:

```
feat(plan): add /uiplan spec-kit-style workflow grounded in workspace

- Three-file plans (spec.md + plan.md + tasks.md) per slug directory
- Five new MCP tools: uipath_plan_{ground,spec_new,plan_new,tasks_new,review,uiplan_new}
- Grounding pulls project-context, skills, library, PDD templates, project templates
- Review enforces spec coverage, constitution gates, TDD pairing, citation resolution
- CLI (uipath-claude plan uiplan) + /uiplan slash + .cursor/skills/uiplan/
- Back-compat with legacy single-file plans
```

Then `git push origin main`.

---

## Self-Review

- Spec coverage: every feature in the Architecture section is covered by at
  least one task above.
- Placeholder scan: no "implement X", "add appropriate handling", or
  "similar to earlier" phrases.
- Type consistency: `PlanLocation`, `Gate`, `Rule`, `Finding`, `GroundingPack`
  are the only shared types; defined once in the earliest task that
  introduces them.

## Rollback

Revert the commit; the branch stays clean because every task commits
independently. `.cursor/plans/<slug>/` directories created during testing
are git-ignored and can be deleted.
