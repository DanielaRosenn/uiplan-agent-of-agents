---
name: uiplan-spec
description: Create the UiPlan draft folder and spec.md for a requested change.
disable-model-invocation: true
---

# UiPlan Spec

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-spec` as `<title> [--intent text]`. Run
`uipath_plan_spec_new` to create `.cursor/plans/<YYYY-MM-DD-slug>/spec.md`.

The generated spec must include the Development Handoff section so the accepted
design can later become build-ready work.
