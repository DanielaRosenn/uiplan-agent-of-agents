# Tasks: {{TITLE}}

> **Grounding:** {{GROUNDING_CITATIONS}}
> **Input**: `./spec.md`, `./plan.md`

**Format**: `[ID] [P?] [Story] Description` - include exact file paths in descriptions (backticks).

## Audience and Scope

This document is the **Solution Engineer -> Developer / Executor** build sheet.
Every architectural and routing decision in `spec.md` and `plan.md` is assumed
settled. Each task line is a single done gate with: artifact path, project,
workflow type, package/activity (when applicable), CLI command, evidence path,
skill / agent / subagent / MCP-tool tag, and acceptance.

- **Stack policy**: Modern UiPath Studio (latest), C# expressions, Windows,
  .NET 8. Prefer UiPath activities (`uipath_doc_get_activity`); coded
  automation (`.cs` workflow) only when justified in `plan.md`'s
  `## Coded Surface Justification`. **No Legacy / VB.Net / Classic.**
- **Capability routing**: every implementation task carries one or more of
  `[skill:...]`, `[agent:...]`, `[subagent:...]`, `[library:...]`, `[askai:...]`.
- **AskAI / Library ladder**: when uncertain, run `uipath_library_search` /
  `uipath_library_lookup` -> `uipath_doc_get_activity` -> `query_uipath_docs`
  -> specialist skill -> ask user (recording attempts).

See [`docs/uiplan/TASK_AUTHORING.md`](../../docs/uiplan/TASK_AUTHORING.md) for
the canonical workflow-design, capability-routing, handoff, and implementation
loop contract.

## Task generation preconditions (already completed)

`/uiplan-tasks` is a build-contract stage. It must consume completed discovery
and grounding, not recreate them as checklist items.

Before generating tasks:

- `spec.md` and `plan.md` are present and reviewable for this slug.
- Project discovery output exists (for example `.claude/rules/project-context.md`)
  and key project surfaces are already captured in `plan.md`.
- `plan.md` includes per-project workflows, template/scaffold decisions, source
  paths, bindings/queues/assets, and build gates.
- Activity/package lookup inputs are known through `uipath_library_search`,
  `uipath_library_lookup`, `uipath_doc_get_activity`, or equivalent grounding.

If these preconditions are not met, stop and rerun `/uiplan-ground` and/or
`/uiplan-plan` before generating `tasks.md`.

## How to read this task list

- **Tests**: failing-first checks that define expected behavior.
- **Implementation**: concrete workflow/graph/flow/app build tasks.
- **Build/Verify**: restore -> analyze -> test -> pack gates.
- **Diagnostics**: parse failures, inspect sources, apply safe fix, rerun.
- **Handoff**: approval-gated deployment and evidence summary tasks.

Every story block should include:

1. one-sentence purpose (`Why this exists`);
2. a story workflow/task map diagram;
3. tests before implementation;
4. explicit verification commands and runtime evidence paths.

## Task detail contract

Every **non-[P]** checklist task MUST embed the following (inline on the same bullet or as indented sub-bullets):

- **Feature build surface**: RPA/Studio, Maestro/Flow, coded app/action, coded agent (`LangGraph` / `LlamaIndex`), platform/config, docs-only, or a named combination.
- **Project** (Studio project / agent package / app name) or owning repo path
- **Starter template / scaffold source** for Studio projects: named template, `uip rpa create-project`
  evidence, existing `project.json` / `project.uiproj` provenance, and workflow-type rationale.
- **Workflow / sequence / node** (`.xaml` / `.cs` workflow / LangGraph node / CLI step)
- **Artifact path** in backticks (source, test, binding, or policy file)
- **UiPath construct** (queue, asset, folder, binding key, graph, process)
- **Activities / SDK calls** only after `uipath_doc_get_activity` documents the concrete package and activity (cite names in prose once resolved; avoid unresolved activity-colon placeholders in committed tasks — they fail `uipath_plan_review` activity-doc checks).
- **AskAI / library lookup**: `uipath_library_search` / `uipath_library_lookup`; `query_uipath_docs` only when library coverage is insufficient; cite durable findings as `[library:...]` or `[askai:...]`
- **Verification**: exact command (`uv run pytest ...`, `uipcli test run ...`, `uipcli package analyze ...`, `uipath run ...`) plus expected pass/fail
- **Runtime evidence**: path or artifact for proof (JUnit/pytest report, analyzer `--resultPath` JSON, `.nupkg` path, robot/job log excerpts)

