# UiPath Builder Agent - Cursor User Guide

This guide covers using the UiPath Builder Agent skills in Cursor IDE for building UiPath automations.

## Quick Setup (5 minutes)

Use one assistant per clone. This repo supports both, but your local setup should be either:

- `cursor` -> `ops/scripts/cursor-quickstart.*`
- `claude` -> `ops/scripts/claude-quickstart.*`

The quickstart scripts persist your local selection in `.assistant-choice` and block cross-setup unless you pass `-Force` / `--force`.

### 0. Almost zero work (one script)

From repo root after clone — does submodules, `uv sync --extra mcp`, copies MCP config if missing, links skills:

```powershell
.\ops\scripts\cursor-quickstart.ps1
```

```bash
bash ops/scripts/cursor-quickstart.sh
```

Then open this folder in Cursor and confirm **Settings → MCP → uipath-builder-agent** is green (reload window if needed). Requires **git** and **uv** on PATH.

If this clone is already configured for Claude, run with `-Force` / `--force` to switch.

### Preflight Doctor

Before opening Cursor, you can run the same read-only health checks the team uses
for support:

```powershell
uipath-claude doctor
```

The doctor checks the skills submodule, Cursor skill redirects, MCP config,
`uip` availability, generated MCP docs, markdown encoding, and library proposal
health. It does not edit files.

### 1. Clone and Initialize

```powershell
git clone <repo-url>
cd uipath-builder-agent
git submodule update --init --recursive
```

### 2. Install Dependencies

**Recommended (matches [.cursor/mcp.json.example](.cursor/mcp.json.example)):** use **uv** at repo root so Cursor and the MCP server share the same environment. (Skip manual steps here if you already ran **§0 quickstart**.)

```powershell
cd uipath-builder-agent
uv sync --extra mcp
```

**Alternative (venv + pip):**

```powershell
# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # macOS/Linux

# Install with MCP support
pip install -e ".[mcp]"
```

If you use venv + pip, point `.cursor/mcp.json` at that interpreter instead of `uv run` (see the JSON block in step 4).

### 3. Setup Cursor Skills

```powershell
# Windows
.\ops\scripts\setup-cursor.ps1

# macOS/Linux
./ops/scripts/setup-cursor.sh
```

### 4. Enable MCP Tools (Optional but Recommended)

The MCP server gives Cursor access to UiPath CLI tools (validation, execution, package management).

Copy the tracked example to your local (gitignored) MCP config:

```powershell
Copy-Item .cursor/mcp.json.example .cursor/mcp.json
```

Edit `.cursor/mcp.json` only if your machine needs a different `command` (for example bare `python` instead of `uv`). The canonical template is `.cursor/mcp.json.example`.

Or manually add to Cursor's MCP settings:
```json
{
  "mcpServers": {
    "uipath-builder-agent": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "c:/path/to/uipath-builder-agent",
      "env": {
        "PYTHONPATH": "c:/path/to/uipath-builder-agent/framework"
      }
    }
  }
}
```

### 5. Install Superpowers Plugin (Recommended)

In Cursor:
1. Open Settings (`Ctrl+,`)
2. Search for "cursor.plugins"
3. Add `cursor-public/superpowers` to your plugins list

Or add to your `settings.json`:
```json
{
  "cursor.plugins": ["cursor-public/superpowers"]
}
```

The superpowers plugin adds development workflow skills:
- **brainstorming** - Design before implementation
- **writing-plans** - Create detailed implementation plans
- **executing-plans** - Execute plans task-by-task
- **test-driven-development** - TDD workflow
- **systematic-debugging** - Bug investigation
- **code-review** - Request and receive reviews

### 4. Open in Cursor

Open the `uipath-builder-agent` folder in Cursor. Skills are now available.

---

## How It Works

When you ask about UiPath topics, Cursor automatically uses the relevant skill. Skills provide:

- **XAML templates** - Correct namespaces, activity patterns
- **Project structure** - `project.json`, dependencies, folder layout
- **Best practices** - Naming conventions, error handling, validation
- **Activity reference** - Modern vs classic, properties, examples

