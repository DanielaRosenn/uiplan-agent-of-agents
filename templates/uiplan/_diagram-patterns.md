# UiPlan diagram patterns (Pro Standard)

Copy one of the blocks below into `spec.md`, `plan.md`, or `tasks.md`, then **replace labels only**. Full rules: [`.cursor/skills/mermaid-diagram-builder/SKILL.md`](../../.cursor/skills/mermaid-diagram-builder/SKILL.md).

## When to use which

| Pattern | Use for |
| --- | --- |
| **Flowchart TB** | Layered architecture, scope boundaries, gate pipelines |
| **Sequence** | Actor vs system vs HITL message flow |
| **State** | Plan lifecycle (draft -> review -> accepted) |
| **Story workflow map** | Per-story execution narrative for spec/plan/tasks |
| **Task dependency map** | Task ordering and parallel tracks in tasks |
| **Queue/data contract map** | Queue, asset, and output boundaries |
| **Capability ownership map** | BA/SA/Dev/QA + skill responsibility split |
| **Build loop** | Restore -> analyze -> test -> pack loop with retry |
| **HITL review sequence** | Review creation, human decision, closure updates |

## Required visual set by UiPlan stage

UiPlan documents are visual-first by default. Use diagrams to make hidden
handoffs, ownership, and verification gates obvious before implementation.

| Visual | Required in | Purpose |
| --- | --- | --- |
| Business process flow | `spec.md` | Stakeholder-readable story and outcome path |
| Solution architecture | `spec.md`, `plan.md` | Artifact, system, queue/asset, connector, and boundary map |
| Runtime sequence | `plan.md` | Handoff timing and input/output contracts |
| Decision tree | `spec.md`, `plan.md` | Branch ownership, human-review triggers, exception paths |
| Workflow internals | `plan.md`, `tasks.md` | One internal-step diagram per executable `.xaml`, `.flow`, `.py` graph, or `.dmn` |
| Evidence map | `tasks.md` | Command -> gate -> output path -> review/acceptance loop |

---

## 1) Flowchart TB (layered scope)

```mermaid
flowchart TB
  subgraph Experience["Experience"]
    A[Entry surface]:::service
  end
  subgraph Domain["Domain"]
    B[Core logic]:::process
  end
  subgraph Integration["Integration"]
    C[External API]:::external
  end
  A --> B
  B --> C
```

---

## 2) Sequence (actors vs system)

```mermaid
sequenceDiagram
  autonumber
  actor U as User
  participant S as System
  participant H as HITL
  U->>S: Request
  S->>H: Escalation
  H-->>S: Decision
  S-->>U: Outcome
```

---

## 3) State diagram (plan lifecycle)

```mermaid
stateDiagram-v2
  [*] --> Draft
  Draft --> Reviewing: submit
  Reviewing --> Draft: changes requested
  Reviewing --> Accepted: approved
  Accepted --> [*]
```

---

## 4) Story workflow map

Use in `spec.md`, `plan.md`, and `tasks.md` when you need one diagram per story.

```mermaid
flowchart LR
  Story["User story"] --> Tests["Tests"]
  Tests --> Build["Implementation"]
  Build --> Verify["Analyze and verify"]
  Verify --> Evidence["Runtime evidence"]
```

---

## 5) Task dependency map

Use in `tasks.md` to show execution order and parallel lanes.

```mermaid
flowchart TB
  Setup["Setup tasks"] --> Foundation["Foundational tasks"]
  Foundation --> StoryA["Story A tasks"]
  Foundation --> StoryB["Story B tasks"]
  StoryA --> BuildGate["Build and verify"]
  StoryB --> BuildGate
```

---

## 6) Queue/data contract map

Use in `spec.md` and `plan.md` to explain queue, asset, and output contracts.

```mermaid
flowchart TB
  Input["Input source"] --> Intake["Intake queue"]
  Intake --> Worker["Processor workflow"]
  Worker --> Review["Review queue"]
  Worker --> Output["Output destination"]
  Worker --> Assets["Assets and bindings"]
```

---

## 7) Capability ownership map

Use in `plan.md` and `tasks.md` to show who owns each part of implementation.

```mermaid
flowchart LR
  BA["BA"] --> Scope["Scope and acceptance"]
  SA["SA"] --> Topology["Architecture and contracts"]
  Dev["Dev"] --> Build["Implementation artifacts"]
  QA["QA"] --> Verify["Tests and evidence"]
  Skills["Specialist skills"] --> Build
```

---

## 8) Build/analyze/test/pack loop

Use in `plan.md` and `tasks.md` build/handoff sections.