**Tests before implementation** within each user story: `### Tests` precedes `### Implementation`.

### Project-specific contract

Every generated task list MUST include project facts from `spec.md` / `plan.md`, not generic placeholders:

- **Repo / solution root** and exact project directories (`projects/<Name>/`, `bindings/*.json`, `tests/`, app/agent folders).
- **Existing descriptors** (`solution.uipx`, `project.json`, `langgraph.json`, `app.config.json`, `.flow` / BPMN, `caseplan.json`) and whether they are existing, generated, or to be created.
- **Environment bindings**: queue names, asset names, connection names, schedules/triggers, folder/workspace defaults, and which values are tenant-only.
- **Studio/tooling facts** for RPA: Studio path or `uip rpa` discovery evidence, `uip rpa create-project` / default activity XAML evidence when creating or wiring Studio activities, `uipcli` restore/analyze/pack commands, and analyzer policy exceptions.
- **Studio template decisions** for each RPA project: Dispatcher/scheduled intake, Performer/queue
  worker, Long Running Workflow/HITL, Sequence/Flowchart/State Machine, or project-specific custom
  template. Each row must include why that template fits the use case and what generated structure
  must be preserved.
- **Agent facts** for agent-backed features: `langgraph.json` / `llama_index.json`, graph entry point, node list, model/gateway assumptions, local `uipath run` or pytest command, and host invocation schema.
- **Feature ownership**: for mixed Solutions, split work by feature + artifact. Do not let a single “solution” task hide RPA, Flow/Maestro, coded app, agent, and platform work.

### Executable task split (default — no “half” tasks)

Every checklist line must be **fully completable** under a single, explicit **Done when** (verification + evidence). **Do not** merge unrelated concerns into one bullet unless scope is explicit.

**Match the use case (paradigm + spec):**

- **When the use case includes Studio / RPA / `.xaml`** (e.g. `modern-rpa`, `solution` with process projects, coded-automation with workflows): tasks **must** drive **building those workflow artifacts** — not only bindings, Python, or tests. Use the tools you have: **`uipath_doc_get_activity`**, **`uipath_library_search` / `uipath_library_lookup`**, **`[skill:uipath-rpa]`**, **`uipcli package restore|analyze|pack`**, and edit **`*.xaml` / `project.json` in the repo** (Studio Desktop **or** the same files in the editor + Studio/CLI validation). Skipping production activities when they are in scope is wrong.
- **When the use case includes Maestro / Flow**, tasks must name `.flow` / BPMN artifacts, Studio Web / `uip` validation path, triggers, data mappings, and solution packaging boundary.
- **When the use case includes coded app / action app**, tasks must name `app.config.json`, `action-schema.json`, TypeScript entry points, `uip codedapp` build/test commands, and Solution packaging boundary.
- **When the use case is coded-agent / Python-only** (no XAML in the plan): the workflow surface is **graph / code** — do not invent RPA-only tasks.
- **When RPA / Flow / app invokes an agent**, tasks must include both sides: the host artifact (`Main.xaml`, `.flow`, app action) and the agent artifact (`langgraph.json` / `llama_index.json`) plus request/response schema and local execution evidence.

### Studio and agent execution contracts

For **RPA / Studio** tasks:

