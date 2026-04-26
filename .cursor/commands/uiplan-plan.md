---
name: uiplan-plan
description: Write plan.md for an existing UiPlan draft.
---

# UiPlan Plan

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

Treat the user's text after `/uiplan-plan` as the UiPlan slug. Run
`uipath_plan_plan_new` to write `plan.md` for the existing draft bundle under
`.cursor/plans/<slug>/`.

If the slug is missing, ask one concise clarifying question. Do not write
`tasks.md` unless the user asks for the next stage.
