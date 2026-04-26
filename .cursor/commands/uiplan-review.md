---
name: uiplan-review
description: Review a UiPlan draft bundle for blocking findings.
---

# UiPlan Review

Use `.cursor/skills/uiplan/SKILL.md` and `@docs/uiplan/` as the operating
contract.

Treat the user's text after `/uiplan-review` as `<slug> [all|spec|plan|tasks]`.
Run `uipath_plan_review`, defaulting the stage to `all` when omitted.

Report blocking findings first. Do not accept, publish, or implement the plan
unless the user explicitly asks for that next step.