### Example: Create a Workflow

You ask:
```
Create a workflow that reads an Excel file and logs each row
```

Cursor uses the `uipath-rpa` skill and generates:

1. `project.json` with Excel package dependency
2. `Main.xaml` with:
   - Proper namespace declarations (single-line Activity root)
   - `UseExcelFile` scope
   - `ForEachExcelRow` with typed iterator
   - `LogMessage` activity

---

## Available UiPath Skills

| Skill | Use For |
|-------|---------|
| `uipath-rpa` | XAML and coded RPA workflow authoring, validation, package setup, UI automation authoring |
| `uipath-interact` | Live desktop/browser inspection, screenshots, click/type actions, post-build verification |
| `uipath-planner` | Multi-skill planning and ambiguous UiPath requests |
| `uiplan` | Cursor-first spec/plan/tasks bundle under `.cursor/plans/` |
| `uipath-platform` | Orchestrator, folders, queues, assets, Integration Service, package publish/deploy |
| `uipath-maestro-flow` | Maestro `.flow` orchestration |
| `uipath-human-in-the-loop` | Action Center and approval gates in Flow/Maestro/agents |
| `uipath-agents` | Coded and low-code UiPath agents |
| `uipath-coded-apps` | UiPath Coded Apps |
| `uipath-data-fabric` | Data Fabric entity and record operations |
| `uipath-diagnostics` | Troubleshooting, failed jobs, selectors, permissions |
| `uipath-feedback` | Report product or skill feedback |
| `uipath-test` | Test Manager and test execution workflows |

### Trigger Keywords

Skills activate on relevant keywords. Examples:

- "create a workflow" / "XAML" / "sequence" → `uipath-rpa`
- "inspect the live browser" / "take a screenshot" / "click this running app" → `uipath-interact`
- "Maestro" / "BPMN" / "process diagram" → `uipath-maestro-flow`
- "error" / "not working" / "debug" → `uipath-diagnostics`
- "publish" / "folder" / "queue" / "asset" → `uipath-platform`

---

## Workflow Patterns

### Pattern 1: Quick Workflow Generation

For simple automations, just describe what you need:

```
Create a workflow that:
- Opens Chrome and navigates to example.com
- Types "hello" in the search box
- Clicks the submit button
```

### Pattern 2: Project Bootstrap (with Superpowers)

For larger projects, use the brainstorming + planning workflow:

```
I need to build a process that:
- Reads invoices from a shared folder
- Extracts data using Document Understanding
- Validates against SAP
- Creates queue items for exceptions

Let's brainstorm this first.
```

This triggers:
1. **Brainstorming skill** - Explore requirements, edge cases, architecture
2. **Writing-plans skill** - Create detailed implementation plan
3. **Executing-plans skill** - Build task-by-task with verification

### Pattern 3: Fix and Debug

When something doesn't work:

```
My workflow fails with "Selector not found" on the login button.
Here's the XAML: [paste]
```

The `uipath-diagnostics` skill guides systematic debugging.

### Pattern 4: Code Review

Before deployment:

```
Review this workflow for best practices:
[paste XAML or describe project]
```

Use `uipath-diagnostics` for failure analysis and `uipath-rpa` for workflow
authoring fixes. For broader repository review, ask Cursor for a code review and
include the relevant files or project path.

---

## MCP Tools (Advanced)

When the MCP server is enabled, Cursor can call the same Python entry points the CLI uses: workflow tools, skill registry, planner/bootstrap agents, bundled activity-docs, and memory.

**Project root:** set `UIPATH_MCP_PROJECT_ROOT` to your UiPath project or repo root so skill discovery and paths resolve consistently (defaults to the process current working directory).

### Workflow tools (`uipath_workflow_*`)

