---
name: uiplan
description: UiPlan (spec-kit-style) — three-file bundle under .cursor/plans/ grounded in project-context, skills, library, and constitution. Use for build-ready specs before implementation.
---

# UiPlan (spec + plan + tasks)

## When to use

- You need a **structured** build contract: `spec.md` (what), `plan.md` (how), `tasks.md` (atomic steps).
- You want outputs **grounded** in this repo (`CLAUDE.md`, `.claude/rules/project-context.md`, skills, docs templates).
- Lightweight ad-hoc plan: use `uipath_plan_new` + brainstorm instead.

## Hard gate

Do **not** start implementation (workflow writes, package installs, deploy) until:

1. `uipath_plan_review` with `stage=all` returns `"ok": true` (no error-severity findings), and
2. The human accepts the bundle via `uipath_plan_accept` (or explicitly waives risk).

## Flow

1. **Ground** — `uipath_plan_ground` with the feature topic; read `matched_skills`, `library_hits`, `unanswered`.
2. **Spec** — `uipath_plan_spec_new` (or `uipath_plan_uiplan_new` for full loop). Fix any `unanswered` items in `spec.md` (add real text; avoid `[NEEDS CLARIFICATION` unless you intend a review failure).
3. **Plan** — `uipath_plan_plan_new`; ensure Constitution Check lists every gate id from `docs/plans/constitution.md`.
4. **Tasks** — `uipath_plan_tasks_new`; keep `- [ ] Tnn [P?] [USn]` format and test sections before implementation sections.
5. **Review** — `uipath_plan_review`; iterate until `ok`.
6. **Accept / publish** — `uipath_plan_accept` then `uipath_plan_publish` (copies folder to `docs/plans/`).

## Slash / CLI

- Chat: `/uiplan full <title>` or staged `/uiplan ground|spec|plan|tasks|review ...`
- CLI: `uipath-claude plan uiplan full "<title>"` or `plan uiplan spec`, `plan uiplan plan <slug>`, etc.

## Mermaid

Use `.cursor/skills/mermaid-diagram-builder/SKILL.md` for diagrams embedded in `plan.md`.
