---
name: uiplan-spec
description: Create the UiPlan draft folder and spec.md for a requested change.
disable-model-invocation: true
---

# UiPlan Spec

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-spec` as `<title> [--intent text]`. Run
`uipath_plan_spec_new` to create `.cursor/plans/<YYYY-MM-DD-slug>/spec.md`.

The generated spec is intentionally basic. It should be readable beside the
formal PDD / SDD and should not copy their prose. Use those documents as
context and traceability sources; summarize only business intent, user stories,
acceptance criteria, SME gaps, and the minimal Development Handoff needed to
prepare `plan.md` and `tasks.md`.

The generated spec must include the Development Handoff section, but that
section should only point the next stages in the right direction. Detailed
architecture, workflow files, activities, CLI commands, skill routing, and
executor instructions belong in `plan.md` and `tasks.md`.

The spec is only the first stage. Do not proceed to `/uiplan-plan`,
`/uiplan-tasks`, review, acceptance, or implementation until the user approves
the generated `spec.md` or explicitly asks for the next stage.

For documentation/process-improvement specs, the Development Handoff must still
name the approval-gated flow:
`spec -> plan -> tasks -> review -> accept -> /uiplan-implement`.
Downstream `tasks.md` must follow `docs/uiplan/TASK_AUTHORING.md`, including
capability routing, BA/SA/Dev/QA lenses, and the develop -> analyze/test ->
parse output -> fix -> rerun evidence loop.
