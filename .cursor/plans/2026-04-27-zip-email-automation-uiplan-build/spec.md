# Feature Specification: Zip Email Automation Smart Invoice Routing

> **Grounding:** [skill:uipath-planner] [agent:uipath-project-discovery-agent] [skill:uipath-solution-design] [skill:uipath-rpa] [skill:uipath-maestro-flow] [skill:uipath-agents] [skill:uipath-platform] [skill:mermaid-diagram-builder] [skill:uiplan]

**Created**: 2026-04-27
**Status**: Draft
**Input**: User description: "Create the build-ready UiPlan specification for the Zip Email Automation Smart Invoice Routing UiPath Solution from the actual PDD, SDD, ADD, and latest user corrections. The solution uses the Email connector (not Microsoft Graph), a Dispatcher template for intake, a Long Running Workflow for the analyzer host, a LangGraph coded agent for analysis, and a UiPath Flow for the final Human-in-the-Loop stage. Start with spec only; plan, tasks, review, acceptance, and implementation remain gated by explicit approval."

_If a PDD/SDD path was supplied, a short excerpt may appear in **Source traceability** at the end of the file. The **User Scenarios** and **Requirements** sections below are the build-ready specification (not a paste of the PDD)._

## Design source priority

1. **SDD** (`sdd.md` or equivalent) is the primary source when it exists — align scope, integrations, and NFRs to it.
2. **PDD** or product brief when no SDD exists.
3. **User description** in this file when neither document exists.

Record production gaps as explicit clarification items until an SME confirms;
never invent tenant mailboxes, credentials, Zip handling mode, or other
tenant-specific values.

## User Scenarios & Testing

### User Story 1 - Intake and analysis pipeline (Priority: P1)

As a Finance operator, I want supplier emails from regional payable mailboxes
deduplicated, classified, and routed to Zip, archive, or review so junk does not
reach Zip and valid invoices follow the correct business path.

**Why this priority**: This is the core business value from the PDD: reduce junk
email reaching Zip by 90%+, prevent duplicate forwards across regional mailboxes,
and preserve an audit trail.

**Independent Test**: Run dispatcher and analyzer-host tests against fixture
mailbox/queue data. Verify `ZipEmailIntakeQueue` receives one item per new
logical message, duplicate messages are not forwarded twice, analyzer results
update the intake item, and correlation IDs appear in logs.

**Acceptance Scenarios**:

1. **Given** a new email from a monitored payable mailbox through the UiPath
   Email connector, **When** `ZipEmail.Dispatcher` runs from the Dispatcher
   template, **Then** it creates exactly one
   `ZipEmailIntakeQueue` item with source mailbox, message identity, sender,
   received time, normalized subject/body evidence reference, and correlation ID.
2. **Given** the same logical email appears in more than one regional mailbox,
   **When** `ZipEmail.Dispatcher` evaluates message identity, **Then** only one
   intake item is queued and the duplicate is audited as skipped.
3. **Given** a pending intake item, **When** `ZipEmail.AnalyzerRunner` invokes
   `ZipEmail.AnalyzerAgent`, **Then** the intake item reaches a terminal or
   waiting status: `InvoiceForwarded`, `NonInvoiceArchived`,
   `DuplicateSkipped`, `NeedsHumanReview`, `HumanReviewPending`, or `Exception`.

### User Story 2 - Human review and closure (Priority: P2)

As a Finance reviewer, I want ambiguous emails routed with enough evidence for a
fast review decision so the linked intake item and review queue stay consistent.

**Why this priority**: Ambiguous or protected documents are lower volume than
the happy path but are mandatory for compliance and operational closure.

**Independent Test**: Inject a `ZipEmailHumanReviewQueue` fixture item and verify
the UiPath Flow creates the Human-in-the-Loop review step, waits for an outcome,
updates the review item, and updates the linked intake item.

**Acceptance Scenarios**:

