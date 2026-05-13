# Implementation Plan: Sales Approval Process

## Solution architecture

Concrete project names and bindings:

```mermaid
flowchart TB
  subgraph Intake["Intake"]
    Entry[/HTTP Trigger/]:::external --> Dispatcher[Dispatcher.Main.xaml]:::service
    Dispatcher --> Queue[(Queue: ApprovalItems)]:::data
  end
  subgraph Processing["Processing"]
    Queue --> Worker[Performer.Worker.xaml]:::service
    Worker --> Decision{Rule: Amount > 10k}:::decision
    Decision -->|Yes| Human[Action Center task]:::human
    Decision -->|No| System[/Salesforce API/]:::external
  end
  subgraph Evidence["Evidence"]
    Worker --> Audit[(Queue: AuditLog)]:::data
    Human --> Audit
    System --> Audit
    Assets[(Asset: SalesforceKey)]:::data --> Worker
  end

  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef data fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef decision fill:#FFFBEB,stroke:#F59E0B,color:#92400E,stroke-width:1.5px
  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef external fill:#FAFAFA,stroke:#94A3B8,color:#334155,stroke-width:1.25px
```

## Runtime sequence

Message handoff timing:

```mermaid
sequenceDiagram
  autonumber
  participant HTTP as HTTP Trigger
  participant Disp as Dispatcher.Main
  participant Queue as Queue: ApprovalItems
  participant Perf as Performer.Worker
  participant SF as Salesforce

  HTTP->>Disp: POST /quotes {data}
  Disp->>Queue: Add item
  Queue-->>Disp: Acknowledge
  Disp-->>HTTP: 202 Accepted

  Queue->>Perf: Get next item
  Perf->>Perf: Validate + check amount
  Perf->>SF: POST /records
  SF-->>Perf: Success
  Perf->>Queue: Mark complete
```

## Workflow catalog

All workflows with internal structure:

| Workflow | Type | Entry point | Internal steps | Dependencies |
| --- | --- | --- | --- | --- |
| `Dispatcher.Main.xaml` | Sequence | HTTP trigger | 1. Load config, 2. Validate, 3. Add to queue | Queue: ApprovalItems |
| `Performer.Worker.xaml` | Long Running | Queue trigger | 1. Get item, 2. Validate, 3. Check amount, 4. Route decision, 5. Log | Queue: ApprovalItems, Asset: SalesforceKey, Integration: Salesforce |
