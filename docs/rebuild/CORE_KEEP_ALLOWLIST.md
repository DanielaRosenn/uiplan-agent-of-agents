# UiPlan Rebuild Core Keep Allowlist

This allowlist defines the core Cato repository scope for the rebuild.

## Core paths to keep

- `templates/uiplan/`
- `agents/builder-orchestrator/`
- `agents/shared/`
- `docs/`
- `scripts/`
- `samples/`
- `ui/` (CopilotKit adapter layer)
- `extensions/`
- `framework/`
- `skills/` (submodule)

## Paths targeted for aggressive cleanup (if present)

- `MaestroFlowsSolution/`
- `StudioWebFlowsSolution/`
- `agents/builder-orchestrator/out/`
- `out/`, `output/`, `generated/`
- legacy demo examples not in final scope
- `test-results/`
- old experiment roots: `flows/`, `ops/`, `solution/`, `workflows/`, `scaffold/`, `test-harness/`

## Execution note

Cleanup is executed only inside the isolated fresh-clone rebuild workspace.