1. **Given** analyzer output requires human review, **When**
   `ZipEmail.AnalyzerRunner` creates a review item, **Then** the UiPath Flow
   Human-in-the-Loop stage receives a linked review item with reason code,
   evidence summary, recommended action, and correlation ID.
2. **Given** a reviewer approves a route, **When**
   the UiPath Flow completes the HITL outcome, **Then** both queue items reflect
   the final business outcome and an audit entry records the decision.
3. **Given** review times out or cannot be completed, **When** the UiPath Flow
   reaches the configured SLA, **Then** the item is escalated or marked
   exception according to the plan/task policy.

### Edge Cases

- Password-protected, image-only, broken-link, or auth-gated invoice evidence
  must route to human review rather than being guessed.
- Mixed English/Hebrew or conflicting invoice signals may require semantic
  classification by `ZipEmail.AnalyzerAgent`.
- Missing vendor or IL country-routing data must not silently forward; it must
  use deterministic fallback or human review according to the final task policy.
- Zip API credentials are not fully confirmed in the PDD; plan/tasks must keep
  secrets and deploy/publish actions as handoff/approval-required.
- The current PDD names 8 explicit regional mailboxes and says 11 total; plan
  must resolve the complete mailbox allow-list before production use.

## Requirements

### Functional Requirements

- **FR-001**: System MUST monitor configured regional payable mailboxes through
  the UiPath Email connector using persisted per-mailbox cursor/state.
- **FR-002**: System MUST deduplicate logical messages across mailboxes using a
  stable email identity from the Email connector such as `InternetMessageId`,
  sender, received time, and normalized subject/body hash.
- **FR-003**: System MUST create and update `ZipEmailIntakeQueue` items for the
  dispatcher/analyzer contract and `ZipEmailHumanReviewQueue` items for
  ambiguous cases.
- **FR-004**: System MUST implement these coordinated build surfaces:
  `ZipEmail.Dispatcher` from the Dispatcher template, `ZipEmail.AnalyzerRunner`
  as a Long Running Workflow, `ZipEmail.AnalyzerAgent` as a Python LangGraph
  coded agent, and a UiPath Flow for the final Human-in-the-Loop stage.
- **FR-005**: System MUST keep the Python/LangGraph agent as the analyzer
  engine only; it must not replace the RPA analyzer host or become a second
  queue consumer.
- **FR-006**: System MUST run deterministic checks before LLM/agent semantic
  classification and reserve agent reasoning for ambiguous cases.
- **FR-007**: System MUST preserve PII minimization: queue payloads and logs
  store metadata, evidence summaries, hashes, and references rather than full raw
  bodies or attachments unless policy changes.
- **FR-008**: System MUST require plan/tasks/review/acceptance before
  implementation and `/uiplan-implement` must execute tasks through the
  develop -> analyze/test -> parse output -> safe fix -> rerun evidence loop.

### Key Entities

- **Email intake item**: Queue item in `ZipEmailIntakeQueue` containing message
  identity, source mailbox, sender, subject/body evidence reference, status,
  analysis result, correlation ID, and optional linked review item.
- **Human review item**: Queue item in `ZipEmailHumanReviewQueue` containing
  reason code, evidence summary, recommended action, review status, reviewer
  outcome, and linked intake item ID.
- **Analyzer result**: Structured output from `ZipEmail.AnalyzerAgent` consumed
  by `ZipEmail.AnalyzerRunner` to forward, archive, skip duplicate, request
  review, or mark exception.
- **Mailbox cursor**: Per-mailbox state used by the dispatcher to avoid re-reading
  already processed messages.
- **Capability inventory**: Skills, agents, MCP/library lookups, activity docs,
  CLIs, and subagents that plan/tasks must route through before implementation.

## Architecture diagram

High-level boundaries from the SDD plus the latest user corrections.

