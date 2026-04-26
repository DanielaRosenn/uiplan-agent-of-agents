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
2. **Dependency and tooling check** - verify required project markers,
   dependencies, CLI family, package files, and credentials/environment
   assumptions for that task. Restore/sync dependencies when the task requires
   it. Stop on dependency drift that cannot be resolved locally.
3. **Development** - implement only the current task scope. Prefer official
   UiPath tooling for scaffolds and package metadata; do not hand-author
   generated Solution descriptors.
4. **Task verification** - run the task-specific verification from `tasks.md`
   or the closest safe local equivalent if external credentials are unavailable.
5. **Analyze gate** - for UiPath projects touched by the task, run the
   applicable analyze/lint gate before continuing. Any analyzer error blocks
   the loop.
6. **Spec compliance review** - compare the changed files against `spec.md`,
   `plan.md`, and the exact task text. Fix gaps before continuing.
7. **Code quality review** - review maintainability, security, secret handling,
   generated-file boundaries, and tests. Fix issues before continuing.
8. **Record progress** - mark the task complete only after the task passes all
   applicable checks, then continue to the next unchecked task.

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
- spec compliance or code quality review issues that cannot be fixed locally,
- missing required credentials or tooling,
- destructive actions outside the accepted task list,
- publish, deploy, shared-resource mutation, or any Production target.
