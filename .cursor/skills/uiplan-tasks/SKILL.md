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

## Required preconditions

Before task generation:

- `spec.md` exists and includes `Development Handoff` with declared paradigm.
- `plan.md` exists and includes `Project Structure` and `Paradigm build loop`.
- If either is missing, stop and ask to run/re-run `/uiplan-spec` or `/uiplan-plan`.

## Task authoring contract

Every story-level task block must include tests before implementation and then
implementation tasks with explicit feasibility details.

### Mandatory task fields

Each implementation task must include:

1. exact artifact path (for example `Workflows/ParseInvoice.xaml`,
   `projects/Process.Alpha/Main.xaml`, `main.py`, `bindings/dev.json`);
2. concrete UiPath construct (activity tag, SDK call, CLI verb, queue/asset/bucket/folder);
3. grounding citation (`[skill:...]`, `[agent:...]`, `[library:...]`, `[askai:...]`,
   or explicit `uipath_library_lookup` / `query_uipath_docs`);
4. verification step (command and expected output/evidence).

### Paradigm detail expectations

Tasks must reflect actual build targets for the declared paradigm:

- modern-rpa / coded-automation: `project.json`, `.xaml`/`.cs`, `uipcli` commands.
- coded-agent: `pyproject.toml`, graph/framework descriptor, `uipath` + `pytest`.
- solution: `solution.uipx`, `projects/`, `bindings/*.json`, `uipcli solution` commands.
- maestro-flow: `.flow` / `.bpmn` with Studio Web validation + sync steps.
- coded-app: `app.config.json`, `action-schema.json`, `src/`, `uip codedapp`.
- api-workflow / case / library / tests: matching descriptor files and CLI verbs.

## Hard rules

- Forbid placeholders (`TBD`, `TODO`, `implement later`, `FIXME`, `NEEDS CLARIFICATION`).
- Keep `Phase 5: Build, Verify, and Handoff`.
- Build phase must include restore -> analyze -> test -> pack (or paradigm equivalent).
- Include explicit deploy gate text: personal workspace default, Production approval-required.
- Do not start source edits from this command; this output is input to `/uiplan-implement`.

## Deliverable quality bar

`tasks.md` should be executable without guessing: a reviewer should be able to
validate feasibility of each task against UiPath capabilities, chosen CLI, and
project structure before implementation starts.
