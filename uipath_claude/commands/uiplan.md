# /uiplan (UiPath spec-kit style)

Slash command **`/uiplan`** is registered in code as `uipath_claude/commands/uiplan.py`
(`register_uiplan_command`). It forwards to the same MCP tools as the CLI.

## Usage (chat)

- `/uiplan full My feature title` — runs `uipath_plan_uiplan_new` (ground → spec → plan → tasks → review).
- `/uiplan ground <topic>` — `uipath_plan_ground` only.
- `/uiplan spec <title> [intent ...]` — `uipath_plan_spec_new`.
- `/uiplan plan <slug>` — `uipath_plan_plan_new`.
- `/uiplan tasks <slug>` — `uipath_plan_tasks_new`.
- `/uiplan review <slug> [all|spec|plan|tasks]` — `uipath_plan_review`.

## CLI equivalent

```bash
uipath-claude plan uiplan full "My feature title"
uipath-claude plan uiplan ground "topic words"
uipath-claude plan uiplan spec "Title" --intent "Goal"
uipath-claude plan uiplan plan my-slug
uipath-claude plan uiplan tasks my-slug
uipath-claude plan uiplan review my-slug --stage all
```

## Docs

- Skill: `.cursor/skills/uiplan/SKILL.md`
- Framework: `docs/PLANNING_FRAMEWORK.md` (UiPlan section)
