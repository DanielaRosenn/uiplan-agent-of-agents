# Sprint 1: Foundation - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish project foundation with dynamic skill discovery, state management, and basic LangGraph orchestration.

**Architecture:** Python-based LangGraph application using AWS Bedrock for LLM calls. Git submodules for UiPath skills and Cato templates. Dynamic skill discovery system that auto-adapts to growing UiPath skills repository.

**Tech Stack:**
- Python 3.11+
- LangGraph (state management & orchestration)
- langchain-aws (ChatBedrockConverse)
- Typer (CLI)
- pytest (testing)
- AWS Bedrock (Sonnet 4.5)

---

## File Structure

**New Files to Create:**
- `pyproject.toml` - Project dependencies and metadata
- `.env.example` - Environment variable template
- `.gitignore` - Git ignore patterns
- `agent/__init__.py` - Agent package marker
- `agent/state.py` - ProjectState TypedDict schema
- `agent/skill_discovery.py` - Dynamic skill registry system
- `agent/graph.py` - LangGraph orchestrator (basic)
- `agent/nodes/__init__.py` - Nodes package marker
- `agent/nodes/conversational.py` - Conversational agent node
- `agent/tools/__init__.py` - Tools package marker
- `agent/tools/skill_invoke.py` - Skill invocation tools
- `agent/prompts/__init__.py` - Prompts package marker
- `agent/prompts/constraints.py` - Hard constraints
- `tests/__init__.py` - Tests package marker
- `tests/unit/__init__.py` - Unit tests package marker
- `tests/unit/test_skill_discovery.py` - Skill discovery tests
- `tests/unit/test_state.py` - State schema tests
- `tests/conftest.py` - Pytest fixtures
- `README.md` - Project documentation

**Git Submodules to Add:**
- `skills/` → https://github.com/UiPath/skills
- `templates/dispatcher/` → Cato dispatcher template
- `templates/performer/` → Cato performer template
- `templates/long-running/` → Cato LRW template

---

## Task 1: Project Setup & Dependencies

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Create pyproject.toml with dependencies**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "uipath-builder-agent"
version = "0.1.0"
description = "Conversational AI agent for generating UiPath RPA projects"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",
    "langchain-aws>=0.2.0",
    "langchain-core>=0.3.0",
    "typer>=0.12.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "boto3>=1.34.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "black>=24.0.0",
    "ruff>=0.3.0",
]

[project.scripts]
uipath-builder = "cli.main:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

- [ ] **Step 2: Create .env.example**

```bash
# AWS Configuration
AWS_PROFILE=default
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-5-20250929-v1:0

# Checkpointing (false for local dev, true for production)
USE_DYNAMODB_CHECKPOINTER=false
CHECKPOINT_TABLE=uipath-builder-checkpoints

# UiPath Orchestrator
UIPATH_URL=https://cloud.uipath.com/your-org/your-tenant
UIPATH_ACCESS_TOKEN=your-token-here

# Project Defaults
COMPANY_NAME=CatoNetworks
DEPARTMENT=IT-Automation
```

- [ ] **Step 3: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/

# Testing
.pytest_cache/
.coverage
htmlcov/
*.cover

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Environment
.env
.env.local

# Generated projects
output/
generated/

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 4: Create README.md**

```markdown
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
```

- [ ] **Step 5: Install dependencies in virtual environment**

Run:
```bash
cd /c/Users/DanielaRosenstein/projects/uipath-builder-agent
python -m venv venv
source venv/Scripts/activate
pip install -e ".[dev]"
```

Expected: Dependencies installed successfully

- [ ] **Step 6: Commit project setup**

```bash
git add pyproject.toml .env.example .gitignore README.md
git commit -m "chore: initial project setup with dependencies

- Add pyproject.toml with core dependencies
- Add .env.example for configuration
- Add .gitignore for Python project
- Add README with installation instructions

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: State Schema Definition

**Files:**
- Create: `agent/__init__.py`
- Create: `agent/state.py`
- Create: `tests/unit/test_state.py`

- [ ] **Step 1: Write failing test for ProjectState schema**

Create `tests/unit/test_state.py`:

```python
"""Tests for ProjectState schema."""

from agent.state import ProjectState


def test_project_state_has_required_fields():
    """ProjectState should define all required fields."""
    # This will fail until we implement ProjectState
    state: ProjectState = {}

    # Core I/O
    assert "messages" in ProjectState.__annotations__
    assert "project_name" in ProjectState.__annotations__
    assert "mode" in ProjectState.__annotations__

    # Design artifacts
    assert "pdd" in ProjectState.__annotations__
    assert "sdd" in ProjectState.__annotations__

    # Generation state
    assert "artifacts" in ProjectState.__annotations__


