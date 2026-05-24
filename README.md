# UiPlan: Agent-of-Agents Builder Orchestrator

A LangGraph-based orchestrator that transforms a business brief into a complete UiPath automation delivery package.

## What It Does

UiPlan compresses the typical automation delivery lifecycle into one supervised run. Submit a business brief and get:

- **Planning docs**: `spec.md`, `plan.md`, `tasks.md`
- **Design package**: `PDD.md`, `SDD.md`, `ADD.md`
- **Build artifacts**: `generated-flow.json`, `run-flow.ps1`
- **Runtime evidence**: `execution-evidence.json`, platform verification
- **Interactive viewer**: Real-time monitoring dashboard

## The Problem

Automation delivery is fragmented:
- Requirements live in one place
- Technical design gets rewritten separately
- Platform resources are provisioned manually
- Verification evidence is scattered
- When scope changes, context is lost

## The Solution

A deterministic 7-phase pipeline with specialist agents:

1. **assign_agents** - Map requirements to agent roles
2. **generate_design_docs** - Create PDD/SDD/ADD with constraints
3. **generate_uipath_artifacts** - Build Flow definitions and scripts
4. **provision_resources** - Create queues, assets, verify access
5. **execute_flow** - Run the generated workflow
6. **emit_ui_events** - Stream events to monitoring viewer
7. **summarize_handoff** - Package evidence for handoff

Each phase produces structured, reviewable outputs.

## Quick Start

### Prerequisites

- Python 3.12+
- UiPath Automation Cloud tenant
- `uipath` CLI (Python SDK)
- `uip` CLI (Node.js, for platform operations)

### Run the Orchestrator

```bash
cd agents/builder-orchestrator

# Run with sample brief
uv run python -c "
import json
from pathlib import Path
from main import run_orchestrator

brief = json.loads(Path('../../samples/agent-of-agents/brief.enterprise-incident.real.json').read_text())
state = run_orchestrator(brief)
print(f'Run ID: {state[\"runId\"]}')
print(f'Status: {state[\"handoff\"][\"status\"]}')
"
```

### View Results

1. **Check output folder**: `agents/builder-orchestrator/out/<runId>/`
   - Planning: `docs/spec.md`, `docs/plan.md`, `docs/tasks.md`
   - Design: `docs/PDD.md`, `docs/SDD.md`, `docs/ADD.md`
   - Artifacts: `artifacts/generated-flow.json`, `artifacts/run-flow.ps1`
   - Evidence: `evidence/execution-evidence.json`

2. **Open viewer**: `ui/copilotkit/viewer.html`
   - 7 interactive tabs: UiPlan, Diagrams, Tasks, Constraints, Execution, Resources, Docs
   - Real-time event stream from latest run

## Key Features

### Agent-of-Agents Model
Named specialists own each delivery phase. The supervisor coordinates but doesn't do the work.

### Typed Planning Contract
`spec → plan → tasks` forms a machine-readable contract that drives all downstream generation.

### Constraint Intelligence
- Extracts constraints from brief, codebase, and skill critical rules
- Classifies by severity (high/medium/low)
- Renders as dependency graph in viewer
- Blocks progression on violations

### Evidence-First Handoff
Every run produces:
- Machine-readable artifacts
- Command logs with timestamps
- Platform verification (queues, assets, jobs)
- Orchestrator telemetry integration

### Real Platform Integration
- Creates queues and assets in Orchestrator
- Verifies permissions and folder access
- Pulls job execution telemetry
- No mocks - uses live tenant data

## Technical Stack

- **Orchestration**: LangGraph state machine
- **Runtime**: UiPath Python SDK (`uipath` package)
- **Platform ops**: UiPath unified CLI (`uip`)
- **Viewer**: CopilotKit static dashboard
- **Testing**: pytest with contract validation

## Repository Structure

```
uipath-builder-agent/
├── agents/
│   └── builder-orchestrator/     # Main orchestrator agent
│       ├── main.py               # LangGraph pipeline
│       ├── out/                  # Run outputs
│       └── langgraph.json        # Entry point config
├── framework/
│   ├── models/                   # Pydantic models for UiPlan contract
│   ├── constraints/              # Constraint extraction and classification
│   └── tests/                    # Test suite
├── samples/
│   └── agent-of-agents/          # Sample business briefs
├── ui/
│   └── copilotkit/
│       ├── viewer.html           # Interactive monitoring dashboard
│       └── current/              # Latest run event stream
├── skills/                       # UiPath skills submodule
└── extensions/                   # Project-specific skill extensions
```

## Safety and Governance

- **No Production deploys** from assistant-driven flows
- **Human approval** as explicit runtime constraint
- **Max iteration budgets** on build/deploy loops with escalation
- **Secrets management** via Orchestrator Assets (never hardcoded)
- **Audit trail** in every run output

## Constraints System

The orchestrator extracts and enforces constraints from:

1. **Brief constraints**: Explicit rules in the business brief
2. **Skill critical rules**: Must/never statements from skill documentation
3. **Codebase constraints**: Project-level rules from CLAUDE.md/AGENTS.md

Constraints are:
- Severity-classified (high/medium/low)
- Validated at phase boundaries
- Rendered as dependency graph
- Block progression on critical violations

## Testing

```bash
# Run all tests
pytest framework/tests/

# Test specific component
pytest framework/tests/unit/constraints/
pytest framework/tests/unit/docs/

# Run with verbose output
pytest -v
```

## Configuration

### Environment Variables

Create `.env` in `agents/builder-orchestrator/`:

```bash
UIPATH_BASE_URL=https://cloud.uipath.com/<org>/<tenant>
UIPATH_CLIENT_ID=<your-client-id>
UIPATH_CLIENT_SECRET=<your-client-secret>
```

Or authenticate with:
```bash
uipath auth
```

### Project Settings

Edit `agents/builder-orchestrator/uipath.json`:

```json
{
  "name": "builder-orchestrator",
  "description": "UiPlan Agent-of-Agents Builder",
  "functions": {
    "run_orchestrator": "main.py:run_orchestrator"
  }
}
```

## Extending

### Add a New Phase

1. Define phase function in `main.py`:
```python
def new_phase(state: OrchestratorState) -> OrchestratorState:
    _add_phase_event(state, "new_phase", "running")
    # Phase logic here
    _add_phase_event(state, "new_phase", "completed")
    return state
```

2. Add to graph:
```python
graph.add_node("new_phase", new_phase)
graph.add_edge("previous_phase", "new_phase")
graph.add_edge("new_phase", "next_phase")
```

### Add Custom Constraints

Add to `framework/constraints/extractor.py`:
```python
def extract_custom_constraints(source: str) -> list[Constraint]:
    # Custom extraction logic
    return constraints
```

## License

MIT License - see [LICENSE](LICENSE)

## Documentation

- **CLI Reference**: `docs/uipath-cli.md`
- **Workflows Guide**: `docs/uipath-workflows.md`
- **Skills Submodule**: `skills/` (upstream UiPath skills catalog)

## Contributing

This is a hackathon submission. For production use, consider:

1. Adding retry logic with exponential backoff
2. Implementing proper logging and observability
3. Adding health checks and monitoring
4. Securing secrets management
5. Adding comprehensive integration tests
6. Implementing proper error recovery
