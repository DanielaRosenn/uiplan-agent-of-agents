---
name: uiplan
description: Create, continue, or review a UiPlan spec/plan/tasks bundle.
---

# UiPlan

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

Interpret the user's text after `/uiplan` as a dispatcher:

- `full <title>` or any free-form title: run the full UiPlan flow through
  `uipath_plan_uiplan_new`.
- `ground <topic>`: run `uipath_plan_ground`.
- `spec <title> [--intent text]`: run `uipath_plan_spec_new`.
- `plan <slug>`: run `uipath_plan_plan_new`.
- `tasks <slug>`: run `uipath_plan_tasks_new`.
- `review <slug> [all|spec|plan|tasks]`: run `uipath_plan_review`.

If no usable title, topic, or slug is provided, ask one concise clarifying
question. Do not start implementation until review has no blocking findings and
the human accepts the plan.