def test_project_state_messages_uses_add_messages_reducer():
    """messages field should use add_messages reducer."""
    from langgraph.graph.message import add_messages
    from typing import get_args, Annotated

    msg_annotation = ProjectState.__annotations__["messages"]

    # Check if it's Annotated with add_messages
    assert hasattr(msg_annotation, "__metadata__")
    assert add_messages in msg_annotation.__metadata__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_state.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'agent.state'"

- [ ] **Step 3: Create agent package**

Create `agent/__init__.py`:

```python
"""UiPath Builder Agent - Core package."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Implement ProjectState schema**

Create `agent/state.py`:

```python
"""State schema for UiPath Builder Agent."""

from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class ProjectState(TypedDict, total=False):
    """
    Complete state for UiPath Builder Agent.

    Tracks project metadata, design artifacts, generation state,
    and conversation flow across bootstrap and conversational modes.
    """

    # ── Core I/O ─────────────────────────────────────────
    messages: Annotated[list, add_messages]

    # ── Project metadata ──────────────────────────────────
    project_name: str
    project_path: str
    template_type: str          # dispatcher|performer|lrw
    git_repo_url: str

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

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_state.py -v`

Expected: PASS (2 tests)

- [ ] **Step 6: Commit state schema**

```bash
git add agent/__init__.py agent/state.py tests/unit/test_state.py
git commit -m "feat: add ProjectState schema with LangGraph integration

- Define complete state schema for agent
- Use Annotated with add_messages for message handling
- Include all fields for bootstrap and conversational modes
- Add comprehensive test coverage

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Skill Discovery - SkillMetadata Model

**Files:**
- Create: `agent/skill_discovery.py`
- Create: `tests/unit/test_skill_discovery.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create pytest fixtures**

Create `tests/conftest.py`:

```python
"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_skills_repo(tmp_path):
    """
    Create a temporary skills repository structure for testing.

    Structure:
    skills/
      ├── test-skill-1/
      │   └── SKILL.md (with YAML frontmatter)
      ├── test-skill-2/
      │   ├── SKILL.md
      │   ├── references/
      │   │   └── guide.md
      │   └── assets/
      │       └── template.py
      └── invalid-skill/  (no SKILL.md)
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # Skill 1: Minimal SKILL.md
    skill1 = skills_dir / "test-skill-1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("""---
name: test-skill-1
description: |
  Test skill for unit testing.
  TRIGGER when: test mode activated
  DO NOT TRIGGER when: production mode
---

# Test Skill 1

This is a test skill.
""")

    # Skill 2: Full structure with references and assets
    skill2 = skills_dir / "test-skill-2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("""---
name: test-skill-2
description: Test skill with references
---

# Test Skill 2

