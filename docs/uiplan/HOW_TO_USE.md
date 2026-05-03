# How to use UiPlan

This file is the **canonical procedural reference** for UiPlan: slash commands, CLI
(`uipath-claude plan uiplan …`), MCP tool names, folder layout, and lifecycle. Other
docs (for example [README.md](README.md), repo-level [USER_GUIDE.md](../USER_GUIDE.md))
should link here instead of copying command matrices.

## Canonical paths

- **Kit:** `templates/uiplan/` at repo root (MCP and `generate-docs` resolve here).
- **Runtime:** `tools/uiplan/` for local CLI entry points and scaffold/adaptor support.
- **Cursor skills:** `.cursor/skills/uiplan*/SKILL.md` for slash command behavior.
- **MCP tools:** `framework/mcp_server/tools/plan_uiplan*.py`.
- **Pytest (UiPlan):** `framework/tests/uiplan/`. Example: `uv run pytest framework/tests/uiplan/ -q`.
- **Task authoring:** [TASK_AUTHORING.md](TASK_AUTHORING.md) for workflow design,
  capability routing, examples, and the implementation loop.
- **Activity and runtime evidence:** [ACTIVITY_AND_RUNTIME_EVIDENCE.md](ACTIVITY_AND_RUNTIME_EVIDENCE.md)
  for the canonical contract on activity grounding, Orchestrator resource
  provisioning, local Studio validation, tenant runtime proof, and UAT/test evidence.

## Default flow (recommended)

Use this as the primary path unless you explicitly need legacy single-file plans:

1. `ground` -> 2) `spec` -> 3) `plan` -> 4) `tasks` -> 5) `review` -> 6) `accept` -> 7) `implement`

Equivalent surfaces:

- Cursor: `/uiplan-ground` -> `/uiplan-spec` -> `/uiplan-plan` -> `/uiplan-tasks` -> `/uiplan-review` -> `/uiplan-implement`
- CLI: `uipath-claude plan uiplan ground|spec|plan|tasks|review ...`
- MCP: `uipath_plan_ground`, `uipath_plan_spec_new`, `uipath_plan_plan_new`, `uipath_plan_tasks_new`, `uipath_plan_review`, `uipath_plan_accept`

Legacy single-file planning (`uipath_plan_new`, `uipath_plan_refine`, `uipath_plan_diff`) is still supported but non-default for UiPlan folders.

## Decision table

| I want to… | Use |
| --- | --- |
| Chat-native flow with grounding and review | MCP `uipath_plan_ground`, `uipath_plan_spec_new`, `uipath_plan_plan_new`, `uipath_plan_tasks_new`, `uipath_plan_review` (or `uipath_plan_uiplan_new` for the bundled path). |
| A file-first bundle from templates with local validation | From repo root: `uv run python -m tools.uiplan generate-docs <slug>` (optional `--out`, `--kit`, `--strict`, `--paradigm`). |
| Slash commands in Cursor | Separate skill commands: `/uiplan-full`, `/uiplan-ground`, `/uiplan-spec`, `/uiplan-plan`, `/uiplan-tasks`, `/uiplan-review`, and `/uiplan-implement`. |
| CLI parity with chat | `uipath-claude plan uiplan …` (see [USER_GUIDE.md](../USER_GUIDE.md)). |

## Paths (folder convention)

- **Drafts (default):** `.cursor/plans/<slug>/` with `spec.md`, `plan.md`, `tasks.md`, `.meta.yaml` (`plan_kind: uiplan`). Draft trees are gitignored like other `.cursor/plans` work.
- **Published:** `docs/plans/<slug>/` after `uipath_plan_accept` + `uipath_plan_publish`.
- **Templates (kit):** [`templates/uiplan/`](../../templates/uiplan/) at the repo root.

## Slug and lifecycle rules

UiPlan has two names that are easy to confuse:

- **Folder slug**: the draft folder under `.cursor/plans/`, often date-prefixed
  like `.cursor/plans/2026-04-27-my-feature/`.
- **Metadata slug**: `.meta.yaml` field `slug`, used by review/accept/publish
  tools as the stable logical plan id.

