# Feature Specification: Sales Approval Process

## Business process flow

Manual process showing how approvals happen today:

```mermaid
flowchart LR
  Start[/Quote request/]:::external --> Actor1[Sales Rep]:::human
  Actor1 -->|Email PDF| Actor2[Approval Manager]:::human
  Actor2 -->|Meeting| Actor3[Finance]:::human
  Actor3 -->|Manual entry| End[/Decision recorded/]:::external

  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef external fill:#FAFAFA,stroke:#94A3B8,color:#334155,stroke-width:1.25px
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

Pain points:
- Email handoffs cause 2-day delays
- No audit trail for decisions
- Manual entry errors require rework

## Solution architecture

Automated solution replacing the manual process:

```mermaid
flowchart TB
  subgraph Intake["Intake"]
    Entry[/HTTP POST/]:::external --> Dispatcher[Dispatcher.Main]:::service
    Dispatcher --> Queue[(Queue: ApprovalItems)]:::data
  end
  subgraph Processing["Processing"]
    Queue --> Worker[Performer.Worker]:::service
    Worker --> Decision{Amount > $10k}:::decision
    Decision -->|Yes| Human[Action Center]:::human
    Decision -->|No| System[/Salesforce/]:::external
  end
  subgraph Evidence["Evidence"]
    Worker --> Audit[(Audit logs)]:::data
    Human --> Audit
    System --> Audit
  end

  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef data fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef decision fill:#FFFBEB,stroke:#F59E0B,color:#92400E,stroke-width:1.5px
  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef external fill:#FAFAFA,stroke:#94A3B8,color:#334155,stroke-width:1.25px
```

## Requirements

- FR-001: System MUST validate quote amount against $10k threshold
- FR-002: System MUST route high-value quotes to Action Center
- FR-003: System MUST log all decisions with timestamp