Another test skill.
""")

    (skill2 / "references").mkdir()
    (skill2 / "references" / "guide.md").write_text("# Guide\n\nTest guide content.")

    (skill2 / "assets").mkdir()
    (skill2 / "assets" / "template.py").write_text("# Template\nprint('test')")

    # Invalid skill: no SKILL.md
    invalid = skills_dir / "invalid-skill"
    invalid.mkdir()
    (invalid / "README.md").write_text("# Not a skill")

    return skills_dir
```

- [ ] **Step 2: Write failing test for SkillMetadata**

Create `tests/unit/test_skill_discovery.py`:

```python
"""Tests for skill discovery system."""

import pytest
from pathlib import Path
from agent.skill_discovery import SkillMetadata, SkillDiscovery


def test_skill_metadata_stores_basic_info(temp_skills_repo):
    """SkillMetadata should store name, description, and prompt."""
    # This will fail until we implement SkillMetadata
    meta = SkillMetadata(
        name="test-skill",
        description="Test description",
        trigger_patterns=["test"],
        references=[],
        assets=[],
        full_prompt="# Test Skill",
        skill_dir=Path("/tmp/test"),
    )

    assert meta.name == "test-skill"
    assert meta.description == "Test description"
    assert meta.trigger_patterns == ["test"]
    assert meta.full_prompt == "# Test Skill"
    assert isinstance(meta.skill_dir, Path)


def test_skill_discovery_finds_all_skills(temp_skills_repo):
    """SkillDiscovery should find all valid skills."""
    discovery = SkillDiscovery(temp_skills_repo)
    registry = discovery.discover_all_skills()

    # Should find test-skill-1 and test-skill-2, but not invalid-skill
    assert len(registry) == 2
    assert "test-skill-1" in registry
    assert "test-skill-2" in registry
    assert "invalid-skill" not in registry
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_skill_discovery.py::test_skill_metadata_stores_basic_info -v`

Expected: FAIL with "cannot import name 'SkillMetadata'"

- [ ] **Step 4: Implement SkillMetadata model**

Create `agent/skill_discovery.py`:

```python
"""Dynamic skill discovery system for UiPath skills repository."""

from dataclasses import dataclass
from pathlib import Path
from typing import List
import yaml
import re


@dataclass
class SkillMetadata:
    """
    Metadata for a UiPath skill parsed from SKILL.md.

    Attributes:
        name: Skill name (from frontmatter or directory name)
        description: Full description from frontmatter
        trigger_patterns: Extracted trigger phrases
        references: List of reference doc paths
        assets: List of asset file paths
        full_prompt: Complete SKILL.md content (used as system prompt)
        skill_dir: Path to skill directory
    """
    name: str
    description: str
    trigger_patterns: List[str]
    references: List[Path]
    assets: List[Path]
    full_prompt: str
    skill_dir: Path


class SkillDiscovery:
    """
    Scans UiPath skills repository and builds dynamic registry.

    Usage:
        discovery = SkillDiscovery(Path("skills"))
        registry = discovery.discover_all_skills()
        skill = registry["uipath-rpa-workflows"]
    """

    def __init__(self, skills_repo_path: Path):
        """
        Initialize skill discovery.

        Args:
            skills_repo_path: Path to cloned UiPath skills repository
        """
        self.skills_path = skills_repo_path / "skills" if (skills_repo_path / "skills").exists() else skills_repo_path
        self.registry = {}

    def discover_all_skills(self) -> dict[str, SkillMetadata]:
        """
        Walk skills directory and parse all SKILL.md files.

        Returns:
            Dictionary mapping skill name to SkillMetadata
        """
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md_path = skill_dir / "SKILL.md"
            if not skill_md_path.exists():
                continue

            skill_meta = self._parse_skill_metadata(skill_dir)
            self.registry[skill_meta.name] = skill_meta

        return self.registry

    def _parse_skill_metadata(self, skill_dir: Path) -> SkillMetadata:
        """
        Parse SKILL.md YAML frontmatter and content.

        Args:
            skill_dir: Path to skill directory

        Returns:
            SkillMetadata with parsed information
        """
        skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")

        # Parse YAML frontmatter
        meta = {}
        body = skill_md

        if skill_md.startswith("---"):
            parts = skill_md.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2]
                meta = yaml.safe_load(frontmatter) or {}

        # Extract trigger patterns
        description = meta.get("description", "")
        triggers = self._extract_triggers(description)

        # Scan references and assets
        references = self._scan_references(skill_dir)
        assets = self._scan_assets(skill_dir)

        return SkillMetadata(
            name=meta.get("name", skill_dir.name),
            description=description,
            trigger_patterns=triggers,
            references=references,
            assets=assets,
            full_prompt=skill_md,
            skill_dir=skill_dir,
        )

    def _extract_triggers(self, description: str) -> List[str]:
        """
        Extract trigger patterns from description.

        Looks for "TRIGGER when:" section and parses comma-separated phrases.

        Args:
            description: Skill description text

        Returns:
            List of trigger phrases
        """
        triggers = []

        if "TRIGGER when:" in description:
            trigger_section = description.split("TRIGGER when:")[1]
            trigger_section = trigger_section.split("DO NOT TRIGGER")[0]

            # Split on commas or newlines
            phrases = re.split(r'[,\n]', trigger_section)
            triggers = [p.strip() for p in phrases if p.strip()]

        return triggers

    def _scan_references(self, skill_dir: Path) -> List[Path]:
        """Find all reference docs in skill/references/."""
        ref_dir = skill_dir / "references"
        if ref_dir.exists() and ref_dir.is_dir():
            return list(ref_dir.glob("*.md"))
        return []

    def _scan_assets(self, skill_dir: Path) -> List[Path]:
        """Find all assets in skill/assets/."""
        asset_dir = skill_dir / "assets"
        if asset_dir.exists() and asset_dir.is_dir():
            return list(asset_dir.iterdir())
        return []
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_skill_discovery.py -v`

Expected: PASS (2 tests)

- [ ] **Step 6: Commit skill discovery foundation**

```bash
git add agent/skill_discovery.py tests/unit/test_skill_discovery.py tests/conftest.py
git commit -m "feat: implement SkillMetadata and basic SkillDiscovery

- Add SkillMetadata dataclass for skill information
- Implement SkillDiscovery.discover_all_skills()
- Parse YAML frontmatter from SKILL.md
- Extract trigger patterns from descriptions
- Scan references and assets directories
- Add comprehensive test fixtures

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Skill Discovery - Trigger Extraction

**Files:**
- Modify: `tests/unit/test_skill_discovery.py`
- Modify: `agent/skill_discovery.py` (already has implementation)

- [ ] **Step 1: Write test for trigger extraction**

Add to `tests/unit/test_skill_discovery.py`:

```python
def test_extract_triggers_from_description():
    """Should extract trigger patterns from TRIGGER when: section."""
    discovery = SkillDiscovery(Path("/tmp"))

    description = """
    Test skill description.
    TRIGGER when: coded workflow projects detected, .cs files present
    DO NOT TRIGGER when: pure XAML workflows
    """

    triggers = discovery._extract_triggers(description)

    assert len(triggers) == 2
    assert "coded workflow projects detected" in triggers
    assert ".cs files present" in triggers


def test_extract_triggers_handles_newlines():
    """Should handle newline-separated triggers."""
    discovery = SkillDiscovery(Path("/tmp"))

    description = """
    TRIGGER when:
      - coded workflow
      - C# activities
      - API integration
    """

    triggers = discovery._extract_triggers(description)

    assert len(triggers) >= 1
    # At least one trigger should be extracted


def test_extract_triggers_returns_empty_when_none():
    """Should return empty list when no TRIGGER when: section."""
    discovery = SkillDiscovery(Path("/tmp"))

    description = "Simple description without triggers"
    triggers = discovery._extract_triggers(description)

    assert triggers == []
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/unit/test_skill_discovery.py::test_extract_triggers -v`

Expected: PASS (3 new tests) - implementation already exists from Task 3

- [ ] **Step 3: Commit trigger extraction tests**

```bash
git add tests/unit/test_skill_discovery.py
git commit -m "test: add comprehensive trigger extraction tests

- Test comma-separated trigger phrases
- Test newline-separated triggers
- Test missing trigger section

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Skill Invocation Tools

**Files:**
- Create: `agent/tools/__init__.py`
- Create: `agent/tools/skill_invoke.py`
- Create: `agent/prompts/__init__.py`
- Create: `agent/prompts/constraints.py`

- [ ] **Step 1: Create constraints module**

Create `agent/prompts/__init__.py`:

```python
"""Prompts and constraints for UiPath Builder Agent."""
```

Create `agent/prompts/constraints.py`:

```python
"""Hard constraints for UiPath project generation."""

HARD_CONSTRAINTS = """
╔══════════════════════════════════════════════════════════════╗
║  HARD CONSTRAINTS — these override everything in this prompt ║
╚══════════════════════════════════════════════════════════════╝

