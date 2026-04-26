---
name: uiplan-full
description: Run the complete UiPlan flow: ground, spec, plan, tasks, and review.
disable-model-invocation: true
---

# UiPlan Full

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-full` as the title and intent. Run the
full UiPlan flow through `uipath_plan_uiplan_new`: grounding, `spec.md`,
`plan.md`, `tasks.md`, and `uipath_plan_review(stage=all)`.

Drafts must stay under `.cursor/plans/<YYYY-MM-DD-slug>/`. Do not implement
until review passes and the human accepts the bundle.
