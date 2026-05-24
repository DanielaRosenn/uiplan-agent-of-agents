# CopilotKit Adapter Validation Notes

## Contract files
- `ui/copilotkit/run-events.schema.json`
- `ui/copilotkit/runtimeAdapter.ts`

## Runtime producer
- Orchestrator emits `ui/run-events.json` inside each run output folder.
- Verified via:
  - `python examples/agent-of-agents-e2e/run_local.py`
  - Output includes `agents/builder-orchestrator/out/<run-id>/ui/run-events.json`.

## Adapter expectations
- Timeline is derived from `phaseHistory`.
- HITL summary is derived from `hitlDecisions`.
- Loop summary is derived from `loopBudgets`, `buildIterations`, `deployIterations`.
- Escalation state is derived from `escalation.reason`.
