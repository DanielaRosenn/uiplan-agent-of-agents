# UiPath Builder Agent API Documentation

## Overview

The UiPath Builder Agent provides a conversational AI interface for generating UiPath RPA projects with proper architecture, constraints enforcement, and skill-based code generation.

---

## Core Components

### 1. State Management (`agent/state.py`)

#### `ProjectState` (TypedDict)

Complete state for the UiPath Builder Agent, tracking project metadata, design artifacts, generation state, and conversation flow.

**Required Fields:**
- `messages`: Annotated list with add_messages reducer for conversation history

**Optional Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `project_name` | str | Name of the UiPath project |
| `project_path` | str | File system path for project output |
| `template_type` | Literal | dispatcher \| performer \| lrw |
| `git_repo_url` | str | Git repository URL for version control |
| `mode` | Literal | bootstrap \| conversational |
| `current_phase` | Literal | ba \| sa \| hitl \| generation \| qa \| dev |
| `pdd` | dict | Process Design Document from BA |
| `sdd` | dict | Solution Design Document from SA |
| `artifacts` | dict[str, str] | Generated files (path → content) |
| `active_skills` | list[str] | Available skills for current context |
| `needs_clarification` | bool | BA clarification flag |
| `clarify_question` | str | BA's question to user |
| `clarification_answer` | str | User's answer |
| `requires_hitl` | bool | Human-in-the-loop required flag |
| `hitl_approved` | bool | HITL approval status |
| `hitl_feedback` | str | HITL rejection reason |
| `validation_errors` | list[str] | QA constraint violations |
| `qa_iterations` | int | Number of QA fix attempts (max 2) |
| `qa_report` | dict | Detailed QA validation report |
| `orchestrator_tenant` | str | UiPath Orchestrator tenant |
| `deployed_version` | str | Deployed package version |

---

### 2. Graph Orchestration (`agent/graph.py`)

#### Main Bootstrap Graph

Entry point: `ba` (Business Analyst persona)

**Flow:**
```
START → BA → SA → HITL (if complex) → Developer → QA → END
```

**Routing Functions:**

##### `route_after_ba(state: ProjectState) -> str`
Routes after BA persona completes:
- Returns `END` if needs clarification
- Returns `"sa"` if PDD is complete

##### `route_after_sa(state: ProjectState) -> str`
Routes after SA persona completes:
- Returns `"hitl"` if requires_hitl is True
- Returns `"developer"` otherwise

##### `route_after_hitl(state: ProjectState) -> str`
Routes after HITL review:
- Returns `"developer"` if approved
- Returns `END` if rejected

##### `route_after_qa(state: ProjectState) -> str`
Routes after QA validation:
- Returns `END` if no errors or max iterations reached
- Returns `"developer"` to retry fixes

#### Conversational Graph

Entry point: `conversational`

**Flow:**
```
START → Conversational Agent (loops until exit) → END
```

---

### 3. Persona Nodes

#### BA Persona (`agent/nodes/ba_persona.py`)

**Function:** `async ba_persona(state: ProjectState) -> dict`

**Purpose:** Business Analyst persona that gathers requirements and generates PDD.

**Input:** User's process description in messages

**Output:**
- `pdd`: dict - Process Design Document
- `needs_clarification`: bool - If more info needed
- `clarify_question`: str - Question to ask user
- `messages`: Updated conversation history

**PDD Structure:**
```json
{
  "project_name": "string",
  "description": "string",
  "business_value": "string",
  "actors": ["string"],
  "steps": ["string"],
  "data_inputs": ["string"],
  "data_outputs": ["string"],
  "exception_scenarios": ["string"]
}
```

#### SA Persona (`agent/nodes/sa_persona.py`)

**Function:** `async sa_persona(state: ProjectState) -> dict`

**Purpose:** Solution Architect persona that creates technical design (SDD) from PDD.

**Input:** PDD from state

**Output:**
- `sdd`: dict - Solution Design Document
- `requires_hitl`: bool - If design is complex
- `hitl_reason`: str - Why HITL is needed
- `messages`: Updated conversation history

**SDD Structure:**
```json
{
  "project_name": "string",
  "namespace": "Company.ProjectName",
  "template_type": "dispatcher|performer|lrw",
  "complexity": "simple|moderate|complex",
  "coded_activities": [
    {
      "class_name": "ActivityName",
      "purpose": "What it does",
      "inputs": ["param1"],
      "outputs": ["result1"]
    }
  ],
  "config_keys": [
    {
      "key": "MaxRetries",
      "description": "Maximum retry attempts",
      "default_value": "3"
    }
  ],
  "nuget_packages": [
    "UiPath.System.Activities",
    "UiPath.UIAutomation.Activities"
  ]
}
```

