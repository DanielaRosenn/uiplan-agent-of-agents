# Template Contract Diff Summary

## Updated template files
- `templates/uiplan/_plan-template.md`
- `templates/uiplan/_tasks-template.md`

## Contract additions
- Added **Supervisor run-state contract** section in plan template.
- Added **UiPlan loop budget and HITL checklist** section in tasks template.

## Runtime field mapping
- `loopBudgets.maxBuildIterations` -> build loop cap tasks/evidence.
- `loopBudgets.maxDeployIterations` -> deploy/test cap tasks/evidence.
- `hitlDecisions[]` -> gate evidence artifacts.
- `buildIterations[]` / `deployIterations[]` -> iteration evidence JSON outputs.
- `escalation` -> escalation packet output.
- `uiEventsPath` -> CopilotKit adapter input artifact.
