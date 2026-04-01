# UiPath Builder Agent — Design Specification

**Version:** 1.0
**Date:** 2026-04-01
**Status:** Approved for Implementation

---

## Executive Summary

The UiPath Builder Agent is a conversational AI system that generates, modifies, and deploys UiPath RPA projects through natural language interaction. It operates in two modes: a **structured bootstrap flow** for creating new projects from requirements, and a **conversational development mode** for iterative refinement and deployment.

**Key Innovation:** Dynamic skill discovery system that automatically adapts to the growing UiPath Skills repository, requiring zero code changes as new capabilities are added.

**Core Capabilities:**
- Generate UiPath projects from plain-text descriptions or PDDs/SDDs
- Support hybrid XAML + C# coded activities based on complexity
- Clone and customize Cato Networks template repositories
- Deploy to UiPath Orchestrator via API integration
- Conversational modification and testing workflow

---

## Architecture Overview

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                    UiPath Builder Agent                         │
│                 (Conversational + Structured)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MODE 1: 🏗️  Project Bootstrap (Guided Flow)                    │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  User: "Build a dispatcher to process invoices from email"     │
│     ↓                                                           │
│  ┌─────────────────────────────────────────────────────┐       │
│  │  /start-project  (triggers structured flow)         │       │
│  └──────────────────┬────────────────────────────────┘       │
│                     ↓                                           │
│  [BA] → clarify? → [SA] → HITL? → [Generator] → [QA]          │
│   │                 │        │         │           │           │
│   └─────────────────┴────────┴─────────┴───────────┘           │
│              Skills invoked dynamically as needed               │
│                     ↓                                           │
│          Project scaffolded, ready for development              │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MODE 2: 💬 Conversational Development (Free-form)              │
│  ═══════════════════════════════════════════════════════════   │
│                                                                 │
│  User: "Add retry logic to the SAP connection activity"        │
│     ↓                                                           │
│  Agent analyzes → determines C# modification needed             │
│     ↓                                                           │
│  [Auto-invokes uipath-coded-workflows skill]                   │
│     ↓                                                           │
│  Generates updated ValidateSAPConnection.cs → commits           │
│                                                                 │
│  User: "Deploy this to our dev Orchestrator tenant"            │
│     ↓                                                           │
│  [Auto-invokes uipath-platform skill]                          │
│     ↓                                                           │
│  Authenticates → packages → publishes process                   │
│                                                                 │
│  User: "Use the rpa-workflows skill to add logging"            │
│     ↓                                                           │
│  [User-directed skill invocation] → modifies XAML               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
uipath-builder-agent/
├── agent/
│   ├── graph.py                    # Main LangGraph orchestrator
│   ├── state.py                    # ProjectState schema
│   ├── skill_discovery.py          # Dynamic skill registry
│   ├── nodes/
│   │   ├── conversational.py       # Free-form chat handler
│   │   ├── ba_persona.py           # Business Analyst persona
│   │   ├── sa_persona.py           # Solution Architect persona
│   │   ├── hitl.py                 # Human-in-the-loop review
│   │   ├── generator_router.py     # Routes to appropriate skills
│   │   └── qa.py                   # QA validation
│   ├── tools/
│   │   ├── git_tools.py            # Template cloning, commits
│   │   ├── skill_invoke.py         # Dynamic skill invocation
│   │   ├── orchestrator_tools.py   # UiPath API integration
│   │   └── aws_tools.py            # S3, DynamoDB helpers
│   └── prompts/
│       ├── main_agent.py           # Conversational agent prompt
│       ├── personas.py             # BA/SA/QA prompts
│       └── constraints.py          # Hard constraints (C#, Modern, Windows)
├── cli/
│   └── main.py                     # Typer CLI interface
├── skills/                         # Git submodule → UiPath/skills
├── templates/                      # Git submodules → Cato templates
│   ├── dispatcher/
│   ├── performer/
│   └── long-running/
├── tests/
│   ├── unit/
│   └── integration/
├── langgraph.json                  # LangGraph configuration
├── pyproject.toml                  # Dependencies
├── .env.example
└── README.md
```

---

## Core Components

### 1. Dynamic Skill Discovery System

**Problem:** UiPath Skills repository grows over time. Hardcoding skill definitions creates maintenance burden and delays adoption of new capabilities.

**Solution:** Scan and parse the cloned UiPath skills repo at runtime to build a dynamic registry.

**Implementation:**

```python
class SkillDiscovery:
    """
    Scans cloned UiPath skills repo and builds registry dynamically.
    """

    def __init__(self, skills_repo_path: Path):
        self.skills_path = skills_repo_path / "skills"
        self.registry = {}

    def discover_all_skills(self) -> dict[str, SkillMetadata]:
        """
        Walks skills/ directory, parses each SKILL.md frontmatter.
        Returns: {skill_name: SkillMetadata}
        """
        for skill_dir in self.skills_path.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                skill_meta = self._parse_skill_metadata(skill_dir)
                self.registry[skill_meta.name] = skill_meta

        return self.registry

    def _parse_skill_metadata(self, skill_dir: Path) -> SkillMetadata:
        """
        Parse SKILL.md YAML frontmatter + description for:
        - name
        - trigger_patterns (from "TRIGGER when:" section)
        - capabilities (inferred from content)
        - full_prompt (entire SKILL.md as agent system prompt)
        """
        skill_md = (skill_dir / "SKILL.md").read_text()

        # Parse YAML frontmatter
        if skill_md.startswith("---"):
            _, frontmatter, body = skill_md.split("---", 2)
            meta = yaml.safe_load(frontmatter)
        else:
            meta = {}
            body = skill_md

        # Extract trigger patterns from description
        description = meta.get("description", "")
        triggers = self._extract_triggers(description)

        return SkillMetadata(
            name=meta.get("name", skill_dir.name),
            description=description,
            trigger_patterns=triggers,
            references=self._scan_references(skill_dir),
            assets=self._scan_assets(skill_dir),
            full_prompt=skill_md,  # Entire SKILL.md
            skill_dir=skill_dir,
        )

    def _extract_triggers(self, description: str) -> list[str]:
        """
        Parse trigger conditions from description text.

        Example:
        "TRIGGER when: coded workflow projects detected, .cs files present
         DO NOT TRIGGER when: pure XAML workflows"

        Returns: ["coded workflow", ".cs files", "C# activities"]
        """
        triggers = []

        # Extract from "TRIGGER when:" section
        if "TRIGGER when:" in description:
            trigger_section = description.split("TRIGGER when:")[1]
            trigger_section = trigger_section.split("DO NOT TRIGGER")[0]

            # Parse trigger phrases (comma-separated)
            phrases = re.split(r'[,\n]', trigger_section)
            triggers = [p.strip() for p in phrases if p.strip()]

        return triggers
