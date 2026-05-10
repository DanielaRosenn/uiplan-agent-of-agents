---
name: uiplan-tasks
description: Wrapper for /uiplan-tasks with artifact-complete handoff expectations.
disable-model-invocation: true
---

# uiplan-tasks wrapper

Source contract: `.cursor/skills/uiplan/SKILL.md`

Primary tool: `uipath_plan_tasks_new`.

Build, Verify, and Handoff:
- Every task must include artifact path, activity intent, and CLI commands.
- Include queue/Orchestrator impact when relevant.
- Include tests before implementation.
- Keep explicit `TODO` entries and `NEEDS CLARIFICATION` markers until resolved.
