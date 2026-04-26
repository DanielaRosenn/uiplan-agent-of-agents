---
name: uiplan-tasks
description: Create or update tasks.md for an existing UiPlan draft.
disable-model-invocation: true
---

# UiPlan Tasks

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-tasks` as the UiPlan slug. Run
`uipath_plan_tasks_new` for the matching `.cursor/plans/<YYYY-MM-DD-slug>/`
folder.

The task list must include story-level tests before implementation tasks and a
final Build, Verify, and Handoff phase. That final phase is the input to
`/uiplan-implement`.