```

**Key Benefits:**
- New skill appears → Agent discovers it automatically
- No code changes required for new capabilities
- Skills self-document via SKILL.md frontmatter
- Version-resilient (agent queries capabilities dynamically)

---

### 2. State Management

**ProjectState Schema:**

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class ProjectState(TypedDict):
    # ── Core I/O ─────────────────────────────────────────
    messages: Annotated[list, add_messages]

    # ── Project metadata ──────────────────────────────────
    project_name: str
    project_path: str
    template_type: str          # dispatcher|performer|lrw
    git_repo_url: str           # where to push generated code

    # ── Mode tracking ─────────────────────────────────────
    mode: str                   # "bootstrap" | "conversational"
    current_phase: str          # "ba" | "sa" | "hitl" | "generation" | "qa" | "dev"

    # ── Design artifacts ──────────────────────────────────
    pdd: dict                   # Process Design Document (from BA)
    sdd: dict                   # Solution Design Document (from SA)

    # ── Generation state ──────────────────────────────────
    artifacts: dict[str, str]   # relative_path → file_content
    active_skills: list[str]    # skills available for current context

    # ── BA clarification flow ─────────────────────────────
    needs_clarification: bool
    clarify_question: str
    clarification_answer: str

    # ── HITL flow ─────────────────────────────────────────
    requires_hitl: bool
    hitl_approved: bool
    hitl_feedback: str

    # ── QA validation ─────────────────────────────────────
    validation_errors: list[str]
    qa_iterations: int          # max 2 fix loops
    qa_report: dict

    # ── Deployment ────────────────────────────────────────
    orchestrator_tenant: str
    deployed_version: str
```

---

### 3. LangGraph Orchestrator

**Graph Structure:**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.dynamodb import DynamoDBSaver
import os

from agent.state import ProjectState
from agent.nodes.conversational import conversational_agent
from agent.nodes.ba_persona import ba_persona_node
from agent.nodes.sa_persona import sa_persona_node
from agent.nodes.hitl import hitl_review_node
from agent.nodes.generator_router import generator_router_node
from agent.nodes.qa import qa_validation_node

# ── Routing Logic ────────────────────────────────────────

def route_main(state: ProjectState) -> str:
    """Main routing from conversational agent."""
    mode = state.get("mode", "conversational")

    # Bootstrap mode routing
    if mode == "bootstrap":
        phase = state.get("current_phase", "ba")
        if phase == "ba" and not state.get("pdd"):
            return "ba_persona"
        elif phase == "sa" and not state.get("sdd"):
            return "sa_persona"
        elif phase == "hitl" and state.get("requires_hitl"):
            return "hitl"
        elif phase == "generation":
            return "generator"
        elif phase == "qa":
            return "qa"

    # Conversational mode - stay in conversational loop
    return "conversational"


def route_after_ba(state: ProjectState) -> str:
    """Route after BA persona completes."""
    if state.get("needs_clarification"):
        return "conversational"  # Ask user for clarification
    return "sa_persona"


def route_after_sa(state: ProjectState) -> str:
    """Route after SA persona completes."""
    if state.get("requires_hitl"):
        return "hitl"
    return "generator"


def route_after_hitl(state: ProjectState) -> str:
    """Route after HITL review."""
    if not state.get("hitl_approved"):
        return END  # User rejected design
    return "generator"


def route_after_qa(state: ProjectState) -> str:
    """Route after QA validation."""
    errors = state.get("validation_errors", [])
    iterations = state.get("qa_iterations", 0)

    if errors and iterations < 2:
        return "generator"  # Retry generation with fixes

    # QA passed or max iterations reached
    return "conversational"  # Return to conversational mode


# ── Graph Building ───────────────────────────────────────

builder = StateGraph(ProjectState)

# Core nodes
builder.add_node("conversational", conversational_agent)
builder.add_node("ba_persona", ba_persona_node)
builder.add_node("sa_persona", sa_persona_node)
builder.add_node("hitl", hitl_review_node)
builder.add_node("generator", generator_router_node)
builder.add_node("qa", qa_validation_node)