#### HITL Node (`agent/nodes/hitl_node.py`)

**Function:** `async hitl_node(state: ProjectState) -> dict`

**Purpose:** Human-in-the-loop review and approval of SDD before code generation.

**Input:** SDD from state, user response in last HumanMessage

**Output:**
- `hitl_approved`: bool - Approval status
- `hitl_feedback`: str - Rejection reason if applicable
- `messages`: Updated conversation history

**User Response Format:**
- `"approved"` - Proceed with generation
- `"rejected: <reason>"` - Abort with reason

#### Developer Node (`agent/nodes/developer_node.py`)

**Function:** `async developer_node(state: ProjectState) -> dict`

**Purpose:** Generate UiPath project files from SDD.

**Input:** SDD from state

**Output:**
- `artifacts`: dict[str, str] - Generated files
- `current_phase`: "generation"
- `messages`: Updated conversation history

**Generated Files:**
1. `project.json` - UiPath project configuration
2. `Main.cs` - Entry point coded workflow
3. `{ActivityName}.cs` - One file per coded activity

#### QA Node (`agent/nodes/qa_node.py`)

**Function:** `async qa_node(state: ProjectState) -> dict`

**Purpose:** Validate generated artifacts against HARD_CONSTRAINTS.

**Input:** artifacts from state

**Output:**
- `validation_errors`: list[str] - Constraint violations
- `qa_iterations`: int - Incremented retry counter
- `qa_report`: dict - Detailed validation report
- `messages`: Updated conversation history

**HARD_CONSTRAINTS Enforced:**
1. ✅ C# ONLY (no VB.Net)
2. ✅ Modern activities ONLY (no Classic)
3. ✅ Windows target ONLY
4. ✅ LogMessage for logging (no Console.Write)
5. ✅ Config in Config.xlsx (no hardcoding)
6. ✅ No secrets in code
7. ✅ BusinessRuleException vs ApplicationException
8. ✅ Modern namespaces only

#### Conversational Node (`agent/nodes/conversational.py`)

**Function:** `async conversational_agent(state: ProjectState) -> dict`

**Purpose:** Free-form conversation with skill invocation capability.

**Input:** messages from state

**Output:**
- `messages`: Updated with AI response
- `_should_end`: bool (if user says goodbye/exit)

**Available Tools:**
- `get_available_skills()`: List discoverable skills
- `invoke_skill(name, task, context)`: Execute specific skill

---

### 4. Skill System

#### Skill Discovery (`agent/skill_discovery.py`)

**Class:** `SkillDiscovery`

**Purpose:** Dynamically scan and register UiPath skills from git submodule.

**Methods:**

##### `__init__(skills_repo_path: Path)`
Initialize discovery with path to skills repository.

##### `discover_all_skills() -> dict[str, SkillMetadata]`
Walk skills directory and parse all SKILL.md files.

**Returns:** Registry mapping skill name to metadata

##### `_parse_skill_metadata(skill_dir: Path) -> SkillMetadata | None`
Parse SKILL.md YAML frontmatter and content.

**Returns:** SkillMetadata or None if parsing fails

##### `_extract_triggers(description: str) -> List[str]`
Extract trigger patterns from "TRIGGER when:" section.

##### `_scan_references(skill_dir: Path) -> List[Path]`
Find all reference docs in skill/references/.

##### `_scan_assets(skill_dir: Path) -> List[Path]`
Find all assets in skill/assets/.

**SkillMetadata Structure:**
```python
@dataclass
class SkillMetadata:
    name: str
    description: str
    trigger_patterns: List[str]
    references: List[Path]
    assets: List[Path]
    full_prompt: str  # Complete SKILL.md content
    skill_dir: Path
```

#### Skill Invocation Tools (`agent/tools/skill_invoke.py`)

##### `get_available_skills() -> str`
LangChain tool that returns JSON list of all available skills.

**Returns:** JSON string with skill metadata

##### `invoke_skill(skill_name: str, task_description: str, context: Optional[dict]) -> str`
LangChain tool that dynamically invokes any UiPath skill.

**Args:**
- `skill_name`: Name from get_available_skills() output
- `task_description`: What you want the skill to do
- `context`: Relevant project state, files, specifications

**Returns:** Skill agent response as string

**Error Handling:** Returns user-friendly error message on failure

---

### 5. CLI Interface (`cli/main.py`)

#### Commands

##### `start_project`
Start the bootstrap flow: BA → SA → HITL → Developer → QA.

