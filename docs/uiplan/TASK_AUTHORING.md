# UiPlan task authoring contract

Use this guide when writing or reviewing `tasks.md`. The goal is to make
`/uiplan-implement` follow instructions instead of inventing architecture during
coding.

## 360 tasking objective

`tasks.md` must execute the `spec.md` 360 visibility contract without gaps. For
every in-scope artifact/surface declared in spec/plan, there must be:

- an explicit task ID (or task group) that builds it;
- a verification command;
- an evidence output path;
- an internal-step workflow diagram for executable workflow artifacts.

If any artifact cannot be mapped to those four elements, stop and fix `spec.md`
or `plan.md` before continuing.

## Capability inventory first

Before tasking non-trivial work, record which project capabilities are relevant:

| Capability family | Use when |
| --- | --- |
| Planning/design skills | Route scope and architecture through `uiplan-*`, `uipath-planner`, `uipath-solution-design`, `writing-uipath-plans`, and `mermaid-diagram-builder`. |
| Product/build skills | Use the owning product skill: `uipath-rpa`, `uipath-rpa-legacy`, `uipath-agents`, `uipath-platform`, `uipath-coded-apps`, `uipath-maestro-flow`, `uipath-case-management`, `uipath-data-fabric`, `uipath-human-in-the-loop`, `uipath-gov-aops-policy`, `uipath-test`, `uipath-diagnostics`, or `uipath-interact`. |
| BA / SA / Dev / QA lenses | BA owns process scope and SME gaps; SA owns solution topology and workflow shape; Dev owns concrete artifacts, activities, and build order; QA/Test owns fixtures, evidence, and failure-path validation. |
| Submodule/project agents | Run `skills/agents/uipath-project-discovery-agent.md` when project context is missing or stale. |
| Diagnostics agents | Use triage, scope-checker, hypothesis-generator, hypothesis-tester, and presenter when analyzer/test output fails. |
| MCP/library tools | Use `uipath_library_search`, `uipath_library_lookup`, `uipath_doc_get_activity`, and `uipath_doc_list_packages` before naming activities or platform constructs. |
| AskAI/docs fallback | Use `query_uipath_docs` or `[askai:...]` only when local/library coverage is insufficient. |
| CLI surfaces | Use `uipcli`, `uipath`, or `uip`; run live `--help` before uncertain flags. |
| Focused subagents | Split discovery, implementation, testing, browser/UI checks, docs, and code review when work can proceed safely in parallel. |

Tasks that skip available capability surfaces should fail review. Do not invent
activity names, package APIs, template shapes, or CLI flags when a project skill,
library lookup, activity doc, CLI help, or subagent can resolve them.

## Discovery boundary

Discovery is a precondition to task authoring, not a task output.

- Run project discovery and architecture routing in `/uiplan-ground` and `/uiplan-plan`.
- Capture project surfaces, template decisions, bindings/contracts, and activity lookup
  context in `plan.md` before generating `tasks.md`.
- If those inputs are missing, stop and return to plan/grounding stages.

`tasks.md` should begin when the team already knows what to build.

## Persona checkpoints

Before acceptance, review a non-trivial UiPlan bundle through these lenses:

- **BA checkpoint**: business process, actors, inputs/outputs, scope, SME
  questions, acceptance criteria, and open policy decisions.
- **SA checkpoint**: solution topology, project split, workflow type per project,
  queues/assets/connections, deployment gates, and handoff boundaries.
- **Dev checkpoint**: artifact paths, package dependencies, activity/SDK/CLI
  constructs, implementation order, local build loop, and generated-file rules.
- **QA/Test checkpoint**: fixture data, test commands, analyzer outputs, runtime
  evidence, failure-path validation, and smoke criteria.

Unresolved choices must be assigned to a persona, skill, or explicit blocker.
Use `[SME REVIEW: ...]` or `[NEEDS CLARIFICATION: ...]` for human decisions.

## Workflow design before tasking

Every non-trivial UiPath task set must name the build surface and workflow shape:

- RPA / Studio: Sequence, Flowchart, State Machine, Long Running Workflow,
  Dispatcher/scheduled intake, Performer/queue worker, HITL handler, or another
  named Studio template.
- Coded agent: LangGraph / LlamaIndex descriptor, graph entry point, nodes,
  request/response schema, host invocation boundary, pytest/JUnit evidence,
  direct graph/function smoke output, and `uipath run` evidence or a documented
  platform-runtime blocker after auth/folder resolution.
- Maestro / Flow: `.flow` / BPMN artifact, trigger, data mappings, solution
  packaging boundary, and `uip flow debug` runtime evidence unless debug is
  unsafe or unavailable.
  On Windows, tasks must also verify `zip` availability for `uip flow debug`
  and keep the solution project folder, `project.uiproj` name, and `.flow`
  filename consistent with the installed CLI's expectations.
- Coded app/action: `app.config.json`, `action-schema.json`, TypeScript entry
  points, and `uip codedapp` build path.
