# UiPlan App Pre-Development Redesign Blueprint

## Status

- Phase: Pre-development only
- Implementation: blocked until this blueprint gates are accepted
- Scope: UiPlan planning app UX/IA redesign (not feature coding)

## Purpose

Refactor the app into a planning-first product that improves:

1. Process comprehension for BA and stakeholders
2. Execution clarity for Solution Engineers and Developers
3. Traceability from spec -> plan -> tasks -> evidence
4. Accessibility and usability for dense technical workflows

## Reviewer synthesis (UX + Solution Engineer + BA)

### Critical findings

1. Planning intent is diluted by map-explorer interactions.
2. Users cannot quickly answer: where am I, what is blocked, what is next.
3. Traceability and readiness semantics are not enforced as primary workflow.
4. Detail density appears before decision context.
5. Stakeholder/business narratives are not first in reading order.

### Operating model to adopt

- Primary modes:
  - `Orient` (process and scope understanding)
  - `Decide` (risks, assumptions, approvals)
  - `Execute` (task sequencing and ownership)
  - `Verify` (evidence and readiness gates)
- Progressive disclosure levels:
  - Summary
  - Structured breakdown
  - Traceability detail
  - Raw technical metadata

## Hard pre-development gates

No app development starts until all gates pass:

1. **IA Gate**
   - Mode model (`Orient/Decide/Execute/Verify`) is approved.
   - Navigation and content hierarchy are documented for BA/SE/Dev personas.

2. **Traceability Gate**
   - Required chain is defined and testable:
     `story -> architecture element -> task -> evidence`.
   - Canonical relation types are fixed.

3. **Readiness Gate**
   - Objective readiness rubric is defined (not subjective).
   - Status transitions and owner responsibilities are explicit.

4. **Accessibility Gate**
   - Keyboard flow map completed.
   - Focus behavior and target-size constraints documented.
   - Contrast and non-color state semantics documented.

5. **Governance Gate**
   - Draft/review/accepted states and approval authority are defined.
   - Change-impact and stale-artifact rules are defined.

## Pre-coding gate clauses (objective pass/fail)

### Traceability gate

PASS only if all are true:

- 100% of in-scope stories map to at least one architecture element, one task,
  and one evidence placeholder.
- 0 orphan tasks (task without parent story) and 0 orphan evidence items.
- All relation types are within the approved enum and validate with 0 errors.
- A versioned traceability export artifact is attached to gate decision records.

### Readiness gate

PASS only if all are true:

- Readiness rubric defines explicit criteria for `NotReady`, `AtRisk`, `Ready`.
- Each transition has owner role, required inputs, and blocking conditions.
- 100% of in-scope tasks have owner + readiness state.
- No `Ready` item has unresolved `Critical` or `High` blockers.

### IA/UX gate

PASS only if all are true:

- Persona scenario tests (BA/SE/Dev) run against fixed scripts.
- Success threshold: >= 90% first-attempt completion for
  "where am I / what next / what blocked" in <= 30s median.
- Failed scenarios are dispositioned as fixed, accepted risk, or out-of-scope.

### Accessibility gate

PASS only if all are true:

- Keyboard-only traversal covers critical planning actions with no traps.
- Focus visibility passes documented checklist in all primary views.
- Contrast and non-color state semantics meet WCAG 2.2 AA targets.

### Governance gate

PASS only if all are true:

- Approver matrix is explicit (`role -> authority -> backup approver`).
- Approval SLA and stale-artifact timeout are documented.
- Every gate decision records approver, timestamp, scope version, and rationale.
- Tie-break authority is explicit for approver disagreement.

## Traceability contract (normative)

### Required entities

- `Story`: id, title, owner, status, acceptance criteria ids.
- `AcceptanceCriterion`: id, story_id, statement, measurable_outcome, owner.
- `ArchitectureElement`: id, type, owner, status, source path.
- `Task`: id, story_id, owner, phase, status, readiness_state.
- `Evidence`: id, task_id, evidence_type, source_path, verified_by, verified_at.
- `Risk`: id, severity, owner, mitigation, status.
- `Assumption`: id, owner, decision_due_date, status, impact_if_false.

