# UiPlan template kit (`templates/uiplan`)

This directory is the canonical source for UiPlan templates used by both:

- MCP generation tools (`uipath_plan_spec_new`, `uipath_plan_plan_new`, `uipath_plan_tasks_new`)
- local generator (`uv run python -m tools.uiplan generate-docs`)

## UX and accessibility quality bar

All templates in this folder must optimize for first-time maintainers and
project teams:

- Keep instructions short, plain-language, and action-first.
- Use a predictable heading hierarchy (`H1 -> H2 -> H3`; avoid skipping levels).
- Place "what to do now" guidance near high-friction sections.
- Prefer concise checklists over dense prose where execution is expected.
- Keep visual guidance readable without relying on color alone.
- Preserve generator-required placeholders, anchors, and section contracts.

## Audience

This README is for **template maintainers**.  
If you want usage/onboarding instructions, start with:

- [docs/uiplan/README.md](../../docs/uiplan/README.md)
- [docs/uiplan/HOW_TO_USE.md](../../docs/uiplan/HOW_TO_USE.md)
- [docs/uiplan/TASK_AUTHORING.md](../../docs/uiplan/TASK_AUTHORING.md)

## Template files

| File | Purpose |
| --- | --- |
| `_spec-template.md` | `spec.md` scaffold (`what`) with 360 scope, visual documentation contracts, and AS-IS business process flow |
| `_plan-template.md` | `plan.md` scaffold (`how`) for architecture, routing, TO-BE solution architecture, runtime sequence, and workflow catalog |
| `_tasks-template.md` | `tasks.md` scaffold (`build`) with executable evidence gates |
| `_workflow-catalog.md` | reusable workflow archetypes and references |
| `_diagram-patterns.md` | reusable Mermaid snippets for bundle docs |

## AS-IS / TO-BE views

Templates now include anchors for UiPlan Studio's AS-IS and TO-BE canvases:

- **AS-IS** (`spec.md#business-process-flow`): Manual process swim-lanes showing actors, handoffs, channels, SLA, and pain points.
- **TO-BE** (`spec.md#solution-architecture` + `plan.md#solution-architecture`, `plan.md#runtime-sequence`, `plan.md#workflow-catalog`): Automated solution architecture with triggers, workflows, integrations, Orchestrator resources, HITL surfaces, and evidence sinks.

To enable these views, configure `.uiplan/explorer.yaml` with a `views:` block pointing at the template-provided anchors. See [docs/uiplan/EXPLORER.md](../../docs/uiplan/EXPLORER.md) for the full schema.

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
3. Confirm heading order and section flow are consistent and scannable.
4. Confirm all newly added guidance is plain-language and task-oriented.
5. For any RPA/Studio task template changes, confirm the generated tasks require
   both Studio Designer validation (`uip rpa get-errors --studio-dir ...`) and a
   Studio build (`uip rpa build --project-path ... --studio-dir ...`) before
   package analyze, deploy, or Orchestrator smoke can close the task.
6. For named-template tasks, confirm the generated tasks do not stop at
   "template copied"; they must require inspection of the copied template and
   business-specific customization inside the shell. Dispatcher tasks require
   config, workflow, logical component, queue payload, logging, and smoke
   evidence. Long Running Workflow / AnalyzerRunner tasks require wait/resume,
   queue, agent invocation, status transition, and log evidence. HITL tasks
   require review schema, outcomes, timeout/escalation, return path, and
   downstream update evidence.
7. Confirm generated specs include business process, solution architecture,
   runtime sequence, decision tree, and evidence coverage visuals or explicit
   instructions for downstream stages to provide them.
8. Run UiPlan review tests.
9. Verify docs links still point to canonical usage docs.
