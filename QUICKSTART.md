# UiPath Claude Code - Quick Start Guide

## Install

```bash
git clone <repo-url>
cd uipath-builder-agent-sprint-1
python -m venv .venv
# Windows:
.\.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate
pip install -e ".[dev]"
git submodule update --init --recursive
```

## AWS Setup (Bedrock)

```bash
aws sts get-caller-identity
```

If this fails, configure credentials first.

Optional overrides:

```bash
# Defaults
set AWS_REGION=us-east-1
set UIPATH_CLAUDE_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

## Start Chat

```bash
uipath-claude chat
```

Exit with `exit` or `quit`.

## Slash Commands

- `/help` - Show available commands
- `/status` - Session status
- `/skills` - Skills summary
- `/analyze [path]` - Analyze project path
- `/bootstrap` - Start bootstrap flow
- `/chat` - Indicates you are already in chat mode

## Start Bootstrap

```bash
uipath-claude start-project "MyProject"
```