| Tool | Description |
|------|-------------|
| `uipath_workflow_create_project` | Scaffold a new UiPath project via `uip rpa create-project` (`--template-id` + Studio dir resolution; CLI-only fallback) |
| `uipath_workflow_ensure_project` | Confirm `project.json` exists under `project_dir`; optional nested `project_name` |
| `uipath_workflow_read_project` | Read and JSON-parse `project.json` |
| `uipath_workflow_read_file` / `uipath_workflow_write_file` | Read/write files under the agent path rules |
| `uipath_workflow_list_directory` | List directory (`directory_path`, optional `pattern`) |
| `uipath_workflow_install_package` | `uip rpa install-or-update-packages` |
| `uipath_workflow_validate` | Static validation of one XAML via `uip rpa get-errors` |
| `uipath_workflow_validate_loop` | Deprecated alias of `validate` (kept for backward compatibility) |
| `uipath_workflow_build_and_verify` | Build, validate, headless-run, and Studio-debug in one shot |
| `uipath_workflow_environment_probe` | Probe local Studio + installed activity packages |
| `uipath_workflow_run` | Run workflow once (destructive) via `uip rpa run-file` |
| `uipath_workflow_debug` | Start a workflow in debug mode (`uip rpa run-file StartDebugging`) |
| `uipath_workflow_run_command` | Escape hatch: raw `uip` (`command` + `args` + optional `project_dir`) |
| `uipath_workflow_publish` | Pack and publish a `.nupkg` to Orchestrator (no process creation) |
| `uipath_workflow_deploy` | Pack + publish + create-process on Orchestrator. `project_type=process|maestro` selects RPA vs Flow toolchain. |
| `uipath_workflow_session_status` | Read-only status of the per-project verification gate (`unknown`/`dirty`/`verified`) |

### Skill tools (`uipath_skill_*`)

| Tool | Description |
|------|-------------|
| `uipath_skill_list` | List skills; optional `agent_role` filter |
| `uipath_skill_get` | Full `SKILL.md` body for one skill |
| `uipath_skill_match` | Same scoring heuristic as CLI chat (`_select_relevant_skills`) |
| `uipath_skill_insights_query` / `uipath_skill_insights_add` | Skill insights store |
| `uipath_skill_manifest` | Provenance manifest JSON |
| `uipath_skill_check_updates` | Check whether the skills submodule has upstream updates |
| `uipath_skill_update` | Refresh the skills submodule cache (`force=true` bypasses the 6h throttle) |
| `uipath_skill_lessons_list` | List ranked lessons for a skill (from the insights store) |
| `uipath_skill_lessons_approve` | Persist an approved lesson for a skill |

The skills submodule auto-refreshes on CLI `chat` startup at most every six hours when `UIPATH_SKILLS_AUTO_REFRESH` is enabled (default). In Cursor, call `uipath_skill_update` to refresh on demand.

### Agent tools (`uipath_agent_*`) — require AWS Bedrock

| Tool | Description |
|------|-------------|
| `uipath_agent_bootstrap` | Legacy BA → SA → Dev → QA (`run_bootstrap_flow`). For the full BA → SA → ADD → TDD → Dev → QA + publish/deploy flow, run `/pdd` from the CLI; see [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md). |
| `uipath_agent_plan` | Read-only planner (`run_planner_agent`) |
| `uipath_agent_execute` | ReAct loop with full skill execution tools |
| `uipath_agent_classify_intent` | `classify_intent` (no cloud) |
| `uipath_agent_ba` / `uipath_agent_sa` | Single-shot PDD / SDD |

### Documentation tools (`uipath_doc_*`)

Activity docs lookup:

| Tool | Description |
|------|-------------|
| `uipath_doc_list_packages` / `uipath_doc_list_activities` | Bundled activity-docs index |
| `uipath_doc_get_activity` / `uipath_doc_get_package_overview` | Markdown from repo |
| `uipath_doc_search` | Name search across packages |
| `uipath_doc_find_activity` | Bundled + `.local/docs` + CLI discovery |
| `uipath_doc_query` | DEPRECATED alias of `query_uipath_docs` |

Project doc authoring (used by `/pdd` agents):

| Tool | Description |
|------|-------------|
| `uipath_doc_read_template` | Read the bundled markdown placeholder template for `pdd`/`sdd`/`add`/`tdd` |
| `uipath_doc_list_docs` | Report which of `pdd.md`/`sdd.md`/`add.md`/`tdd.md` exist under `<project_dir>/docs/` |
| `uipath_doc_read_doc` | Read an existing project doc from `<project_dir>/docs/<doc_type>.md` |
| `uipath_doc_write_doc` | Write/overwrite `<project_dir>/docs/<doc_type>.md` |

