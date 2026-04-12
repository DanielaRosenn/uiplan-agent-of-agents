# UiPath Claude Code

Conversational AI agent for UiPath automation, inspired by Claude Code architecture.

## Features

- **Conversational Chat**: Interactive AI assistant for UiPath development
- **Bootstrap Flow**: Automated PDD → SDD → Code → QA workflow
- **Specialized Agents**: BA, SA, Developer, and QA modes
- **Multi-Source Skills**: Official UiPath skills + custom skills + project-local skills
- **Slash Commands**: `/help`, `/status`, `/skills`, `/analyze`, `/bootstrap`
- **UiPath Integration**: Workflow Analyzer, Orchestrator API, Ask AI
- **Memory System**: Global and project-specific memory persistence
- **Hooks System**: Event-driven automation (session start, tool use, file changes)

## Installation

```bash
# Clone repository
git clone <your-repo-url>
cd uipath-builder-agent-sprint-1

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install package
pip install -e ".[dev]"

# Initialize submodules (for official UiPath skills)
git submodule update --init --recursive
```

## Usage

### Chat Mode

```bash
uipath-claude chat
```

Requires AWS Bedrock credentials. Verify with:

```bash
aws sts get-caller-identity
```

Optional overrides:

```bash
set AWS_REGION=us-east-1
set UIPATH_CLAUDE_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
```

### Bootstrap Flow

```bash
uipath-claude start-project "MyProject"
```

### Slash Commands

- `/help` - Show available commands
- `/status` - Show session status
- `/skills` - List available skills
- `/analyze` - Analyze UiPath project
- `/bootstrap` - Start bootstrap flow
- `/chat` - Indicates you are already in chat mode

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Development

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=uipath_claude --cov-report=html

# Format code
black uipath_claude/ tests/

# Lint code
ruff check uipath_claude/ tests/
```

## License

MIT
