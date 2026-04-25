# UiPlan diagram patterns (Pro Standard)

Copy one of the blocks below into `spec.md`, `plan.md`, or `tasks.md`, then **replace labels only**. Full rules: [`.cursor/skills/mermaid-diagram-builder/SKILL.md`](../../.cursor/skills/mermaid-diagram-builder/SKILL.md).

## When to use which

| Pattern | Use for |
| --- | --- |
| **Flowchart TB** | Layered architecture, scope boundaries, gate pipelines |
| **Sequence** | Actor vs system vs HITL message flow |
| **State** | Plan lifecycle (draft -> review -> accepted) |

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
