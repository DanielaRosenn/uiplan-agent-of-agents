# UiPlan template kit (`templates/uiplan`)

This directory is the canonical source for UiPlan templates used by both:

- MCP generation tools (`uipath_plan_spec_new`, `uipath_plan_plan_new`, `uipath_plan_tasks_new`)
- local generator (`uv run python -m tools.uiplan generate-docs`)

## Audience

This README is for **template maintainers**.  
If you want usage/onboarding instructions, start with:

- [docs/uiplan/README.md](../../docs/uiplan/README.md)
- [docs/uiplan/HOW_TO_USE.md](../../docs/uiplan/HOW_TO_USE.md)
- [docs/uiplan/TASK_AUTHORING.md](../../docs/uiplan/TASK_AUTHORING.md)

## Template files

| File | Purpose |
| --- | --- |
| `_spec-template.md` | `spec.md` scaffold (`what`) with 360 scope contract |
| `_plan-template.md` | `plan.md` scaffold (`how`) for architecture and routing |
| `_tasks-template.md` | `tasks.md` scaffold (`build`) with executable evidence gates |
| `_workflow-catalog.md` | reusable workflow archetypes and references |
| `_diagram-patterns.md` | reusable Mermaid snippets for bundle docs |

## Maintainer rules

- Keep placeholders and headings aligned with generator mappings in:
  - [framework/mcp_server/tools/plan_uiplan.py](../../framework/mcp_server/tools/plan_uiplan.py)
  - [tools/uiplan/generators/docs_bundle.py](../../tools/uiplan/generators/docs_bundle.py)
- Keep review expectations aligned with:
  - [framework/mcp_server/tools/plan_uiplan_review.py](../../framework/mcp_server/tools/plan_uiplan_review.py)
  - [framework/tests/mcp_tests/test_uiplan_review.py](../../framework/tests/mcp_tests/test_uiplan_review.py)
  - [.cursor/skills/uiplan-review/SKILL.md](../../.cursor/skills/uiplan-review/SKILL.md)
- When adding new required sections/markers, update template + generator defaults + review rules + tests in the same change.
- Do not put user onboarding or command walkthroughs here; keep this file maintenance-focused.

## Validation checklist for template changes

1. Generate a sample bundle from templates.
2. Confirm no unresolved placeholder tokens remain unexpectedly.
3. Run UiPlan review tests.
4. Verify docs links still point to canonical usage docs.