- Platform/config: queues, assets, folders, connections, bindings, policies, and
  deployment approvals.

For each workflow shape, state why it fits the process and what evidence proves
the scaffold/template is correct: Studio-generated files, `uip rpa create-project`
output, existing `project.json` / `project.uiproj`, default activity XAML,
package-local examples, or documented library/skill guidance.

## Task bullet contract

Each non-parallel implementation task must include:

- project or package name;
- workflow / sequence / node / CLI step;
- artifact path in backticks;
- UiPath construct: activity, SDK call, queue, asset, folder, binding, graph,
  process, app, flow, or policy;
- grounding path: skill, agent, library lookup, activity doc, AskAI fallback, CLI
  help, or subagent;
- exact verification command;
- runtime evidence path or artifact.
- prerequisites (task IDs and required pre-existing artifacts);
- external dependencies (systems, permissions, policies);
- tooling/access requirements (CLI/runtime/cloud/studio access needed).

Each story block should also include:

- **Why this exists**: one sentence explaining business/workflow purpose.
- **Workflow/task diagram**: Mermaid visual showing tests, implementation,
  verification, and evidence outputs.
- **Dependencies note**: what must be done before this story starts.
- **Executor context**: compact role/scope + environment + workflow +
  guardrails + tools + pattern anchors + output style block.

## 360 traceability row (required)

Near the top of `tasks.md`, include a visibility execution matrix:

| Artifact path | Surface | Owning story | Build task IDs | Verify command | Evidence path |
| --- | --- | --- | --- | --- | --- |
| `projects/<Name>/Main.xaml` | RPA | US1 | `T011A` | `uipcli package analyze ...` | `out/analyze.json` |

This matrix is the fastest check for under-specification and should align with
`spec.md` 360 visibility rows and `plan.md` inventories.

## Deployment task minimum contract

Deployment/publish tasks must never be considered complete from local pack
output alone. For any task that includes `deploy`, `publish`, `activate`,
`upload-package`, `job run`, or `test run`, require:

- explicit target tenant/folder and non-Production boundary;
- required auth inputs (or explicit `[HANDOFF:Secrets]` if withheld);
- exact tenant mutation command(s), not just local build commands;
- activation/setup branch (`download-config` + bindings) when Solutions are used;
- runtime resource provisioning commands for required assets, queues, storage
  buckets, and connections before smoke; non-secret assets/queues should use
  `uip resource`, while credential/secret assets remain `[HANDOFF:Secrets]`
  unless values are explicitly provided;
- evidence that resources exist in the same folder path used by deployed
  processes, plus queue item evidence when queue workflows are in scope;
- runtime evidence from tenant execution (deployment id, job id, final state);
- tenant log evidence after execution (`uip or jobs logs`, `uipcli` job result,
  or equivalent), including deployed package version/dependency evidence for
  coded agents when available;
- blocker class + handoff evidence when tenant mutation is not possible.

If only local evidence exists (restore/analyze/test/pack), mark the task as
`local-ready` and keep deploy/smoke tasks open.

## Placeholder completion is forbidden

Tasks must not treat scaffold-only or placeholder artifacts as implemented
workflow behavior.

- Flow nodes labeled or behaving as `placeholder`, `would invoke`, or
  `contract only` are not complete unless a real callable resource is unavailable
  after registry/process discovery and a remediation task remains open.
- Agent-backed Flow tasks must prove both sides: the agent graph runs locally,
  the deployed entrypoint can be invoked when deployment is in scope, and the
  Flow host has `uip flow debug` evidence for the branch that consumes the
  agent-shaped response.
- RPA tasks with `LogMessage` markers only are scaffold evidence, not production
  behavior, unless the task explicitly says scaffold-only and a production
  wiring task remains open.
- Any platform limitation must include command evidence, searched resource names,
  blocker class, and the closest safe executable smoke test.

Good task:

```text
- [ ] T014 [US1] In `ZipEmail.Dispatcher`, implement the `ReadMailboxMessages`
  sequence in `projects/ZipEmail.Dispatcher/Main.xaml` using Email connector mail
  activities resolved by `uipath_doc_get_activity` and queue guidance from
  `uipath_library_search`; verify with `uipcli package analyze
  projects/ZipEmail.Dispatcher/project.json --resultPath out/dispatcher.json`
  and record analyzer JSON plus a smoke log containing `CorrelationId`.
```

Bad task:

```text
- [ ] T014 Implement the dispatcher workflow.
```

The bad task omits the project, workflow shape, artifact path, activities/docs,
verification command, and runtime evidence.

## Implementation loop

For every task, `/uiplan-implement` should run this loop:

1. Read the task, `spec.md`, and `plan.md`; confirm scope and artifact path.
2. Ground missing details through skills, library/docs, AskAI, CLI help, or
   focused subagents.
3. Develop only the current task scope.
4. Run the task verification command and the relevant analyze/test gate.
5. Parse output files and structured errors, not just console summaries.
6. Compare results against the accepted `spec.md`, `plan.md`, and `tasks.md`.
7. Apply one safe local source/config/tooling fix when evidence supports it.
8. Rerun the same gate and record whether the original issue cleared, changed,
   or remains.
