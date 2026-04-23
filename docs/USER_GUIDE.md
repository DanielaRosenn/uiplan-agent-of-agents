# User Guide

This guide walks you through setting up and using UiPath Claude Code for UiPath automation development.

## Quick Start (5 Minutes)

### Prerequisites

- Python 3.10+
- AWS account with Bedrock access (Claude models)
- UiPath CLI (`uip`) installed and configured
- Git

### Installation

Use one assistant per clone. This repo supports both Cursor and Claude, but each local clone should pick one setup path.

Recommended Claude-first setup:

```powershell
.\ops\scripts\claude-quickstart.ps1
```

```bash
bash ops/scripts/claude-quickstart.sh
```

The quickstart scripts persist your local selection in `.assistant-choice` and block cross-setup unless you pass `-Force` / `--force`.

```bash
# Clone the repository
git clone <repo-url>
cd uipath-builder-agent

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install the package
pip install -e ".[dev]"

# Initialize git submodules (for official skills)
git submodule update --init --recursive
```

### Verify AWS Credentials

```bash
aws sts get-caller-identity
```

You should see your AWS account info. If not, configure AWS credentials:

```bash
aws configure
```

### Start Chatting

```bash
uipath-claude chat
```

## First Chat Session

When you start a chat session, you can ask the agent to create UiPath automations:

```
You: Create a workflow that reads emails from Outlook and logs the subjects
```

The agent will analyze your request, route it to the appropriate skill, and generate UiPath project files.

## Agentic Mode

For fully automated project creation with validation, enable agentic mode:

```powershell
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"  # See tool calls
uipath-claude chat
```

In agentic mode, the agent will:

1. Create `project.json` with proper structure
2. Install required NuGet packages
3. Generate XAML workflow files
4. **Validate syntax** against UiPath Studio
5. **Execute workflows** to verify runtime behavior
6. Iterate and fix errors automatically until the workflow works

### Example Session

```
You: Create a UiPath project that reads data from Excel and writes to another sheet

+------------------------------------------------------------------------------+
| Iteration 1 of 25                              [>         ]                  |
+------------------------------------------------------------------------------+

   ensure_project_structure
     Created project.json at ./generated/chat/20260414-161008-bcb53f2f/project.json

+------------------------------------------------------------------------------+
| Iteration 2 of 25                              [>         ]                  |
+------------------------------------------------------------------------------+

   install_package
         -> UiPath.Excel.Activities
     Successfully installed UiPath.Excel.Activities

+------------------------------------------------------------------------------+
| Iteration 3 of 25                              [=>        ]                  |
+------------------------------------------------------------------------------+

   write_file
         -> Main.xaml
     Successfully wrote 2,341 bytes to Main.xaml

+------------------------------------------------------------------------------+
| Iteration 4 of 25                              [=>        ]                  |
+------------------------------------------------------------------------------+

   validate_file
         -> Main.xaml
     Validation passed: 0 errors
```

Generated files are saved to `generated/chat/{session-id}/`.

### Debug Output Modes

Control debug verbosity with environment variables:

```powershell
# Show formatted debug output (default in debug mode)
$env:UIPATH_DEBUG_AGENT = "1"

# Quieter tool logs (default is verbose: full tool args JSON)
# $env:UIPATH_DEBUG_VERBOSE = "0"

# Show raw JSON output (for debugging the debugger)
$env:UIPATH_DEBUG_RAW = "1"
```

**Formatted output** (default): Clean, human-readable with progress bars and status icons.

**Verbose output** (default `UIPATH_DEBUG_VERBOSE=1`): Includes full tool arguments in the console; set to `0` for shorter summaries.

**Raw output**: Shows complete JSON for all tool calls and results.

## Common Workflows

### Excel Automation

```
Create a workflow that reads an Excel file, filters rows where Amount > 1000, and writes results to a new sheet
```

### Email Automation

```
Create a workflow that reads unread emails from Outlook and saves attachments to a folder
```

### Web Automation

```
Create a workflow that opens a browser, logs into a website, and downloads a report
```

### Data Processing

```
Create a workflow that reads a CSV file, transforms the data, and uploads to Orchestrator queue
```

## Slash Commands

Use slash commands for quick actions in **`uipath chat`** (input starts with `/`). Which commands are accepted is controlled by **`UIPATH_CLAUDE_TOOL_PROFILE`** (`safe`, `uipath-dev`, or `all`); the **`safe`** profile includes the full SDLC set (`/pdd`, `/validate`, `/uiplan`, library commands, etc.). Full matrix: [SLASH_COMMANDS.md](SLASH_COMMANDS.md).

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show session status |
| `/skills` | List loaded skills |
| `/pdd <brief>` | Run the full BA -> SA -> ADD -> TDD -> Dev -> QA lifecycle (optionally publish + deploy) |
| `/bootstrap <brief>` | Legacy four-stage BA -> SA -> Dev -> QA flow |
| `/analyze` | Analyze current UiPath project |
| `/validate` | Validate XAML files |
| `/recall <term>` | Search session history |