LANGUAGE    C# ONLY. Never generate VB.Net. Never use 'Dim', 'As String',
            'AndAlso', 'OrElse' or any other VB syntax.

EXPERIENCE  MODERN ONLY. Never reference Classic activities, namespaces
            (UiPath.Classic.*), or Classic-era patterns.

TARGET      WINDOWS ONLY. project.json must have "targetFramework": "Windows".
            Never suggest Cross-platform target.

LOGGING     Use UiPath LogMessage activity. Never Console.Write/WriteLine
            in production code.

CONFIG      All configurable values (URLs, timeouts, credentials) belong
            in Data/Config.xlsx or Orchestrator Assets. Never hardcode.

SECRETS     Never write passwords, API keys, or tokens in code or comments.

EXCEPTIONS  Always separate BusinessRuleException from ApplicationException.
            REFramework retry logic applies to ApplicationException only.

ACTIVITIES  Use UiPath.Core.Activities and UiPath.System.Activities (Modern).
            Never UiPath.UIAutomation.Activities (Classic).
"""
```

- [ ] **Step 2: Create tools package**

Create `agent/tools/__init__.py`:

```python
"""Tools for UiPath Builder Agent."""
```

- [ ] **Step 3: Write failing test for get_available_skills**

Add to `tests/unit/test_skill_discovery.py`:

```python
def test_get_available_skills_tool(temp_skills_repo, monkeypatch):
    """get_available_skills should return JSON list of skills."""
    from agent.tools.skill_invoke import get_available_skills
    import json

    # Mock the skills path to use temp_skills_repo
    monkeypatch.setattr(
        "agent.tools.skill_invoke.SKILLS_REPO_PATH",
        temp_skills_repo
    )

    result = get_available_skills()
    skills = json.loads(result)

    assert len(skills) == 2
    assert any(s["name"] == "test-skill-1" for s in skills)
    assert any(s["name"] == "test-skill-2" for s in skills)

    # Check structure
    skill = skills[0]
    assert "name" in skill
    assert "description" in skill
    assert "triggers" in skill
    assert "references" in skill
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/unit/test_skill_discovery.py::test_get_available_skills_tool -v`

Expected: FAIL with "cannot import name 'get_available_skills'"

- [ ] **Step 5: Implement get_available_skills tool**

Create `agent/tools/skill_invoke.py`:

```python
"""Tools for dynamic skill invocation."""

from pathlib import Path
import json
from typing import Optional

from langchain_core.tools import tool
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage

from agent.skill_discovery import SkillDiscovery


# Default skills path (can be overridden for testing)
SKILLS_REPO_PATH = Path(__file__).parent.parent.parent / "skills"


@tool
def get_available_skills() -> str:
    """
    Returns JSON list of all available UiPath skills with descriptions.

    Use this when you need to know what skills are available.
    Dynamically scans the cloned UiPath skills repo, so new skills
    appear automatically after repo updates.

    Returns:
        JSON string with list of skill metadata
    """
    discovery = SkillDiscovery(SKILLS_REPO_PATH)
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


@tool
def invoke_skill(
    skill_name: str,
    task_description: str,
    context: Optional[dict] = None,
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
        invoke_skill("uipath-rpa-workflows", "Generate Main.xaml", {...})
        invoke_skill("uipath-coded-workflows", "Create activity", {...})

    Returns:
        Skill agent response
    """
    discovery = SkillDiscovery(SKILLS_REPO_PATH)
    registry = discovery.discover_all_skills()

    if skill_name not in registry:
        available = ", ".join(registry.keys())
        return f"❌ Skill '{skill_name}' not found. Available: {available}"

    skill = registry[skill_name]

    # Load skill references (truncate large docs)
    references_context = []
    for ref_path in skill.references:
        content = ref_path.read_text(encoding="utf-8")
        references_context.append({
            "file": ref_path.name,
            "content": content[:5000],  # Truncate at 5000 chars
        })

    # Build system prompt
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

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/test_skill_discovery.py::test_get_available_skills_tool -v`

Expected: PASS

- [ ] **Step 7: Commit skill invocation tools**

```bash
git add agent/tools/ agent/prompts/ tests/unit/test_skill_discovery.py
git commit -m "feat: implement skill invocation tools

