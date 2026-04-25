# Deployment Integration Notes

For deploy instructions, use the canonical runbook:

- [Orchestrator Deployment Runbook](ORCHESTRATOR_DEPLOYMENT.md)

This file is kept only as an integration note for older references that point at deployment internals.

## Current Policy

- Run the compatibility preflight before project creation, package selection, validation, pack, or deploy.
- Run restore/analyze/test/pack gates before any publish or deploy.
- Ask for explicit human confirmation before any publish, deploy, invoke, or job run.
- Use a personal workspace or explicitly named Dev folder for assistant-driven review.
- Never use Production from an AI-assistant session.

## Current Integration Points

The deploy stages are implemented in:

- `framework/uipath_claude/tools/deploy_tool.py`
- `framework/uipath_claude/query/pdd_lifecycle.py`
- `framework/mcp_server/tools/workflow_tools.py`

Older examples in this document used broad conversational triggers and direct deployment phrasing. Those examples are historical and should not be copied into new prompts or tests. New docs must point to [ORCHESTRATOR_DEPLOYMENT.md](ORCHESTRATOR_DEPLOYMENT.md) instead.

## Process Cleanup

Process cleanup remains relevant for local validation and test runs:

- test-spawned `UiPath.Studio.exe` / `UiPath.Executor.exe` processes may be tracked and cleaned up by local tooling;
- manually opened Studio sessions stay open;
- Orchestrator robot processes are not local cleanup targets.
