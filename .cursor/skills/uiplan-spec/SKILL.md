---
name: uiplan-spec
description: Create the UiPlan draft folder and spec.md for a requested change.
disable-model-invocation: true
---

# UiPlan Spec

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-spec` as `<title> [--intent text]`. Run
`uipath_plan_spec_new` to create `.cursor/plans/<YYYY-MM-DD-slug>/spec.md`.

The generated spec should stay readable beside formal PDD / SDD, without
copying their prose. Use those documents as context and traceability sources;
summarize business intent, user stories, acceptance criteria, SME gaps, and a
clear handoff contract for `plan.md` and `tasks.md`.

The generated spec must include:

- `## Development Handoff` (with implementation paradigm, CLI family, and
  deploy gate),
- `## LLM / Executor Readiness Contract` (role/scope, environment, skill
  routing matrix, decision logic inventory, and build readiness checklist),
- `## 360 Build Visibility Contract` with all required visibility tables:
  - workflow/artifact inventory,
  - activity/connector/dependency/package inventory,
  - agent/DMN/Flow/HITL/platform-resource inventory,
  - logging/observability contract,
  - scaffold provenance + anti-stub rules,
  - verification commands + evidence outputs,
- at least one business/process Mermaid diagram.

Detailed step-by-step implementation still belongs in `tasks.md`, but spec-level
visibility is mandatory: all in-scope surfaces must be named with expected
ownership, boundaries, and evidence. Unknowns must be explicit
`[NEEDS CLARIFICATION: ...]` markers, never generic placeholders.

The spec is only the first stage. Do not proceed to `/uiplan-plan`,
`/uiplan-tasks`, review, acceptance, or implementation until the user approves
the generated `spec.md` or explicitly asks for the next stage.

For documentation/process-improvement specs, the Development Handoff must still
name the approval-gated flow:
`spec -> plan -> tasks -> review -> accept -> /uiplan-implement`.
Downstream `tasks.md` must follow `docs/uiplan/TASK_AUTHORING.md`, including
capability routing, BA/SA/Dev/QA lenses, and the develop -> analyze/test ->
parse output -> fix -> rerun evidence loop.
