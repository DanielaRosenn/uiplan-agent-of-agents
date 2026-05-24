# UiPlan: Agent-of-Agents

## 30-second pitch

Most teams lose time in handoffs between BA, architecture, development, and platform setup.
UiPlan compresses that lifecycle into one supervised run: submit a business brief and get a
full UiPath delivery package with planning docs, build artifacts, resource provisioning checks,
execution evidence, and a monitorable event stream.

## Problem

Automation delivery is usually fragmented:

- Business requirements sit in one document.
- Technical design is rewritten separately.
- Runtime resources (queues/assets) are provisioned out-of-band.
- Verification evidence is scattered across terminals and manual notes.

When scope changes, the cycle repeats and context is lost.

## Solution

UiPlan is a LangGraph-based builder orchestrator that runs a fixed specialist pipeline:

1. `assign_agents`
2. `generate_design_docs`
3. `generate_uipath_artifacts`
4. `provision_resources`
5. `execute_flow`
6. `emit_ui_events`
7. `summarize_handoff`

Each phase emits structured state, so outputs are reviewable by both humans and agents.

## What it generates

From one brief, the system generates:

- UiPlan contract: `spec.md`, `plan.md`, `tasks.md`
- Design package: `PDD.md`, `SDD.md`, `ADD.md`
- Build artifacts: `generated-flow.json`, `run-flow.ps1`
- Runtime evidence: `execution-evidence.json`, `flow-run-output.log`
- UI monitor payload: `ui/run-events.json` mirrored to `ui/copilotkit/current/run-events.json`

## Technical stack

- Python 3.12
- LangGraph state machine orchestration
- `uipath` CLI for coded-agent runtime
- `uip` CLI for Orchestrator resources and monitoring
- CopilotKit static viewer for run inspection
- pytest test suite for orchestrator and contract checks

## Key differentiators

- **Agent-of-agents execution model:** named specialist ownership per delivery phase.
- **Typed planning contract:** `spec -> plan -> tasks` drives downstream generation.
- **Constraint intelligence:** codebase + skill critical rules are severity-classified and
  rendered as a constraints graph in viewer events.
- **Evidence-first handoff:** every run produces machine-readable artifacts and command logs.
- **Real platform integration:** queue/asset verification and Orchestrator job telemetry are
  pulled from live tenant data.

## Real run evidence used for submission

- Run ID: `enterpriseincidentagentbuilder-20260524163750`
- Queue: `Q_AGENT_OF_AGENTS_WORK` (Shared folder)
- Asset: `ASSET_AGENT_OF_AGENTS_POLICY` (Shared folder)
- Viewer payload: `ui/copilotkit/current/run-events.json`

## Safety and governance

- No Production deployment in assistant-driven flow.
- Human approval is an explicit runtime constraint.
- Build/deploy loops have max-iteration budgets with escalation.
- Secrets are not hardcoded in generated artifacts.

## Demo flow summary

1. Show skills + CLI foundation.
2. Run orchestrator with real brief.
3. Open generated UiPlan files (`spec`, `plan`, `tasks`).
4. Show CopilotKit 7-tab viewer, emphasizing Constraints and Tasks.
5. Show Orchestrator-backed resource and job data.
6. Close with deploy path and reproducibility.

## Reproducibility

1. Use `samples/agent-of-agents/brief.enterprise-incident.real.json`.
2. Run orchestrator from `agents/builder-orchestrator`.
3. Open `ui/copilotkit/viewer.html` to inspect the current event stream.
