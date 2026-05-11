---
slug: uiplan-visual-reorganization-execution
title: UiPlan Visual Reorganization Execution Plan
date: 2026-05-11
status: accepted
owner: codex
project_type: mixed
linked_pdd: ""
supersedes: null
accepted_at: 2026-05-11T22:37:00+03:00
accepted_by: user
rejection_reason: null
published_at: null
---

# UiPlan Visual Reorganization Execution Plan

> For agentic workers: implement task-by-task; use checkboxes below.

**Goal:** Reorganize all UiPlan flow visuals so `AS-IS`, `TO-BE`, workflow,
phase, and kanban views remain readable, non-overlapping, and ownership-clear.

**Architecture:** The execution introduces deterministic layout contracts
(phase-row + actor-column), orthogonal edge routing, and adaptive progressive
disclosure. Core behavior is centered in canvas rendering components so all
views share a consistent visual grammar while preserving each view's planning
purpose.

## Architecture diagram

```mermaid
flowchart TD
  Start([Input Bundle]):::start --> Parse[Parse phases actors tasks views]:::process
  Parse --> Layout[Apply lane grid and spacing contracts]:::service
  Layout --> Route[Route edges through handoff corridors]:::service
  Route --> Render[Render overview surfaces]:::process
  Render --> Expand{User focuses phase actor handoff?}:::decision
  Expand -- Yes --> Detail[Reveal scoped detail panel and trace rail]:::human
  Expand -- No --> Stable[Keep executive uncluttered state]:::process
  Detail --> Verify[Run visual and interaction verification]:::service
  Stable --> Verify
  Verify --> EndOk(((Readable consistent flows))):::endOk

  classDef start fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px
  classDef process fill:#F1F5F9,stroke:#64748B,color:#0F172A,stroke-width:1.25px
  classDef service fill:#EFF6FF,stroke:#3B82F6,color:#1E3A8A,stroke-width:1.25px
  classDef decision fill:#FFFBEB,stroke:#F59E0B,color:#92400E,stroke-width:1.5px
  classDef human fill:#F5F3FF,stroke:#8B5CF6,color:#5B21B6,stroke-width:1.5px
  classDef endOk fill:#ECFDF5,stroke:#10B981,color:#065F46,stroke-width:2px

  linkStyle default stroke:#94A3B8,stroke-width:1.5px
  linkStyle 0,1,2,3 stroke:#3B82F6,stroke-width:2px
  linkStyle 4 stroke:#10B981,stroke-width:2px
```

## File plan

| Path | Responsibility |
|------|------------------|
| `studio/web/src/components/UiplanCanvas.tsx` | View orchestration, tabs, shared layout and interaction state |
| `studio/web/src/components/AsIsCanvas.tsx` | `AS-IS` lane layout, ownership cues, pain-point readable rendering |
| `studio/web/src/components/ToBeCanvas.tsx` | `TO-BE` architecture layout, automation emphasis, SLA markers |
| `studio/web/src/projectGraph/types.ts` | Optional typed metadata support for phase/actor/lane/density contracts |
| `templates/uiplan/_spec-template.md` | Keep `AS-IS` anchor expectations aligned with visual contracts |
| `templates/uiplan/_plan-template.md` | Keep `TO-BE` and runtime visual contracts aligned with renderer |
| `docs/uiplan/EXPLORER.md` | Document explorer/view mapping expectations after layout changes |
| `docs/superpowers/specs/2026-05-11-uiplan-visual-organization-design.md` | Approved design baseline referenced by implementation |

## Bite-sized tasks

- [ ] Add explicit lane model (`phase`, `actor`, `depth`) for all primary nodes
- [ ] Implement deterministic slot assignment and minimum spacing guarantees
- [ ] Replace free/curved connector routing with orthogonal corridor routing
- [ ] Add overview density cap and cluster collapsing in `AS-IS`/`TO-BE`
- [ ] Add focus chips and one-click reset behavior in `UiplanCanvas`
- [ ] Add scoped expansion panel for selected phase/actor/handoff
- [ ] Add trace rail/breadcrumb state shared across views
- [ ] Add `AS-IS vs TO-BE` delta highlighting mode
- [ ] Ensure workflow/phase/kanban use same semantic IDs and styling tokens
- [ ] Add long-label handling and overflow-safe card rendering
- [ ] Add fixture-based visual regression checks for overlap and crossing limits
- [ ] Add interaction tests for focus, reset, and cross-view selection coherence
- [ ] Update UiPlan docs/templates to reflect final visual contracts
- [ ] Run verification commands
- [ ] Commit with a clear implementation message

## Verification

```bash
pnpm --dir studio/web test
pnpm --dir studio/web lint
pnpm --dir studio/web build
```

## Rollback

Revert implementation commits touching UiPlan canvas and view components, then
restore previous rendering behavior while retaining the design/spec docs for the
next iteration.
