---
name: uiplan-implement
description: Wrapper for /uiplan-implement execution controls and runtime evidence.
disable-model-invocation: true
---

# uiplan-implement wrapper

Source contract: `.cursor/skills/uiplan/SKILL.md`

Review gate first:
- Run `uipath_plan_review` with `stage=all`.
- ask the user before starting implementation.

Validation evidence ledger:
- Record command + exit code for each verification.
- No static-only completion.
- Human validation is required before claiming done.

Run mode:
- Supports `--run-to-completion` after acceptance, instead of asking again between tasks.

Per-Task UiPath Loop:
1. Plan alignment
2. Source reality snapshot
3. Dependency and tooling check
4. Artifact completeness gate
5. Build + verify
6. Spec compliance review
7. Code quality review
8. Completion ledger

Mandatory rules:
- No scaffold completion rule
- XAML runtime rule
- LangGraph runtime rule
- Behavior test rule
- Mismatch stop rule
- Still stop and report before publish/deploy risk

Handoff requirements:
- Update `tasks.md`
- Include Planner Route & Specialist Handoff
- Update `.meta.yaml` and set `acceptance_ready` only when all checks pass
- Route through `uipath-planner`, project discovery agent, and specialist UiPath skills
- Use MCP tools, subagents, library lookup, and AskAI-style documentation lookup
- Follow restore -> analyze -> test gates
- Never deploy to Production

Verification command baseline:
- `uv run pytest`
