# Feature Specification: {{TITLE}}

> **Grounding:** {{GROUNDING_CITATIONS}}

**Created**: {{DATE}}
**Status**: Draft
**Input**: User description: "{{INTENT}}"

## User Scenarios & Testing

### User Story 1 - {{US1_TITLE}} (Priority: P1)

{{US1_BODY}}

**Why this priority**: {{US1_PRIORITY}}

**Independent Test**: {{US1_TEST}}

**Acceptance Scenarios**:

1. **Given** {{US1_GIVEN_1}}, **When** {{US1_WHEN_1}}, **Then** {{US1_THEN_1}}

### User Story 2 - {{US2_TITLE}} (Priority: P2)

{{US2_BODY}}

**Why this priority**: {{US2_PRIORITY}}

**Independent Test**: {{US2_TEST}}

**Acceptance Scenarios**:

1. **Given** {{US2_GIVEN_1}}, **When** {{US2_WHEN_1}}, **Then** {{US2_THEN_1}}

### Edge Cases

- {{EDGE_1}}

## Requirements

### Functional Requirements

- **FR-001**: System MUST {{FR_001}}
- **FR-002**: System MUST {{FR_002}}
- **FR-003**: Users MUST be able to {{FR_003}}

### Key Entities

- **{{ENTITY_1}}**: {{ENTITY_1_DESC}}

## Architecture diagram

High-level boundaries for this feature (replace labels with real components: Studio project, Orchestrator folder, queues, Integration Service connectors).

```mermaid
flowchart TB
  subgraph Entry["Trigger"]
    Trig([Job / queue / schedule / API]):::start
  end
  subgraph Auto["Automation"]
    Pkg[UiPath process or library]:::service
    Logic[Coded workflow or activity flow]:::process
  end
  subgraph Platform["UiPath platform"]
    Orch[Orchestrator + folders / assets / queues]:::external
  end
  subgraph Persistence["Data"]
    Store[(Queues / DB / Storage buckets / Data)]:::data
  end
  Trig --> Pkg
  Pkg --> Logic
  Logic --> Orch
  Logic --> Store

  classDef start    fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef external fill:#FEF9C3,stroke:#CA8A04,color:#713F12,stroke-width:1.25px
  classDef data     fill:#ECFEFF,stroke:#0891B2,color:#164E63,stroke-width:1.25px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1,2 stroke:#3B82F6,stroke-width:2px
```

## Primary interaction (sequence)

Who talks to whom for the main scenario (replace actors and messages).

```mermaid
sequenceDiagram
  autonumber
  actor Op as Operator / Robot
  participant WF as UiPath workflow
  participant Orch as Orchestrator
  participant Ext as External system
  Op->>WF: Start run / queue item
  WF->>Orch: Read asset / queue / folder
  WF->>Ext: Integration call
  Ext-->>WF: Response
  WF-->>Op: Final status / logs

  classDef persona fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  class Op,WF,Orch,Ext persona
```

## Success Criteria

### Measurable Outcomes

- **SC-001**: {{SC_001}}

## Assumptions

- {{ASSUMPTION_1}}

## Development Handoff

This section turns the accepted design into build-ready work.

- **Build entry point**: {{BUILD_ENTRYPOINT}}
- **Implementation scope**: {{IMPLEMENTATION_SCOPE}}
- **Execution command**: {{BUILD_COMMAND}}
- **Quality gates**: {{QUALITY_GATES}}
- **Handoff rule**: Do not start source changes until `uipath_plan_review` passes
  and the human accepts the bundle. After acceptance, execute `tasks.md` in
  order and keep implementation aligned to `plan.md`.