### Allowed relation types

- `implements` (`Task -> Story`)
- `derived_from` (`ArchitectureElement -> Story`)
- `depends_on` (`Task -> Task|ArchitectureElement`)
- `blocks` (`Risk|Assumption -> Task|Story`)
- `verifies` (`Evidence -> Task|AcceptanceCriterion`)

### Cardinality rules

- `Story -> Task`: `1..N`
- `Story -> ArchitectureElement`: `1..N`
- `Task -> Evidence`: `1..N` for Done/Ready tasks, `0..N` otherwise
- `Evidence -> AcceptanceCriterion`: `1..N`

### Blocking failures

- Any in-scope story with no task link
- Any done/ready task with no evidence link
- Any invalid relation type
- Any missing required entity id

## Readiness rubric (scored)

Score each in-scope item from 0 to 3 on:

1. Traceability completeness
2. Blocker clarity
3. Evidence sufficiency
4. Dependency integrity
5. Approval completeness

Readiness states:

- `NotReady`: any critical dimension < 2
- `AtRisk`: all dimensions >= 2 but total average < 2.6
- `Ready`: all dimensions >= 2 and total average >= 2.6 with no unresolved
  `Critical`/`High` blockers

## Governance workflow specification

### State model

- `draft -> in_review -> accepted -> published`
- Allowed rollback: `in_review -> draft` with reason
- `accepted -> in_review` only with explicit change request record

### RACI per gate

- IA gate: Accountable = UX reviewer, Approver = BA + SE
- Traceability gate: Accountable = Solution Engineer, Approver = BA
- Readiness gate: Accountable = Solution Engineer, Approver = BA + UX
- Accessibility gate: Accountable = UX reviewer, Approver = SE
- Governance gate: Accountable = BA, Approver = SE

Tie-break authority:

- process/governance dispute -> BA Accountable
- architecture/readiness dispute -> Solution Engineer Accountable
- UX/accessibility dispute -> UX reviewer Accountable

### SLA and escalation

- Review response SLA: 2 business days
- Stale approval timeout: 5 business days after artifact updates
- Escalation owner: Solution Engineer (technical), BA (process)

## Information architecture specification

### Diagram strategy (as-is / to-be)

- Adopt the current solution-map visual style as the canonical top-level flow
  pattern for planning views.
- Use this same pattern for **as-is** and **to-be** flows so comparisons are
  immediate and layout language stays consistent.
- Add drill-down levels under player lanes/roles to expose nested decisions,
  handoffs, and execution details without changing the top-level map language.
- Keep drill-downs progressive: top-level flow first, then player-level
  breakdown, then task/evidence detail.

### Canonical mode model

- `Orient`: business intent, scope boundary, process context
- `Decide`: open decisions, assumptions, risks, owners
- `Execute`: ordered tasks, blockers, dependency path, next action
- `Verify`: evidence map, gate outcomes, acceptance confidence

### Landing requirements (first 5 seconds)

Must visibly answer:

1. Current phase/mode
2. Primary blocker count
3. Next recommended action
4. Current approval state

### Transition rules

- Landing defaults to `Orient`.
- `Decide` requires visible unresolved decision list.
- `Execute` requires ordered task list with owner and readiness.
- `Verify` requires evidence completeness and gate status.

## Interaction contracts

### Left rail (intent-first)

Priority slots:

1. Search and scope selector
2. Mode-specific quick filters
3. Blockers and risks
4. Optional advanced filters

### Inspector (decision-first)

Priority slots:

1. Why this matters
2. What is blocked
3. Next action
4. Evidence and ownership
5. Advanced technical metadata (collapsed by default)

### Always-visible contract

In all primary views, users must see:

- current location
- primary blocker
- next action cue

## Multi-level drill-down specification (UX normative)

### Drill-down levels and semantics

- `L0 System`: cross-lane as-is/to-be flow with phase, blockers, and approval state.
- `L1 Lane`: role/player lane context with lane-level goals, blockers, and owned decisions.
- `L2 Work Item`: story/task/evidence cluster with explicit owner, readiness, and acceptance mapping.
- `L3 Raw Metadata`: technical payload, identifiers, and diagnostic metadata (collapsed by default).

