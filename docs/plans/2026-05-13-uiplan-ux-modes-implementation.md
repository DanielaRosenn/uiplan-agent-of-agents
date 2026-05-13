---
slug: uiplan-ux-modes-implementation
title: UiPlan UX Modes and Skills Hub Implementation
date: 2026-05-13
status: draft
owner: codex
project_type: mixed
linked_pdd: ""
supersedes: null
accepted_at: null
accepted_by: null
rejection_reason: null
published_at: null
---

# UiPlan UX Modes and Skills Hub Implementation

> For agentic workers: implement task-by-task; use checkboxes below.

**Goal:** Implement the 4-mode IA (Orient, Decide, Execute, Verify), L0-L3 progressive disclosure, and dynamic Skills Hub in UiPlan Studio.

**Architecture:** Refactor `UiplanCanvas.tsx` to use the 4 canonical modes instead of ad-hoc views. The header will permanently display 4 landing metrics. The `ContextKnowledgePanel` will be upgraded into a mode-aware Skills & Integrations Hub. CSS fixes for overflow and truncation will be applied.

## Architecture diagram

```mermaid
flowchart TD
  Start([User Opens Plan]):::start --> Header[Header: 4 Metrics + 4 Modes]:::process
  Header --> Mode{Active Mode?}:::decision
  
  Mode -- Orient --> OrientView[AS-IS/TO-BE + Narrative Delta]:::service
  Mode -- Decide --> DecideView[Decisions & Risks Panel]:::service
  Mode -- Execute --> ExecuteView[Kanban + Dependency Path]:::service
  Mode -- Verify --> VerifyView[Traceability + Readiness]:::service
  
  OrientView --> HubL0[Skills Hub: Solution Topology]:::data
  ExecuteView --> HubL2[Skills Hub: Prescriptive Skills & Assets]:::data
  
  HubL0 --> EndOk(((Done))):::endOk
  HubL2 --> EndOk
  DecideView --> EndOk
  VerifyView --> EndOk

  classDef start fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef decision fill:#FFFBEB,stroke:#F59E0B,color:#92400E,stroke-width:1.5px
  classDef data fill:#F8FAFC,stroke:#94A3B8,color:#334155,stroke-width:1.25px
  classDef endOk fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
```

## File plan

| Path | Responsibility |
|------|------------------|
| `studio/web/src/components/UiplanCanvas.tsx` | Mode state, header metrics, view routing, Skills Hub logic, CSS fixes |
| `studio/web/src/components/OrientView.tsx` | (New) Executive summary, AS-IS/TO-BE diagrams, narrative delta |
| `studio/web/src/components/DecideView.tsx` | (New) Decisions, assumptions, risks inspector |
| `studio/web/src/components/VerifyView.tsx` | (New) Traceability map, readiness gate scores |

## Bite-sized tasks

- [ ] Update `UiplanCanvas.tsx` state to use `orient`, `decide`, `execute`, `verify` modes.
- [ ] Refactor header in `UiplanCanvas.tsx` to show Phase, Blocker Count, Next Action, Approval State.
- [ ] Create `OrientView` component (Executive Summary + Narrative Delta).
- [ ] Create `DecideView` component.
- [ ] Create `VerifyView` component.
- [ ] Upgrade `ContextKnowledgePanel` to be mode-aware (Skills & Integrations Hub).
- [ ] Implement L0-L3 drill-down logic in `UiplanCanvas.tsx`.
- [ ] Apply CSS fix: `overflowX: auto` for `docFlowRail`.
- [ ] Apply CSS fix: `textOverflow: ellipsis` for `ContextItem` labels.
- [ ] Run linter and tests.
- [ ] Commit with clear message.

## Verification

```bash
pnpm --dir studio/web test
pnpm --dir studio/web lint
pnpm --dir studio/web build
```

## Rollback

Revert the commits touching `studio/web/src/components/UiplanCanvas.tsx` and the new view components.
