---
name: uiplan-tasks
description: Create a feasibility-ready tasks.md with paradigm-specific artifacts, verification steps, and build handoff detail.
disable-model-invocation: true
---

# UiPlan Tasks

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-tasks` as the UiPlan slug. Run
`uipath_plan_tasks_new` for the matching `.cursor/plans/<YYYY-MM-DD-slug>/`
folder.

## Audience

`tasks.md` is the **Solution Engineer -> Developer / Executor** build sheet.
Every architectural and routing decision in `spec.md` and `plan.md` is settled.
Each task line is a single done gate carrying: artifact path, project, workflow
type, package/activity (when applicable), CLI command, evidence path, skill /
agent / subagent / MCP-tool tag, and acceptance.

## Required preconditions

Before task generation:

- `spec.md` exists and includes `Development Handoff` with declared paradigm.
- `plan.md` exists with the full Solution-Engineer sections: `Audience and
  Scope`, `Stack Policy`, `Project Inventory`, `Workflow Catalog`,
  `Activity Inventory`, `Bindings and Environment`,
  `Skill and Subagent Routing`, plus the existing `Project Structure`,
  `Paradigm build loop`, and `Planner Route & Specialist Handoff` sections.
- grounding inputs for activities/packages are already captured (`uipath_library_*`,
  `uipath_doc_get_activity`, optional `query_uipath_docs` fallback).
- If either is missing, stop and ask to run/re-run `/uiplan-spec` or `/uiplan-plan`.
- If discovery/surface/template details are missing, stop and ask to rerun
  `/uiplan-ground` and `/uiplan-plan` before `/uiplan-tasks`.

## Task authoring contract

Every story-level task block must include tests before implementation and then
implementation tasks with explicit feasibility details.

Every story-level block must also include:

- a one-sentence explanation (`Why this exists`);
- at least one Mermaid workflow/task map for that story;
- explicit evidence expectations (command output paths/log artifacts).

### Mandatory task fields

Each **non-[P]** implementation or paradigm-specific task must include:

1. **Project** name (Studio process, agent package, or app) tied to an artifact path.
2. **Workflow / sequence / node** (`.xaml` entry, `.cs` workflow, LangGraph node, or CLI step name).
3. exact artifact path in backticks (for example `Workflows/ParseInvoice.xaml`,
   `projects/ZipEmail.Dispatcher/Main.xaml`, `main.py`, `bindings/dev.json`);
4. concrete UiPath construct (activity tag after `uipath_doc_get_activity`, SDK call, CLI verb, queue/asset/binding key);
5. grounding citation (`[skill:...]`, `[agent:...]`, `[library:...]`, `[askai:...]`,
   or explicit `uipath_library_search` / `uipath_library_lookup` / `query_uipath_docs`);
6. **Verification**: exact command (`uv run pytest ...`, `uipcli test run ...`, `uipcli package analyze --resultPath ...`, `uipath run ...`) and pass/fail expectation.
7. **Runtime evidence** artifact path (JUnit/pytest output, analyzer JSON, `.nupkg`, robot/job log excerpt).

Each **Tests** subsection task must cite a real test command (`pytest`, `uipcli test run`, `uipath run`, etc.) plus the test file path in backticks.

### Paradigm detail expectations

Tasks must reflect actual build targets for the declared paradigm:

- modern-rpa / coded-automation: `project.json`, `.xaml`/`.cs`, `uipcli` commands.
- coded-agent: `pyproject.toml`, graph/framework descriptor, `uipath` + `pytest`.
- solution: `solution.uipx`, `projects/`, `bindings/*.json`, `uipcli solution` commands.
- maestro-flow: `.flow` / `.bpmn` with Studio Web validation + sync steps.
- coded-app: `app.config.json`, `action-schema.json`, `src/`, `uip codedapp`.
- api-workflow / case / library / tests: matching descriptor files and CLI verbs.

## Visuals contract (mandatory)

Generated `tasks.md` must include all of these diagrams (Pro Standard Mermaid;
`classDef` + `linkStyle` only, no `%%{init}%%`):

- Top-level: `Project topology map`, `Capability routing map`,
  `Story execution map`.
- Per user story: `Story flow`, `Workflow interaction` (sequence),
  `Data / queue contract`, and one mini-topology diagram per workflow file.
- Phase 5: `Build, Verify, and Handoff` flow with explicit
  `Diagnose / safe fix / rerun` failure loop and the
  `Developer <-> Solution Engineer` handoff.

Reject `tasks.md` whose stories are missing any of the per-story diagrams.

## Stack policy enforcement

- Modern UiPath Studio + activity-first. **No Legacy / Windows-Legacy /
  VB.Net / Classic / `uipath-rpa-legacy`.**
- Refuse to emit a `.cs` workflow task line unless `plan.md`'s
  `## Coded Surface Justification` has a corresponding non-empty row.
- Prefer UiPath activities (resolved via `uipath_doc_get_activity`).

## Capability routing on every task

Every implementation task carries one or more of `[skill:...]`,
`[agent:...]`, `[subagent:...]`, `[library:...]`, `[askai:...]`. The Phase 5
loop carries `[skill:uipath-platform]`, `[skill:uipath-test]`, and
`[skill:uipath-diagnostics]` plus `[subagent:shell]` (and
`[subagent:browser-use]` when UI smoke is in scope).

## AskAI / Library ladder during execution

When the executor hits a knowledge gap during a task: `uipath_library_search` /
`uipath_library_lookup` -> `uipath_doc_get_activity` -> `query_uipath_docs` ->
specialist skill -> ask user. Record attempted steps next to any
`[NEEDS CLARIFICATION]`.

## Custom HITL default

For any HITL surface in scope, route through `[skill:uipath-custom-hitl]`
(Action Center External Tasks + HITL_Application Adaptive Cards / Slack). Do
**not** route HITL through UiPath Flow.

## Hard rules

- Forbid placeholders (`TBD`, `TODO`, `implement later`, `FIXME`, `NEEDS CLARIFICATION`).
- Keep `Phase 5: Build, Verify, and Handoff` with the Dev <-> SE loop.
- Build phase must include restore -> analyze -> test -> pack (or paradigm equivalent).
- Include explicit deploy gate text: personal workspace default, Production approval-required.
- Do not start source edits from this command; this output is input to `/uiplan-implement`.

## Do / Don't

**Do**:

- Render per-workflow + per-activity + per-code-module tasks pulled from
  `plan.md` inventories.
- Embed all visuals from the visuals contract above.
- Tag every task with skill / agent / subagent / MCP-tool routing.

**Don't**:

- Emit thin one-liners or generic "implement workflow" tasks.
- Drop visuals because the story is "small".
- Route HITL through UiPath Flow.
- Emit `.cs` workflow tasks without `## Coded Surface Justification`.

## Deliverable quality bar

`tasks.md` should be executable without guessing: a reviewer should be able to
validate feasibility of each task against UiPath capabilities, chosen CLI, and
project structure before implementation starts.

Reject checklist-only walls of text. A non-trivial `tasks.md` must be visual and
explanatory enough that a reviewer can understand the workflow and task purpose
before reading individual checklist lines.
