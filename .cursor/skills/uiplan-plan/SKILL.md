---
name: uiplan-plan
description: Create or update plan.md for an existing UiPlan draft.
disable-model-invocation: true
---

# UiPlan Plan

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-plan` as the UiPlan slug. Run
`uipath_plan_plan_new` for the matching `.cursor/plans/<YYYY-MM-DD-slug>/`
folder.

The generated plan must include the Development execution contract and identify
the skills, tools, project paths, and build gates used to implement the design.
