# Architecture

UiPath Claude Code follows the Claude Code architecture pattern, adapted for UiPath automation.

## Directory Structure

```
uipath_claude/
├── query/          # Conversation engine (Claude Code: src/query/)
├── agents/         # Specialized agent modes
├── artifacts/      # Generated artifacts and writers
├── tools/          # Tool implementations
├── skills/         # Skill discovery and management
├── commands/       # Slash command system
├── context/        # Project and environment detection
├── memory/         # Memory persistence
├── hooks/          # Event hooks
├── rendering/      # Output formatting
└── cli/            # CLI interface
```

## Agent Modes

All agents share the same conversation engine, specialized via:

1. **System Prompts** - Role-specific instructions
2. **Tool Availability** - Filtered tool sets
3. **Skill Loading** - Role-specific skills

### Available Agents

- **Conversational** (default): All skills, general assistance
- **BA**: PDD creation, business process design
- **SA**: SDD creation, solution architecture
- **Developer**: Workflow implementation, coding
- **QA**: Code review, testing, validation

## Skill Loading

Skills are loaded from multiple sources with precedence:

1. Project-local (`.uipath-claude/skills/`)
2. User custom (`~/.cursor/skills/`)
3. Official UiPath (`skills/skills/` submodule)
4. Cato templates (`templates/` submodule)

## Runtime Controls

Runtime behavior is configured by environment variables:

- `UIPATH_CLAUDE_TOOL_PROFILE=safe|uipath-dev|all`
  - Resolved in `uipath_claude.tools.profiles`.
  - Controls which slash commands are available to the session.
- `UIPATH_CLAUDE_REQUIRE_APPROVAL=true`
  - Enforces the approval gate in `uipath_claude.tools.uipath.approval`
    for guarded UiPath CLI operations.
  - Approval can be granted per run with
    `UIPATH_CLAUDE_CLI_APPROVED=true` or `UIPATH_CLAUDE_APPROVED=true`.

## Session Recall

Session recall is exposed through `/recall <term>` and implemented in
`uipath_claude.commands.recall`, backed by
`uipath_claude.query.session_search`.

## Agentic Execution Flow

When `UIPATH_AGENTIC_MODE=1`, the agent uses a ReAct-style tool-use loop:

```
User Request
    ↓
Route to Skill
    ↓
┌─────────────────────────────────┐
│  AgenticExecutor (max 15 iter)  │
│  ┌───────────────────────────┐  │
│  │ 1. LLM generates response │  │
│  │ 2. Extract tool_calls     │  │
│  │ 3. Execute tools          │  │
│  │ 4. Append ToolMessage     │  │
│  │ 5. Loop until complete    │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
    ↓
Generated Project
```

### Skill Execution Tools

Located in `uipath_claude/tools/skill_execution_tools.py`:

| Tool | Purpose |
|------|---------|
| `ensure_project_structure` | Create project.json scaffold |
| `install_package` | Install NuGet packages via `uip` |
| `write_file` | Write files with XAML auto-fix |
| `read_file` | Read project files |
| `validate_file` | Validate XAML against Studio |
| `validate_and_fix_loop` | Iterative validation guidance |
| `find_activity_info` | Look up activity documentation |
| `query_uipath_docs` | Query UiPath Ask AI |
| `run_uip_command` | Execute arbitrary `uip` commands |
| `debug_workflow` | Debug workflow execution |

### XAML Auto-Fix

The `write_file` tool automatically corrects common LLM XAML issues:

- Unescapes `&lt;` / `&gt;` to `<` / `>`
- Removes `<![CDATA[` wrappers
- Strips extraneous `<xaml>` tags
- Validates XML structure before writing

### AgenticExecutor Class

Located in `uipath_claude/query/agentic_executor.py`:

```python
class AgenticExecutor:
    MAX_ITERATIONS = int(os.environ.get("UIPATH_MAX_ITERATIONS", "25"))
    
    def run(self, messages, system_prompt) -> AgenticResult:
        progress = AgenticProgressReporter() if debug else None
        
        for i in range(MAX_ITERATIONS):
            if progress:
                progress.iteration_start(i, MAX_ITERATIONS)
            
            response = model.invoke(messages)
            if no tool_calls:
                return final_response
            
            for tool_call in response.tool_calls:
                if progress:
                    progress.tool_call(tool_call.name, tool_call.args)
                
                result = execute_tool(tool_call)
                
                if progress:
                    progress.tool_result(tool_call.name, success, result)
                
                messages.append(ToolMessage(result))
```

**Key Features:**
- Configurable iteration limit via `UIPATH_MAX_ITERATIONS` (default: 25)
- Human-readable debug output with `AgenticProgressReporter`
- Progress bars and status indicators
- Multiple debug modes (formatted, verbose, raw)

## Bootstrap Flow

```
User Request
    ↓
BA Agent (PDD)
    ↓
SA Agent (SDD)
    ↓
Developer Agent (Code)
    ↓
QA Agent (Validation)
    ↓
Complete
```

## Evaluation Framework

The agent includes a LangSmith-style evaluation system for measuring quality:

```
uipath_claude/evaluation/
├── __init__.py
├── datasets.py      # Dataset management
├── evaluators.py    # Evaluation functions
└── runner.py        # Evaluation runner
```

### Evaluation Types

1. **Final Response Evaluator**: Checks if generated project is valid
   - Files created
   - Packages installed
   - Validation passed

2. **Trajectory Evaluator**: Checks if agent took correct tool sequence
   - Expected steps matched
   - Subsequence matching

3. **Single Step Evaluator**: Checks individual tool calls
   - Correct tool used
   - Correct arguments
   - Expected result

### Running Evaluations

```python
from uipath_claude.evaluation import EvaluationDataset, EvaluationRunner

dataset = EvaluationDataset.from_workflow_benchmarks()
runner = EvaluationRunner(target_function, evaluators)
run = await runner.run(dataset)
```

See [EVALUATION_RESULTS.md](EVALUATION_RESULTS.md) for latest results.

## Comparison with Claude Code

| Claude Code | UiPath Claude Code |
|-------------|-------------------|
| `src/query/` | `uipath_claude/query/` |
| `src/tools/` | `uipath_claude/tools/` |
| `src/skills/` | `uipath_claude/skills/` |
| `src/commands/` | `uipath_claude/commands/` |
| `src/components/` | `uipath_claude/rendering/` |
| `src/utils/hooks.ts` | `uipath_claude/hooks/` |
| `memory.md` | `uipath_claude/memory/` |
| TypeScript/React | Python/LangGraph |

For detailed comparison, see [docs/internal/CLAUDE_CODE_COMPARISON.md](internal/CLAUDE_CODE_COMPARISON.md) (internal only).