### Edge rules and collapse/expand behavior

- Expand reveals one level at a time (`L0 -> L1 -> L2 -> L3`) and must preserve parent context.
- Collapse returns to immediate parent and must restore prior scroll, focus, and filter state.
- Cross-lane edges are always visible at `L0`; at deeper levels, only contextual edges render.
- Drill expansion must not create or mutate IDs, relation types, lifecycle states, or audit metadata.

### Side-panel behavior contract

- Side panel opens on selection and defaults to `Why this matters -> What is blocked -> Next action`.
- Side panel must always show `scope_version`, owning role, and blocker severity summary.
- Deep technical fields stay collapsed unless the user explicitly expands `Raw metadata`.
- Panel close/reopen must not reset drill depth, selected item, or active mode.

### UX acceptance criteria

PASS only if all are true:

- Users complete BA/SE/Dev scripted drill tasks at >= 90% first-attempt in <= 30s median.
- Users can navigate `L0 -> L2` and return to `L0` without losing place or context.
- Side panel preserves decision-first reading order across all four modes.
- 0 critical drill-navigation ambiguity defects and <= 2 medium with documented mitigation.

### BA/SE/Dev drill scenario matrix

| Role | Scenario objective | Required visible outcome | Pass threshold |
| --- | --- | --- | --- |
| BA | Explain business delta and immediate decision need | Plain-language delta, owner, due date, impact if delayed | <= 30s median |
| SE | Validate cross-level dependency and execution order | Parent-child chain + blocking dependency path | <= 30s median |
| Dev | Confirm implementable task and evidence contract | Task acceptance mapping + required evidence ids | <= 30s median |

## Multi-level drill-down contract (SE normative)

### ID invariants and cross-level references

- `story_id`, `architecture_element_id`, `task_id`, and `evidence_id` are globally stable across all drill levels.
- Parent-child references are immutable for accepted scope versions and versioned on approved change.
- Every `L2` item must resolve to a valid `L0` trace path: `Story -> ArchitectureElement -> Task -> Evidence`.
- Any unresolved cross-level reference is a traceability gate fail.

### Diff contract and must-not-break clauses

- All scope deltas must publish machine-readable drill diffs: added, removed, moved, retyped, relinked.
- Diff output must include reason, owner, timestamp, and impacted gate(s).
- A diff is invalid if it breaks stable IDs without an explicit migration map.
- Accepted scope versions must remain replayable with deterministic drill lineage.

### Migration and handoff checklist

- Generate drill reference manifest (`DRILLREF-001`) for level definitions, references, and panel slots.
- Generate drill ID invariant report (`DRILLID-001`) for stable IDs and cross-level integrity checks.
- Generate drill diff report (`DRILLDIFF-001`) for vN -> vN+1 scope deltas and impact classification.
- Handoff packet must link all three drill artifacts before coding is allowed.

### Drill-down readiness evidence checks

PASS only if all are true:

- 0 broken references across `L0-L3`.
- 0 unauthorized ID mutations between accepted scope versions.
- 100% of changed drill entities appear in `DRILLDIFF-001` with impact rationale.
- BA + SE sign-off confirms diff interpretation is business-readable and technically complete.

## Business narrative and interpretation criteria (BA normative)

### Narrative requirements

- Each accepted scope version includes a plain-language narrative of what changed and why.
- Narrative must map changes to business outcomes, decisions, and stakeholder impact.
- Narrative must call out no-change areas to prevent false assumptions during handoff.

### Plain-language delta interpretation criteria

PASS only if all are true:

- A non-technical reviewer can identify `what changed`, `who is impacted`, and `what action is needed now`.
- Delta narrative references drill artifact ids (`DRILLREF-001`, `DRILLID-001`, `DRILLDIFF-001`) without technical jargon dependency.
- Ambiguous terms are resolved in the domain glossary or explicitly marked as open decisions.
- BA confirms interpretation parity with SE before go/no-go is marked `pass`.

### BA-led sign-off checklist