When in doubt, read `.meta.yaml` and pass the metadata slug to MCP/CLI review
commands. The status flow is:

1. **Draft**: generated or edited under `.cursor/plans/<folder>/`.
2. **Review**: run `uipath_plan_review` or `/uiplan-review <slug>` until no
   error-severity findings remain.
3. **Accept**: use `uipath_plan_accept` or
   `uipath-claude plan uiplan accept <slug>` after human approval.
4. **Implement**: use `/uiplan-implement <slug>`; it re-runs review, checks
   `.meta.yaml` status, and executes from `tasks.md`.
5. **Publish**: use `uipath_plan_publish` or
   `uipath-claude plan uiplan publish <slug>` when the accepted bundle should be
   copied to `docs/plans/<slug>/`.

Never publish by manually copying files to `docs/plans/`, and never treat a draft
as implementation-approved only because it exists on disk.

## Lessons now codified for future builds

These are permanent guardrails from recent build retrospectives and are required
in new UiPlan bundles:

- **Named-template lifecycle**: when a UiPlan names a concrete repo or Studio
  template, tasks must require `copy/export -> read/inspect -> preserve ->
  customize in place -> verify`. The executor must inspect the copied
  template's workflows, config, arguments, variables, dependencies, and extension
  points before changing it. A copied template is only a host shell for the
  business process; it is not completion evidence by itself.
- **Dispatcher-template fidelity**: if mailbox intake enqueues work, tasks must
  physically copy or export the dispatcher template project from
  `scaffold/template/dispatcher` (or a named Studio template export) into the
  target dispatcher folder before customization. Naming the source in prose is
  not enough. The copied project must preserve dispatcher structure
  (`Data/`, `Framework/`, `Logical/`, `Templates/`, `Main.xaml`,
  `Process.xaml`, queue push workflow), not be replaced with a generic manual
  workflow. The dispatcher template is only the host shell for the actual
  business process: the UiPlan must also require business-specific config,
  connector intake, queue payload mapping, idempotency/cursor behavior, logging,
  and smoke evidence inside that copied shell.
- **Long-running and HITL templates are host shells too**: AnalyzerRunner,
  performer, and human-review projects that use Long Running Workflow or HITL
  templates must copy/export or scaffold those templates, read the copied
  project, preserve generated wait/resume/review control flow, and customize the
  specific queue, coded-agent invocation, review schema, outcomes, timeout,
  return path, and status-transition logic in place.
- **Template provenance is mandatory**: when `spec.md` names a project template
  or starter pattern, `plan.md` must carry that template into `## Project
  Inventory`, `## Workflow Catalog`, and `## Workflow diagram + activity
  conformance matrix`. Templates exist to preserve runtime shape, not just file
  names.
- **Real connector intake evidence**: intake stories must prove real mailbox
  read behavior (safe sample is fine); stub payloads or fabricated message IDs
  are not valid completion evidence.
- **Per-workflow visual contract**: each in-scope `.xaml`, `.flow`, graph, and
  DMN surface needs its own internal-step diagram and activity checklist row.
- **Visual-first spec standard**: `spec.md` must include or require the full
  visual set: business process flow, solution architecture, runtime sequence,
  decision tree, workflow/artifact inventory, and evidence coverage map. Use
  these visuals to expose handoffs and build proof, not as decoration.
- **Studio-visible observability**: workflow phases and correlation IDs must be
  visible in runtime logs, and log assertions must be included in verification
  evidence.
- **Resource/deploy realism**: local pack success is not enough; tasks must
  explicitly handle resource/binding provisioning and record tenant/runtime
  evidence or an explicit blocker class.

## Human approval gate

Do **not** treat `generate-docs` output as approved scope by default.

1. Read the three files for real grounding text (replace `_…_` placeholders).
2. Confirm `spec.md` includes **Development Handoff**, `plan.md` includes
   **Development execution contract**, and `tasks.md` includes
   **Build, Verify, and Handoff**.
