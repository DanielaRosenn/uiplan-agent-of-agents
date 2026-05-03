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

**Evidence contracts** (see `docs/uiplan/ACTIVITY_AND_RUNTIME_EVIDENCE.md`):
- Activity evidence: every non-trivial activity must include package, version, required
  scope, inputs/outputs, and default XAML from `uip rpa get-default-activity-xaml` or
  Studio scaffold.
- Resource provisioning: every queue/asset/folder/connection must include provisioning
  command, verification command, evidence path, and secret boundary; use
  `[skill:uipath-platform]` for resource tasks.
- Local validation: every build/pack task must include `uip rpa get-errors`, `uip rpa build`,
  and `uipcli package analyze` evidence.
- Tenant evidence: every deploy/smoke task must include target folder, package version,
  job ID, final state, logs, queue/asset proof, OR a structured blocker JSON.
- UAT/test evidence: every production-bound story must include test artifacts, execution
  commands, results, and AC mapping.

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

### Named template copy/read/customize contract

When `spec.md` or `plan.md` names a concrete repo or Studio project template,
tasks must require a physical copy/export of that template into the target
project folder before customization. A citation, hand-written placeholder, or
"shape-compatible" scaffold does not satisfy the template requirement.

After copy/export, tasks must require the executor to read/inspect the copied
template's real workflows, config files, arguments, variables, dependencies, and
extension points before changing it. The generated control flow must be
preserved unless the accepted plan records an approved equivalent. Business
logic must then be customized inside the copied shell, and verification must
prove the customized shell, not merely the copied baseline.

For mailbox dispatcher work, the task must copy or export
`scaffold/template/dispatcher` into the target dispatcher folder and verify the
copied inventory includes `Data/`, `Framework/`, `Logical/`, `Templates/`,
`Main.xaml`, `Process.xaml`, and the queue push workflow. Follow-on mailbox,
queue, idempotency, and logging tasks must modify that copied template rather
than replacing it with standalone workflows.

For AnalyzerRunner / Long Running Workflow work, the task must copy/export or
scaffold the accepted Long Running Workflow template, read the copied wait/resume
structure, and customize queue item handling, coded-agent invocation, response
mapping, status transitions, and correlation-aware logs inside that shell.

For HumanReview / HITL work, the task must copy/export or scaffold the accepted
HITL template/canvas, read the copied review workflow/schema structure, and
customize review inputs, outcomes, timeout/escalation behavior, return path, and
downstream queue/process update inside that shell.

Named templates are host shells, not finished business processes. Tasks must
separate:

1. template copy/export and inventory verification;
2. copied-template inspection (workflows, config, arguments, variables,
   dependencies, extension points);
3. business-specific customization inside that copied shell (`Data/Config.json`,
   `Process.xaml`, `Logical/*`, queue payload mapping, connector boundary,
   idempotency/cursor logic, wait/resume behavior, review schema, status
   transitions, and log markers as applicable);
4. evidence proving the customized shell runs the business process safely.

Do not allow a named-template story to close after only copying the template.

## Visuals contract (mandatory)

Generated `tasks.md` must include all of these diagrams (Pro Standard Mermaid;
`classDef` + `linkStyle` only, no `%%{init}%%`):

- Top-level: `Project topology map`, `Capability routing map`,
  `Story execution map`.
- Per user story: `Story flow`, `Workflow interaction` (sequence),
  `Data / queue contract`, and one workflow diagram per workflow file.
- Per workflow file: the diagram must represent the **target internal step
  flow** (entry, major branches, external/system interactions, and terminal
  outcomes), not just a placeholder topology box.
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

## HITL route source

For any HITL surface in scope, follow the route selected in accepted `spec.md`
and `plan.md`; do not fall back to a different HITL canvas during task
generation. The HITL route is still subject to the named-template lifecycle:
copy/export or scaffold the chosen HITL template, read the copied template,
customize it in place, and verify completed/cancelled/timeout behavior.

- If accepted `spec.md` / `plan.md` explicitly choose UiPath Flow as HITL
  canvas, route HITL tasks through `[skill:uipath-maestro-flow]` and
  `[skill:uipath-human-in-the-loop]`, and cite the override near the top of
  `tasks.md`.
- If no route is selected, keep a planning correction open rather than inventing
  a HITL canvas in `tasks.md`. The task sheet must name whether the host is RPA
  Long Running Workflow, UiPath Flow, coded agent escalation, or another
  accepted template.

## Hard rules

- Forbid placeholders (`TBD`, `TODO`, `implement later`, `FIXME`, `NEEDS CLARIFICATION`).
- Forbid marking placeholder/scaffold-only runtime nodes complete. If Flow/RPA/app
  tasks cannot wire a real callable resource because the installed CLI or tenant
  registry does not expose it, require command evidence, a named remediation
  task, and the closest executable smoke (`uip flow debug`, `uipath invoke`,
  analyzer/job logs, or equivalent).
- For `*Invoke*Agent*Boundary*.xaml` tasks, require `Run Job` with explicit
  business argument mapping and non-empty typed `Input`/`Output` binding when
  the process contract exposes typed bundles.
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
- Ignore an explicit Flow HITL override from accepted spec/plan.
- Emit `.cs` workflow tasks without `## Coded Surface Justification`.

## Deliverable quality bar

`tasks.md` should be executable without guessing: a reviewer should be able to
validate feasibility of each task against UiPath capabilities, chosen CLI, and
project structure before implementation starts.

Reject checklist-only walls of text. A non-trivial `tasks.md` must be visual and
explanatory enough that a reviewer can understand the workflow and task purpose
before reading individual checklist lines.
