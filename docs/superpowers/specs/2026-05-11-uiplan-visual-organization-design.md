# UiPlan Visual Organization Design

## Context

Current UiPlan visuals are crowded across all flow surfaces (`AS-IS`, `TO-BE`,
workflow, phase, kanban). The target is a clean, planning-first experience for
UiPath projects where ownership, sequence, and handoffs are readable without
manual rearrangement.

## Goals

- Eliminate node overlap in default views.
- Reduce connector crossings and visual noise.
- Make `AS-IS` and `TO-BE` mentally distinct at a glance.
- Make ownership obvious (who does what, in which phase).
- Keep overview simple and reveal detail progressively.
- Keep all flow views semantically consistent.

## Out of Scope

- No change to business semantics or task generation logic.
- No rebuild of underlying project graph schema in this phase.
- No major redesign of non-UiPlan canvases.

## Recommended Approach

Adopt a layered hybrid visualization model:

- **Rows = phases** (Discovery, Design, Build, Validate, Deploy, etc.).
- **Columns = actors/systems** (Business user, Robot, Human approver, External
  system, Orchestrator).
- **Default = executive overview** with milestone nodes and major handoffs.
- **Adaptive expansion** for selected phase/actor/handoff.

This balances clarity and completeness while preventing dense "all-at-once"
graphs.

## Alternative Approaches Considered

### A. Split concern views with linked navigator

- Separate phase view, actor view, and timeline with synchronized selection.
- **Trade-off:** high clarity per concern, but extra tab switching and context
  loss.

### B. Auto-layout only on current single views

- Improve spacing/routing without changing information architecture.
- **Trade-off:** reduces collisions but does not fully solve ownership and
  `AS-IS` vs `TO-BE` comprehension.

## Information Architecture

Each flow surface follows the same hierarchy:

1. **Context header**
   - Canvas title, mode badge (`AS-IS` or `TO-BE`), active scope chips.
2. **Primary map**
   - Milestones and key handoffs only.
3. **Focused expansion panel**
   - Detail for selected phase, actor, or edge.
4. **Trace rail**
   - Current position and dependency path.

This creates a stable mental model: overview first, focused detail second.

## Visual Layout Contracts

### Grid contract

- Lock nodes to phase-row and actor-column intersections.
- Disable free placement in default planning mode.

### Routing contract

- Use orthogonal connectors only.
- Reserve explicit handoff corridors between lanes.
- Bundle parallel edges and label once.

### Density contract

- Cap primary nodes per viewport (target: 12-18).
- Collapse excess detail into clusters.
- Expand only the active scope cluster.

### Spacing contract

- Enforce minimum horizontal and vertical node spacing tokens.
- Keep whitespace gutters between phase rows.

### Semantics contract

- Preserve shape and color meanings across all views.
- `AS-IS`: muted/manual emphasis, visible pain points.
- `TO-BE`: automation emphasis, SLA target cues.

## Interaction Model

### Default state

- Open in executive density with hybrid matrix active.
- Show major path and top-level dependencies only.

### Progressive disclosure

- Selecting a phase expands only that phase row.
- Selecting an actor isolates ownership path.
- Selecting a handoff opens structured details (owner, SLA, inputs/outputs,
  failure mode).

### Focus tools

- Scope chips: phase, actor, system, critical path, exceptions.
- One-click reset to uncluttered overview.

### Delta mode

- Add `AS-IS vs TO-BE` diff overlay:
  - removed manual step,
  - automated replacement,
  - SLA shift markers.

## View-Specific Behavior

### AS-IS

- Prioritize manual process lanes, queue delays, rework loops, and current pain
  points.

### TO-BE

- Prioritize orchestration path, automation responsibilities, exception routes,
  and expected outcomes.

### Workflow

- Show only selected-scope detailed execution graph.
- Group by template/subflow boundary.

### Phase

- Show macro phase sequencing with gate status badges.

### Kanban

- Keep execution tracking, but preserve 1:1 node identity with visual graph.

## Implementation Waves

### Wave 1: Foundation contracts

- Introduce lane/grid/routing/density contracts.
- Apply first to `AS-IS` and `TO-BE` canvases.
- **Gate:** no overlap in default overview on representative bundles.

### Wave 2: Adaptive behavior

- Implement focus chips, scope expansion, trace rail, and reset behavior.
- **Gate:** isolate phase or actor in at most two user actions.

### Wave 3: Cross-view consistency

- Align identities and semantics across workflow/phase/kanban.
- **Gate:** selecting same logical node stays coherent in every view.

### Wave 4: Hardening

- Improve long-label behavior, routing edge cases, and large-flow performance.
- **Gate:** readability preserved for complex plans without manual layout.

## Error Handling and Fallbacks

- If phase extraction is missing, render an explicit "unstructured flow" mode
  with suggested remediation.
- If actor classification is incomplete, place nodes in `Unassigned` column and
  flag in details panel.
- If graph density exceeds threshold, auto-switch to executive mode and show an
  expansion prompt.

## Validation Strategy

- Golden-layout snapshots for each view mode.
- Interaction checks for:
  - phase/actor focus,
  - reset,
  - diff overlay,
  - selection coherence across views.
- Stress fixtures for large bundles and long labels.
- Manual UX walkthrough against three target scenarios:
  - small plan,
  - medium cross-team plan,
  - high-complexity enterprise plan.

## Definition of Done

- No node overlap in default `AS-IS` and `TO-BE`.
- Controlled connector routing with minimal crossings.
- Immediate visual distinction between current and target states.
- Ownership clarity by phase and actor.
- Progressive disclosure active and consistent.
- Cross-view semantics aligned for planning confidence.

## Risks and Mitigations

- **Risk:** over-constrained layout can feel rigid.  
  **Mitigation:** keep optional detail expansion and flexible side-panel depth.
- **Risk:** diff overlay becomes noisy on large plans.  
  **Mitigation:** limit to changed milestones by default; offer “show all.”
- **Risk:** metadata gaps reduce ownership clarity.  
  **Mitigation:** explicit `Unassigned` handling with surfaced remediation.

## Execution Authority

This design is approved as the execution baseline for end-to-end visual
organization improvements across UiPlan flow surfaces.
