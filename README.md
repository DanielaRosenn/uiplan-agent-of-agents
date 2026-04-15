# UiPath Claude Code

Conversational AI agent for UiPath automation, inspired by Claude Code architecture.

## How this project works

At a high level:

1. **Chat runtime** (`uipath-claude chat`) loads configuration, memory, and a **skill registry** built from several filesystem layers (see [Skills system](#skills-system)). The model receives system context plus tools (UiPath CLI, analyzer, skills execution, and so on).
2. **Skills** are markdown playbooks (`SKILL.md`) with YAML frontmatter. They teach the agent procedures, constraints, and product vocabulary. Official content lives in the `skills/skills` git submodule; your team adds skills under `extensions/skills` or locally without forking the submodule.
3. **Slash commands** (`/skills`, `/bootstrap`, …) are registered on the in-session command registry and call into the same Python packages as the CLI.
4. **Skill insights** (optional) store short, durable learnings *about* skills in JSON files (user, project, or shared). They complement static `SKILL.md` content and are designed so the UiPath submodule stays read-only.

For deeper technical detail, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Features

- **Conversational Chat**: Interactive AI assistant for UiPath development
- **Bootstrap Flow**: Automated PDD → SDD → Code → QA workflow
- **Specialized Agents**: BA, SA, Developer, and QA modes
- **Multi-source skills with provenance**: User, project, team extensions, UiPath submodule, and optional template skills
- **Skill insights (learning layer)**: Record and query learnings per skill without editing submodule files
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

### Chat mode

```bash
uipath-claude chat
```

Requires AWS Bedrock credentials. Verify with:

```bash
aws sts get-caller-identity
```

### Agentic execution mode

The agent supports an agentic execution mode with ReAct-style tool-use loops. When enabled, the agent can:

- Create UiPath project structures (`ensure_project_structure`)
- Install NuGet packages (`install_package`)
- Write and validate XAML files (`write_file`, `validate_file`)
- Debug and iterate until validation passes (`validate_and_fix_loop`)
- Query UiPath documentation (`find_activity_info`, `query_uipath_docs`)

Enable agentic mode (Windows PowerShell):

```powershell
$env:UIPATH_AGENTIC_MODE = "1"
$env:UIPATH_DEBUG_AGENT = "1"   # Optional: show tool calls
uipath-claude chat
```

Generated projects are saved to `generated/chat/{session-id}/`.

### Environment variables

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
| `UIPATH_INCLUDE_TEMPLATE_SKILLS` | Include `templates/**/.cursor/skills` (and `.claude/skills`) | `0` |

### Runtime controls

Tool profiles control which slash commands are available:

- `UIPATH_CLAUDE_TOOL_PROFILE=safe` — Non-destructive commands only
- `UIPATH_CLAUDE_TOOL_PROFILE=uipath-dev` — Safe + `/validate`
- `UIPATH_CLAUDE_TOOL_PROFILE=all` — All commands

Approval settings for CLI operations:

- `UIPATH_CLAUDE_REQUIRE_APPROVAL=true` — Require approval before guarded operations
- `UIPATH_CLAUDE_CLI_APPROVED=true` — Pre-approve (for CI/automation)

### Bootstrap flow

```bash
uipath-claude start-project "MyProject"
```

### Slash commands

- `/help` — Show available commands
- `/status` — Show session status
- `/skills` — List available skills (shows **`[origin]`** per skill: `user`, `project`, `extensions`, `uipath-submodule`, `template`)
- `/analyze` — Analyze UiPath project
- `/bootstrap` — Start bootstrap flow
- `/chat` — Indicates you are already in chat mode
- `/recall <term>` — Search recent session messages for matching text

## Skills system

Skills are domain playbooks (`SKILL.md` under a folder named after the skill). The loader merges **multiple roots**; **first source wins** when two folders define the same skill `name` in frontmatter.

### Source priority (highest first)

| Order | Origin | Path | Purpose |
|------:|--------|------|---------|
| 1 | `user` | `~/.cursor/skills/` | Personal overrides (not in git) |
| 2 | `project` | `.uipath-claude/skills/`, `.claude/skills/` | Per-checkout / project-local |
| 3 | `extensions` | `extensions/skills/` | **Team-shared** skills in this repo (safe from submodule updates) |
| 4 | `uipath-submodule` | `skills/skills/` | Official **UiPath/skills** submodule |
| 5 | `template` | `templates/**/.cursor/skills` (and `.claude/skills`) | Opt-in via `UIPATH_INCLUDE_TEMPLATE_SKILLS=1` |

If `.uipath-claude/config.yaml` defines `skills.sources`, those paths are merged with defaults (see `uipath_claude/skills/sources.py`).

### Team extensions

Add new team skills under **`extensions/skills/<skill-name>/SKILL.md`**. See [extensions/skills/README.md](extensions/skills/README.md) for naming and collision rules. Do not edit files inside `skills/skills/` for team customization; override by skill name from a higher-priority layer instead.

### Skills manifest (provenance audit)

Generate a JSON snapshot of every resolved skill, its `origin`, and paths (useful for CI and answering “where did this skill come from?”):

```bash
# From repository root, editable install on PATH
python -c "from uipath_claude.commands.skills import print_skills_manifest; print(print_skills_manifest('skills-manifest.json'))"
```

Open `skills-manifest.json`: fields include `generated_at`, `submodule_commit`, `total_skills`, `counts`, `by_origin`, and `skills`.

## Skill insights (learning)

Insights are **short notes about a skill** (gotchas, failures, what worked, edge cases, proposed doc improvements). They are stored **separately** from `SKILL.md` so the UiPath submodule can stay pristine.

### Storage layers (highest priority first)

| Layer | Directory | Typical use |
|-------|-----------|-------------|
| User | `~/.cursor/skill-insights/` | Personal preferences and experiments |
| Project | `.uipath-claude/skill-insights/` | Per-machine / per-checkout (often gitignored) |
| Shared | `extensions/skill-insights/` | Team-curated, PR-reviewed (see [extensions/skill-insights/README.md](extensions/skill-insights/README.md)) |

Merged view deduplicates by content hash; summaries favor **gotchas** and **failure patterns** first, with a token budget (see `SkillInsightsStore.get_summary` in code).

### Phases (how to adopt learning)

Think of learning in **three phases**; you can stop at any phase that fits your risk tolerance.

**Phase 1 — Explicit capture (available now)**  
Use the Python API or small scripts to record what the team learns:

```bash
python -c "from uipath_claude.tools.skill_insights_tool import skill_insights_tool as t; print(t('add','uipath-rpa',insight_type='gotcha',content='Close Studio before CLI analyze',layer='project')); print(t('query','uipath-rpa'))"
```

- **`add`** — Store an insight (set `layer` to `user` or `project`).
- **`query`** — List insights and a markdown `summary` for prompting.
- **`propose`** — Append to `extensions/skill-insights/proposals/` for human review before promoting to shared JSON.

**Phase 2 — Usage telemetry and auto-capture (library ready)**  
`SkillUsageTracker`, `post_skill_execution_hook`, and `SkillExecutionContext` in `uipath_claude/skills/usage_tracker.py` and `execution_hook.py` can record success/failure and optionally write `failure_pattern` / `edge_case` insights. Wiring them into your **skill execution** path (e.g. around the same place `SkillTool` runs) is integration work: call the hook after each skill run with `success`, `tool_calls`, and optional `error`.

**Phase 3 — Automatic injection into model context (when wired)**  
When your integration loads a skill for the model, append `SkillInsightsStore.get_summary(skill_name)` (or a future `get_skill_with_insights` helper) to the skill body so the model sees “Learned from usage” before acting. Today the storage and summary logic exist; connect them wherever skill text is assembled for the LLM.

### Privacy note

Insights may contain **error text or paths**. Keep sensitive content in **user** or **project** layers; sanitize before committing anything under `extensions/skill-insights/`.

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

# Skills + provenance + insights tests only
pytest tests/unit/skills tests/integration/test_skills_provenance.py -q

# Run with coverage
pytest tests/ --cov=uipath_claude --cov-report=html

# Format code
black uipath_claude/ tests/

# Lint code
ruff check uipath_claude/ tests/
```

## License

MIT
