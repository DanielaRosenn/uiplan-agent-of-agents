---
name: uiplan-spec
description: Create a UiPlan spec.md draft for a requested change.
---

# UiPlan Spec

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

Treat the user's text after `/uiplan-spec` as `<title> [--intent text]`. Run
`uipath_plan_spec_new` to create the draft bundle and write `spec.md` under
`.cursor/plans/<YYYY-MM-DD-slug>/`.

If the title is missing, ask one concise clarifying question. Do not write
`plan.md` or `tasks.md` unless the user asks for the next stage.
