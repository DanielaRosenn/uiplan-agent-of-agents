# UiPlan Setup In A Cloned Project

Use this when a cloned project needs the same UiPlan contract as this repo.

## Canonical Paths

| Role | Path |
| --- | --- |
| Human guidance | `docs/uiplan/` |
| Template kit | `templates/uiplan/` |
| Runtime code | `tools/uiplan/` |
| Runtime tests | `framework/tests/uiplan/` |
| Draft bundles | `.cursor/plans/<YYYY-MM-DD-slug>/` |
| Published bundles | `docs/plans/<YYYY-MM-DD-slug>/` |

## Cursor

1. Attach `@docs/uiplan/` when asking for a UiPlan so the agent sees the
   repo-local contract.
2. Use the UiPlan skill (`.cursor/skills/uiplan/SKILL.md`) for structured
   `spec.md`, `plan.md`, and `tasks.md` output.
3. Keep drafts under `.cursor/plans/`; publish accepted bundles to `docs/plans/`.

## Claude CLI

Use `/uiplan` in chat or the CLI equivalent:

```powershell
uipath-claude plan uiplan full "Describe the feature"
```

The command reads from `templates/uiplan/` and writes the same three-file bundle
used by Cursor.

## Validation

Run the focused checks after moving or editing the kit:

```powershell
uv run pytest framework/tests/uiplan framework/tests/mcp_tests/test_uiplan_tools.py -q
```