9. Mark complete only with runtime evidence; otherwise leave an explicit blocker
   or handoff.

## Visual task authoring

For every non-trivial story, include three visuals:

1. **Story workflow map**: how runtime steps move across surfaces.
2. **Task dependency map**: order/parallelization of tests, implementation, and gates.
3. **Build/verify loop**: restore -> analyze -> test -> pack with diagnosis retry.

Minimal pattern:

```mermaid
flowchart LR
  Explain[Why this exists] --> Tests[Tests]
  Tests --> Build[Implementation]
  Build --> Verify[Analyze and verify]
  Verify --> Evidence[Runtime evidence]
```

Pair each diagram with a short explanatory paragraph so readers understand why
the checklist exists, not only what to run.

For large bundles, also add one phase-level dependency diagram using task IDs
only (for example `T001 -> T010 -> T020`) to make ordering and parallelization
readable at a glance.

## Actual workflow diagrams are mandatory

`tasks.md` is not only a checklist. It is the executable visual build sheet.
For each workflow artifact named in `plan.md` (`.xaml`, `.flow`, LangGraph
graph, DMN decision), include a corresponding Mermaid diagram that captures the
**target internal flow**:

- entry/input trigger;
- step-by-step processing sequence;
- branch/decision outcomes;
- external calls/resources;
- terminal outcomes/write-backs.

Reject task bundles that provide only high-level topology boxes without
workflow-level step diagrams.

## Activity conformance is mandatory

Alongside each workflow diagram, `tasks.md` must include a per-workflow activity
checklist row describing:

- the concrete required activities/nodes (`.xaml`, `.flow`, graph nodes, DMN rows);
- how those are verified (activity docs lookup, validate/analyze/test command);
- which skill/tool route owns implementation;
- where evidence is written.

For XAML surfaces, list concrete activity names (for example `Sequence`,
`Switch`, `Assign`, `If`, `Log Message`, `Try Catch`) and verify them through
`uipath_doc_get_activity` plus analyzer evidence.

## Executor context block (required)

Add this before tasks for each phase or story:

```markdown
### Executor context for <phase/story>
- **Role/scope**: what to build and what not to touch.
- **Environment**: required CLIs/runtimes/access + evidence locations.
- **Workflow**: read/explore -> implement minimal scope -> verify -> parse output -> safe fix -> rerun.
- **Guardrails**: non-negotiable constraints.
- **Tools**: skills/MCP/CLI sequence for this slice.
- **Pattern anchors**: existing files to mirror.
- **Return/evidence**: exact artifacts expected in completion output.
```

Use imperative wording for required behaviors (`always`, `never`), not soft
phrasing (`consider`, `try`).

## HITL routing override rule

Default HITL routing can remain Action Center/custom HITL, but if `spec.md` or
`plan.md` explicitly mandates UiPath Flow as the HITL canvas, `tasks.md` must:

1. Include a visible override note near the top of the document.
2. Route implementation tasks through `[skill:uipath-maestro-flow]`.
3. Keep the reasoning traceability to the spec/plan override text.

## Failure review

Do not call a failed analyzer/test/Studio/CLI run "blocked" until the failure has
been diagnosed and rerun. A blocker report must include:

- command, working directory, exit code, and result path;
- parsed rule/error and affected artifact;
- docs, skills, MCP tools, CLI help, or subagents consulted;
- source/config/schema inspected;
- local fix attempted, or why no safe local fix exists;
- rerun result;
- blocker class: tenant-only, human UI-only, missing credentials, generated
  descriptor required, unsupported local tooling, or unsafe action.

Additionally, the review/implement preflight now hard-blocks the bundle for:

- missing spec 360 contract,
- missing spec->plan->tasks artifact chain,
- missing connector/resource inventory,
- missing invocation boundaries,
- missing logging phase/correlation/assertion contract,
- stub-only XAML completion wording,
- missing per-workflow diagrams,
- leftover template tokens (`{{...}}`).

## Handoff tags

Use `[HANDOFF:...]` narrowly:

- `[HANDOFF:Secrets]` for credentials or secret values.
- `[HANDOFF:OrchestratorDeploy]` for publish/deploy approval.
- `[HANDOFF:OAuth]` for first-time browser or OAuth consent.
- `[HANDOFF:RobotSmoke]` for physical robot or attended smoke validation.

Do not use a handoff tag to skip in-scope XAML, agent, Flow, app, or platform
implementation. If the artifact is in scope, task it directly or record an
explicit blocker with evidence.

## Reviewer clarifications

Group clarification output by topic and make every item actionable:

```text
### Human review
- `[NEEDS CLARIFICATION: review channel]` Should ambiguous invoices be reviewed
  in UiPath Flow HITL, Action Center, or another approved channel?
```

Write answers back into `spec.md`, `plan.md`, or `tasks.md` before acceptance.
