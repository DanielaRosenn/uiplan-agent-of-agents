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
| `_spec-template.md` | `spec.md` scaffold (`what`) with 360 scope and visual documentation contracts |
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
- Visual standards are part of the template contract. If `_spec-template.md`
  changes required visuals, update `_diagram-patterns.md`,
  [docs/uiplan/README.md](../../docs/uiplan/README.md),
  [docs/uiplan/HOW_TO_USE.md](../../docs/uiplan/HOW_TO_USE.md), and
  [docs/uiplan/TASK_AUTHORING.md](../../docs/uiplan/TASK_AUTHORING.md).
- Named project templates are host shells unless documented otherwise. If a
  template task names a repo or Studio template, the generated tasks must require
  the full lifecycle: copy/export the template, read/inspect the copied
  project's real workflows/config/arguments/dependencies/extension points,
  preserve the generated runtime shape, customize the copied shell for the
  specific business process, and verify the customized shell.
- Dispatcher, Long Running Workflow / AnalyzerRunner, and HITL templates must
  never close as "template copied" only. They require business-specific
  customization inside the copied template and runtime evidence for the
  customized behavior.
- Do not put user onboarding or command walkthroughs here; keep this file maintenance-focused.

## Validation checklist for template changes

1. Generate a sample bundle from templates.
2. Confirm no unresolved placeholder tokens remain unexpectedly.
3. For any RPA/Studio task template changes, confirm the generated tasks require
   both Studio Designer validation (`uip rpa get-errors --studio-dir ...`) and a
   Studio build (`uip rpa build --project-path ... --studio-dir ...`) before
   package analyze, deploy, or Orchestrator smoke can close the task.
4. For named-template tasks, confirm the generated tasks do not stop at
   "template copied"; they must require inspection of the copied template and
   business-specific customization inside the shell. Dispatcher tasks require
   config, workflow, logical component, queue payload, logging, and smoke
   evidence. Long Running Workflow / AnalyzerRunner tasks require wait/resume,
   queue, agent invocation, status transition, and log evidence. HITL tasks
   require review schema, outcomes, timeout/escalation, return path, and
   downstream update evidence.
5. Confirm generated specs include business process, solution architecture,
   runtime sequence, decision tree, and evidence coverage visuals or explicit
   instructions for downstream stages to provide them.
6. Run UiPlan review tests.
7. Verify docs links still point to canonical usage docs.