3. Run `uipath_plan_review` until `"ok": true` when using MCP.
4. Only then accept the bundle and start implementation with
   `/uiplan-implement <slug>`. Use `scaffold-code` only when you specifically
   need the local runtime/adaptor checks described in [SCAFFOLD_CODE.md](SCAFFOLD_CODE.md).

## Acceptance gates before implementation

Do not start build execution until all are true:

- `uipath_plan_review(stage=all)` returns no error-severity findings.
- `.meta.yaml` status is accepted (`uipath_plan_accept` was run).
- `spec.md` includes 360 visibility contract and workflow visual catalog coverage.
- `plan.md` includes artifact chain map, conformance matrix, connector/boundary/log contracts.
- `tasks.md` includes per-workflow activity checklist and executable evidence gates.
- **Activity/resource/runtime/UAT evidence contracts** are present for all
  relevant tasks (see [ACTIVITY_AND_RUNTIME_EVIDENCE.md](ACTIVITY_AND_RUNTIME_EVIDENCE.md)).
  This includes:
  - Activity doc lookups and default XAML for non-trivial activities.
  - Resource provisioning and verification for queues/assets/folders/connections.
  - Local validation evidence (`uip rpa get-errors`, `uip rpa build`, `uipcli package analyze`).
  - Tenant evidence (folder, package version, job ID, logs, queue/asset proof) or structured blocker.
  - UAT/test evidence (test artifacts, execution commands, results, AC mapping).

**Local-ready vs tenant-verified:** a task marked `local-ready` has passed
analyzer and local validation but lacks tenant deployment/smoke evidence. This
is acceptable for tasks where tenant credentials, folder permissions, or runtime
environment are unavailable at implementation time. However, such tasks must
record a structured blocker explaining the missing tenant evidence and must not
be considered complete for production sign-off. Tenant-verified tasks include
full runtime evidence (job logs, queue items, deployed package version) and are
the only acceptable completion state for production-bound stories.

## Top review failures and fastest fixes

| Review failure | Fastest fix |
| --- | --- |
| `RULE_SPEC_NO_360` | Add `## 360 Build Visibility Contract` and fill required inventory tables. |
| `RULE_SPEC_NO_WORKFLOW_VISUAL` | Add `### Workflow surface visual catalog (required)` with one `#### <artifact>` + Mermaid per in-scope workflow artifact, plus the visual set from `templates/uiplan/_diagram-patterns.md`. |
| `RULE_TASKS_NO_ACTIVITY_CHECKLIST` | Add `## Per-workflow activity checklist (required)` and include every workflow path from scope. |
| `RULE_TASKS_NO_DIAGRAM` | Add dedicated per-workflow mini-topology sections and ensure each scoped path has concrete internal-step coverage. |
| `RULE_ANY_TEMPLATE_RESIDUE` | Remove unresolved `{{...}}` template tokens from `spec.md`, `plan.md`, and `tasks.md`. |

## Numbered quickstarts

### A) Cursor skill / slash

1. Open the repo in Cursor with skills installed ([INSTALL.md](../INSTALL.md)).
2. Use `/uiplan-full <title>` for the bundled path, or staged commands:
   `/uiplan-ground`, `/uiplan-spec`, `/uiplan-plan`, `/uiplan-tasks`, and
   `/uiplan-review`.
3. After review passes and you approve the build, use `/uiplan-implement <slug>`
   to execute from `tasks.md` with the relevant skills, MCP tools, subagents,
   library/AskAI lookup, CLI commands, tests, and build gates.
4. The command wrappers point back to `.cursor/skills/uiplan/SKILL.md`, map to
   the same `uipath_plan_*` MCP tools as the CLI/chat surface, and keep
   implementation behind review plus human approval.

5. Generated docs are visual-first, but detail increases by stage. Expect:
   - `spec.md`: business-readable scope plus a concrete 360 visibility contract
     (artifact inventory, workflow-surface catalog, dependencies/connectors,
     boundary decisions, and verification expectations). It should stay readable
     beside formal PDD / SDD docs and should not copy their prose.
   - `plan.md`: story visual map, capability/ownership map, data-contract map,
     architecture, and build-loop diagrams for Solution Engineer planning.
   - `tasks.md`: execution map, story workflow/task maps, per-workflow internal
     step diagrams, activity conformance rows, and build/diagnostics loop
     evidence for LLM/executor implementation.