### Library tools (`uipath_library_*`)

The library is the curated UiPath knowledge base under `data/library/`. Always prefer these tools over raw `Read`/`Grep` — they apply ranking, citation lines, and overlay precedence. See [LIBRARY_LEARNING.md](LIBRARY_LEARNING.md) and [LIBRARY_AUTHORING.md](LIBRARY_AUTHORING.md).

| Tool | Description |
|------|-------------|
| `uipath_library_list` | List books with chapter counts and manifest tags |
| `uipath_library_toc` | Chapters and sections for one book |
| `uipath_library_read_section` | Section content with inline citation |
| `uipath_library_search` | Keyword search across sections |
| `uipath_library_lookup` | Question-style lookup that returns ranked sections |
| `uipath_library_propose_section` | Stage a NEW_SECTION proposal for review |
| `uipath_library_propose_chapter` | Stage a NEW_CHAPTER proposal (creates the chapter folder) |
| `uipath_library_list_proposals` | List pending proposals awaiting human review |
| `uipath_library_approve_proposal` | Approve a pending proposal and write it into the library |
| `uipath_library_reject_proposal` | Drop a pending proposal without writing |

### Design tools (`uipath_design_*`)

The design gate is an optional per-project write-lock. When `UIPATH_DESIGN_APPROVAL_ENABLED=1`, projects start with `status="pending"` and writes are blocked until a design proposal is approved.

| Tool | Description |
|------|-------------|
| `uipath_design_propose` | Submit a design proposal for a project (releases write-lock once approved) |
| `uipath_design_approve` | Approve a pending design by id; the project becomes writable |
| `uipath_design_reject` | Reject a pending design; the project stays write-locked |
| `uipath_design_list` | List proposals (optionally filter by `project_dir` or `status`) |
| `uipath_design_status` | Read-only status of the design gate for a project |

### Memory tools (`uipath_memory_*`)

| Tool | Description |
|------|-------------|
| `uipath_memory_load` / `uipath_memory_save` / `uipath_memory_append` | Global + optional project `memory.md` |

### MCP resources

- `uipath://skill/<name>` — full skill markdown
- `uipath://doc/<package>/overview` and `uipath://doc/<package>/<ActivityName>` — bundled activity-docs (when present under the repo `skills` layout)
- `uipath://project/context` — JSON with `project.json` summary and memory excerpt when `project.json` exists under `UIPATH_MCP_PROJECT_ROOT`

### Pattern: Validate and Fix Loop

```
Validate this workflow using UiPath Studio and fix any errors:
[paste XAML or point to file]
```

Cursor can call `uipath_workflow_validate` (and `uipath_workflow_validate_loop` for the error list contract), then edit files with `uipath_workflow_write_file`.

### Pattern: Runtime Testing

```
Run this workflow and check for runtime errors:
Project: ./my-project
File: Main.xaml
Input: {"orderId": "12345"}
```

Use `uipath_workflow_run` with `input_arguments` as a JSON string.

### Prerequisites for MCP Tools

- **UiPath CLI (`uip`)** installed and on PATH
- **UiPath Studio** running (for `--use-studio` validation)
- **Python environment** activated with `pip install -e ".[mcp]"`

### Verify MCP is Working

In Cursor, check MCP status in Settings > MCP. The `uipath-builder-agent` server should show as connected.

If not connected:
1. Check Python environment is active
2. Verify `mcp` package is installed: `pip show mcp`
3. Check `.cursor/mcp.json` exists and has correct paths

---

## Best Practices

### 1. Be Specific About Requirements

**Less effective:**
```
Create an Excel workflow
```

**More effective:**
```
Create a workflow that:
- Reads data from Sheet1 of input.xlsx
- Filters rows where Column A contains "Active"
- Writes filtered results to output.xlsx Sheet1
- Logs the count of filtered rows
```