- New Studio projects must be scaffolded with `uip rpa create-project --studio-dir <path>` when Studio is available; if an existing project is used, record the existing `project.json` / `project.uiproj` as the scaffold source.
- Before any activity wiring, tasks must choose and record the **starter template** per Studio
  project. Examples: Dispatcher/scheduled intake template for mailbox polling and enqueue,
  Performer/queue-worker template for transaction processing, Long Running Workflow/HITL template
  for human waits, Sequence for deterministic linear work, Flowchart for branching, State Machine
  for stateful transitions. If template selection is still uncertain, stop and return to
  `/uiplan-plan`; do not emit discovery-question tasks in `tasks.md`.
- Template evidence is part of the done gate: generated files, command output, `project.json` /
  `project.uiproj`, workflow type, and preserved generated control-flow structure. A generic
  hand-written `Main.xaml` with `LogMessage` markers is scaffold-only and cannot satisfy a Studio
  project implementation task unless a follow-up template remediation task remains open.
- Non-trivial activities must come from `uipath_doc_get_activity` plus Studio/default-activity evidence (`uip rpa get-default-activity-xaml`, Studio-generated XAML, or documented package-local activity XAML). Do not hand-invent activity XML when a tool can generate it.
- Each activity-level task must name the package/activity, inputs, outputs, variables/arguments, connection/asset names, and analyze command.
- Studio validation evidence can be from Studio Desktop or CLI (`uipcli package analyze`), but source artifacts still need to be built in-repo.

For **agent-backed** tasks:

- Build the agent package when the feature needs agentic reasoning. Default to **LangGraph**; use **LlamaIndex** only when the plan explicitly calls for retrieval/document-heavy indexing.
- Tasks must name `langgraph.json` / `llama_index.json`, graph entry point, graph nodes/tools, request schema, response schema, local run command (`uipath run` or pytest), and the host invocation artifact.
- Host workflows/flows/apps must explicitly include the Invoke Agent boundary (activity, command, or API wrapper) and how the response updates queues, forms, or downstream systems.

### Failure diagnosis contract

Generated tasks must not allow analyzer, solution, Studio, CLI, or agent test failures to be
summarized as blockers until the implementer has diagnosed and rerun them. Every Phase 5
verification path must require:

- evidence capture: exact command, working directory, exit code, result file path, and relevant output excerpt;
- structured parsing: analyzer rule IDs/severity/file/activity/message, or solution command failure class;
- grounding lookup: `uipath_library_search` / `uipath_library_lookup`, `query_uipath_docs` only when needed, relevant `uipath_doc_get_activity`, live CLI `--help`, or Studio IPC commands;
- source/schema inspection: affected `project.json`, `.xaml`, `solution.uipx`, bindings, generated metadata, or tool-generated examples;
- one safe local source/config/tooling fix attempt when evidence supports one, followed by the same verification rerun;
- blocker report only after rerun, with blocker class: tenant-only, human UI-only, missing credentials, generated descriptor required, unsupported local tooling, or unsafe action.

If `solution.uipx` is present, tasks must distinguish project-level restore/analyze from
`solution.uipx` descriptor validity and provenance (generated by Studio/Automation Cloud vs
placeholder/manual descriptor). If analyzer rules such as `ST-USG-034` appear, tasks must
require analyzer JSON parsing, docs/tooling lookup, Studio/project-setting inspection, a local
metadata fix attempt when safe, and rerun evidence.

**What `[HANDOFF:…]` is for (narrow):** secrets (`[HANDOFF:Secrets]`), tenant **deploy/publish** approval (`[HANDOFF:OrchestratorDeploy]`), first-time OAuth/browser consent, **physical robot / attended smoke** (`[HANDOFF:RobotSmoke]`). **Do not** use a handoff tag to mean “we will not implement `Main.xaml`” when XAML is in scope.

- Split tasks (e.g. `T011A`, `T011B`, …) when **scope** differs (scaffold vs production activities vs agent code), not to drop XAML from the plan.
- **Scaffold-only** XAML (`LogMessage` phase markers) is allowed **only** in bullets that explicitly say **scaffold-only** and must be **replaced** by production-activity tasks **before the story is done** when RPA is in scope.

## Project topology map