```mermaid
flowchart TB
  subgraph Schedule["Schedules"]
    DispatchSchedule([Every 30 min: Dispatcher]):::start
    AnalyzeSchedule([After dispatcher: AnalyzerRunner]):::start
    ReviewTrigger([Queue / event: HITL Flow]):::start
  end
  subgraph RPA["RPA / Studio projects"]
    Dispatcher[ZipEmail.Dispatcher]:::process
    AnalyzerRunner[ZipEmail.AnalyzerRunner]:::process
  end
  subgraph Flow["UiPath Flow"]
    HumanReview[Human-in-the-Loop Flow]:::process
  end
  subgraph Agent["Coded agent"]
    AnalyzerAgent[ZipEmail.AnalyzerAgent]:::service
  end
  subgraph Queues["Orchestrator queues"]
    Intake[(ZipEmailIntakeQueue)]:::data
    Review[(ZipEmailHumanReviewQueue)]:::data
  end
  subgraph External["External systems"]
    Email[UiPath Email connector]:::external
    Vendor[Vendor master]:::external
    Zip[Zip mailbox / API]:::external
    ReviewChannel[Human review channel]:::external
  end
  DispatchSchedule --> Dispatcher
  Dispatcher --> Email
  Dispatcher --> Intake
  AnalyzeSchedule --> AnalyzerRunner
  Intake --> AnalyzerRunner
  AnalyzerRunner --> AnalyzerAgent
  AnalyzerAgent --> Vendor
  AnalyzerRunner --> Zip
  AnalyzerRunner --> Intake
  AnalyzerRunner --> Review
  ReviewTrigger --> HumanReview
  Review --> HumanReview
  HumanReview --> ReviewChannel
  HumanReview --> Review
  HumanReview --> Intake

  classDef start    fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef service  fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef process  fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef external fill:#FEF9C3,stroke:#CA8A04,color:#713F12,stroke-width:1.25px
  classDef data     fill:#ECFEFF,stroke:#0891B2,color:#164E63,stroke-width:1.25px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1,2,3,4,5,6,7,8,9,10,11,12 stroke:#3B82F6,stroke-width:2px
```

## Primary interaction (sequence)

Main happy-path and human-review interaction.

```mermaid
sequenceDiagram
  autonumber
  actor Scheduler as Scheduler
  participant Dispatcher as ZipEmail.Dispatcher
  participant Intake as ZipEmailIntakeQueue
  participant Runner as ZipEmail.AnalyzerRunner
  participant Agent as ZipEmail.AnalyzerAgent
  participant ReviewQ as ZipEmailHumanReviewQueue
  participant Handler as HITL UiPath Flow
  participant Zip as Zip mailbox or API
  Scheduler->>Dispatcher: start mailbox intake
  Dispatcher->>Intake: add normalized queue item
  Scheduler->>Runner: start analyzer host
  Runner->>Intake: get pending item
  Runner->>Agent: invoke graph with request schema
  Agent-->>Runner: structured classification result
  alt valid invoice
    Runner->>Zip: forward or submit invoice
    Runner->>Intake: mark InvoiceForwarded
  else needs human review
    Runner->>ReviewQ: create linked review item
    Handler->>ReviewQ: wait for reviewer outcome
    Handler->>Intake: apply final status
  end

  classDef persona fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  class Scheduler,Dispatcher,Intake,Runner,Agent,ReviewQ,Handler,Zip persona
```

## Success Criteria

### Measurable Outcomes

- **SC-001**: Junk/non-invoice email forwarded to Zip is reduced by at least 90%
  against the manual baseline, measured on agreed test or pilot data.
- **SC-002**: Duplicate logical messages across monitored mailboxes produce at
  most one Zip forward or intake-processing outcome.
- **SC-003**: Every processed item has a correlation ID and auditable status
  transition across dispatcher, analyzer host, analyzer engine, and human review
  when applicable.
- **SC-004**: The generated UiPlan bundle passes `uipath_plan_review` before
  acceptance, and implementation tasks require concrete workflow/activity/tool
  evidence before `/uiplan-implement` executes.

## Assumptions

- Source of truth is the target project design set:
  `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation/docs/design/sdd.md`,
  `pdd.md`, and `add.md`.
- The complete 11-mailbox allow-list, Zip API mode, credential scopes, review
  channel, and production folder remain human-confirmed values before deploy.