# Set entry point
builder.set_entry_point("conversational")

# Add edges
builder.add_conditional_edges("conversational", route_main, {
    "conversational": "conversational",
    "ba_persona": "ba_persona",
    "sa_persona": "sa_persona",
    "hitl": "hitl",
    "generator": "generator",
    "qa": "qa",
})

builder.add_conditional_edges("ba_persona", route_after_ba, {
    "conversational": "conversational",
    "sa_persona": "sa_persona",
})

builder.add_conditional_edges("sa_persona", route_after_sa, {
    "hitl": "hitl",
    "generator": "generator",
})

builder.add_conditional_edges("hitl", route_after_hitl, {
    "generator": "generator",
    END: END,
})

builder.add_edge("generator", "qa")

builder.add_conditional_edges("qa", route_after_qa, {
    "generator": "generator",
    "conversational": "conversational",
})

# Checkpointer selection (local vs AWS)
if os.getenv("USE_DYNAMODB_CHECKPOINTER", "false").lower() == "true":
    checkpointer = DynamoDBSaver.from_conn_info(
        region="us-east-1",
        table_name=os.getenv("CHECKPOINT_TABLE", "uipath-builder-checkpoints"),
    )
else:
    checkpointer = MemorySaver()

# Compile graph
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["hitl"],  # Only HITL requires user interaction
)
```

---

### 4. Personas as Lightweight Prompts

**BA (Business Analyst) Persona:**

```python
async def ba_persona_node(state: ProjectState) -> dict:
    """
    Business Analyst persona - converts user input into structured PDD.

    Two input modes:
    - DOCUMENT: User provides PDD/SDD markdown
    - INSTRUCTION: User describes what they want in plain text

    If instruction mode and input is too vague, sets needs_clarification=True
    and routes back to conversational agent for user interaction.
    """

    system_prompt = """
You are a Business Analyst working on a UiPath RPA project.

Your job: Convert user requirements into a structured Process Design Document (PDD).

Input modes:
1. DOCUMENT mode: User provides existing PDD/SDD → extract and structure
2. INSTRUCTION mode: User describes process → generate PDD from scratch

If instruction mode and input lacks critical details (process, trigger,
systems, outcome), set needs_clarification=True and craft ONE focused question.

Output: PDD with sections:
- Executive Summary
- AS-IS Process (current manual steps)
- TO-BE Process (automated steps with tags: [AUTO] [MANUAL] [DECISION] [HITL])
- Exception Handling
- Systems Involved
- Configuration Keys (for Config.xlsx)

Platform detection:
- Maestro keywords (Action Center, Slack, webhooks) → Maestro
- Traditional keywords (queues, REFramework, selectors) → Studio
- Ambiguous → ask user

Template detection:
- Many items + queue → Dispatcher/Performer
- HITL steps + long wait → Long Running Automation
- Simple flow → Sequence

HARD CONSTRAINTS (never violate):
- C# only (never VB.Net)
- Modern activities only (never Classic)
- Windows target only
- No hardcoded credentials/URLs
"""

    # Implementation: LLM call with state context
    # Returns: Updated state with pdd or needs_clarification flag
```

**SA (Solution Architect) Persona:**

```python
async def sa_persona_node(state: ProjectState) -> dict:
    """
    Solution Architect persona - transforms PDD into technical SDD.

    Responsibilities:
    1. Confirm or override template choice (with justification)
    2. Define coded activity map (which .cs files to generate)
    3. Specify project structure and namespace
    4. Define Config.xlsx schema
    5. Identify UiPath package dependencies
    6. Set requires_hitl flag if design has risk/ambiguity

    Output: SDD with:
    - Architecture Decision Record (ADR)
    - Project structure (XAML workflows + coded activities)
    - Activity specifications (inputs, outputs, error handling)
    - Config schema
    - Orchestrator resources (queues, assets)
    - Generation strategy (XAML vs C# vs Hybrid)
    """

    system_prompt = """
You are a Solution Architect designing a UiPath RPA solution.

Input: PDD from Business Analyst
Output: Technical SDD with architecture decisions

Template Decision Matrix:
- DISPATCHER: Reads many items from source → pushes to queue
- PERFORMER: Consumes from queue → processes with retry logic
- REFRAMEWORK: Queue-based but D+P would be overkill
- LONG RUNNING: Must suspend/wait hours/days for external event
- SEQUENCE: Simple linear flow, no retry needs

Coded Activity Design:
- ONE responsibility per activity
- Name the external system (for credential handling)
- Error contract: BusinessRuleException vs ApplicationException
- Prefer CodeActivity for stateless work
- Use ICodedWorkflow for orchestration logic

Generation Strategy (CRITICAL):
Based on complexity, choose:
- XAML: Simple orchestration, standard activities
- C#: Complex logic, API integrations, custom validations
- HYBRID: XAML orchestration + C# coded activities

HITL Trigger Conditions (set requires_hitl=True when):
- Template changed from BA's recommendation
- More than 5 coded activities
- System with no clear credential strategy
- LRW pattern (suspend/resume points)
- Dispatcher + Performer (TWO separate projects)
- Any PDD open items affecting architecture

Include in SDD:
- ADR with context/decision/consequences
- Full activity specs (class_name, inputs, outputs, error_handling)
- Config.xlsx keys with descriptions and defaults
- Package dependencies with version constraints
"""

    # Implementation: LLM call with PDD context
    # Returns: Updated state with sdd and requires_hitl flag