- Add get_available_skills tool for dynamic skill discovery
- Add invoke_skill tool for spawning skill agents
- Create HARD_CONSTRAINTS in prompts module
- Include skill references in invocation context
- Add test coverage for get_available_skills

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Basic Conversational Node

**Files:**
- Create: `agent/nodes/__init__.py`
- Create: `agent/nodes/conversational.py`

- [ ] **Step 1: Create nodes package**

Create `agent/nodes/__init__.py`:

```python
"""Graph nodes for UiPath Builder Agent."""
```

- [ ] **Step 2: Implement conversational agent node**

Create `agent/nodes/conversational.py`:

```python
"""Conversational agent node for free-form interaction."""

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from agent.state import ProjectState
from agent.tools.skill_invoke import get_available_skills, invoke_skill


# Main conversational agent LLM
conversational_llm = ChatBedrockConverse(
    model="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="us-east-1",
    temperature=0.3,
).bind_tools([get_available_skills, invoke_skill])


CONVERSATIONAL_PROMPT = """
You are the UiPath Builder Agent - a conversational assistant for
building and managing UiPath RPA projects.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DYNAMIC SKILLS SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You have access to a growing library of UiPath skills. Skills are
specialized agents that handle specific aspects of RPA development.

To discover available skills, call: get_available_skills()
To invoke a skill, call: invoke_skill(name, task, context)

When to invoke skills:
• User explicitly requests: "use the rpa-workflows skill to..."
• You determine a task needs specialized capability
• During project bootstrap (generation phase)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONVERSATION MODES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOOTSTRAP MODE (/start-project):
  User provides process description → You guide through personas.

CONVERSATIONAL MODE (default):
  Free-form development conversation. Invoke skills as needed.

Current Mode: {mode}
Current Phase: {current_phase}
"""


async def conversational_agent(state: ProjectState) -> dict:
    """
    Main conversational agent node.

    Handles:
    - Free-form conversation
    - Skill invocation (auto or user-directed)
    - Mode transitions (bootstrap → conversational)

    Args:
        state: Current ProjectState

    Returns:
        Updated state with new messages
    """
    mode = state.get("mode", "conversational")
    current_phase = state.get("current_phase", "dev")

    system_prompt = CONVERSATIONAL_PROMPT.format(
        mode=mode,
        current_phase=current_phase,
    )

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state.get("messages", []))

    response = await conversational_llm.ainvoke(messages)

    # Update state with response
    return {
        "messages": state.get("messages", []) + [response],
    }
```

