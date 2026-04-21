# UiPlan constitution (project gates)

Override or extend these bullets; `uipath_plan_review` checks that `plan.md`
**Constitution Check** section references each gate (checkbox list).

- **modern_experience_only**: Modern experience only: C#, Windows, .NET 8. No Classic, no VB.Net.
- **analyze_gate**: Never publish if `analyze` returns errors; gate CI on analyze.
- **no_prod_from_assistant**: Never deploy to Production from an AI-assistant session.
- **secrets**: Never commit secrets; use Orchestrator assets or environment variables.
- **cli_version_match**: Match CLI version to Studio/Orchestrator version.

## Complexity tracking

When a gate cannot be met, add a row to **Complexity Tracking** in `plan.md`
with violation, justification, and rejected simpler alternative.