```

---

### 5. Skill Invocation Tools

**get_available_skills Tool:**

```python
@tool
def get_available_skills() -> str:
    """
    Returns JSON list of all available UiPath skills with descriptions.
    Use this when you need to know what skills are available.

    Dynamically scans the cloned UiPath skills repo, so new skills
    appear automatically after repo updates.
    """
    from agent.skill_discovery import SkillDiscovery
    from pathlib import Path

    skills_repo = Path(__file__).parent.parent / "skills"
    discovery = SkillDiscovery(skills_repo)
    registry = discovery.discover_all_skills()

    skills_list = [
        {
            "name": skill.name,
            "description": skill.description,
            "triggers": skill.trigger_patterns,
            "references": [ref.name for ref in skill.references],
        }
        for skill in registry.values()
    ]

    return json.dumps(skills_list, indent=2)
```

**invoke_skill Tool:**

```python
@tool
def invoke_skill(
    skill_name: str,
    task_description: str,
    context: dict = None,
) -> str:
    """
    Dynamically invoke any UiPath skill by name.

    Args:
        skill_name: Name from get_available_skills() output
        task_description: What you want the skill to do
        context: Relevant project state, files, specifications

    The skill's full SKILL.md is used as the system prompt,
    along with its references and assets available as context.

    Examples:
    - invoke_skill("uipath-rpa-workflows", "Generate Main.xaml dispatcher flow", {...})
    - invoke_skill("uipath-coded-workflows", "Create ValidateInvoice activity", {...})
    - invoke_skill("uipath-platform", "Deploy to dev tenant", {...})
    """
    from agent.skill_discovery import SkillDiscovery
    from langchain_aws import ChatBedrockConverse
    from langchain_core.messages import SystemMessage, HumanMessage
    from pathlib import Path

    skills_repo = Path(__file__).parent.parent / "skills"
    discovery = SkillDiscovery(skills_repo)
    registry = discovery.discover_all_skills()

    if skill_name not in registry:
        available = ", ".join(registry.keys())
        return f"❌ Skill '{skill_name}' not found. Available: {available}"

    skill = registry[skill_name]

    # Load skill's references as additional context
    references_context = []
    for ref_path in skill.references:
        references_context.append({
            "file": ref_path.name,
            "content": ref_path.read_text()[:5000]  # Truncate large docs
        })

    # Build system prompt from skill's SKILL.md
    system_prompt = f"""
{skill.full_prompt}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AVAILABLE REFERENCE DOCUMENTATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{json.dumps(references_context, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT TASK REQUEST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{task_description}

Project Context:
{json.dumps(context or {}, indent=2)}
"""

    # Spawn skill agent
    skill_agent = ChatBedrockConverse(
        model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region_name="us-east-1",
        temperature=0.15,
    )

    response = skill_agent.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=task_description),
    ])

    return response.content
```

---

### 6. Generator Router Node

**Routes to appropriate skill based on SDD generation strategy:**

```python
async def generator_router_node(state: ProjectState) -> dict:
    """
    Routes generation to appropriate UiPath skills based on SDD strategy.

    Strategy from SDD:
    - "xaml" → invoke uipath-rpa-workflows
    - "coded" → invoke uipath-coded-workflows
    - "hybrid" → invoke both (XAML orchestration + C# activities)

    Steps:
    1. Clone Cato template (dispatcher/performer/lrw)
    2. Invoke skill(s) to generate/modify files
    3. Update artifacts dict with generated files
    4. Return to QA for validation
    """

    sdd = state.get("sdd", {})
    template_type = state.get("template_type")
    generation_strategy = sdd.get("generation_strategy", "hybrid")

    artifacts = {}

    # Step 1: Clone template
    template_url = get_template_url(template_type)  # From Cato repos
    project_path = state.get("project_path")

    clone_template(template_url, project_path)

    # Step 2: Invoke skills based on strategy
    context = {
        "sdd": sdd,
        "pdd": state.get("pdd"),
        "project_path": project_path,
        "template_type": template_type,
    }

    if generation_strategy in ["xaml", "hybrid"]:
        # Generate/modify XAML workflows
        xaml_result = invoke_skill(
            skill_name="uipath-rpa-workflows",
            task_description=f"Generate XAML workflows for {template_type} template",
            context=context,
        )
        artifacts["xaml_generation"] = xaml_result

    if generation_strategy in ["coded", "hybrid"]:
        # Generate C# coded activities
        coded_result = invoke_skill(
            skill_name="uipath-coded-workflows",
            task_description="Generate coded activities from SDD specs",
            context=context,
        )
        artifacts["coded_generation"] = coded_result

    # Step 3: Update Config.json if needed
    config_updates = generate_config_json(sdd.get("config_schema", []))
    artifacts["Data/Config.json"] = config_updates

    return {
        "artifacts": {**state.get("artifacts", {}), **artifacts},
        "current_phase": "qa",
    }