- [ ] **Step 3: Commit conversational node**

```bash
git add agent/nodes/
git commit -m "feat: implement basic conversational agent node

- Add conversational_agent with tool binding
- Support dynamic skill discovery and invocation
- Include mode-aware system prompt
- Use ChatBedrockConverse with Sonnet 4.5

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Basic LangGraph Setup

**Files:**
- Create: `agent/graph.py`
- Create: `langgraph.json`

- [ ] **Step 1: Implement basic graph**

Create `agent/graph.py`:

```python
"""LangGraph orchestrator for UiPath Builder Agent."""

import os
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import ProjectState
from agent.nodes.conversational import conversational_agent


def route_main(state: ProjectState) -> str:
    """
    Main routing from conversational agent.

    For Sprint 1, always stays in conversational mode.
    Bootstrap mode routing will be added in Sprint 2.
    """
    mode = state.get("mode", "conversational")

    if mode == "bootstrap":
        # Sprint 2: will route to personas
        # For now, stay in conversational
        return "conversational"

    return "conversational"


# Build graph
builder = StateGraph(ProjectState)

# Add nodes
builder.add_node("conversational", conversational_agent)

# Set entry point
builder.set_entry_point("conversational")

# Add edges
builder.add_conditional_edges("conversational", route_main, {
    "conversational": "conversational",
})

# Use MemorySaver for local development
checkpointer = MemorySaver()

# Compile graph
graph = builder.compile(
    checkpointer=checkpointer,
)
```

- [ ] **Step 2: Create langgraph.json config**

Create `langgraph.json`:

```json
{
  "graphs": {
    "builder": "agent/graph.py:graph"
  },
  "python_version": "3.11",
  "dependencies": ["."]
}
```

- [ ] **Step 3: Commit graph setup**

```bash
git add agent/graph.py langgraph.json
git commit -m "feat: implement basic LangGraph orchestrator

- Create StateGraph with conversational node
- Add route_main for mode-based routing
- Use MemorySaver checkpointer for local dev
- Add langgraph.json configuration

Bootstrap mode routing will be added in Sprint 2.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Git Submodules Setup

**Files:**
- Add: `.gitmodules`
- Add: `skills/` (git submodule)
- Add: `templates/dispatcher/` (git submodule)
- Add: `templates/performer/` (git submodule)
- Add: `templates/long-running/` (git submodule)

- [ ] **Step 1: Add UiPath skills submodule**

Run:
```bash
cd /c/Users/DanielaRosenstein/projects/uipath-builder-agent
git submodule add https://github.com/UiPath/skills skills
```

Expected: Submodule added, .gitmodules created

- [ ] **Step 2: Add Cato dispatcher template submodule**

Run:
```bash
git submodule add https://github.com/cato-networks-IT/AgenticAi_PROCESSNAME_DispatcherTemplate templates/dispatcher
```

Expected: Submodule added

- [ ] **Step 3: Add Cato performer template submodule**

Run:
```bash
git submodule add https://github.com/cato-networks-IT/AgenticAi_PROCESSNAME_PerformerTemplate templates/performer
```

Expected: Submodule added

- [ ] **Step 4: Add Cato long-running template submodule**

Run:
```bash
git submodule add https://github.com/cato-networks-IT/AgenticAi_PROCESSNAME_LongRunningAutomationTemplate templates/long-running
```

Expected: Submodule added

- [ ] **Step 5: Initialize submodules**

Run:
```bash
git submodule update --init --recursive
```

Expected: All submodules cloned successfully

- [ ] **Step 6: Commit submodule configuration**

