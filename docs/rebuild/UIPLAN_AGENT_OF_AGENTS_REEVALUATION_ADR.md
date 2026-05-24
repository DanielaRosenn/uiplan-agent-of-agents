# UiPlan Agent-of-Agents Re-Evaluation ADR

Date: 2026-05-24
Status: Accepted
Owner: UiPlan Builder Team

## 1) Source-of-truth decision

The implementation source of truth is this repository:

- `C:/Users/DanielaRosenstein/projects/uipath-builder-agent`

The split repositories remain downstream targets:

- `C:/Users/DanielaRosenstein/projects/cato-uiplan-core` (core mirror/export target)
- `C:/Users/DanielaRosenstein/projects/danielarosenn-agenthack` (demo/submission target)

Rationale:

- The active orchestrator, contracts, templates, tests, and rebuild evidence are maintained here.
- Existing dual-repo process already documents export/sync from this workspace.
- A single canonical authoring repo avoids drift while the architecture evolves.

Operational rule:

1. Author and validate changes in this repo.
2. Export/sync to downstream repos only after local verification gates pass.

## 2) Current-state audit

### Implemented today (validated)

- Supervisor-style LangGraph pipeline with deterministic phases and loop budgets in:
  - `agents/builder-orchestrator/main.py`
- Build/deploy loop evidence, escalation packets, and run event emission:
  - `agents/builder-orchestrator/main.py`
  - `ui/copilotkit/run-events.schema.json`
  - `ui/copilotkit/runtimeAdapter.ts`
- Core contract models for brief/assignment/artifacts/resources/evidence/handoff:
  - `agents/shared/agent_contracts.py`
- Focused orchestrator and contract tests:
  - `agents/builder-orchestrator/tests/test_orchestrator.py`
  - `agents/shared/tests/test_contracts.py`
  - Recorded output: `docs/rebuild/ORCHESTRATION_LOOP_TEST_OUTPUTS.md`

### Simulated or placeholder behavior

- Specialist agents are static assignments, not independent runtime workers.
- HITL decisions are auto-accepted in local flow.
- Provisioning and deploy/test paths are frequently dry-run simulated.
- Generated design docs are template-derived artifacts, not yet model-grounded specialist outputs.

### Missing for target architecture

- First-class BPMN artifact contract and generation/validation lifecycle.
- Durable lineage/drift model across source and generated artifacts.
- Per-agent telemetry contract (tokens, latency, model, cost, hash lineage).
- Real HITL interrupt lifecycle (request -> resolution -> resume) beyond auto-approval.
- Executable tasks handoff contract for coding-agent dispatch and review gate.

### Active risks

- Contract depth is insufficient for true multi-agent orchestration.
- Test defaults in root `pyproject.toml` exclude `agents/*` tests unless explicitly invoked.
- Generated `agents/builder-orchestrator/out/*` artifacts add noise and can mask signal.
- Non-prod deployment remains blocked in existing evidence due to missing entry points.

## 3) Contract-first roadmap

Implement contracts before behavior changes.

### 3.1 New contract set (v0.2 target)

Add to `agents/shared/agent_contracts.py` (or sibling module):

- `ArtifactLineage`
  - `artifact_id`, `artifact_type`, `path`, `hash`, `parents`, `generated_by`, `generated_at`
- `BpmnArtifact`
  - `name`, `bpmn_path`, `mermaid_path`, `validation_status`, `validation_errors`
- `AgentRunTelemetry`
  - `run_id`, `agent_name`, `phase`, `model`, `input_tokens`, `output_tokens`, `cost_usd`,
    `latency_ms`, `status`, `error_details`, `input_hashes`, `output_hashes`
- `HitlRequest`
  - `request_id`, `phase`, `reason`, `payload`, `channel`, `status`, `resolved_by`, `resolved_at`
- `CodingAgentTask`
  - `task_id`, `story_id`, `scope_paths`, `acceptance_criteria`, `dependencies`, `priority`
- `ReviewGate`
  - `gate_id`, `required_checks`, `status`, `failed_checks`, `approved_by`, `approved_at`

### 3.2 Run-event schema versioning (v0.2 target)

Add schema version and extension buckets to:

- `ui/copilotkit/run-events.schema.json`

Minimum additions:

- `schemaVersion`
- `telemetryRuns[]`
- `lineageArtifacts[]`
- `hitlRequests[]`
- `codingHandoff`

Keep backward compatibility in `ui/copilotkit/runtimeAdapter.ts` by supporting both old and new payloads.

### 3.3 Runtime adoption order (v0.3 target)

1. Emit new contracts in orchestrator output without changing routing logic.
2. Switch one phase at a time from static specialist assignment to concrete specialist nodes.
3. Keep deterministic fallback mode for CI and local reproducibility.

## 4) Phase roadmap and verification gates

## v0.2 - Contract foundation

Goal: make runtime observable and evolvable without changing external behavior.

Scope:

- Introduce new shared contracts.
- Version run-events schema.
- Emit lineage/telemetry/HITL-task placeholders in orchestrator outputs.
- Add tests for serialization and backward compatibility.

Gates:

- `python -m pytest agents/shared/tests/test_contracts.py -q`
- `python -m pytest agents/builder-orchestrator/tests/test_orchestrator.py -q`
- JSON schema validation for generated `ui/run-events.json` against updated schema.

Exit criteria:

- Existing sample run still succeeds.
- Copilot adapter reads old and new event payloads.

## v0.3 - Real specialist boundaries

Goal: replace static specialist labeling with executable phase boundaries.

Scope:

- Split into explicit specialist nodes:
  - Spec
  - Plan/BPMN
  - Tasks/Handoff
- Add real HITL interrupt lifecycle in one phase (spec clarification).
- Add lineage parent/child chaining across produced artifacts.

Gates:

- Existing orchestrator tests updated and passing.
- New golden-output tests for spec/plan/tasks outputs.
- Forced failure tests for HITL escalation and resume paths.

Exit criteria:

- At least one specialist boundary runs with real phase-local logic.
- Escalation and resume are deterministic under test.

## v1.0 - Product-grade agent-of-agents loop

Goal: complete target architecture for supervised build pipeline.

Scope:

- BPMN dual-output (`.bpmn` + `.mermaid`) with validation.
- Per-phase telemetry and cost tracing emitted for every specialist run.
- Executable coding-agent handoff contract and review gate checks.
- Adapter-ready HITL channels (CopilotKit first; Action Center/Slack pluggable).

Gates:

- Full end-to-end sample run with no simulated approvals in the critical path.
- Non-prod deploy/test evidence passes once entry-point blocker is resolved.
- Regression suite includes lineage drift detection scenarios.

Exit criteria:

- Supervisor output is actionable as a coding contract, not only documentation.
- Evidence bundle contains lineage, telemetry, HITL, and review-gate results.

## 5) Immediate execution backlog

1. Add contract types and tests (v0.2).
2. Add `schemaVersion` and backward-compatible adapter handling.
3. Emit new contract structures in orchestrator handoff and run-events output.
4. Add dedicated schema/compatibility tests for Copilot adapter input.
5. Separate generated `out/` run artifacts from tracked implementation changes.