```

---

### 7. QA Validation Node

**Validates generated artifacts against constraints:**

```python
async def qa_validation_node(state: ProjectState) -> dict:
    """
    QA validation node - checks generated artifacts for:
    1. Hard constraint violations (VB.Net, Classic, hardcoded values)
    2. project.json schema correctness
    3. SDD completeness (all activities generated)
    4. UiPath CLI validation (if available)

    Returns:
    - validation_errors: List of blocking issues
    - qa_report: Full report including warnings
    - qa_iterations: Incremented count

    If errors found and qa_iterations < 2: routes back to generator for fixes
    Otherwise: returns to conversational mode
    """

    artifacts = state.get("artifacts", {})
    sdd = state.get("sdd", {})
    iterations = state.get("qa_iterations", 0)

    validation_errors = []
    warnings = []

    # Check 1: project.json validation
    project_json = artifacts.get("project.json")
    if project_json:
        proj = json.loads(project_json)
        if proj.get("targetFramework") != "Windows":
            validation_errors.append(
                "[CRITICAL] project.json: targetFramework must be 'Windows'"
            )
        if proj.get("expressionLanguage") == "VisualBasic":
            # Templates use VB by default, but coded activities should be C#
            warnings.append(
                "[WARNING] project.json: expressionLanguage is VisualBasic, "
                "coded activities must use C#"
            )

    # Check 2: Scan .cs files for violations
    for file_path, content in artifacts.items():
        if file_path.endswith(".cs"):
            # VB.Net patterns
            if re.search(r'\bDim\s+\w+', content):
                validation_errors.append(
                    f"[CRITICAL] {file_path}: VB.Net 'Dim' keyword detected"
                )

            # Hardcoded URLs
            if re.search(r'https?://[a-zA-Z0-9\-\.]+', content):
                validation_errors.append(
                    f"[ERROR] {file_path}: Hardcoded URL detected, move to Config"
                )

            # Console.Write (should use LogMessage)
            if re.search(r'Console\.(Write|WriteLine)', content):
                warnings.append(
                    f"[WARNING] {file_path}: Console.Write detected, use LogMessage"
                )

    # Check 3: SDD completeness
    expected_activities = [
        act["class_name"]
        for act in sdd.get("project_structure", {}).get("coded_activities", [])
    ]
    generated_activities = [
        Path(path).stem
        for path in artifacts.keys()
        if path.endswith(".cs")
    ]

    missing = set(expected_activities) - set(generated_activities)
    if missing:
        validation_errors.append(
            f"[ERROR] Missing activities from SDD: {', '.join(missing)}"
        )

    # Check 4: UiPath CLI validation (if available)
    project_path = state.get("project_path")
    if project_path and shutil.which("uip"):
        cli_result = subprocess.run(
            ["uip", "rpa", "validate", "--project", project_path, "--output", "json"],
            capture_output=True,
            text=True,
        )
        if cli_result.returncode != 0:
            try:
                cli_errors = json.loads(cli_result.stdout)
                for err in cli_errors.get("errors", []):
                    validation_errors.append(f"[CLI] {err['message']}")
            except:
                validation_errors.append(f"[CLI] Validation failed: {cli_result.stderr}")

    qa_report = {
        "iteration": iterations + 1,
        "errors": validation_errors,
        "warnings": warnings,
        "verdict": "PASS" if not validation_errors else "FAIL",
    }

    return {
        "validation_errors": validation_errors,
        "qa_iterations": iterations + 1,
        "qa_report": qa_report,
        "artifacts": {
            **artifacts,
            "qa_report.json": json.dumps(qa_report, indent=2),
        },
    }
```

---

## Git Integration

### Template Cloning

**Cato Networks Templates (Git Submodules):**

```bash
# Initialize submodules for Cato templates
git submodule add \
  https://github.com/cato-networks-IT/AgenticAi_PROCESSNAME_DispatcherTemplate \
  templates/dispatcher

git submodule add \
  https://github.com/cato-networks-IT/AgenticAi_PROCESSNAME_PerformerTemplate \
  templates/performer

git submodule add \
  https://github.com/cato-networks-IT/AgenticAi_PROCESSNAME_LongRunningAutomationTemplate \
  templates/long-running

# Initialize UiPath Skills (Git Submodule)
git submodule add \
  https://github.com/UiPath/skills \
  skills
```

**Template Cloning Function:**

```python
def clone_template(template_type: str, output_path: str) -> str:
    """
    Clone Cato template to output directory.

    Templates are git submodules in templates/ directory.
    This function copies the template (not clones) to avoid
    git history coupling.
    """
    from pathlib import Path
    import shutil

    template_map = {
        "dispatcher": Path(__file__).parent.parent / "templates" / "dispatcher",
        "performer": Path(__file__).parent.parent / "templates" / "performer",
        "lrw": Path(__file__).parent.parent / "templates" / "long-running",
    }

    template_src = template_map.get(template_type)
    if not template_src or not template_src.exists():
        raise ValueError(f"Template '{template_type}' not found")

    output = Path(output_path)
    output.mkdir(parents=True, exist_ok=True)

    # Copy template files (exclude .git)
    shutil.copytree(
        template_src,
        output,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('.git', '.gitignore'),
    )

    return str(output)
