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
cd uipath-builder-agent

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

### Agentic Execution Mode

The agent supports an agentic execution mode with ReAct-style tool-use loops. When enabled, the agent can:

- Create UiPath project structures (`ensure_project_structure`)
- Install NuGet packages (`install_package`)
- Write and validate XAML files (`write_file`, `validate_file`)
- Debug and iterate until validation passes (`validate_and_fix_loop`)
- Query UiPath documentation (`find_activity_info`, `query_uipath_docs`)

Enable agentic mode:

```bash
set UIPATH_AGENTIC_MODE=1
set UIPATH_DEBUG_AGENT=1  # Optional: show tool calls
uipath-claude chat
```

Generated projects are saved to `generated/chat/{session-id}/`.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `AWS_REGION` | AWS region for Bedrock | `us-east-1` |
| `UIPATH_CLAUDE_MODEL` | Bedrock model ID | `anthropic.claude-3-sonnet-20240229-v1:0` |
| `UIPATH_AGENTIC_MODE` | Enable agentic tool-use loops | `0` |
| `UIPATH_DEBUG_AGENT` | Show formatted debug output | `0` |
| `UIPATH_DEBUG_VERBOSE` | Show full tool args/results (not truncated) | `0` |
| `UIPATH_DEBUG_RAW` | Show raw JSON output | `0` |
| `UIPATH_MAX_ITERATIONS` | Maximum ReAct loop iterations | `25` |
| `UIPATH_CLAUDE_TOOL_PROFILE` | Tool profile (`safe`, `uipath-dev`, `all`) | `safe` |
| `UIPATH_CLAUDE_REQUIRE_APPROVAL` | Require approval for CLI ops | `false` |
| `UIPATH_CLAUDE_CLI_APPROVED` | Pre-approve CLI operations | `false` |

### Runtime Controls

Tool profiles control which slash commands are available:

- `UIPATH_CLAUDE_TOOL_PROFILE=safe` - Non-destructive commands only
- `UIPATH_CLAUDE_TOOL_PROFILE=uipath-dev` - Safe + `/validate`
- `UIPATH_CLAUDE_TOOL_PROFILE=all` - All commands

Approval settings for CLI operations:

- `UIPATH_CLAUDE_REQUIRE_APPROVAL=true` - Require approval before guarded operations
- `UIPATH_CLAUDE_CLI_APPROVED=true` - Pre-approve (for CI/automation)

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
- `/recall <term>` - Search recent session messages for matching text

## Skills System

Skills provide domain knowledge and templates for the agent. They are loaded from multiple sources:

1. **Project-local**: `.uipath-claude/skills/` in your project
2. **User custom**: `~/.cursor/skills/`
3. **Official UiPath**: `skills/skills/` (git submodule)

Key skills included:

- `uipath-rpa` - RPA workflow templates and activity docs
- `uipath-automation` - General automation patterns
- `uipath-excel` - Excel automation
- `uipath-orchestrator-api` - Orchestrator integration
- `uipath-reframework` - REFramework templates

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## Evaluation

The agent includes a LangSmith-style evaluation framework for measuring quality:

```python
from uipath_claude.evaluation import EvaluationDataset, EvaluationRunner
from uipath_claude.evaluation import final_response_evaluator, trajectory_evaluator

# Load benchmark dataset
dataset = EvaluationDataset.from_workflow_benchmarks()

# Create runner with evaluators
runner = EvaluationRunner(
    target_function=your_agent_function,
    evaluators={
        "final_response": final_response_evaluator,
        "trajectory": trajectory_evaluator,
    }
)

# Run evaluation
run = await runner.run(dataset)
print(f"Pass rate: {run.summary['pass_rate']:.1%}")
```

See [docs/EVALUATION_RESULTS.md](docs/EVALUATION_RESULTS.md) for latest benchmark results.

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
