# UiPlan Slash Commands (UiPath spec-kit style)

UiPlan slash commands are registered in `uipath_claude/commands/uiplan.py`
(`register_uiplan_command`). Each command forwards directly to the matching
`uipath_plan_*` MCP tool.

## Usage (chat)

| Command | MCP tool | Purpose |
| --- | --- | --- |
| `/uiplan-ground <topic>` | `uipath_plan_ground` | Build the grounding pack only. |
| `/uiplan-spec <title> [--intent text] [--paradigm value]` | `uipath_plan_spec_new` | Create the draft folder and `spec.md`. |
| `/uiplan-plan <slug> [--paradigm value]` | `uipath_plan_plan_new` | Write `plan.md` after spec exists. |
| `/uiplan-tasks <slug> [--paradigm value]` | `uipath_plan_tasks_new` | Write `tasks.md` after plan exists. |
| `/uiplan-review <slug> [all|spec|plan|tasks]` | `uipath_plan_review` | Review the bundle. |
| `/uiplan-full <title>` | `uipath_plan_uiplan_new` | Run ground → spec → plan → tasks → review. |
| `/uiplan-implement <slug>` | `uipath_plan_review` (`stage=all`) | Build preflight: review-only handoff; then follow `uiplan-implement` skill. |

`/uiplan-ground` and the generated `plan.md` grounding section include the
planning skill route, matched specialist skill excerpts, local library hits, and
the `uipath_library_lookup` / AskAI-style knowledge path when available.

Backwards-compatible dispatcher:

- `/uiplan full My feature title`
- `/uiplan ground <topic>`
- `/uiplan spec <title> [--intent text]`
- `/uiplan plan <slug>`
- `/uiplan tasks <slug>`
- `/uiplan review <slug> [all|spec|plan|tasks]`
- `/uiplan implement <slug>`

## CLI equivalent

```bash
uipath-claude plan uiplan full "My feature title"
uipath-claude plan uiplan ground "topic words"
uipath-claude plan uiplan spec "Title" --intent "Goal" --paradigm coded-agent
uipath-claude plan uiplan plan my-slug --paradigm modern-rpa
uipath-claude plan uiplan tasks my-slug --paradigm modern-rpa
uipath-claude plan uiplan review my-slug --stage all
uipath-claude plan uiplan implement my-slug
```

## Docs

- Skill: `.cursor/skills/uiplan/SKILL.md`
- Wrapper contracts: `.cursor/skills/uiplan-review/SKILL.md`, `.cursor/skills/uiplan-tasks/SKILL.md`
- Human guides (Cursor context): `docs/uiplan/` — attach `@docs/uiplan/`
- Template kit (source): `templates/uiplan/`
- Framework: `docs/PLANNING_FRAMEWORK.md` (UiPlan section)
- Pytest (UiPlan): `framework/tests/uiplan/`
