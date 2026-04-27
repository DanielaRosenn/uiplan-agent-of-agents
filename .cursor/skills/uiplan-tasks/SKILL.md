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
- `plan.md` already includes discovery results, project surfaces, template/scaffold
  decisions, source paths, bindings/contracts, and capability routing.
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

Reject checklist-only walls of text. A non-trivial `tasks.md` must be visual and
explanatory enough that a reviewer can understand the workflow and task purpose
before reading individual checklist lines.
