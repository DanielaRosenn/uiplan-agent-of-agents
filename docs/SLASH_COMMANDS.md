# Slash commands

These commands are typed at the **`uipath chat`** (or equivalent) prompt when
the input starts with `/`. Cursor exposes UiPlan through separate skill-backed
slash commands, each wrapping the same MCP-backed workflow for Cursor chat. MCP
tools remain documented in [MCP_TOOLS.md](MCP_TOOLS.md).

## Cursor-native skill slash

Cursor discovers the UiPlan skill wrappers from `.cursor/skills/uiplan*/`.
They expose separate native Cursor entries:

| Cursor command | Purpose |
| --- | --- |
| `/uiplan` | Overview/help/router for the UiPlan command suite. |
| `/uiplan-full <title>` | Run ground -> spec -> plan -> tasks -> review. |
| `/uiplan-ground <topic>` | Read-only grounding pack. |
| `/uiplan-spec <title> [--intent text]` | Create the draft bundle and `spec.md`. |
| `/uiplan-plan <slug>` | Write `plan.md` for an existing draft. |
| `/uiplan-tasks <slug>` | Write `tasks.md` for an existing draft. |
| `/uiplan-review <slug> [all\|spec\|plan\|tasks]` | Review a draft bundle. |
| `/uiplan-implement <slug>` | Review first, confirm planner/discovery/specialist handoff, ask before build, then implement from `tasks.md`. |

Each wrapper points back to `.cursor/skills/uiplan/SKILL.md` as the canonical
contract and stops before implementation until review passes and the human
approves the build.

## Tool profile (`UIPATH_CLAUDE_TOOL_PROFILE`)

| Profile | Effect |
| --- | --- |
| unset / empty | Same as **`all`**: every slash string is accepted (unknown names still fail at execution). |
| **`safe`** | Allow-list for SDLC + library maintenance (see table below). Recommended default for guided sessions. |
| **`uipath-dev`** | Same allow-list as **`safe`** (alias kept for backward compatibility). |
| **`all`** | Wildcard: any command name passes the profile gate. |

Set for example:

```powershell
$env:UIPATH_CLAUDE_TOOL_PROFILE = "safe"
uipath chat
```

Implementation: [`framework/uipath_claude/tools/profiles.py`](../framework/uipath_claude/tools/profiles.py).

## Command reference

Commands are registered in [`framework/uipath_claude/cli/app.py`](../framework/uipath_claude/cli/app.py) (`_build_command_registry`). **`/plan`** is only registered when the chat session is built with a planner callback.

| Command | Purpose | `safe` / `uipath-dev` |
| --- | --- | --- |
| `/help` | List commands and short descriptions | yes |
| `/doctor` | Run read-only workspace health checks | yes |
| `/status` | Session / engine status | yes |
| `/skills` | List skills | yes |
| `/analyze` | Analyze UiPath project | yes |
| `/validate` | Validate XAML / project | yes |
| `/repair-restore` | Repair / restore workflow | yes |
| `/bootstrap` | Legacy BA → SA → Dev → QA bootstrap | yes |
| `/pdd` | Full PDD → … → deploy lifecycle ([PDD_LIFECYCLE.md](PDD_LIFECYCLE.md)) | yes |
| `/recall` | Search session history | yes |
| `/resume` | List or inspect prior chat sessions | yes |
| `/update-skills` | Update `skills/` submodule from upstream | yes |
| `/scan-upstream-skills` | Diff skills submodule vs last scan | yes |
| `/library-harvest` | Enqueue library proposals from skills | yes |
| `/library-proposals` | List / show / approve / reject proposals | yes |
| `/books` | List library books | yes |
| `/uiplan-ground` | UiPlan grounding pack (`uipath_plan_ground`) | yes |
| `/uiplan-spec` | Create UiPlan `spec.md` (`uipath_plan_spec_new`) | yes |
| `/uiplan-plan` | Create UiPlan `plan.md` (`uipath_plan_plan_new`) | yes |
| `/uiplan-tasks` | Create UiPlan `tasks.md` (`uipath_plan_tasks_new`) | yes |
| `/uiplan-review` | Review a UiPlan bundle (`uipath_plan_review`) | yes |
| `/uiplan-full` | Full UiPlan scaffold (`uipath_plan_uiplan_new`) | yes |
| `/uiplan` | Backwards-compatible UiPlan dispatcher/help alias ([uiplan command README](../framework/uipath_claude/commands/uiplan.md)) | yes |
| `/plan` | Planner slash command (when planner enabled) | yes |

Use `/help` in a live session for the exact list your build registers.

## SDLC mapping

| Phase / concern | Primary slash entry |
| --- | --- |
| Full lifecycle (BA → … → QA, optional deploy) | `/pdd` |
| Lighter four-stage flow | `/bootstrap` |
| Static validation | `/validate`, `/analyze` |
| Planning / three-file bundles | `/uiplan-spec`, `/uiplan-plan`, `/uiplan-tasks`, `/uiplan-review`, `/uiplan-full`; `/uiplan` remains as a dispatcher alias |
| Skills + library hygiene | `/doctor`, `/update-skills`, `/scan-upstream-skills`, `/library-harvest`, `/library-proposals`, `/books` |

Related: [USER_GUIDE.md](USER_GUIDE.md), [CAPABILITY_CONTRACT.md](CAPABILITY_CONTRACT.md), and [SMOKE_TESTS.md](SMOKE_TESTS.md) (env vars and scenarios).