### 2. Specify Project Context

If you're working on an existing project:

```
I'm working on a REFramework project that processes invoices.
The Config.xlsx has these settings: [list]
I need to add retry logic to the HTTP calls in ProcessTransaction.xaml
```

### 3. Use Superpowers for Complex Work

For multi-file changes or new features:

```
I need to add Document Understanding to my invoice processor.
Let's use the brainstorming skill to design this properly.
```

### 4. Validate Generated Code

Generated XAML should be validated in UiPath Studio:
1. Copy generated files to your UiPath project
2. Open in Studio
3. Run Workflow Analyzer (Design > Analyze Project)
4. Fix any warnings/errors

If validation fails, share the errors:
```
The generated XAML has these errors:
[paste Workflow Analyzer output]
```

---

## Common Tasks

### Create a New UiPath Project

```
Create a new UiPath project structure for an attended automation that:
- Processes customer requests
- Uses modern Excel activities
- Targets Windows with .NET 6
```

### Add Error Handling

```
Add Try-Catch error handling to this workflow:
[paste XAML]

Requirements:
- Catch BusinessRuleException separately
- Log errors with full context
- Set transaction status on failure
```

### Generate Test Cases

```
Generate test cases for this workflow:
[paste XAML or describe logic]

Include:
- Happy path
- Edge cases
- Error scenarios
```

### Convert Classic to Modern

```
Convert this classic UI automation to modern design:
[paste XAML with Attach Browser, etc.]
```

---

## Troubleshooting

### Skills Not Loading

Verify the setup completed:
```powershell
# Check if skills link exists
dir .cursor\skills
```

If missing, re-run setup:
```powershell
.\ops\scripts\setup-cursor.ps1 -Force
```

### Submodule Not Initialized

```
Error: skills/skills directory not found
```

Run:
```bash
git submodule update --init --recursive
```

### Generated XAML Has Errors

Common issues:

1. **Missing namespace** - Ask Cursor to add the required namespace
2. **Wrong activity name** - Specify the exact activity from UiPath docs
3. **Invalid property** - Check the activity's property names in Studio

Example fix request:
```
The generated XAML has error: "BC30451: 'UseExcelFile' is not declared"
Add the required namespace for Excel activities.
```

### 5. Use the Right UI Skill

Use `uipath-rpa` when the task creates or edits an automation. Use
`uipath-interact` only when the task drives a running app or browser directly,
such as taking screenshots, reading current UI state, clicking a live button, or
verifying behavior after a build.

### Superpowers Not Available

If superpowers skills don't appear:
1. Check plugin is installed in Cursor settings
2. Restart Cursor
3. Verify with: Settings > Extensions > Cursor Plugins

---

## Comparison: Cursor vs CLI

| Feature | Cursor (no MCP) | Cursor (with MCP) | CLI (`uipath-claude chat`) |
|---------|-----------------|-------------------|---------------------------|
| Skills | All 21 UiPath skills | All 21 UiPath skills | All 21 UiPath skills |
| Superpowers | Via plugin | Via plugin | Not available |
| Runtime validation | Manual (Studio) | Via MCP tools | Automatic |
| Package installation | Manual (Studio) | Via MCP tools | Automatic |
| Static validation | Manual | Via MCP tools | Automatic |
| Orchestrator API | Manual | Manual | Built-in tools |
| Session memory | Cursor context | Cursor context | Persistent memory |
| Subagents | Cursor Task tool | Cursor Task tool | LangGraph agents |
| Best for | Quick generation | Full dev workflow | Batch automation |

**Recommendation:**
- Use **Cursor + MCP** for the best IDE experience with validation
- Use **Cursor (no MCP)** for quick design and generation
- Use **CLI** for batch operations and CI/CD integration

---

## Further Reading

- [README.md](../README.md) - Project overview
- [USER_GUIDE.md](USER_GUIDE.md) - CLI usage guide
- [skills/skills/](../skills/skills/) - Browse skill source files
- [framework/mcp_server/](../framework/mcp_server/) - MCP server source
- [UiPath Documentation](https://docs.uipath.com/) - Official reference
