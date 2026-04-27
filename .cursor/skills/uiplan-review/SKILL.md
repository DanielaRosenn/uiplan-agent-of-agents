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
- `## Task detail contract` (from the UiPlan template) must be satisfied: **Feature build surface**, **Project**, **Workflow/sequence/node**, backtick **artifact paths**, **Activities/SDKs** only after `uipath_doc_get_activity` documents the concrete activity (no unresolved activity-tag placeholders), **AskAI/library** lookups, **Verification** commands, and **Runtime evidence** paths.
- `tasks.md` should include a **Project-specific contract** for non-trivial work: repo root, descriptors, project directories, bindings, queues/assets/connections, schedules/triggers, package versions, and local verification commands.
- For RPA/Studio or Solution plans with `.xaml` projects, `tasks.md` must include a **Studio
  template decision matrix** before implementation: each project path, selected starter template or
  scaffold source, workflow type, why it matches the use case, generated structure to preserve, and
  `uip rpa create-project` / Studio evidence. If the right template is not knowable, tasks must
  include a discovery/question item rather than silently hand-scaffolding.
- **No half-tasks:** warn when one bullet mixes unrelated concerns without a clear split, or when **RPA/XAML is in scope** but tasks allow **log-only** completion without an explicit **scaffold-only** + named production-activity follow-up (see template **Executable task split**). **`[HANDOFF:…]`** is for secrets/deploy/OAuth/robot smoke — not for skipping `.xaml` when the paradigm requires it.
- Each **non-[P]** implementation or `### Paradigm-specific tasks` line must include:
  - artifact path in backticks,
  - feature build surface (RPA/Studio, Maestro/Flow, coded app/action, coded agent, platform/config, or combination),
  - workflow hint (`.xaml` / `projects/` / graph / `Main.xaml` — stricter for Solution/RPA vs coded-agent),
  - concrete UiPath construct (activity, SDK call, CLI verb, or platform resource),
  - feasibility grounding (`[skill:]`, `[agent:]`, `[library:]`, `[askai:]`,
    or explicit `uipath_library_search` / `uipath_library_lookup` / `query_uipath_docs` /
    `uipath_doc_get_activity`),
  - lines mentioning queues/assets/bindings/folders must also name `uipath_library_search` or `uipath_library_lookup` (or documented `query_uipath_docs` fallback),
  - verification command plus evidence expectation.
- **Tests** subsection: every checklist line must include an explicit test runner command (`pytest`, `uipcli test run`, `uipath run`, etc.).
- Phase 5 (`Build, Verify, and Handoff`) must exist and include analyzer/test/pack gates plus
  **smoke run** and **robot/job log assertions** (correlation id, phase markers, terminal status), and name evidence artifacts (JUnit/pytest, analyzer `--resultPath` JSON, `.nupkg`).
- Phase 5 must also include a **failure diagnosis/fix loop** for analyzer, solution, Studio,
  CLI, and agent-test failures. Review must reject task bundles that only say "stop on analyzer
  errors" or "blocked by tenant policy" without requiring parsed evidence, docs/tooling lookup,
  source/schema inspection, one safe local fix attempt when available, and rerun evidence.
- Blocker wording must require these evidence fields before an issue can be declared blocked:
  command, working directory, exit code, result path, parsed rule/error, docs/tool consulted,
  source/config inspected, attempted local fix or why none is safe, rerun result, and blocker class
  (tenant-only, human UI-only, missing credentials, generated descriptor required, unsupported
  local tooling, or unsafe action).
- Tasks mentioning `ST-USG-034`, Automation Hub, tenant policy, or "validates except" must require
  analyzer JSON parsing, UiPath docs/library lookup, Studio/project-setting inspection, a local
  project metadata fix attempt when safe, and rerun evidence.
- Tasks mentioning `solution.uipx` must require descriptor/schema validation and provenance:
  generated by Studio/Automation Cloud versus placeholder/manual descriptor. They must distinguish
  project-level restore/analyze failures from Solution definition/resource-builder failures.
- RPA-style tasks must require **LogMessage** (or equivalent), **correlation ids**, and
  `uipath_doc_get_activity` / activity tags before implementation work.
- RPA/Studio tasks that mention Graph, Slack, queue, asset, or Integration Service must name
  Studio/default-activity evidence (`uip rpa create-project --studio-dir ...`,
  Studio-generated XAML, `uip rpa get-default-activity-xaml`, or package-local activity XAML)
  plus package/activity/property mapping. Broad wording such as "Graph + queue activities"
  is not build-ready.
- RPA/Studio tasks must not treat a generic manually-written `Main.xaml` as complete when a
  Dispatcher, Performer/queue worker, Long Running Workflow/HITL, Flowchart, or State Machine
  template is the correct build shape. Review should flag missing template remediation or missing
  question/discovery work.
- Agent-backed tasks that mention "agent", "Invoke Agent", "LangGraph", or "LlamaIndex"
  must name the agent descriptor (`langgraph.json` / `llama_index.json`), graph entry point,
  host invocation artifact, request/response schema, and local run/test command.
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
3. **`Clarifications`** (readability layer, not a severity bucket)
   - After `uipath_plan_review`, read `clarifications` (structured) and/or `clarifications_text` (numbered groups with bullets).
   - Present groups in this order when present: **Mailboxes and routing**, **Execution triggers**, **Zip integration**, **Vendor data**, **Human review**, **Audit and retention**, **Security and links**, **SLA and escalation**, **SME review**, **Other open items**.
   - Under each group, list one bullet per marker, formatted as: ``- `[NEEDS CLARIFICATION: topic]` <clear question ending in ?>`` (or `[SME REVIEW]` equivalent).
   - If `clarifications.open_count` is greater than zero and `ok` is true, tell the user to answer these questions (and update `spec.md` / `plan.md` / `tasks.md`) before Production-bound implementation; follow `next_action` verbatim.
4. `Pass summary` by stage (`spec`, `plan`, `tasks`, `cross`)
5. `Next action` (exact fix/re-run command from tool output)