```mermaid
flowchart TB
  subgraph Repo["Solution / repo"]
    Projects["Projects from plan.md"]:::process
  end
  subgraph Platform["UiPath platform"]
    Bindings["Bindings, queues, assets"]:::data
  end
  subgraph Verify["Build & verify"]
    CLI["uipcli / uipath / uip"]:::service
  end
  Projects --> Bindings
  Projects --> CLI

  classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef data    fill:#ECFEFF,stroke:#0891B2,color:#164E63,stroke-width:1.25px
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

## Capability routing map

```mermaid
flowchart LR
  Plan["plan.md routing table"]
  subgraph Skills["Specialist skills"]
    RPA["uipath-rpa"]
    Agents["uipath-agents"]
    HITL["uipath-custom-hitl"]
    Platform["uipath-platform"]
    Diag["uipath-diagnostics"]
    Test["uipath-test"]
    Mermaid["mermaid-diagram-builder"]
  end
  subgraph Tools["MCP / AskAI tools"]
    Library["uipath_library_search / lookup"]
    AskAI["query_uipath_docs"]
    ActivityDoc["uipath_doc_get_activity"]
  end
  Plan --> RPA
  Plan --> Agents
  Plan --> HITL
  Plan --> Platform
  Plan --> Diag
  Plan --> Test
  Plan --> Mermaid
  RPA --> Library
  Agents --> AskAI
  HITL --> ActivityDoc
  classDef skill fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.25px
  classDef tool  fill:#ECFEFF,stroke:#0891B2,color:#164E63,stroke-width:1.25px
  class RPA,Agents,HITL,Platform,Diag,Test,Mermaid skill
  class Library,AskAI,ActivityDoc tool
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

## Story execution map

Execution order vs. parallel tracks (replace with story IDs and real tasks).

```mermaid
flowchart TD
  subgraph Phases["Phases"]
    Setup([Setup / shared]):::start
    Foundation[Foundational work]:::process
    StoryA[User story A]:::service
    StoryB[User story B]:::service
    Polish[Polish / cross-cutting]:::process
    Done(((Done))):::endOk
  end
  Setup --> Foundation
  Foundation --> StoryA
  Foundation --> StoryB
  StoryA --> Polish
  StoryB --> Polish
  Polish --> Done

  classDef start    fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef endOk    fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1 stroke:#3B82F6,stroke-width:2px
  linkStyle 4,5 stroke:#10B981,stroke-width:2px
```

## Phase 1: Contract and Test Baseline

**Why this exists**: lock executable contracts and baseline checks before source implementation.

- [ ] T001 [P] [US1] {{T001}}
- [ ] T001A [US1] Run the compatibility preflight from [docs/ORCHESTRATOR_DEPLOYMENT.md](../../docs/ORCHESTRATOR_DEPLOYMENT.md) before scaffolding, package selection, pack, publish, or deploy; record Studio/CLI/package/target-folder evidence.

---

## Phase 2: Foundational Build Slice

**Purpose**: Core infrastructure that MUST be complete before user stories.

- [ ] T002 [US1] {{T002}}

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - {{US1_TITLE}} (Priority: P1)

**Why this exists**: {{US1_GOAL}}

### Story 1 workflow map

```mermaid
flowchart LR
  subgraph Story["US1 execution slice"]
    Tests[Tests]:::service --> Impl[Implementation]:::process
    Impl --> Verify[Analyze and verify]:::service
    Verify --> Evidence[Runtime evidence]:::endOk
  end

  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef endOk    fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

**Goal**: {{US1_GOAL}}

**Independent Test**: {{US1_IND_TEST}}

### Tests for User Story 1

- [ ] T010 [P] [US1] {{T010_TEST}}

### Implementation for User Story 1

- [ ] T011 [US1] {{T011_IMPL}} Concrete `.xaml` paths are on the **T011A–…** lines under `### Paradigm-specific tasks` (e.g. `projects/<Process>/Main.xaml` from `plan.md`). *(If that section lists `T011A`/`T011B`/…, complete those in order; each is its own done gate.)*

### Paradigm-specific tasks