- Confirm business intent remains intact after drill depth changes.
- Confirm decision ownership, due dates, and delay impact are explicit.
- Confirm handoff packet language is interpretable without reverse-engineering metadata.
- Confirm unresolved narrative ambiguity is logged with owner and due date.

## Progressive disclosure rules

- Default level by persona:
  - BA: Summary
  - Solution Engineer: Structured breakdown
  - Developer: Structured breakdown
- Promote to deeper levels only when:
  - risk severity is high, or
  - confidence is low, or
  - dependency conflict is unresolved, or
  - user explicitly requests advanced detail

## Accessibility compliance contract

- Target standard: WCAG 2.2 AA minimum.
- Keyboard path map must cover: mode switch, filter, select item, inspect, trace.
- Focus indicators must remain visible and unobscured in all pane states.
- Status semantics must never rely on color alone.
- Minimum interactive target size: 24x24 CSS px.
- Focus indicator: minimum 2px outline/perimeter with >= 3:1 contrast.

## Phase exit evidence checklist

Each phase exits only with:

1. artifact links
2. objective pass criteria result
3. blocker list and disposition
4. accountable + approver sign-off records
5. required drill-down artifacts (`DRILLREF-001`, `DRILLID-001`, `DRILLDIFF-001`)

No evidence, no exit.

## Test scripts and phase metrics (normative)

### Fixed persona scripts

- Script A (BA): identify process purpose, current blocker, and decision owner in <= 30s.
- Script B (SE): identify dependency path and next executable task in <= 30s.
- Script C (Dev): identify task evidence requirements and acceptance mapping in <= 30s.

Pass thresholds:

- >= 90% first-attempt completion for each script.
- median completion time <= 30s.

### Phase metrics

- Phase 1: scenario script pass rate >= 90%.
- Phase 2: 0 critical interaction ambiguity defects and <= 2 medium.
- Phase 3: 100% pass on accessibility checklist for critical flows.
- Phase 4: all pre-coding gate rows set to `pass`.

## Evidence schema template (normative)

All gate evidence artifacts must include:

- `artifact_id`
- `gate_name`
- `phase`
- `owner`
- `approved_by`
- `created_at`
- `scope_version`
- `result` (`pass` or `fail`)
- `summary`
- `linked_entities` (ids)
- `file_path`

Storage and naming:

- Path: `docs/plans/evidence/<blueprint-slug>/`
- File pattern: `<phase>-<gate>-<artifact-id>.json`
- Version marker required in artifact metadata (`v1`, `v1.1`, etc.)

## Business-facing required artifacts

Before coding, these artifacts are mandatory:

1. **Executive Readiness Snapshot**
   - business objective status
   - decision needed now
   - owner and due date
   - impact if delayed
2. **Scope and Change Impact Narrative**
   - in-scope and out-of-scope recap
   - what changed since last revision
   - downstream impact on tasks and readiness
3. **BA -> SE -> Dev handoff packet**
   - business intent summary
   - architecture mapping summary
   - task and evidence execution checklist
   - ambiguity log and resolution status
4. **Drill-down reference manifest (`DRILLREF-001`)**
   - drill levels, semantics, and edge visibility rules
   - side-panel slot contract per level
5. **Drill-down ID invariant report (`DRILLID-001`)**
   - stable ID checks across levels and scope versions
   - cross-level reference integrity validation
6. **Drill-down delta report (`DRILLDIFF-001`)**
   - plain-language + machine-readable scope deltas
   - impact classification for BA/SE/Dev

## Business KPI targets for redesign value

- Time-to-next-decision identification: <= 30s median
- Handoff interpretation defects: <= 1 medium-equivalent per cycle
- Rework caused by unclear scope/handoff: reduce by >= 30% from baseline
- Stakeholder confidence score (BA/SE/Dev review): >= 4/5 average

## Pre-coding go/no-go checklist

| Gate | Required artifacts | Test result | Owner sign-off | Status |
| --- | --- | --- | --- | --- |
| IA | Mode map, nav model, persona read order, `DRILLREF-001` | pass | UX + BA + SE | pass |
| Traceability | relation export + validation report, `DRILLID-001` | pass | SE + BA | pass |
| Readiness | scored rubric report | pass | SE + BA | pass |
| Accessibility | checklist + keyboard/focus report | pass | UX + SE | pass |
| Governance | approval matrix + decision log, `DRILLDIFF-001` | pass | BA + SE | pass |

