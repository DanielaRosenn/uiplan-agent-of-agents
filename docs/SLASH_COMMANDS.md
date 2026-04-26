# Slash commands (in-chat / `uipath chat`)

These commands are typed at the **`uipath chat`** (or equivalent) prompt when the input starts with `/`. They are **separate from MCP tools** in Cursor; see [MCP_TOOLS.md](MCP_TOOLS.md) for MCP.

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
| `/uiplan` | UiPlan CLI bridge from chat ([uiplan command README](../framework/uipath_claude/commands/uiplan.md)) | yes |
| `/plan` | Planner slash command (when planner enabled) | yes |

Use `/help` in a live session for the exact list your build registers.

## SDLC mapping

| Phase / concern | Primary slash entry |
| --- | --- |
| Full lifecycle (BA → … → QA, optional deploy) | `/pdd` |
| Lighter four-stage flow | `/bootstrap` |
| Static validation | `/validate`, `/analyze` |
| Planning / three-file bundles | `/uiplan`, `/plan` (if enabled) |
| Skills + library hygiene | `/doctor`, `/update-skills`, `/scan-upstream-skills`, `/library-harvest`, `/library-proposals`, `/books` |

Related: [USER_GUIDE.md](USER_GUIDE.md), [CAPABILITY_CONTRACT.md](CAPABILITY_CONTRACT.md), and [SMOKE_TESTS.md](SMOKE_TESTS.md) (env vars and scenarios).
