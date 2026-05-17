# Builder Orchestrator Coded Agent

LangGraph-coded UiPath orchestrator for AgentOps Builder Task 3.

## State Contract

The orchestrator state includes:

- `intake`
- `classification`
- `agentAssignments`
- `planSummary`
- `verificationStatus`
- `deploymentReadiness`
- `handoff`

## Graph Nodes

- `classify_request`
- `assign_agents`
- `draft_solution_plan`
- `request_approval`
- `prepare_build`
- `summarize_handoff`

## Local Verification

```powershell
uv run pytest -q
uip codedagent run --input-file ..\..\samples\invoice-exception\intake.json --output-file out\orchestrator-run.json
```

## Input Contract

The runtime accepts either:

- Raw intake payload (example: `samples/invoice-exception/intake.json`)
- Wrapped state payload with `intake` and optional `verificationStatus`

Example wrapped input:

```json
{
  "intake": {
    "businessGoal": "Reduce manual invoice exception handling",
    "systems": ["Email inbox", "ERP"]
  },
  "verificationStatus": "passed"
}
```

Approval/readiness behavior:

- If `verificationStatus` is missing, flow sets `pending_approval` and keeps deployment blocked.
- If input already has `verificationStatus: "passed"`, flow preserves it and marks deployment ready.