**Arguments:**
- `--description, -d`: Process description (prompts if not provided)
- `--output, -o`: Output directory (default: ./output)

**Flow:**
1. Prompt for description if not provided
2. Initialize graph with user description
3. Run graph (stops at HITL interrupt if needed)
4. Display SDD for human review
5. Resume graph with approval/rejection
6. Display generated artifacts

##### `chat`
Start conversational mode for free-form interaction.

**Flow:**
1. Initialize conversational graph
2. Loop: prompt user → send to agent → display response
3. Exit on "exit", "quit", or "q"

**Features:**
- Natural language interaction
- Dynamic skill invocation
- Context-aware responses

---

## Usage Examples

### Example 1: Bootstrap a Project

```python
# Command line
python -m cli.main start-project -d "Invoice processing automation"

# Programmatic
from agent.graph import graph
from langchain_core.messages import HumanMessage

config = {"configurable": {"thread_id": "unique-id"}}
initial_state = {
    "messages": [HumanMessage(content="Invoice processing automation")],
    "mode": "bootstrap",
    "qa_iterations": 0,
}

result = await graph.ainvoke(initial_state, config)
print(result["artifacts"])  # Generated files
```

### Example 2: Conversational Mode

```python
# Command line
python -m cli.main chat

# Programmatic
from agent.graph import conversational_graph

config = {"configurable": {"thread_id": "chat-id"}}
state = {
    "messages": [HumanMessage(content="What skills are available?")],
    "mode": "conversational",
}

result = await conversational_graph.ainvoke(state, config)
print(result["messages"][-1].content)  # AI response
```

### Example 3: Direct Skill Invocation

```python
from agent.tools.skill_invoke import invoke_skill

response = invoke_skill(
    skill_name="uipath-rpa-workflows",
    task_description="Generate Main.xaml workflow",
    context={"project_name": "InvoiceProcessor", "template": "dispatcher"}
)

print(response)  # Skill output
```

---

## Error Handling

All nodes implement error handling that:
1. Catches exceptions during LLM calls
2. Returns user-friendly error messages
3. Logs errors for debugging
4. Continues gracefully without crashing

**Example Error Response:**
```python
{
    "messages": [
        AIMessage(content="⚠️ LLM Error: RuntimeError: AWS API rate limit exceeded")
    ]
}
```

---

## Testing

### Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_bootstrap_flow.py -v

# With coverage
pytest --cov=agent --cov=cli --cov-report=html

# Integration tests only
pytest tests/integration/ -v
```

### Test Coverage

| Module | Coverage | Description |
|--------|----------|-------------|
| agent/state.py | 100% | State schema tests |
| agent/skill_discovery.py | 90% | Skill system tests |
| agent/nodes/developer_node.py | 100% | Code generation tests |
| agent/nodes/conversational.py | 100% | Conversational tests |
| agent/graph.py | 84% | Routing logic tests |
| cli/main.py | 17% | CLI command tests |

---

## Configuration

### Environment Variables

Create `.env` file from `.env.example`:

```bash
# AWS Credentials for Bedrock
AWS_PROFILE=default
AWS_REGION=us-east-1

# Optional: Custom model
LLM_MODEL=us.anthropic.claude-sonnet-4-5-20250929-v1:0
```

### Model Configuration

Models are configured in each node:
- **BA/SA/Developer/QA**: Claude Sonnet 4.5 (temperature 0.15)
- **Conversational**: Claude Sonnet 4.5 (temperature 0.3)
- **Skill Agents**: Claude Sonnet 4.5 (temperature 0.15)

---

## Deployment

### Package Installation

```bash
# Install in development mode
pip install -e .

# Install for production
pip install .

# Run as package
uipath-builder start-project
uipath-builder chat
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -e .

CMD ["python", "-m", "cli.main", "chat"]
```

---

## Troubleshooting

### Common Issues

**Issue:** `AWS authentication failed`
**Solution:** Configure AWS credentials: `aws configure` or set AWS_PROFILE

**Issue:** `Skill not found`
**Solution:** Initialize git submodules: `git submodule update --init --recursive`

**Issue:** `Tests failing with connection error`
**Solution:** Tests use mocks, check test setup in conftest.py

**Issue:** `Graph infinite loop`
**Solution:** Ensure routing functions return correct node names or END

---

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Run tests: `pytest`
4. Run linters: `ruff check agent cli && black agent cli`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open Pull Request

---

## License

See LICENSE file for details.

---

## Support

- **Issues:** https://github.com/your-org/uipath-builder-agent/issues
- **Documentation:** This file and docs/
- **Email:** support@your-org.com
