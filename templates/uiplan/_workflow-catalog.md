# UiPlan Workflow Catalog

Curated reference of workflow templates available to the Solution Engineer when
filling `plan.md` `## Workflow Catalog` and `tasks.md` per-workflow tasks.

Each entry includes:

- **Diagram** (Pro Standard Mermaid using `classDef` / `linkStyle`).
- **When to use** / **When not to use**.
- **Required activities / nodes** (resolve names via `uipath_doc_get_activity`).
- **CLI verbs** for build/verify.
- **Skills, subagents, and MCP tools** to route through.

---

## Dispatcher (RPA, Sequence)

Polling intake that enqueues work items.

```mermaid
flowchart LR
  Trigger([Schedule / mailbox poll]) --> Read[Read input]
  Read --> Validate{Valid?}
  Validate -- yes --> Enqueue[(Add Queue Item)]
  Validate -- no --> Reject[Log + reject]
  classDef start fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef proc fill:#F1F5F9,stroke:#64748B,color:#0F172A
  classDef data fill:#ECFEFF,stroke:#0891B2,color:#164E63
  class Trigger start
  class Enqueue data
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

- **When to use**: scheduled or event-triggered intake; producer side of a
  Dispatcher/Performer split.
- **When not to use**: long-running per-item processing; use Performer or LRW.
- **Required activities**: `UiPath.Mail.Activities.GetIMAPMailMessages` (or
  connector-specific intake), `UiPath.Core.Activities.AddQueueItem`,
  `UiPath.Core.Activities.LogMessage` (correlationId).
- **CLI**: `uipcli package restore | analyze | pack`.
- **Skills**: `[skill:uipath-rpa]`, `[skill:uipath-platform]`. **MCP**:
  `uipath_doc_get_activity`, `uipath_library_search`.

---

## Performer / Queue Worker (RPA, Flowchart)

Per-item processor.

```mermaid
flowchart TD
  Get[Get Queue Item] --> Process[Process item]
  Process --> Out{Outcome?}
  Out -- success --> Set[Set Transaction Status: Successful]
  Out -- business rule --> Biz[Set Status: Business]
  Out -- error --> App[Set Status: Application]
  classDef proc fill:#F1F5F9,stroke:#64748B,color:#0F172A
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

- **When to use**: deterministic per-item processing.
- **When not to use**: human waits crossing job boundaries (use LRW).
- **Required activities**: `GetTransactionItem`, `SetTransactionStatus`.
- **Skills**: `[skill:uipath-rpa]`. **MCP**: `uipath_doc_get_activity`.

---

## Long Running Workflow (RPA, persisted)

Orchestrator-persisted workflow that suspends across human or external events.

```mermaid
flowchart TB
  Start([Job start]) --> Work[Pre-suspend work]
  Work --> Wait[Wait For Form / External Task]
  Wait --> Resume[Resumed branch]
  Resume --> Done([Complete])
  classDef start fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef proc fill:#F1F5F9,stroke:#64748B,color:#0F172A
  class Start,Done start
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

- **When to use**: process truly waits for human or external system.
- **When not to use**: synchronous deterministic work — use Sequence/Flowchart.
- **Required activities**: `WaitForForm`, `WaitForExternalTaskAndResume`,
  `CreateExternalTask`.
- **Skills**: `[skill:uipath-rpa]`, `[skill:uipath-custom-hitl]`.

---

## Custom HITL (Action Center External Tasks + Slack Adaptive Cards)

The org-standard HITL: External Tasks combined with the
[`cato-networks-IT/HITL_Application`](https://github.com/cato-networks-IT/HITL_Application)
(Adaptive Cards + Slack approval).

```mermaid
sequenceDiagram
  autonumber
  participant LRW as Long Running Workflow
  participant AC as Action Center (External Task)
  participant HITLApp as HITL_Application (Adaptive Cards + Slack)
  actor Reviewer
  LRW->>AC: Create External Task (payload + schema)
  AC->>HITLApp: emit task event
  HITLApp->>Reviewer: Slack message (Adaptive Card)
  Reviewer-->>HITLApp: approve / reject + comment
  HITLApp->>AC: complete External Task with outcome
  AC-->>LRW: Wait For External Task And Resume returns
  LRW->>LRW: branch on outcome
```

- **When to use**: any human approval / data-enrichment / write-back gate where
  the org wants Slack-based UX with audit trail.
- **When not to use**: Action Center forms only (use plain LRW + WaitForForm).
- **Do not use UiPath Flow** as the HITL canvas; UiPath Flow is the visual
  orchestration canvas, not the HITL surface here.
- **Required activities**: `CreateExternalTask`, `WaitForExternalTaskAndResume`,
  HITL_Application webhook config (Slack channel, card schema, callback URL).
- **CLI**: `uipcli package analyze | pack`; HITL_Application deployed
  separately.
- **Skills**: `[skill:uipath-custom-hitl]`, `[skill:uipath-rpa]`.
- **MCP**: `uipath_doc_get_activity` (External Task activities),
  `uipath_library_search` (`Action Center External Tasks`).

---

## LangGraph Coded Agent

Stateful agent with named graph + nodes.

```mermaid
flowchart LR
  Entry[graph entry] --> N1[node: classify]
  N1 --> N2[node: lookup_vendor]
  N2 --> Out[response]
  classDef proc fill:#F1F5F9,stroke:#64748B,color:#0F172A
  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

- **When to use**: stateful reasoning, branching, tool-calling.
- **When not to use**: pure document retrieval (use LlamaIndex).
- **Required artifacts**: `langgraph.json`, `main.py:graph`, request/response
  schema. **Model**: UiPath LLM Gateway via `uipath_langchain.chat.UiPathChat`.
- **CLI**: `uipath run`, `uv run pytest`, `uipath pack | publish`.
- **Skills**: `[skill:uipath-agents]`.

---

## LlamaIndex Coded Agent

Document-heavy retrieval / index-backed agent.

- **When to use**: retrieval over a corpus.
- **When not to use**: stateful tool-calling — use LangGraph.
- **Required artifacts**: `llama_index.json`, indexer + query entrypoint.

---

## Maestro / BPMN Flow

Studio Web BPMN flow (`.bpmn` / `.flow`).

- **When to use**: cross-system process orchestration with explicit BPMN events.
- **When not to use**: simple worker loops — use Sequence/Flowchart.
- **Skills**: `[skill:uipath-maestro-flow]`.

---

## Coded App / Coded Action App

TypeScript-backed app surfaces.

- **Required artifacts**: `app.config.json`, `action-schema.json`, `src/`.
- **CLI**: `uip codedapp build | test | deploy`.
- **Skills**: `[skill:uipath-coded-apps]`.

---

## API Workflow

`api-workflow.json` for synchronous API-style workflows.

- **CLI**: `uipcli package` verbs.
- **Skills**: `[skill:uipath-rpa]`.

---

## Email Intake (connector)

UiPath.Mail.Activities or Integration Service Email connector.

- **When to use**: mailbox polling for Dispatcher.
- **Required activities**: `GetIMAPMailMessages` /
  `UiPath.Email.Activities.Office365.GetMailMessages`.

---

## Queues / Buckets / Data Fabric

Platform-level data planes.

- **Queues**: `AddQueueItem`, `GetTransactionItem`, `SetTransactionStatus`.
- **Buckets**: `UiPath.Storage.Activities` for blob I/O.
- **Data Fabric**: `uip df` for entity/record CRUD;
  `[skill:uipath-data-fabric]`.