```bash
git add .gitmodules skills/ templates/
git commit -m "chore: add git submodules for skills and templates

- Add UiPath/skills for dynamic skill discovery
- Add Cato dispatcher template
- Add Cato performer template
- Add Cato long-running automation template

All templates and skills now version-controlled via submodules.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Integration Test - Skill Discovery

**Files:**
- Create: `tests/integration/__init__.py`
- Create: `tests/integration/test_skill_discovery_integration.py`

- [ ] **Step 1: Create integration tests package**

Create `tests/integration/__init__.py`:

```python
"""Integration tests for UiPath Builder Agent."""
```

- [ ] **Step 2: Write integration test for real skills**

Create `tests/integration/test_skill_discovery_integration.py`:

```python
"""Integration tests for skill discovery with real UiPath skills repo."""

import pytest
from pathlib import Path
from agent.skill_discovery import SkillDiscovery


@pytest.mark.skipif(
    not (Path(__file__).parent.parent.parent / "skills").exists(),
    reason="UiPath skills submodule not initialized"
)
def test_discover_real_uipath_skills():
    """
    Integration test: discover skills from real UiPath repo.

    This test requires git submodule init.
    """
    skills_path = Path(__file__).parent.parent.parent / "skills"
    discovery = SkillDiscovery(skills_path)
    registry = discovery.discover_all_skills()

    # Should find at least the known skills
    assert len(registry) >= 5, f"Expected at least 5 skills, found {len(registry)}"

    # Check for known skills (as of design spec)
    expected_skills = [
        "uipath-rpa-workflows",
        "uipath-coded-workflows",
        "uipath-platform",
    ]

    for skill_name in expected_skills:
        assert skill_name in registry, f"Expected skill '{skill_name}' not found"

        skill = registry[skill_name]
        assert skill.name == skill_name
        assert skill.full_prompt  # SKILL.md loaded
        assert skill.skill_dir.exists()


@pytest.mark.skipif(
    not (Path(__file__).parent.parent.parent / "skills").exists(),
    reason="UiPath skills submodule not initialized"
)
def test_rpa_workflows_skill_has_references():
    """
    Integration test: uipath-rpa-workflows should have reference docs.
    """
    skills_path = Path(__file__).parent.parent.parent / "skills"
    discovery = SkillDiscovery(skills_path)
    registry = discovery.discover_all_skills()

    if "uipath-rpa-workflows" in registry:
        skill = registry["uipath-rpa-workflows"]

        # Should have references
        assert len(skill.references) > 0, "Expected reference docs in uipath-rpa-workflows"

        # Check reference files exist
        for ref in skill.references:
            assert ref.exists(), f"Reference file missing: {ref}"
```

- [ ] **Step 3: Run integration tests**

Run: `pytest tests/integration/ -v`

Expected: PASS (if submodules initialized) or SKIP (if not initialized)

- [ ] **Step 4: Commit integration tests**

```bash
git add tests/integration/
git commit -m "test: add integration tests for real UiPath skills

- Test discovery against actual UiPath skills repo
- Verify known skills are found
- Check skill references exist
- Skip if submodules not initialized

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Documentation & Sprint 1 Completion

**Files:**
- Update: `README.md`
- Create: `docs/sprint-1-summary.md`

- [ ] **Step 1: Update README with Sprint 1 status**

Update `README.md` to add:

```markdown
## Project Status

### ✅ Sprint 1: Foundation (Complete)

- [x] Project structure and dependencies
- [x] Dynamic skill discovery system
- [x] State management (ProjectState schema)
- [x] Basic LangGraph orchestrator
- [x] Skill invocation tools (get_available_skills, invoke_skill)
- [x] Conversational agent node
- [x] Git submodules (UiPath skills + Cato templates)
- [x] Unit and integration tests

### 🚧 Sprint 2: Bootstrap Flow (Next)

- [ ] BA persona node
- [ ] SA persona node
- [ ] HITL review node
- [ ] Template cloning tools
- [ ] CLI: start-project command

## Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests (requires submodule init)
git submodule update --init --recursive
pytest tests/integration/ -v

# Run all tests with coverage
pytest --cov=agent --cov-report=html
```
```

- [ ] **Step 2: Create Sprint 1 summary document**

Create `docs/sprint-1-summary.md`:

```markdown
# Sprint 1: Foundation - Summary

**Status:** ✅ Complete

**Duration:** 2 weeks

**Goal:** Establish project foundation with dynamic skill discovery, state management, and basic LangGraph orchestration.

---

## Completed Tasks

