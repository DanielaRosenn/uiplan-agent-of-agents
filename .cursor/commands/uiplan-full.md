---
name: uiplan-full
description: Run the full UiPlan flow for a requested change.
---

# UiPlan Full

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

Treat the user's text after `/uiplan-full` as the plan title and intent. Run
`uipath_plan_uiplan_new`, which performs grounding, spec, plan, tasks, and
review for the bundle under `.cursor/plans/<YYYY-MM-DD-slug>/`.

If the title is missing, ask one concise clarifying question. Do not start
implementation until review has no blocking findings and the human accepts the
plan.