{{PARADIGM_TASK_BLOCKS}}

**Checkpoint**: User Story 1 independently functional.

---

## Phase 4: Polish & Cross-Cutting

**Why this exists**: finalize cross-cutting quality, docs, and approval-gated handoff notes.

- [ ] T020 [P] {{T020}}
- [ ] T021 [P] Optional deploy handoff: if deployment is in scope, request explicit approval and follow [docs/ORCHESTRATOR_DEPLOYMENT.md](../../docs/ORCHESTRATOR_DEPLOYMENT.md); do not embed unsafe deploy commands in this task list.

---

## Phase 5: Build, Verify, and Handoff

**Purpose**: Convert the accepted plan into a verified build artifact, using a
**Developer <-> Solution Engineer** loop. The Developer implements each task; the
Solution Engineer runs `restore -> analyze -> test -> pack`, parses output, and
either signs off or sends the task back with a diagnosed failure. No task is
"complete" without runtime evidence. **Skills**: `[skill:uipath-platform]`,
`[skill:uipath-test]`, `[skill:uipath-diagnostics]`. **Subagents**:
`[subagent:shell]` for CLI execution, `[subagent:browser-use]` for UI smoke when
needed.

```mermaid
flowchart LR
  subgraph Gates["Build and verify"]
    Restore[Restore]:::process --> Analyze[Analyze]:::service
    Analyze --> Test[Test]:::service
    Test --> Pack[Pack]:::process
    Pack --> Evidence[Evidence and handoff]:::endOk
  end
  subgraph Recovery["Failure loop"]
    Analyze -->|Fail| Diagnose[Diagnose and safe fix]:::human
    Test -->|Fail| Diagnose
    Diagnose --> Analyze
  end

  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef human    fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef endOk    fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

- [ ] T030 Run the accepted-plan handoff: confirm `spec.md`, `plan.md`, and
  `tasks.md` are reviewed and accepted before source edits.
- [ ] T030A {{PLANNER_TASKS}}
- [ ] T031 Execute implementation tasks in order, using the specialist skill(s)
  cited in `plan.md` for project-specific source changes.
- [ ] T032 Run the build loop for the detected project type: restore -> analyze
  -> test -> pack. If restore/analyze/test/pack fails, run T032B before declaring the task
  blocked or complete. Capture **runtime evidence** paths:
  analyzer `--resultPath` JSON (e.g. `out/analyze.json`), `TestResults/*.trx` or pytest/JUnit XML,
  and the produced `.nupkg` path.
- [ ] T032A [P] [US1] Smoke run and log validation: run a documented local smoke (`uipcli job run`,
  `uip rpa run-file`, or tenant-safe fixture per plan) after pack; capture robot/job logs and assert
  expected substrings (correlation id, phase markers, terminal status) for the happy path and at
  least one failure path. Use `LogMessage` with correlation id in workflows per plan.
- [ ] T032B Diagnose and fix verification failures before any blocker report: parse analyzer
  `--resultPath` JSON or CLI output into rule IDs/error class, affected file/activity/descriptor,
  severity, and message; consult `uipath_library_search` / `uipath_library_lookup`,
  `query_uipath_docs` only when needed, live CLI `--help`, and Studio IPC/tool-generated examples;
  inspect the affected `project.json`, `.xaml`, `solution.uipx`, binding, or generated metadata;
  apply one safe local source/config/tooling fix when available; rerun the same command and record
  whether the original error cleared, changed, or remains. For `solution.uipx`, separate
  project-level restore/analyze failures from descriptor/schema/provenance failures. For
  analyzer rules such as `ST-USG-034`, include project metadata/Automation Hub setting inspection
  and rerun evidence before using tenant-only blocker wording.
- [ ] T033 Summarize exact verification evidence, changed files, package path
  if produced, and any approval-required deploy follow-up.
- [ ] T034 Verify deploy gate: `{{DEPLOY_GATE}}`

---

## Dependencies & Execution Order

{{DEPENDENCIES_TEXT}}
