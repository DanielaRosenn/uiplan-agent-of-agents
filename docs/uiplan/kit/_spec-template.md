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

High-level boundaries for this feature (replace labels with real components).

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#E2E8F0','primaryTextColor':'#0F172A','primaryBorderColor':'#94A3B8','lineColor':'#94A3B8','secondaryColor':'#F1F5F9','tertiaryColor':'#F8FAFC','background':'#FFFFFF','clusterBkg':'#F8FAFC','clusterBorder':'#CBD5E1','titleColor':'#0F172A','edgeLabelBackground':'#FFFFFF','fontFamily':'Inter, ui-sans-serif, system-ui'}}}%%
flowchart TB
  subgraph Entry["Entry"]
    Trigger([Trigger / API]):::start
  end
  subgraph Core["Core"]
    App[Application layer]:::service
    Domain[Domain logic]:::process
  end
  subgraph External["External"]
    Partner[Partner system]:::external
  end
  subgraph Persistence["Data"]
    Db[(Primary store)]:::data
  end
  Trigger --> App
  App --> Domain
  Domain --> Partner
  Domain --> Db

  classDef start    fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef data     fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef external fill:#FAFAFA,stroke:#94A3B8,color:#334155,stroke-width:1.25px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1,2 stroke:#3B82F6,stroke-width:2px
  linkStyle 3 stroke:#10B981,stroke-width:2px
```

## Primary interaction (sequence)

Who talks to whom for the main scenario (replace actors and messages).

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#E2E8F0','primaryTextColor':'#0F172A','primaryBorderColor':'#94A3B8','lineColor':'#94A3B8','secondaryColor':'#F1F5F9','tertiaryColor':'#F8FAFC','background':'#FFFFFF','clusterBkg':'#F8FAFC','clusterBorder':'#CBD5E1','titleColor':'#0F172A','edgeLabelBackground':'#FFFFFF','fontFamily':'Inter, ui-sans-serif, system-ui'}}}%%
sequenceDiagram
  autonumber
  actor User as User / operator
  participant App as Application
  participant Ext as External system
  User->>App: Primary action
  App->>Ext: Integration call
  Ext-->>App: Response
  App-->>User: Outcome

  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef external fill:#FAFAFA,stroke:#94A3B8,color:#334155,stroke-width:1.25px
  class User human
  class App service
  class Ext external
```

## Success Criteria

### Measurable Outcomes

- **SC-001**: {{SC_001}}

## Assumptions

- {{ASSUMPTION_1}}
