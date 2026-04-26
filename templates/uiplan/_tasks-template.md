# Tasks: {{TITLE}}

> **Grounding:** {{GROUNDING_CITATIONS}}
> **Input**: `./spec.md`, `./plan.md`

**Format**: `[ID] [P?] [Story] Description` - include exact file paths in descriptions.

## Architecture diagram

Execution order vs. parallel tracks (replace with story IDs and real tasks).

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#E2E8F0','primaryTextColor':'#0F172A','primaryBorderColor':'#94A3B8','lineColor':'#94A3B8','secondaryColor':'#F1F5F9','tertiaryColor':'#F8FAFC','background':'#FFFFFF','clusterBkg':'#F8FAFC','clusterBorder':'#CBD5E1','titleColor':'#0F172A','edgeLabelBackground':'#FFFFFF','fontFamily':'Inter, ui-sans-serif, system-ui'}}}%%
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

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 [P] [US1] {{T001}}
- [ ] T001A [US1] Run the compatibility preflight from [docs/ORCHESTRATOR_DEPLOYMENT.md](../../docs/ORCHESTRATOR_DEPLOYMENT.md) before scaffolding, package selection, pack, publish, or deploy; record Studio/CLI/package/target-folder evidence.
- [ ] T001B [US1] Confirm paradigm `{{PARADIGM}}` and CLI family `{{CLI_FAMILY}}`; if unknown, stop and resolve project type before implementation.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before user stories.

- [ ] T002 [US1] {{T002}}
- [ ] T002A [US1] Record feasibility grounding links for this story using `uipath_library_lookup`, `uipath_skill_match`, and `query_uipath_docs` when library evidence is insufficient.

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - {{US1_TITLE}} (Priority: P1)

**Goal**: {{US1_GOAL}}

**Independent Test**: {{US1_IND_TEST}}

### Tests for User Story 1

- [ ] T010 [P] [US1] {{T010_TEST}}

### Implementation for User Story 1

- [ ] T011 [US1] {{T011_IMPL}}

### Paradigm-specific tasks

{{PARADIGM_TASK_BLOCKS}}

**Checkpoint**: User Story 1 independently functional.

---

## Phase 4: Polish & Cross-Cutting

- [ ] T020 [P] {{T020}}
- [ ] T021 [P] Optional deploy handoff: if deployment is in scope, request explicit approval and follow [docs/ORCHESTRATOR_DEPLOYMENT.md](../../docs/ORCHESTRATOR_DEPLOYMENT.md); do not embed unsafe deploy commands in this task list.

---

## Phase 5: Build, Verify, and Handoff

**Purpose**: Convert the accepted plan into a verified build artifact.

- [ ] T030 Run the accepted-plan handoff: confirm `spec.md`, `plan.md`, and
  `tasks.md` are reviewed and accepted before source edits.
- [ ] T030A {{PLANNER_TASKS}}
- [ ] T031 Execute implementation tasks in order, using the specialist skill(s)
  cited in `plan.md` for project-specific source changes.
- [ ] T032 Run the build loop for the detected project type: restore -> analyze
  -> test -> pack. Stop on analyzer errors or failing tests.
- [ ] T033 Summarize exact verification evidence, changed files, package path
  if produced, and any approval-required deploy follow-up.
- [ ] T034 Verify deploy gate: `{{DEPLOY_GATE}}`

---

## Dependencies & Execution Order

{{DEPENDENCIES_TEXT}}
