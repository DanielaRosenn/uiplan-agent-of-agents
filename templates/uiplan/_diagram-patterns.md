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
