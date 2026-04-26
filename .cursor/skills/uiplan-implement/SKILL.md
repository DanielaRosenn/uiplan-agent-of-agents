---
name: uiplan-implement
description: Review an accepted UiPlan bundle, then implement from tasks.md using project tools and gates.
disable-model-invocation: true
---

# UiPlan Implement

Use `.cursor/skills/uiplan/SKILL.md` as the canonical planning contract and the
project-specific specialist skills as the implementation contract.

## Flow

1. Treat the user's text after `/uiplan-implement` as the UiPlan slug. If the
   slug is missing, ask for it.
2. Read `spec.md`, `plan.md`, and `tasks.md`, including the `Planner Route &
   Specialist Handoff` section in `plan.md`.
3. Run or request `uipath_plan_review` with `stage=all` before any source
   changes.
4. If review has error-severity findings, stop and report the blockers.
5. If review passes, ask the user before starting implementation unless the
   user explicitly supplied `--run-to-completion`, `--yes`, `--no-stop`, or
   clearly asked to run the accepted task plan end to end without stopping.
6. Confirm the `uipath-planner` route, project discovery agent output, matched
   specialist skills, MCP tools, library/AskAI-style lookup, and useful
   subagents before source edits.
7. Implement from `tasks.md` in order. Use every relevant project capability as
   needed: specialist UiPath skills, MCP tools, subagents, library lookup,
   AskAI-style documentation lookup, local CLI commands, tests, and build gates.
8. Run the build loop for the detected project type: restore -> analyze -> test
   -> pack. Stop on analyzer errors or failing tests.
9. Summarize exact verification evidence, changed files, package path if
   produced, and approval-required next steps.

## Per-Task UiPath Loop

For each unchecked task in `tasks.md`, run a complete dev + verification loop
before moving to the next task:

1. **Plan alignment** - restate the task ID, artifact path, UiPath construct,
   grounding citations, and verification command from `tasks.md`; confirm the
   intended edit is inside the accepted plan.
2. **Source reality snapshot** - before and after the task, list changed source
   files and classify each as `scaffold`, `runtime`, `test`, `docs`, or
   `config`. If the source reality contradicts a status note in `tasks.md`
   (for example, "implementation executed" while task checkboxes or artifacts
   remain incomplete), stop and report the mismatch before continuing.
3. **Dependency and tooling check** - verify required project markers,
   dependencies, CLI family, package files, and credentials/environment
   assumptions for that task. Restore/sync dependencies when the task requires
   it. Stop on dependency drift that cannot be resolved locally.
4. **Development** - implement only the current task scope. Prefer official
   UiPath tooling for scaffolds and package metadata; do not hand-author
   generated Solution descriptors.
5. **Artifact completeness gate** - verify that each task artifact path exists
   and contains task-relevant runtime substance. An artifact is not complete if
   it is empty, a no-op, only logging, a placeholder, disconnected from the
   runtime entry point, or only a generated scaffold.
6. **Task verification** - run the task-specific verification from `tasks.md`
   or the closest safe local equivalent if external credentials are unavailable.
   Tests must assert behavior tied to the task; existence/layout tests alone
   cannot satisfy business implementation tasks.
7. **Analyze gate** - for UiPath projects touched by the task, run the
   applicable analyze/lint gate before continuing. Any analyzer error blocks
   the loop.
8. **Spec compliance review** - compare the changed files against `spec.md`,
   `plan.md`, and the exact task text. Fix gaps before continuing.
9. **Code quality review** - review maintainability, security, secret handling,
   generated-file boundaries, and tests. Fix issues before continuing.
10. **Completion ledger** - record completed task IDs, changed runtime
   artifacts, verification commands/results, and remaining unchecked or blocked
   task IDs. Mark the task complete only after all applicable checks pass, then
   continue to the next unchecked task.

## Artifact Completeness Rules

- **No scaffold completion rule**: scaffolding can complete scaffold/layout
  tasks only. It cannot complete business implementation tasks such as mailbox
  reads, queue creation, duplicate suppression, analyzer graph flow, document
  evidence extraction, or human review handling.
- **XAML runtime rule**: XAML with only `LogMessage`, an empty `Sequence`, or no
  invoked workflow/business activity is incomplete unless the task is explicitly
  a scaffold/logging task.
- **LangGraph runtime rule**: Python graphs containing `noop`, `pass`,
  placeholder comments, or disconnected pipeline functions are incomplete for
  graph-flow tasks.
- **Behavior test rule**: tests that only check files, folders, schemas, or
  project markers cannot satisfy user-story behavior tasks. A behavioral test
  should fail before the implementation or be documented as an external-gated
  smoke test.
- **Mismatch stop rule**: if plan status notes, task checkboxes, and runtime
  artifacts disagree, stop and report the inconsistency instead of summarizing
  the plan as complete.

Use a fresh focused subagent for implementation or review when the task is
large, independent, or benefits from isolated context. Do not dispatch multiple
implementation subagents that edit the same project in parallel.

## Gates

- Never deploy or publish without explicit approval.
- Never deploy to Production from an AI-assistant session.
- Do not invent UiPath APIs, activity names, packages, or CLI verbs. Check
  skills, library/MCP docs, AskAI-style lookup, and repo docs first.

## Run-To-Completion Mode

When the user runs `/uiplan-implement <slug> --run-to-completion` (or `--yes`)
or explicitly asks for the accepted implementation plan to run end to end, treat
that as approval to continue through all local, non-deployment tasks without
asking again between tasks.

Still stop and report before:

- review errors or missing human acceptance,
- `skills/` submodule guard failure,
- analyzer errors, failing tests, or failed restore/pack commands,
- dependency drift or failed restore/sync,
- incomplete runtime artifacts, scaffold-only progress, or self-certifying tests,
- task status mismatches between `tasks.md` and source reality,
- spec compliance or code quality review issues that cannot be fixed locally,
- missing required credentials or tooling,
- destructive actions outside the accepted task list,
- publish, deploy, shared-resource mutation, or any Production target.
