# Copilot Visuals Walkthrough

Date: 2026-05-24
Status: Draft (to be finalized during submission run)

## Purpose

Define the exact visual narrative to demonstrate how UiPlan runtime events become
CopilotKit-visible cards and summaries.

## Visual surfaces to show

1. Phase timeline (`phaseHistory`)
2. HITL decisions (`hitlDecisions`)
3. Loop budget summary (`loopBudgets`, `buildIterations`, `deployIterations`)
4. Escalation state (`escalation`)
5. Artifact and evidence counts (`generatedDocuments`, `buildArtifacts`, `provisionedResources`)

## Demo files

- Core contract:
  - `ui/copilotkit/runtimeAdapter.ts`
  - `ui/copilotkit/run-events.schema.json`
- Demo viewer:
  - `demo/copilot_viewer.html` (in AgentHack repo)
- Event payload:
  - `agents/builder-orchestrator/out/enterpriseincidentagentbuilder-20260524124819/ui/run-events.json`

## Notes

- This file is promoted into AgentHack `submission/` during export.
- Final screenshot/video references are added in the final handoff phase.
