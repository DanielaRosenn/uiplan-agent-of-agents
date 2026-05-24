# Agent-of-Agents E2E Example

This example demonstrates a full run of the rebuilt orchestrator:

1. read a business brief,
2. generate `PDD`/`SDD`/`ADD`,
3. generate build artifacts,
4. provision queue/asset through CLI commands (or simulate in dry-run),
5. generate execution evidence and handoff output.

## Dry Run (reproducible locally)

```powershell
python "examples/agent-of-agents-e2e/run_local.py"
```

Expected output structure:

```text
agents/builder-orchestrator/out/<run-id>/
  docs/
    PDD.md
    SDD.md
    ADD.md
  artifacts/
    generated-flow.json
    run-flow.ps1
  evidence/
    simulated-run-output.json
    execution-evidence.json
  ui/
    run-events.json
  handoff.json
```