```mermaid
flowchart LR
  Restore["Restore"] --> Analyze["Analyze"]
  Analyze --> Test["Test"]
  Test --> Pack["Pack"]
  Pack --> Handoff["Evidence and handoff"]
  Analyze --> Diagnose["Diagnose and safe fix"]
  Test --> Diagnose
  Diagnose --> Analyze
```

---

## 9) HITL review sequence

Use in `spec.md` and `tasks.md` where human-review logic is required.

```mermaid
sequenceDiagram
  participant Runner as AnalyzerRunner
  participant ReviewQ as ReviewQueue
  participant Flow as HITLFlow
  actor Reviewer as Reviewer
  participant Intake as IntakeQueue
  Runner->>ReviewQ: create review item
  Flow->>ReviewQ: load pending item
  Flow->>Reviewer: request decision
  Reviewer-->>Flow: approve or reject
  Flow->>ReviewQ: persist outcome
  Flow->>Intake: update linked status
```

---

## 10) Solution architecture

Use in `spec.md` and `plan.md` when a solution spans workflows, agents, flows,
queues/assets, connectors, and external systems.

```mermaid
flowchart TB
  subgraph Intake["Intake And State"]
    Entry[/Input or trigger/]:::external --> Orchestrator[Primary orchestrator]:::service
    Orchestrator --> State[(Queue or state store)]:::data
  end
  subgraph Processing["Processing And Review"]
    State --> Worker[Worker or agent host]:::service
    Worker --> Review[Human review surface]:::human
    Worker --> External[/External system/]:::external
  end
  subgraph Evidence["Configuration And Evidence"]
    Worker --> Audit[(Audit evidence)]:::data
    Review --> Audit
    Assets[(Assets and bindings)]:::data --> Orchestrator
    Assets --> Worker
  end

  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef data fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef external fill:#FAFAFA,stroke:#94A3B8,color:#334155,stroke-width:1.25px
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1,2 stroke:#3B82F6,stroke-width:2px
```

---

## 11) Decision tree

Use in `spec.md` and `plan.md` for business routing, policy ownership, and
human-review or exception boundaries.

```mermaid
flowchart TD
  subgraph IntakeChecks["Intake Checks"]
    Start([Work item ready]):::start --> Valid{Input valid?}:::decision
    Valid -->|No| Fail[Exception or clarification]:::endFail
  end
  subgraph RouteDecision["Route Decision"]
    Valid -->|Yes| Auto{Can process automatically?}:::decision
    Auto -->|Yes| Done[Apply automated outcome]:::endOk
    Auto -->|No| Human[Human review]:::human
  end
  subgraph ReviewClosure["Review Closure"]
    Human --> Final{Decision received?}:::decision
    Final -->|Yes| Closed[Apply final outcome]:::endOk
    Final -->|No| Escalate[Escalate or exception]:::endFail
  end

  classDef start fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef decision fill:#FFFBEB,stroke:#F59E0B,color:#92400E,stroke-width:1.5px
  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef endOk fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef endFail fill:#FEF2F2,stroke:#EF4444,color:#991B1B,stroke-width:2px
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,2,4 stroke:#3B82F6,stroke-width:2px
  linkStyle 3,6 stroke:#10B981,stroke-width:2px
  linkStyle 1,7 stroke:#EF4444,stroke-width:2px
```

---

## 12) Evidence coverage map

Use in `tasks.md` and review reports to prove each planned surface has a command,
gate, output path, and rerun loop.

```mermaid
flowchart LR
  subgraph Planning["Planning Contract"]
    Spec[Spec rows]:::process --> Plan[Plan phases]:::process
    Plan --> Tasks[Task cards]:::process
  end
  subgraph Verification["Verification Loop"]
    Tasks --> Build[Build surfaces]:::service
    Build --> Gates[Analyze/test gates]:::service
    Gates --> Evidence[(Evidence outputs)]:::data
    Evidence --> Review{Review passes?}:::decision
    Review -->|No| Fix[Fix and rerun]:::error
    Fix --> Tasks
  end
  Review -->|Yes| Accept[Accept]:::endOk

  classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef data fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef decision fill:#FFFBEB,stroke:#F59E0B,color:#92400E,stroke-width:1.5px
  classDef endOk fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef error fill:#FEF2F2,stroke:#EF4444,color:#991B1B,stroke-width:1.5px
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1,2,3,4 stroke:#3B82F6,stroke-width:2px
  linkStyle 6 stroke:#10B981,stroke-width:2px
  linkStyle 7,8 stroke:#EF4444,stroke-width:2px
```
