---
name: uiplan
description: Create, continue, or review a UiPlan spec/plan/tasks bundle.
---

# UiPlan

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

This is the single Cursor-native UiPlan dispatcher. It must guide users through
the project-building planning path, not directly into implementation:

`ground -> spec -> plan -> tasks -> review -> human acceptance -> implementation handoff`

Interpret the user's text after `/uiplan` as a dispatcher:

- `full <title>` or any free-form title: run the full UiPlan flow through
  `uipath_plan_uiplan_new`.
- `ground <topic>`: run `uipath_plan_ground`.
- `spec <title> [--intent text]`: run `uipath_plan_spec_new`.
- `plan <slug>`: run `uipath_plan_plan_new`.
- `tasks <slug>`: run `uipath_plan_tasks_new`.
- `review <slug> [all|spec|plan|tasks]`: run `uipath_plan_review`.

Draft bundles live under `.cursor/plans/<YYYY-MM-DD-slug>/` with `spec.md`,
`plan.md`, `tasks.md`, and `.meta.yaml`.

If no usable title, topic, or slug is provided, ask one concise clarifying
question. Do not start implementation until review has no blocking findings and
the human accepts the plan.