- Default implementation is Automation Cloud Solution packaging with personal or
  development workspace deployment only after explicit approval.
- This stage creates `spec.md` only. `/uiplan-plan`, `/uiplan-tasks`,
  `/uiplan-review`, acceptance, and `/uiplan-implement` require explicit
  approval in sequence.

## Source traceability

- **SDD**:
  `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation/docs/design/sdd.md`
  v1.2. Defines the base solution, two queues, schedules, and RPA host vs agent
  engine split. Latest user correction supersedes its Graph/HumanReviewHandler
  details: use Email connector and UiPath Flow for the HITL stage.
- **PDD**:
  `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation/docs/design/pdd.md`.
  Defines business problem, 90% junk-reduction objective, regional payable
  mailbox monitoring, duplicate prevention, IL routing, and audit needs.
- **ADD**:
  `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation/docs/design/add.md`.
  Defines the analyzer graph, deterministic-first agent gating, structured
  state, outputs, and human-review item creation.
- **User correction 2026-04-27**: Use the UiPath Email connector instead of
  Microsoft Graph; use the Dispatcher template for intake; use a Long Running
  Workflow for the analyzer host; use LangGraph for the agent; use UiPath Flow
  for the final Human-in-the-Loop stage.

## SME inputs (do not invent)

Until the human confirms facts, record gaps as explicit SME review or
clarification prose. Examples: mailbox allow-lists, credential scope, Zip
handling mode, audit log sink, trigger cadence, and human review channel. Do not
silently invent production values.

## Source routing & MCP contracts

- **Project discovery (blocking precondition)**: run
  `[agent:uipath-project-discovery-agent]` for the target solution repo before
  locking implementation tasks.
- **Library MCP**: `uipath_library_search` (ranked search) and `uipath_library_lookup` (book/section precision).
- **AskAI-style fallback**: `query_uipath_docs` (and `[askai:topic]` notes in tasks) when library evidence is insufficient.
- **Activity docs MCP**: `uipath_doc_get_activity` / `uipath_doc_list_packages` before naming activities or pinning package versions.
- **Specialists / subagents**: cite `[skill:...]` for build personas; split heavy work via subagents or `Task` for isolated discovery or implementation.

## Development Handoff

This section turns the accepted design into build-ready work.

- **Build entry point**: `tasks.md` after review passes and the bundle is accepted.
- **Implementation scope**:
  `C:/Users/DanielaRosenstein/cursor_projects/AgenticAI_FIN02_ZipMailboxAutomation`
  solution files, project artifacts, tests, bindings, queues/assets/connections,
  and docs named in `plan.md` / `tasks.md`.
- **Implementation paradigm**: solution
- **Target stack**: Modern UiPath stack: C# expressions, Windows target, .NET 8.
- **CLI family**: uipcli
- **Deploy gate**: Automation Cloud only; deploy to personal workspace or dev workspace first. Never deploy to Production without explicit human approval.
- **Execution command**: `/uiplan-implement zip-email-automation-uiplan-build` after `uipath_plan_review` passes and `uipath_plan_accept` records human approval. Use `scaffold-code` only for optional local runtime/adaptor checks.
- **Quality gates**: restore -> analyze -> test -> pack; add smoke run and
  robot/job log assertions for correlation ID, phase markers, and terminal
  status. Analyzer/test/tooling failures must enter the documented
  diagnose -> ground -> safe fix -> rerun loop before being called blocked.
- **Feasibility evidence**: Use `uipath_library_search` and/or `uipath_library_lookup` first, then
  `query_uipath_docs` / `[askai:...]` for uncertain UiPath APIs or CLI flags; use
  `uipath_doc_get_activity` / `uipath_doc_list_packages` before naming activities; do
  not invent activity names or SDK methods.
- **Handoff rule**: Do not start source changes until `uipath_plan_review` passes
  and the human accepts the bundle. After acceptance, execute `tasks.md` in
  order and keep implementation aligned to `plan.md`.