**Implementation validation:** `/uiplan-implement` must prove behavior with
**runtime evidence**, not only static checks. Expect a **validation evidence ledger**
in the session summary: commands run (or MCP tools used), exit codes, changed
paths, and observed pass/fail. For this repo (Python / LangGraph), that should
normally include `uv run pytest …` on affected tests or an equivalent run named
in `tasks.md`. If proof needs the Cursor UI (slash picker, reload), the agent
should ask for **human confirmation** and record it in the ledger instead of
claiming end-to-end proof without it.

### B) Local Typer CLI (`tools/uiplan`)

```bash
cd <repo-root>
uv sync
uv run python -m tools.uiplan generate-docs 2026-04-23-my-feature
# optional: --out path/to/folder --kit path/to/kit --no-strict --paradigm coded-agent
# optional runtime/adaptor support, not a replacement for /uiplan-implement:
uv run python -m tools.uiplan scaffold-code 2026-04-23-my-feature --max-loops 5
```

### C) MCP (`uipath_plan_*`)

Use when the agent session already has MCP enabled ([MCP_TOOLS.md](../MCP_TOOLS.md)). Prefer `uipath_plan_ground` first, then the `spec` / `plan` / `tasks` stages, then `uipath_plan_review`.

The grounding pack is workspace-aware: it includes the `uipath-planner` route,
the `uipath-project-discovery-agent` handoff, matched specialist skill excerpts,
local library search, and the library → AskAI lookup path when available.
`uipath_plan_plan_new` writes those inputs into `plan.md` so later task
generation, implementation, and review can cite them.

`uipath_plan_tasks_new` is the build handoff. Its final phase should drive the
accepted implementation loop. In Cursor, `/uiplan-implement <slug>` reads the
planner/specialist handoff, reviews first, asks before building, executes tasks
in order, runs restore -> analyze -> test -> pack, and stops before any
approval-required deploy.

`/uiplan-tasks` assumes discovery is done. If project discovery, template
decisions, workflow surfaces, and capability routing are missing in `plan.md`,
stop and rerun `/uiplan-plan` before task generation.

`uipath_plan_review` now includes feasibility checks for declared paradigm,
code-structure descriptors, CLI-family consistency, artifact-rich tasks, and
deploy gates.

## Document personas (BA / Dev / Solution Engineer)

Each UiPlan document targets a different audience. Keep content in the right
document; review flags persona leakage.

| Document | Audience | Owns | Avoids |
| --- | --- | --- | --- |
| `spec.md` | BA <-> Developer | Business intent, user stories, acceptance criteria, NFRs, SME items, PDD / SDD traceability, and 360 artifact/surface/dependency/logging scope contracts | Per-activity implementation micro-steps, generated placeholder text, copied PDD / SDD prose |
| `plan.md` | Developer <-> Solution Engineer | Architecture, paradigm, project topology, workflow catalog, activity inventory, bindings, capability routing, stack policy, coded-surface justification | Per-activity micro-instructions, per-line CLI recipes |
| `tasks.md` | Solution Engineer -> Developer / Executor | Artifact paths, exact CLI commands, evidence paths, `[skill:]`/`[agent:]`/`[subagent:]`/`[library:]`/`[askai:]` tags, acceptance gates, build/verify/diagnose/fix loop | Re-opening architectural decisions |

When any persona hits a knowledge gap, run the **AskAI / Library ladder**
before asking the user: `uipath_library_search` / `uipath_library_lookup` ->
`uipath_doc_get_activity` -> `query_uipath_docs` -> specialist skill or
`[agent:uipath-project-discovery-agent]` -> user.

HITL routing is a required design decision, not a hidden default. Use the route
declared in accepted `spec.md`/`plan.md`:

- Flow/Maestro-owned HITL: route through `[skill:uipath-maestro-flow]` and
  `[skill:uipath-human-in-the-loop]`.
