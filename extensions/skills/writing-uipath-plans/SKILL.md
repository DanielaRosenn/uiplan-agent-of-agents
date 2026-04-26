---
name: writing-uipath-plans
description: "Use when you have a multi-step UiPath or builder-agent task: write a git-tracked implementation plan under docs/plans/ with embedded Mermaid (Pro Standard). Complements uipath-planner (routing only) and PDD_LIFECYCLE (formal PDD/SDD/ADD)."
---

# Writing UiPath Builder Plans

**Announce at start:** "I'm using the writing-uipath-plans skill to persist the plan."

## Role

You **plan and document** — you do not execute build/publish/deploy. After this skill finishes, the main agent (or specialist skills) implements the checkboxes.

## When to use

- Non-trivial work: multiple files, MCP tools, tests, or unclear scope
- User asked for a plan, roadmap, or "before we code" breakdown
- After `uipath-planner` routes to specialists — capture the agreed routing + file touch list here

Skip for one-line fixes or a single obvious file change.

## Dependencies

1. Load **mermaid-diagram-builder** (same `.cursor/skills/`) for every diagram: Pro Standard palette, `classDef` per node, `linkStyle` for critical path, no inline `style` fills.
2. Align with [docs/PDD_LIFECYCLE.md](../../../docs/PDD_LIFECYCLE.md): link formal PDD/SDD/ADD paths in front-matter `linked_pdd` when they exist.

## Output location

- **Path:** `docs/plans/YYYY-MM-DD-<slug>.md` (UTC or local date — be consistent with existing files in that folder).
- **Template:** Start from [docs/plans/_TEMPLATE.md](../../../docs/plans/_TEMPLATE.md).
- **Index:** After creating or materially editing a plan, run `python ops/scripts/generate_plan_index.py` from repo root (or ask the user to run it) so [docs/plans/README.md](../../../docs/plans/README.md) stays current.

## Drafting vs publishing (brainstorm loop)

For multi-step or ambiguous work, load the **`uiplan`** skill first (see
`.cursor/skills/uiplan/SKILL.md`). It runs the UiPlan loop and writes drafts to
the correct location:

- **Drafts** live under `.cursor/plans/<YYYY-MM-DD-slug>.md` (git-ignored, per-user).
  Created by `uipath_plan_new`, evolved by `uipath_plan_refine`.
- **Publishing** copies the accepted draft to `docs/plans/` (git-tracked) via
  `uipath_plan_publish`. Publish only after `uipath_plan_accept`.
- **Acceptance is recorded in front matter** (`status: accepted`,
  `accepted_at`, `accepted_by`). When `UIPATH_PLAN_GATE=1`, destructive
  workflow tools refuse writes until a plan is accepted.

This skill (writing-uipath-plans) still owns the *shape* of the file:
required sections, front matter, Mermaid. The **`uiplan`** skill owns the
*workflow* of getting there (three-file bundle or explicit legacy single-file).

## MCP (optional but recommended)

Prefer the plan MCP tools so Cursor and agents share one source of truth.

- Brainstorm loop: `uipath_plan_new` -> `uipath_plan_brainstorm` ->
  `uipath_plan_refine` -> `uipath_plan_diff` -> `uipath_plan_accept`
  (or `uipath_plan_reject`) -> `uipath_plan_publish`.
- CRUD on the published set: `uipath_plan_save`, `uipath_plan_list`
  (`scope=drafts|published|both`), `uipath_plan_read`,
  `uipath_plan_render_mermaid`, `uipath_plan_status_set`.
- `uipath_plan_status_set` to `done` may require an approved design for
  that `project_dir` when `UIPATH_DESIGN_APPROVAL_ENABLED` is on.

## Plan contents (required)

1. **Front matter** — all keys in `_TEMPLATE.md` (slug, title, date, status, owner, project_type; optional linked_pdd, supersedes).
2. **Goal** — one sentence.
3. **Architecture** — include at least one ` ```mermaid ` flowchart or sequence diagram showing components and boundaries.
4. **File plan** — table or list: path → responsibility.
5. **Bite-sized tasks** — `- [ ]` checkboxes, each 2–5 minutes of work; include "run tests" and "commit" where relevant.
6. **Verification** — exact pytest / CLI commands.
7. **Rollback** — how to revert if the change is wrong.

## UiPath project_type hints

Set `project_type` in front matter to one of: `rpa`, `coded-agent`, `solution`, `coded-app`, `mixed`. Detect from repo markers (`project.json` + `.xaml`, `langgraph.json`, `solution.uipx`, etc.) per root `CLAUDE.md` §1 — do not guess if ambiguous; use `mixed` and list open questions.

## Anti-patterns

- Plans without Mermaid (always include at least one diagram).
- Duplicating entire specialist skill procedures (link skill id instead).
- Saving only in chat — the repo must contain `docs/plans/*.md` for the next session.
