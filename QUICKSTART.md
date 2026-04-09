# UiPath Claude Code - Quick Start Guide

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd uipath-builder-agent-sprint-1

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install package in editable mode
pip install -e ".[dev]"
```

## Running the Agent

### Conversational Chat Mode

```bash
# Start chat with welcome banner
python -m cli.main chat

# Start chat without banner
python -m cli.main chat --no-banner
```

### Bootstrap Flow Mode

```bash
# Start the full BA -> SA -> HITL -> Developer -> QA flow
python -m cli.main start-project
```

## Slash Commands

During a chat session, you can use these commands:

| Command | Alias | Description |
|---------|-------|-------------|
| `/help` | `/h`, `/?` | Show available commands |
| `/status` | - | Show current session status |
| `/skills` | `/sk` | List available skills |
| `/analyze` | `/wa` | Run UiPath Workflow Analyzer |

## Project Detection

The agent automatically detects UiPath projects when you run it from:
- A directory containing `project.json`
- A directory containing `*.uiproj` files
- Up to 5 parent directories above

When detected, you'll see the project name in the welcome banner.

## Memory Files

Create persistent context that loads on every session:

### Global Memory
`~/.uipath-claude/memory.md`

```markdown
# My UiPath Preferences

- Always use VB.NET expression language
- Target framework: Windows
- Prefer REFramework for transactional processes
```

### Project Memory
`.uipath-claude/memory.md` (in your project root)

```markdown
# Project-Specific Context

- This project uses Orchestrator queues
- Database: SQL Server 2019
- Authentication: Windows Auth
```

## Example Session

```
$ python -m cli.main chat

       ┌─────────┐
       │  o   o  │
       │    ▼    │
       │  └───┘  │
       └────┬────┘
          ┌─┴─┐
         ─┤   ├─
          └───┘

  UiPath Claude Code v0.1.0
  Project: MyRPAProject
  Model: claude-sonnet-4-5
  Working in: C:\projects\my-rpa-project

You: /help

Available commands:

  /help - Show available commands (aliases: /h, /?)
  /status - Show current session status
  /skills - List available skills (aliases: /sk)
  /analyze - Run UiPath Workflow Analyzer (aliases: /wa)

You: /status

Session Status:

  Session ID: abc123...
  Model: claude-sonnet-4-5
  Project: MyRPAProject
  Working Dir: C:\projects\my-rpa-project

You: Create a simple workflow that reads from Excel