- Action Center/native HITL: route through `[skill:uipath-human-in-the-loop]`
  with explicit task/payload/audit fields.
- Org custom HITL (for example Slack + Adaptive Card + Action Center External
  Task): route through the approved custom process and include explicit
  callback/resume, timeout/escalation, and secret/asset contracts.

Embedded email forms are compatibility-risky and must not be the only approval
path. Use email as a notification/entry point with a fallback CTA link to the
hosted approval surface.

## HITL contract block (required when HITL is in scope)

For each HITL-enabled story or phase, include:

- `channel` (Flow HITL, Action Center, Slack/custom, Coded App page);
- `approval actor` and ownership;
- `payload schema` (human-visible fields and hidden metadata);
- `decision values` and validation rules;
- `resume target`/callback contract;
- `timeout` and escalation behavior;
- `audit evidence` (task/approval id, job id, correlation id, log assertion);
- `required secrets/assets` and handoff expectations;
- `verification command/evidence` (local + tenant/runtime where available).

If any required HITL dependency is unavailable (Slack app, OAuth consent,
Action Center permissions, callback endpoint), record a blocker class and the
closest safe executable local/schema smoke evidence.

The stack policy is **Modern Studio + activity-first** (latest Studio, C#,
Windows, .NET 8); coded `.cs` workflows are allowed only when justified in
`plan.md` -> `## Coded Surface Justification`.

## Capability and persona routing

Before accepting a non-trivial bundle, inventory the active capabilities and show
how `plan.md` / `tasks.md` will use them:

- **Planning/design skills**: `uiplan-*`, `uipath-planner`,
  `uipath-solution-design`, `writing-uipath-plans`, `mermaid-diagram-builder`.
- **Product/build skills**: `uipath-rpa`, `uipath-rpa-legacy`,
  `uipath-agents`, `uipath-platform`, `uipath-coded-apps`,
  `uipath-maestro-flow`, `uipath-case-management`, `uipath-data-fabric`,
  `uipath-human-in-the-loop`, `uipath-gov-aops-policy`, `uipath-test`,
  `uipath-diagnostics`, `uipath-interact`.
- **Submodule agents**: `skills/agents/uipath-project-discovery-agent.md` when
  project context is missing or stale.
- **Diagnostic agent personas**: triage, scope-checker, hypothesis-generator,
  hypothesis-tester, and presenter for failed analyzer/test/tooling loops.
- **MCP/library/docs**: `uipath_library_search`, `uipath_library_lookup`,
  `uipath_doc_get_activity`, `uipath_doc_list_packages`, and
  `query_uipath_docs` / `[askai:...]` only when local/library coverage is not
  enough.
- **CLI/tooling**: `uipcli`, `uipath`, `uip`, and live `--help` before uncertain
  flags.
- **Focused subagents**: discovery, implementation, shell/test execution,
  browser/UI verification, documentation, and code review when work can be split
  safely.

Run non-trivial plans through BA / SA / Dev / QA lenses before acceptance:

- **BA**: process, actors, inputs/outputs, acceptance criteria, SME gaps.
- **SA**: topology, project split, workflow shape, queues/assets/connections,
  deployment gates.
- **Dev**: artifacts, activities/SDK calls, package dependencies, implementation
  order, local build loop.
- **QA/Test**: fixtures, analyze/test commands, runtime evidence, failure-path
  validation, smoke criteria.

Any unresolved design choice should name its owning persona, skill, or blocker
so `/uiplan-implement` does not make architecture decisions while coding.

## Task quality gate

Use [TASK_AUTHORING.md](TASK_AUTHORING.md) when drafting or reviewing `tasks.md`.
At minimum, each implementation task must name:

- project or package;
- workflow / sequence / graph node / CLI step;
- artifact path;
- UiPath construct;
- skill/library/docs/AskAI/CLI/subagent grounding;
- exact verification command;
- runtime evidence.

The implementation loop is always: develop -> analyze/test -> parse output ->
compare against plan/tasks -> fix safely -> rerun -> record evidence.
