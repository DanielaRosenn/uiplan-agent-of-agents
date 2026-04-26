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
5. If review passes, ask the user before starting implementation.
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

## Gates

- Never deploy or publish without explicit approval.
- Never deploy to Production from an AI-assistant session.
- Do not invent UiPath APIs, activity names, packages, or CLI verbs. Check
  skills, library/MCP docs, AskAI-style lookup, and repo docs first.