### `/pdd` flags

`/pdd` runs the full lifecycle implemented in [`uipath_claude/query/pdd_lifecycle.py`](../uipath_claude/query/pdd_lifecycle.py).

| Flag | Default | Effect |
|------|---------|--------|
| `--project-type process\|maestro` | `process` | `process` runs `uip rpa` + `uip solution pack/publish` + `uip or processes create`; `maestro` runs `uip flow init/validate/pack` + `uip solution publish` + `uip flow process create`. |
| `--deploy` | off | After validate/run, also pack, publish, and create the Orchestrator process. Without this flag the lifecycle stops at QA. |
| `--folder <name>` | `Shared` | Orchestrator folder used by the `deploy` stage. |

Examples:

```bash
# RPA, no deploy
/pdd "Read invoices from Outlook and queue them" 

# RPA, full deploy to Shared folder
/pdd --deploy --folder Shared "Read invoices from Outlook and queue them"

# Maestro flow, full deploy
/pdd --project-type maestro --deploy "Triage support tickets across email and Slack"
```

Full reference: [PDD_LIFECYCLE.md](PDD_LIFECYCLE.md).

## Troubleshooting

### "No AWS credentials found"

Configure AWS credentials:

```bash
aws configure
# Or set environment variables:
set AWS_ACCESS_KEY_ID=...
set AWS_SECRET_ACCESS_KEY=...
set AWS_REGION=us-east-1
```

### "uip command not found"

Install the UiPath CLI:

```bash
# Download from UiPath Automation Cloud
# Or use winget:
winget install UiPath.CLI
```

### Validation errors persist

Enable debug mode to see tool calls:

```bash
set UIPATH_DEBUG_AGENT=1
```

Check that UiPath Studio is running for full validation.

## Understanding the Validation Process

The agent uses a two-stage validation process to ensure workflows work correctly:

### Stage 1: Static Validation

After generating a workflow, the agent calls `validate_file` to check:
- XAML is well-formed XML
- All activities have required properties
- Variable types are declared correctly
- Namespaces are imported
- Package dependencies are met

If static validation fails, you'll see error messages like:

```
Validation failed: 2 error(s)
- [Main.xaml] Missing required property 'Text' on LogMessage activity
- [Main.xaml] Variable 'emails' is not declared
```

The agent will fix these and re-validate.

### Stage 2: Runtime Testing

After static validation passes, the agent calls `run_workflow` to actually execute the workflow:
- Runs the workflow in UiPath Studio/Robot
- Captures runtime errors and logs
- Detects issues that validation can't catch

Common runtime errors:
- **Wrong property names**: `GetOutlookMailMessages.Result` → should be `.Messages`
- **Null references**: Variable not set before use
- **Type mismatches**: Passing wrong data type to activity
- **Logic errors**: Incorrect control flow

If runtime testing fails, you'll see:

```
RUNTIME EXECUTION: FAILED

ERROR: The property 'Result' does not exist on 'GetOutlookMailMessages'
Activity: GetOutlookMailMessages
Problem: Using incorrect output property

FIX NEEDED: Change GetOutlookMailMessages.Result to GetOutlookMailMessages.Messages
```

The agent reads this feedback, understands the fix, and updates the workflow.

### When Runtime Testing Happens

Runtime testing is automatic and happens:
1. After static validation passes
2. Before the agent declares the workflow complete
3. After any fix that changes workflow logic

You can see runtime testing in action in debug mode:

```bash
set UIPATH_DEBUG_VERBOSE=1
uipath-claude chat
```

### Skills not loading

Ensure submodules are initialized:

```bash
git submodule update --init --recursive
```

## Environment Variables Reference

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `UIPATH_CLAUDE_MODEL` | Bedrock model ID | Claude 3 Sonnet |
| `UIPATH_AGENTIC_MODE` | Enable tool-use loops | `0` |
| `UIPATH_DEBUG_AGENT` | Show debug output | `0` |
| `UIPATH_DEBUG_VERBOSE` | Show full tool args/results | `1` |
| `UIPATH_DEBUG_RAW` | Show raw JSON output | `0` |
| `UIPATH_MAX_ITERATIONS` | Maximum ReAct loop iterations | `25` |
| `UIPATH_CHAT_OUTPUT_DIR` | Override output directory | `generated/chat/` |

## Getting Help

- Check `/help` for available commands
- Review `docs/ARCHITECTURE.md` for system design
- Look at `skills/skills/` for available automation templates