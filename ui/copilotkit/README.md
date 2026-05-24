# CopilotKit Runtime Layer for UiPlan

This module is the UI adapter boundary for the UiPlan supervisor runtime.

## Purpose

- Load run-state output from orchestrator (`ui/run-events.json`).
- Convert it into CopilotKit-friendly cards/threads for:
  - phase timeline
  - loop iteration status
  - dependencies/resources
  - escalation packet details

## Data contract

- Input schema: `ui/copilotkit/run-events.schema.json`
- Adapter: `ui/copilotkit/runtimeAdapter.ts`
- Viewer: `ui/copilotkit/viewer.html`

## Integration model

1. Builder run writes `ui/run-events.json` per run.
2. CopilotKit frontend fetches/streams that JSON.
3. Adapter builds view-model objects (timeline, tasks, dependencies, evidence).
4. UI components render dynamic state and planning artifacts.

## Viewer usage

1. Start a static server at the repository root:
   - `python -m http.server 8765`
2. Open:
   - `http://localhost:8765/ui/copilotkit/viewer.html`
3. The viewer auto-loads latest run data from:
   - `/ui/copilotkit/current/run-events.json`
4. Optional fallback: drop a run file (`run-events.json` or `handoff.json`) onto the page.

The viewer prioritizes agent-readable UiPlan files:
- `uiPlanFiles`: primary content (expected: `spec.md`, `plan.md`, `tasks.md`)
- `humanDocs`: secondary human-facing docs (`PDD.md`, `SDD.md`, `ADD.md`)
- `generatedDocuments`: backward compatibility alias for `humanDocs`

The viewer includes a dedicated **Diagrams** tab that aggregates and renders all
Mermaid diagrams found across UiPlan files. This supports large solution sets
where diagrams represent each part of the architecture and execution design.

The viewer also includes a **Constraints** tab that summarizes:
- Brief-level constraints from runtime payload (`brief.constraints`)
- Runtime policy constraints (loop budgets and escalation behavior)
- Guardrail statements extracted from UiPlan docs (must/never/required/do-not)
- Copilot-focused code constraint guidance for implementation safety

For visual, folder-scoped codebase constraints, the runtime payload also contains
`constraintsGraph`, which includes:
- `targetFolder`: analyzed folder path (default `agents/builder-orchestrator`)
- `constraints`: folder-derived statements with `source=folder`
- `skillConstraints`: SKILL.md-derived critical rules with `source=skill`
- `selectedSkills`: multi-skill set used for extraction (default includes troubleshoot/platform/rpa/test)
- `sourceCounts`: counts split by folder vs skill source
- `severityCounts` and `violationsCount`
- `topFiles` by constraint density
- `mermaid`: prebuilt graph source for visual rendering (`F-*` folder constraints, `S-*` skill constraints)
- `codebaseDoc`: generated markdown summary for documentation use

## Automatic data refresh contract

- `agents/builder-orchestrator/main.py` mirrors each run payload to:
  - `ui/copilotkit/current/run-events.json`
- This gives the viewer a stable endpoint for dynamic, no-upload loading.

## Notes

- The adapter is intentionally framework-agnostic to support Cato internal UI and
  AgentHack demo UI.
- This folder stores the canonical mapping contract between orchestrator output
  and CopilotKit visual components.
