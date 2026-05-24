# Dual Repo Strategy: Cato Core + AgentHack Example

## Cato core repo (primary)

This repository stays implementation-focused:

- `templates/uiplan/` canonical templates
- orchestrator/runtime code
- CopilotKit adapter contract
- tests, governance, and deployment readiness checks

## DanielaRosen AgentHack repo (exported)

AgentHack-facing repository is generated from core using:

```powershell
python scripts/export_agenthack_repo.py
```

Generated output location:

- `dist/agenthack-repo/`

Contents include:

- one clean E2E example
- one AgentHack example flow
- CopilotKit UI adapter layer
- submission support docs and export manifest

## Sync model

1. Build/update in Cato core repo.
2. Re-run export script.
3. Push exported folder contents to DanielaRosen AgentHack repository.

This keeps demo material isolated from core architecture while preserving a
repeatable submission workflow.
