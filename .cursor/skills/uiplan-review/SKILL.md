---
name: uiplan-review
description: Review a UiPlan bundle and report blockers before acceptance or build.
disable-model-invocation: true
---

# UiPlan Review

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-review` as `<slug> [all|spec|plan|tasks]`.
Run `uipath_plan_review`, defaulting to `stage=all` when omitted.

Report error-severity findings first. Do not accept, publish, or implement from
this command unless the user explicitly asks for the next step after seeing the
review result.
