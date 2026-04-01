# UiPath Builder Agent

Conversational AI agent for generating, modifying, and deploying UiPath RPA projects.

## Features

- 🤖 Dual-mode: Bootstrap new projects + conversational development
- 🔧 Dynamic skill discovery from UiPath skills repository
- 📋 Guided requirements gathering (BA persona)
- 🏗️ Technical design generation (SA persona)
- ✅ QA validation with constraint checking
- 🚀 Deploy to UiPath Orchestrator

## Installation

```bash
# Clone repository
git clone <repo-url>
cd uipath-builder-agent

# Initialize submodules
git submodule update --init --recursive

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

## Quick Start

```bash
# Start conversational session
uipath-builder chat

# Bootstrap a new project
uipath-builder start-project --input requirements.md
```

## Development

```bash
# Run tests
pytest

# Format code
black .
ruff check .

# Type check
mypy agent/
```

## Architecture

See [Design Specification](docs/superpowers/specs/2026-04-01-uipath-builder-agent-design.md)