```

### Generated Project Repository

**Git initialization for generated projects:**

```python
def init_project_git(project_path: str, repo_url: str) -> None:
    """
    Initialize git repo in generated project and push to remote.

    Args:
        project_path: Path to generated UiPath project
        repo_url: GitHub/GitLab/Bitbucket URL for the project
    """
    import subprocess
    from pathlib import Path

    p = Path(project_path)

    commands = [
        ["git", "init", "-b", "main"],
        ["git", "add", "."],
        ["git", "commit", "-m", "feat: initial project generation by UiPath Builder Agent"],
        ["git", "remote", "add", "origin", repo_url],
        ["git", "push", "-u", "origin", "main"],
    ]

    for cmd in commands:
        result = subprocess.run(
            cmd,
            cwd=p,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git command failed: {' '.join(cmd)}\n{result.stderr}")
```

---

## Deployment Strategy

### Local Development

**Default mode using MemorySaver:**

```python
# .env file
USE_DYNAMODB_CHECKPOINTER=false
AWS_PROFILE=default
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# UiPath Orchestrator
UIPATH_URL=https://cloud.uipath.com/catonetworks/Production
UIPATH_ACCESS_TOKEN=<from-env-or-aws-secrets>

# Template customization
COMPANY_NAME=CatoNetworks
DEPARTMENT=IT-Automation
```

**CLI Usage:**

```bash
# Install dependencies
pip install -e .

# Start conversational session
uipath-builder chat

# Bootstrap a new project
uipath-builder start-project --input requirements.md --output ./output

# Resume existing session
uipath-builder resume --thread my-project-123
```

### AWS Production Deployment

**Architecture:**

```
┌─────────────────────────────────────────────────┐
│  ECS Fargate Task                                │
│  Image: uipath-builder-agent:latest              │
│                                                  │
│  ┌──────────┐   ┌─────────────────────────┐     │
│  │ LangGraph│──►│ AWS Bedrock             │     │
│  │ Agent    │   │ claude-sonnet-4-5       │     │
│  └────┬─────┘   └─────────────────────────┘     │
│       │                                          │
│  ┌────▼─────┐   ┌─────────────────────────┐     │
│  │DynamoDB  │   │ S3 Bucket               │     │
│  │Checkpoint│   │ (project artifacts)     │     │
│  └──────────┘   └─────────────────────────┘     │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │ UiPath Orchestrator API                  │   │
│  │ (deploy, run processes)                  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

**Environment Variables (ECS Task Definition):**

```json
{
  "environment": [
    {"name": "USE_DYNAMODB_CHECKPOINTER", "value": "true"},
    {"name": "CHECKPOINT_TABLE", "value": "uipath-builder-checkpoints"},
    {"name": "AWS_REGION", "value": "us-east-1"},
    {"name": "BEDROCK_MODEL_ID", "value": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"},
    {"name": "S3_ARTIFACTS_BUCKET", "value": "cato-uipath-projects"},
    {"name": "UIPATH_URL", "value": "https://cloud.uipath.com/catonetworks/Production"}
  ],
  "secrets": [
    {
      "name": "UIPATH_ACCESS_TOKEN",
      "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:uipath/orchestrator-token"
    }
  ]
}
```

**DynamoDB Table Setup:**

```bash
aws dynamodb create-table \
  --table-name uipath-builder-checkpoints \
  --attribute-definitions \
      AttributeName=thread_id,AttributeType=S \
      AttributeName=checkpoint_id,AttributeType=S \
  --key-schema \
      AttributeName=thread_id,KeyType=HASH \
      AttributeName=checkpoint_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**IAM Permissions:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-sonnet-4-5*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/uipath-builder-checkpoints"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::cato-uipath-projects",
        "arn:aws:s3:::cato-uipath-projects/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:uipath/*"
    }
  ]
}
```

---

## Example Usage Flows

### Flow 1: Bootstrap New Project

```
User: /start-project
      "Build a dispatcher that reads insurance claims from a SharePoint list
       and pushes them to an Orchestrator queue for processing"

Agent: [Enters bootstrap mode]

       BA Persona activates:
       "I need to clarify: Should the dispatcher run on a schedule or be
        triggered by file uploads?"

User: "Run every hour on a schedule"

Agent: BA Persona completes:
       ✅ PDD generated

       SA Persona activates:
       📋 Solution Design:
       - Template: Dispatcher (scheduled bulk processing)
       - Platform: Traditional Studio
       - Generation: Hybrid (XAML orchestration + C# SharePoint connector)
       - 4 coded activities needed:
         1. ConnectToSharePoint (C#)
         2. ReadClaimsList (C#)
         3. ValidateClaimFormat (C#)
         4. PushToQueue (XAML activity wrapper)

       ⚠️  HITL Review Required: Template involves 4 coded activities

       [Pauses for review]

User: "Approved, looks good"

Agent: Generator Router activates:
       1️⃣ Cloning DispatcherTemplate...
       2️⃣ Invoking uipath-coded-workflows skill (3 activities)...
       3️⃣ Invoking uipath-rpa-workflows skill (Main.xaml)...
       4️⃣ Generating Config.json...

       QA Validation:
       ✅ All constraints passed
       ✅ 3 coded activities generated
       ✅ project.json valid
       ✅ Config.json structured correctly

       🎉 Project generated: ./output/ClaimsDispatcher/

       [Enters conversational mode]

User: "Deploy this to our dev Orchestrator tenant"

Agent: [Auto-invokes uipath-platform skill]

       🔐 Authenticating with Orchestrator...
       📦 Packaging ClaimsDispatcher v1.0.0...
       🚀 Publishing to catonetworks/Development tenant...

       ✅ Deployed successfully!
       Process Name: ClaimsDispatcher
       Version: 1.0.0
       Feed: Development

User: "Add error handling for SharePoint connection timeouts"

Agent: [Auto-invokes uipath-coded-workflows skill]

       📝 Analyzing ConnectToSharePoint.cs...
       🔧 Adding retry logic with exponential backoff...
       ✅ Updated ConnectToSharePoint.cs

       Changes:
       - Added max 3 retries
       - Exponential backoff (1s, 2s, 4s)
       - Throws ApplicationException after max retries

       Would you like me to commit these changes?
```

### Flow 2: Conversational Development

```
User: "I have an existing UiPath project. Can you help me add a new
       coded activity for validating email addresses?"

Agent: ✅ I can help! First, let me check what skills are available...

       [Calls get_available_skills()]

       I'll use the uipath-coded-workflows skill to generate that.

       A few questions:
       1. What should the activity be called?
       2. What validation rules? (format only, or also check deliverability?)
       3. Should it throw BusinessRuleException on invalid emails?

User: "Call it ValidateEmailAddress. Just format validation using regex.
       Yes, throw BusinessRuleException with a clear message."

Agent: [Invokes uipath-coded-workflows skill]

       ✅ Generated ValidateEmailAddress.cs

       Activity Details:
       - Input: EmailAddress (string)
       - Output: IsValid (bool)
       - Throws: BusinessRuleException on invalid format
       - Regex: Standard email pattern

       File created at: .objects/ValidateEmailAddress.cs

       Should I also:
       1. Add this to your Main.xaml workflow?
       2. Add a test case for this activity?

User: "Yes to both"

Agent: [Invokes uipath-rpa-workflows skill for XAML]
       [Invokes uipath-coded-workflows skill for test]

       ✅ Updated Main.xaml with ValidateEmailAddress activity
       ✅ Created ValidateEmailAddressTests.cs

       You can run tests with: uip rpa test
```

---

## Technical Decisions & Trade-offs

### Decision 1: Skills as Subagents vs Tools

**Chosen:** Skills as subagents (invoke full LLM with SKILL.md as prompt)

**Rationale:**
- Skills are already designed as complete agent prompts (SKILL.md)
- References and assets can be loaded dynamically as context
- Skills evolve independently - no code coupling
- New skills work immediately (just git pull)

**Trade-off:** Higher token usage (each skill invocation = separate LLM call) vs simpler maintenance

### Decision 2: Personas as Prompts vs Separate Agents

**Chosen:** Personas as lightweight prompt sections within main graph nodes

**Rationale:**
- Avoids overcomplexity (original architecture had 5 separate persona agents)
- BA/SA/QA provide structure and decision guidance, not generation
- Actual generation delegated to UiPath skills (which are the domain experts)
- Easier to debug and trace decision flow

**Trade-off:** Less isolation between personas vs simpler architecture

### Decision 3: XAML vs C# Generation Strategy

**Chosen:** Configurable based on SA analysis (not hardcoded)

**Rationale:**
- Cato templates are XAML-based (proven patterns)
- Complex logic benefits from C# (testable, reusable)
- Hybrid approach uses best of both (XAML orchestration + C# components)
- SA persona makes informed decision based on PDD complexity

**Trade-off:** Two generation paths to maintain vs flexibility

### Decision 4: Git Submodules for Templates and Skills

**Chosen:** Use git submodules for both Cato templates and UiPath skills

**Rationale:**
- Keeps templates and skills versioned separately
- Easy to update (git submodule update --remote)
- No code duplication
- Clear separation of concerns

**Trade-off:** Requires git submodule initialization vs simpler repo structure

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_skill_discovery.py
def test_skill_discovery_scans_all_skills():
    """Verify skill discovery finds all SKILL.md files."""
    discovery = SkillDiscovery(Path("skills"))
    registry = discovery.discover_all_skills()

    assert "uipath-rpa-workflows" in registry
    assert "uipath-coded-workflows" in registry
    assert len(registry) >= 8  # Known skills as of 2026-04-01

def test_skill_metadata_parsing():
    """Verify SKILL.md frontmatter parsing."""
    skill_dir = Path("skills/uipath-rpa-workflows")
    discovery = SkillDiscovery(Path("skills"))
    meta = discovery._parse_skill_metadata(skill_dir)

    assert meta.name == "uipath-rpa-workflows"
    assert "XAML" in meta.trigger_patterns or "workflow" in meta.trigger_patterns
    assert len(meta.references) > 0

# tests/unit/test_ba_persona.py
async def test_ba_detects_vague_input():
    """BA should flag vague inputs for clarification."""
    state = {
        "input_document": "automate something with salesforce",
        "messages": [],
    }

    result = await ba_persona_node(state)

    assert result["needs_clarification"] == True
    assert "clarify_question" in result

async def test_ba_extracts_pdd_from_document():
    """BA should extract PDD from structured markdown."""
    state = {
        "input_document": """
## Process Design Document: Invoice Processing

### TO-BE Process
1. [AUTO] Read invoice from email
2. [AUTO] Extract data using OCR
3. [HITL] Manager approves amounts > $10k
4. [AUTO] Post to SAP
""",
        "messages": [],
    }

    result = await ba_persona_node(state)

    assert result["pdd"] is not None
    assert result["pdd"]["has_hitl"] == True
```

### Integration Tests

```python
# tests/integration/test_end_to_end_flow.py
async def test_complete_bootstrap_flow():
    """Test full flow from requirements to generated project."""

    # Simulate user starting project
    state = {
        "messages": [{"role": "user", "content": "Build a simple dispatcher"}],
        "mode": "bootstrap",
    }

    config = {"configurable": {"thread_id": "test-123"}}

    # Run graph
    result = None
    async for event in graph.astream(state, config=config):
        result = event

    # Verify project generated
    final_state = graph.get_state(config).values
    assert final_state["pdd"] is not None
    assert final_state["sdd"] is not None
    assert len(final_state["artifacts"]) > 0
    assert "project.json" in final_state["artifacts"]

# tests/integration/test_skill_invocation.py
async def test_invoke_uipath_rpa_skill():
    """Test invoking a real UiPath skill."""

    result = invoke_skill(
        skill_name="uipath-rpa-workflows",
        task_description="Explain XAML structure of a dispatcher",
        context={},
    )

    assert result is not None
    assert "XAML" in result or "workflow" in result
```

---

## Security Considerations

### Credential Management

1. **Never store credentials in code or Config.json**
   - Use Orchestrator Assets for sensitive values
   - Reference via GetAsset activity

2. **AWS Secrets Manager for Orchestrator tokens**
   ```python
   import boto3

   def get_orchestrator_token() -> str:
       client = boto3.client('secretsmanager', region_name='us-east-1')
       response = client.get_secret_value(SecretId='uipath/orchestrator-token')
       return json.loads(response['SecretString'])['token']
   ```

3. **IAM roles for ECS tasks** (no hardcoded AWS credentials)

### Generated Code Validation

1. **QA scans for credential patterns:**
   ```python
   CREDENTIAL_PATTERNS = [
       r'password\s*=\s*["\'][^"\']+["\']',
       r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
       r'token\s*=\s*["\'][^"\']+["\']',
   ]
   ```

2. **Hardcoded URL detection** (all URLs must be in Config)

3. **Classic activity blocking** (prevent security vulnerabilities from old packages)

---

## Performance & Scalability

### Token Optimization

1. **Skill references truncated** (5000 chars max per reference doc)
2. **Artifacts summarized** (full files only when needed for context)
3. **Incremental generation** (generate files one at a time, not all at once)

### Checkpointing Strategy

1. **DynamoDB in production** - persistent across restarts
2. **MemorySaver in development** - fast iteration
3. **Checkpoint after each persona** - can resume mid-bootstrap

### Caching

1. **Skill discovery cached** (refresh only on explicit update)
2. **Template clones cached locally** (avoid repeated git operations)

---

## Future Enhancements

### Phase 2 Features

1. **Multi-project orchestration**
   - Generate Dispatcher + Performer in one flow
   - Handle dependencies between projects

2. **Testing integration**
   - Auto-generate test cases using uipath-servo skill
   - Run tests before QA approval

3. **Version control**
   - Auto-create feature branches
   - Generate pull request descriptions

4. **Analytics dashboard**
   - Track generation success rates
   - Monitor skill usage patterns
   - Identify common failure modes

### Phase 3 Features

1. **Custom skill creation**
   - Template for building internal Cato-specific skills
   - Skill marketplace integration

2. **Legacy modernization**
   - Convert Classic projects to Modern
   - Upgrade VB.Net to C#

3. **Process mining integration**
   - Generate PDDs from UiPath Process Mining exports
   - Auto-detect automation opportunities

---

## Implementation Plan

### Sprint 1: Foundation (Week 1-2)
- [ ] Project structure setup
- [ ] Skill discovery system
- [ ] State management and graph wiring
- [ ] Basic conversational agent (no personas yet)
- [ ] Tool: get_available_skills, invoke_skill

### Sprint 2: Bootstrap Flow (Week 3-4)
- [ ] BA persona node
- [ ] SA persona node
- [ ] HITL review node
- [ ] Template cloning (git submodules setup)
- [ ] CLI: start-project command

### Sprint 3: Generation (Week 5-6)
- [ ] Generator router node
- [ ] Skill invocation for XAML generation
- [ ] Skill invocation for C# generation
- [ ] Config.json generation
- [ ] QA validation node

### Sprint 4: Deployment (Week 7-8)
- [ ] UiPath Orchestrator API integration
- [ ] Git repository initialization
- [ ] AWS DynamoDB checkpointing
- [ ] S3 artifact storage
- [ ] ECS deployment configuration

### Sprint 5: Testing & Polish (Week 9-10)
- [ ] Unit test suite
- [ ] Integration tests
- [ ] Documentation
- [ ] Example workflows
- [ ] Performance optimization

---

## Success Criteria

### Must Have (MVP)
- ✅ Generate working Dispatcher project from text description
- ✅ Support all three Cato templates (Dispatcher, Performer, LRW)
- ✅ HITL review before generation
- ✅ QA validation catches constraint violations
- ✅ Deploy to Orchestrator via API
- ✅ Conversational modifications work (add activity, modify workflow)

### Should Have
- ✅ Dynamic skill discovery (zero maintenance for new skills)
- ✅ Hybrid XAML + C# generation
- ✅ Git integration (commit changes, push to remote)
- ✅ AWS production deployment (ECS + DynamoDB)

### Nice to Have
- Testing integration (auto-run tests before QA)
- Multi-project generation (D+P pairs)
- Process mining integration
- Analytics dashboard

---

## Conclusion

This design provides a **conversational, skill-driven architecture** for generating UiPath RPA projects. Key innovations:

1. **Dynamic skill discovery** - Zero maintenance as UiPath skills grow
2. **Dual-mode operation** - Structured bootstrap + free-form conversation
3. **Simplified personas** - Lightweight prompts instead of complex agents
4. **Hybrid generation** - XAML + C# based on complexity
5. **Production-ready** - AWS deployment with proper security and checkpointing

The system is designed to be **maintainable, extensible, and aligned with Cato Networks' existing UiPath patterns**.
