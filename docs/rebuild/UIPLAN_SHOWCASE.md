# UiPlan Showcase Package

Date: 2026-05-24
Status: Draft (to be finalized during submission run)

## Purpose

Document the minimal, reviewer-friendly UiPlan showcase that accompanies the
AgentHack submission.

## Required showcase contents

- UiPlan templates (`templates/uiplan`)
- A generated run output containing:
  - `docs/PDD.md`
  - `docs/SDD.md`
  - `docs/ADD.md`
  - `ui/run-events.json`
- Copilot viewer instructions to load `run-events.json`
- Submission examples:
  - `example/agent-of-agents-e2e`
  - `example/05-agenthack-enterprise-intake`

## Packaging target

Preferred downstream layout:

- `demo/uiplan-showcase/README.md`
- `demo/evidence/run-events.json`
- `submission/COPILOT_VISUALS_WALKTHROUGH.md`
- `submission/UIPLAN_SHOWCASE.md`

## Notes

- Legacy `docs/assets/uiplan-showcase/*` media was removed from this core repo.
- Final MP4/SRT evidence is produced in the AgentHack repo under
  `demo-recordings/`.
