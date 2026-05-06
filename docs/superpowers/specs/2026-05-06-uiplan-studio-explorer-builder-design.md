# UiPlan Studio Explorer + Builder Design

## Goal

Redefine UiPlan Studio from a planning-doc visualization surface into a combined explorer and builder workspace:

- explorer for understanding a mixed UiPath codebase and its context,
- builder for creating and editing solution structure through a typed graph,
- Copilot-assisted operations for explain, mutate, validate, and generate flows.

This design replaces a docs-first center of gravity (`spec.md`/`plan.md`/`tasks.md` rendering) with a graph-first center of gravity where planning docs are one input and one output of the system.

## Scope and Recommendation

### Options considered

1. Explorer-first only:
   - Strong repo understanding.
   - Weak build and mutation workflows.
2. Builder-first only:
   - Strong creation workflows.
   - Weak project comprehension and context traceability.
3. Combined explorer + builder:
   - Shared graph model supports understanding and construction in one surface.
   - Best fit for project goals and reference direction (`project-explorer.jsx`).

### Recommended direction

Adopt **combined explorer + builder** on a single typed graph contract, with preview-first generation and explicit apply controls.

## Product Shape

UiPlan Studio becomes a graph workspace with four coordinated areas:

- Left rail: graph outline, filters, source palette, skills/books search.
- Center canvas: interactive graph editor and explorer.
- Right rail: node/edge inspector with explainability and context.
- Bottom panel: generated proposals, diffs, findings, and stage approvals.

Node categories include:

- explorer nodes (`file`, `workflow`, `agent`, `coded_app`, `api`, `asset`, `queue`, `doc`, `skill`, `book_section`),
- builder nodes (`plan_step`, `integration`, `test_gate`, `hitl_step`, `deployment_step`, `artifact`),
- generation/review nodes (`proposal`, `finding`, `approval_stage`).

Selecting any node shows:

- plain-language concept summary,
- source snippet or workflow excerpt when available,
- citations and context lineage,
- dependencies and downstream impacts,
- available builder actions.

## System Architecture

### 1. Graph Indexer (read-only)

Purpose:

- discover and index project artifacts into explorer nodes/edges.

Responsibilities:

- scan repo and known UiPath structures,
- emit stable typed nodes and relationships,
- support incremental refresh,
- mark partial/index errors without blocking UI.

Non-goal:

- never mutate user-authored bundle or graph builder state directly.

### 2. Graph Builder Service (read-write)

Purpose:

- own user/Copilot graph mutations and persistence.

Responsibilities:

- create/update/delete/connect nodes,
- enforce node and edge contracts,
- persist layout and semantic fields,
- produce immutable snapshots for generation.

Safety:

- core nodes (`spec`, `plan`, `tasks`, `skills`, `library`, `review`) are protected from destructive mutations unless explicitly unlocked by policy.

### 3. Context Resolver

Purpose:

- attach high-quality context to graph entities.

Responsibilities:

- resolve skills context,
- resolve library/book sections and citations,
- map snippets and source ranges,
- attach strict/advisory context flags,
- report stale/unavailable context clearly.

### 4. Copilot Runtime and Actions

Purpose:

- expose graph-native conversational actions.

Core action families:

- explain: summarize node intent and relationships,
- mutate: add/edit/remove/connect nodes and attach context,
- validate: run readiness and contract checks,
- generate: trigger proposal package creation from graph snapshots.

Examples:

- "Explain this workflow and related skills."
- "Add HITL after this review gate."
- "Attach the relevant library section for this node."
- "Generate a plan proposal from the selected subgraph."

### 5. Generation and Review Service

Purpose:

- convert approved graph snapshots into proposal artifacts.

Outputs:

- `spec.md`, `plan.md`, `tasks.md` proposals,
- scaffold proposals,
- findings, citations, and readiness metadata.

Invariant:

- preview-first and apply-explicit; no silent writes, no direct deploy/publish.

## Data Model Contract

Introduce a canonical `uiplan_graph.v2` contract with:

- node schema: id, type, title, summary, metadata, layout, status, context refs,
- edge schema: id, type, source, target, label, validation flags,
- context attachments: source id, strict/advisory, citation payload, freshness,
- snapshot metadata: timestamp, source hash, author, stage, readiness summary.

Contract guarantees:

- deterministic IDs for stable diffing,
- forward migration from current diagram shape,
- compatibility with proposal generation and review pipeline.

## Interaction and Workflow

1. User loads bundle and project root.
2. Indexer populates explorer nodes and relationships.
3. User and Copilot edit graph through builder APIs.
4. Resolver enriches selected nodes with skills/books/source context.
5. User runs readiness checks and resolves blockers.
6. User generates proposal package from graph snapshot.
7. User reviews file-level diffs and findings.
8. User applies selected approved proposals.

## Error Handling and Guardrails

- Indexer failures:
  - show partial graph and source-specific warnings.
- Context failures:
  - keep node visible, mark attachment unavailable/stale.
- Copilot action failures:
  - return actionable error with retry path and target details.
- Readiness blockers:
  - prevent generation/apply for strict contract violations.
- Apply safety:
  - explicit preview and confirmation required.

## Testing Strategy

Backend:

- unit: graph typing, mutation validation, snapshot determinism, context resolution,
- integration: index -> context attach -> generation proposal flow.

Frontend:

- unit/component: canvas interactions, inspector rendering, context/citation display,
- interaction: Copilot action request/response and graph state updates.

End-to-end:

- load graph,
- run one Copilot mutation,
- attach one skill/book context,
- generate one plan proposal,
- preview/apply one approved change.

Regression fixtures:

- mixed project fixture containing workflow + agent + docs context.

## Migration from Current Direction

Current planning-doc visualization work remains useful but is repositioned:

- planning-doc extraction becomes a context source and proposal view helper,
- Mermaid rendering becomes one inspector/view mode, not the primary product axis,
- `PlanningDocsPanel` and similar components become optional detail views linked to selected graph nodes and proposal files.

## Success Criteria

- Users can understand project structure and build solution intent in one graph.
- Copilot can explain, mutate, validate, and generate from graph state.
- Skills and library context are first-class, cited, and traceable.
- Proposal workflow stays preview-first with robust file-level drill-down.
- UI supports both exploration and construction without mode switching to separate tools.
