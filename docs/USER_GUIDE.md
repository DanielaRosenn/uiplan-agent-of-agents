# User Guide

This guide walks you through setting up and using UiPath Claude Code for UiPath automation development.

## Quick Start (5 Minutes)

### Prerequisites

- Python 3.10+
- AWS account with Bedrock access (Claude models)
- UiPath CLI (`uip`) installed and configured
- Git

### Installation

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
4. Validate against UiPath Studio
5. Iterate and fix errors automatically

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

# Show full tool arguments and results (not truncated)
$env:UIPATH_DEBUG_VERBOSE = "1"

# Show raw JSON output (for debugging the debugger)
$env:UIPATH_DEBUG_RAW = "1"
```

**Formatted output** (default): Clean, human-readable with progress bars and status icons.

**Verbose output**: Includes full tool arguments and complete results.

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

Use slash commands for quick actions:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/status` | Show session status |
| `/skills` | List loaded skills |
| `/analyze` | Analyze current UiPath project |
| `/validate` | Validate XAML files |
| `/recall <term>` | Search session history |

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
| `UIPATH_CHAT_OUTPUT_DIR` | Override output directory | `generated/chat/` |

## Getting Help

- Check `/help` for available commands
- Review `docs/ARCHITECTURE.md` for system design
- Look at `skills/skills/` for available automation templates