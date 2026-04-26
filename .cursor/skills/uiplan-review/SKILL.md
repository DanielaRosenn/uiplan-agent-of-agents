---
name: uiplan-review
description: Review a UiPlan bundle for feasibility, grounding, and build readiness before acceptance or implementation.
disable-model-invocation: true
---

# UiPlan Review

Use `.cursor/skills/uiplan/SKILL.md` as the canonical contract.

Treat the user's text after `/uiplan-review` as `<slug> [all|spec|plan|tasks]`.
Run `uipath_plan_review`, defaulting to `stage=all` when omitted.

## Required review scope

Report `error` findings first, then `warn`, then `info`.

Do not accept, publish, or implement from this command unless the user
explicitly asks for the next step after seeing review output.

### Spec checks

- `spec.md` must include user stories, acceptance scenarios, FR/SC sections.
- `## Development Handoff` must include:
  - implementation paradigm (`modern-rpa`, `coded-automation`, `coded-agent`,
    `solution`, `maestro-flow`, `coded-app`, `api-workflow`, `case-management`,
    `library`, `tests`);
  - target stack and CLI family (`uipcli` / `uipath` / `uip`);
  - deploy gate (`personal workspace` default, `Production` approval-required);
  - no invented activities or SDK methods clause with `uipath_library_search` /
    `uipath_library_lookup` first, `query_uipath_docs` / AskAI fallback, and
    `uipath_doc_get_activity` when activity-level detail is needed.

### Plan checks

- `plan.md` must include:
  - `Planner Route & Specialist Handoff`;
  - explicit `Project Structure` coverage for repository artifacts;
  - `### Source Code (repository root)` with paradigm-appropriate descriptors;
  - `### Paradigm build loop` matching the declared paradigm CLI family.
- For **modern-rpa / coded-automation / solution / library / tests** paradigms, `plan.md` should
  anchor **XAML-first** orchestration, name **workflow types** (Sequence, Flowchart, State Machine,
  Long Running Workflow) per process, and document **C#** expressions unless legacy VisualBasic is
  explicit.
- **Solution** plans must call out `solution.uipx`, `projects/*`, and `bindings/` together with
  queue/status contracts across sub-projects.
- Verify structure feasibility:
  - `project.json` + `.xaml` for modern-rpa,
  - `pyproject.toml` + graph/framework descriptor for coded-agent,
  - `solution.uipx` + `bindings/` for solution,
  - and equivalent descriptors for other paradigms.

### Tasks checks

- `tasks.md` must include tests before implementation in each story slice.
- Each implementation task must include:
  - artifact path in backticks,
  - concrete UiPath construct (activity, SDK call, CLI verb, or platform resource),
  - feasibility grounding citation (`[skill:]`, `[agent:]`, `[library:]`, `[askai:]`,
    or explicit `uipath_library_search` / `uipath_library_lookup` / `query_uipath_docs` /
    `uipath_doc_get_activity`),
  - verification step.
- Phase 5 (`Build, Verify, and Handoff`) must exist and include analyzer/test/pack gates plus
  **smoke run** and **robot/job log assertions** (correlation id, phase markers, terminal status).
- RPA-style tasks must require **LogMessage** (or equivalent), **correlation ids**, and
  `uipath_doc_get_activity` / activity tags before implementation work.
- Deploy tasks must keep personal workspace default and explicit Production block.

### Grounding checks

- Confirm plan grounding includes:
  - `uipath_plan_ground` evidence,
  - project discovery evidence (`[agent:uipath-project-discovery-agent]`),
  - `uipath_skill_match` output / matched specialist skills,
  - library lookup evidence (`uipath_library_search` / `uipath_library_lookup`),
  - AskAI-style evidence (`query_uipath_docs`) when library coverage is insufficient.
- Confirm activity tags `[activity:Package:Activity]` are resolvable in activity docs.

### Stack and policy checks

- Enforce modern stack for RPA/coded automation (`C#`, Windows target, `.NET 8`).
- Reject classic/VB/Windows-Legacy unless explicitly documented in project context.
- Never permit Production deploy paths from assistant sessions.
- Solutions must remain Automation Cloud compatible.

## Output format

1. `Errors` (blocking)
2. `Warnings` (non-blocking)
3. `Pass summary` by stage (`spec`, `plan`, `tasks`, `cross`)
4. `Next action` (exact fix/re-run command)