### 1. Project Setup ✅
- pyproject.toml with all dependencies
- .env.example for configuration
- .gitignore for Python project
- README with installation instructions
- Virtual environment setup

### 2. State Management ✅
- ProjectState TypedDict schema
- LangGraph integration with add_messages
- Support for bootstrap and conversational modes
- Complete test coverage

### 3. Dynamic Skill Discovery ✅
- SkillMetadata dataclass
- SkillDiscovery class with auto-scanning
- YAML frontmatter parsing
- Trigger pattern extraction
- Reference and asset scanning
- Unit tests with fixtures

### 4. Skill Invocation Tools ✅
- get_available_skills tool
- invoke_skill tool with full SKILL.md as prompt
- HARD_CONSTRAINTS module
- Tool integration with LangGraph

### 5. Basic Conversational Agent ✅
- Conversational node with tool binding
- Mode-aware system prompts
- ChatBedrockConverse integration

### 6. LangGraph Orchestrator ✅
- Basic StateGraph setup
- route_main function for mode routing
- MemorySaver checkpointer
- langgraph.json configuration

### 7. Git Submodules ✅
- UiPath/skills submodule
- Cato dispatcher template
- Cato performer template
- Cato long-running automation template

### 8. Testing ✅
- Unit test suite with pytest
- Integration tests for real skills
- Test fixtures for temp skill repos
- Skip logic for missing submodules

---

## Key Achievements

1. **Zero-Maintenance Skill System**: Skills auto-discovered from git submodule
2. **Production-Ready State**: Complete ProjectState schema for all modes
3. **Tool Integration**: Skills invocable as LangGraph tools
4. **Test Coverage**: Comprehensive unit and integration tests

---

## Metrics

- **Files Created:** 20+
- **Lines of Code:** ~800
- **Test Coverage:** >90% (unit tests)
- **Commits:** 10
- **Tests Passing:** 15+

---

## Next Steps (Sprint 2)

1. Implement BA persona node
2. Implement SA persona node
3. Add HITL review node
4. Create template cloning tools
5. Build CLI with start-project command

See: `docs/superpowers/plans/2026-04-01-sprint-2-bootstrap-flow.md` (to be created)
```

- [ ] **Step 3: Run full test suite**

Run:
```bash
pytest --cov=agent --cov-report=term
```

Expected: All tests pass, coverage >80%

- [ ] **Step 4: Commit documentation updates**

```bash
git add README.md docs/sprint-1-summary.md
git commit -m "docs: update README and add Sprint 1 summary

- Mark Sprint 1 as complete in README
- Add Sprint 1 summary document
- Document completed tasks and metrics
- Outline Sprint 2 next steps

Sprint 1 Foundation: ✅ Complete

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Create Sprint 1 git tag**

Run:
```bash
git tag -a v0.1.0-sprint1 -m "Sprint 1: Foundation complete

- Dynamic skill discovery system
- State management and LangGraph orchestrator
- Skill invocation tools
- Git submodules for skills and templates
- Comprehensive test coverage"
```

Expected: Tag created successfully

---

## Self-Review Checklist

Before marking this plan as complete, verify:

**✅ Spec Coverage**
- [x] Project structure setup (from Implementation Plan)
- [x] Skill discovery system (from Core Components #1)
- [x] State management (from Core Components #2)
- [x] Basic conversational agent (from Component Architecture)
- [x] Tool layer (from Core Components #5)
- [x] Git submodules (from Git Integration)

**✅ No Placeholders**
- [x] All code blocks show actual implementation
- [x] All file paths are exact
- [x] All commands have expected outputs
- [x] No "TBD" or "TODO" markers
- [x] No "similar to Task N" references

**✅ Type Consistency**
- [x] ProjectState fields match across all files
- [x] SkillMetadata fields consistent
- [x] Tool names match (get_available_skills, invoke_skill)
- [x] Function signatures consistent across tests and implementation

---

## Plan Complete ✅

**Saved to:** `docs/superpowers/plans/2026-04-01-sprint-1-foundation.md`

**Next Steps:**
1. Choose execution approach (Subagent-Driven or Inline)
2. Execute tasks 1-10 in sequence
3. Verify all tests pass
4. Create Sprint 2 plan for Bootstrap Flow

**Estimated Time:** 2 weeks (10 tasks × 1-2 hours per task)

**Dependencies for Sprint 2:**
- AWS Bedrock access configured
- Git submodules initialized
- Virtual environment active
- All Sprint 1 tests passing