Coding starts only when all rows are `pass`.

## Gate decision log

| Date | Scope version | Decision | Approvers | Notes |
| --- | --- | --- | --- | --- |
| 2026-05-12 | v1.0 | no-go | UX, SE, BA | Initial review: contracts not fully objective. |
| 2026-05-12 | v1.1 | no-go | UX, SE, BA | Added objective gates, rubric, schema, and RACI. |
| 2026-05-12 | v1.2 | go | UX, SE, BA | Added fixed scripts, KPI targets, evidence schema, and handoff artifacts. |
| 2026-05-12 | v1.3 | go | UX, SE, BA | Added multi-level drill-down UX/SE/BA contracts, diff checks, and required DRILL artifacts. |

## Redesign phases (before implementation)

### Phase 0 - Product contract alignment

Outputs:
- Domain glossary
- Persona goals and top jobs
- Success metrics baseline
- Source-of-truth hierarchy

Exit criteria:
- Domain glossary and source-of-truth hierarchy artifacts stored in evidence path.
- Review sign-offs recorded for BA + Solution Engineer + UX reviewer.

### Phase 1 - Information architecture and journeys

Outputs:
- Mode map
- Read order per persona
- Journey maps for:
  - BA review
  - Solution engineering design
  - Developer execution handoff

Exit criteria:
- Scripts A/B/C executed with >= 90% first-attempt completion.
- Median completion time <= 30s across reviewers.

### Phase 2 - Interaction and content contracts

Outputs:
- Inspector decision-first content model
- Left rail intent-first model
- Search scope model (tasks/architecture/risks/evidence)
- Progressive disclosure behavior spec
- Drill-down level spec (`L0-L3`) with collapse/expand and side-panel contracts

Exit criteria:
- 0 critical interaction ambiguity defects.
- <= 2 medium ambiguity defects with explicit mitigation owner/date.

### Phase 3 - Visual and accessibility system

Outputs:
- Typography, spacing, density tiers
- State semantics and status badges
- Keyboard and focus contract

Exit criteria:
- WCAG 2.2 AA checklist evidence recorded.
- Keyboard and focus checks pass for critical flows.

### Phase 4 - Migration and implementation handoff

Outputs:
- Backward-compatibility list (must-not-break contracts)
- Implementation sequence and risk controls
- Acceptance checklist for coding start
- Drill readiness evidence bundle (`DRILLREF-001`, `DRILLID-001`, `DRILLDIFF-001`)

Exit criteria:
- Pre-coding go/no-go checklist has all rows set to `pass`.
- Build-ready decision includes BA + SE + UX approval record.

## Must-not-break contracts

1. Stable IDs for nodes/edges/tasks/artifacts
2. Stable lifecycle state vocabulary
3. Stable traceability relation semantics
4. Audit metadata requirements (`who/when/why`)
5. Artifact integrity constraints across spec/plan/tasks

## Persona acceptance criteria

### BA
- Can explain process purpose, scope boundary, and decision points from first view.
- Can identify unresolved assumptions and approval needs quickly.
- Can identify "decision needed now, owner, due date, impact if delayed" from
  Executive Readiness Snapshot in <= 30s.

### Solution Engineer
- Can map every story to architecture and tasks without ambiguity.
- Can determine blockers and dependency order from one execution view.

### Developer
- Can identify next implementable task and required evidence without interpretation gaps.
- Can prove completion against explicit acceptance/evidence mapping.
- Can confirm upstream business intent is unambiguous from handoff packet.

## Definition of done for pre-development package

The package is complete only when:

1. IA, interaction, visual, accessibility, and governance contracts are documented.
2. Role reviewers (UX, BA, SE) approve without unresolved critical items.
3. Traceability and readiness gates are concrete and testable.
4. Implementation handoff sequence is explicit and risk-mitigated.

Until then: **no further app development work**.
