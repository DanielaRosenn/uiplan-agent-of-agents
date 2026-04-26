---
name: uiplan-tasks
description: Write tasks.md for an existing UiPlan draft.
---

# UiPlan Tasks

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

Treat the user's text after `/uiplan-tasks` as the UiPlan slug. Run
`uipath_plan_tasks_new` to write `tasks.md` for the existing draft bundle under
`.cursor/plans/<slug>/`.

If the slug is missing, ask one concise clarifying question. Do not start
implementation from the task list until the bundle is reviewed and accepted.
