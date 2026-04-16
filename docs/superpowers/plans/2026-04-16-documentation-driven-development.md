# Documentation-Driven Development with Specialized Agent Roles

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable the UiPath Builder Agent to detect when a project requires documentation (PDD/SDD/ADD/TDD) and route to specialized documentation agents before proceeding with implementation.

**Architecture:** Intent classifier detects documentation needs, router dispatches to BA Agent (PDD creation) or Solution Architect Agent (SDD/ADD/TDD creation), documentation artifacts are persisted to project workspace, and main executor uses generated docs as context for implementation.

**Tech Stack:** Python 3.11+, LangGraph, AWS Bedrock (Claude), existing skill framework, YAML/Markdown templates

---

## File Structure

### Files to Create

| File | Responsibility |
|------|---------------|
| `uipath_claude/query/doc_need_detector.py` | Detect when project requires documentation based on complexity/scope |
| `uipath_claude/query/ba_agent.py` | Business Analyst agent for PDD creation via chat |
| `uipath_claude/query/solution_architect_agent.py` | Solution Architect agent for SDD/ADD/TDD creation |
| `uipath_claude/query/doc_router.py` | Route to appropriate documentation agent based on detected need |
| `uipath_claude/tools/doc_tools.py` | Tools for reading/writing documentation files |
| `uipath_claude/skills/documentation/` | Directory for documentation skill markdown files |
| `uipath_claude/skills/documentation/pdd-creation.md` | PDD creation skill (port from template project) |
| `uipath_claude/skills/documentation/sdd-creation.md` | SDD creation skill (port from template project) |
| `uipath_claude/skills/documentation/add-creation.md` | ADD creation skill (port from template project) |
| `uipath_claude/skills/documentation/tdd-creation.md` | TDD creation skill (port from template project) |
| `uipath_claude/templates/pdd.md` | PDD template file |
| `uipath_claude/templates/sdd.md` | SDD template file |
| `uipath_claude/templates/add.md` | ADD template file (for agentic projects) |
| `tests/test_doc_need_detector.py` | Unit tests for documentation need detection |
| `tests/test_ba_agent.py` | Unit tests for BA agent |
| `tests/test_solution_architect_agent.py` | Unit tests for SA agent |
| `tests/test_doc_router.py` | Unit tests for documentation router |

### Files to Modify

| File | Changes |
|------|---------|
| `uipath_claude/query/intent_classifier.py` | Add `DOCUMENTATION` intent type, detect doc-related phrases |
| `uipath_claude/graph/nodes/route.py` | Add documentation routing branch |
| `uipath_claude/graph/builder.py` | Add documentation nodes to graph |
| `uipath_claude/graph/state.py` | Add doc-related state fields |
| `uipath_claude/tools/skill_execution_tools.py` | Add doc reading tools to available tools |
| `uipath_claude/cli/app.py` | Add `--doc-mode` flag and doc-specific CLI markers |
| `uipath_claude/rendering/progress.py` | Add doc-phase rendering |

---

## Phase 1: Documentation Need Detection

### Task 1: Add Documentation Intent Type

**Files:**
- Modify: `uipath_claude/query/intent_classifier.py:9-15`
- Test: `tests/test_doc_need_detector.py`

- [ ] **Step 1: Write the failing test for documentation intent**

```python
# tests/test_doc_need_detector.py
"""Tests for documentation need detection."""

import pytest
from uipath_claude.query.intent_classifier import IntentType, classify_intent


class TestDocumentationIntent:
    """Tests for documentation-related intent classification."""

    def test_explicit_pdd_request(self):
        """Explicit PDD request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("Create a PDD for invoice processing")
        assert intent == IntentType.DOCUMENTATION
        assert "pdd" in reason.lower() or "documentation" in reason.lower()

    def test_explicit_sdd_request(self):
        """Explicit SDD request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("I need an SDD for this automation")
        assert intent == IntentType.DOCUMENTATION

    def test_help_me_document_request(self):
        """Help me document request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("Help me document this process")
        assert intent == IntentType.DOCUMENTATION

    def test_process_definition_request(self):
        """Process definition request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("I need to create a process definition")
        assert intent == IntentType.DOCUMENTATION

    def test_technical_design_request(self):
        """Technical design request should return DOCUMENTATION intent."""
        intent, reason = classify_intent("Create a technical design document")
        assert intent == IntentType.DOCUMENTATION

    def test_simple_build_not_documentation(self):
        """Simple build request should NOT return DOCUMENTATION."""
        intent, _ = classify_intent("Create a workflow that sends an email")
        assert intent != IntentType.DOCUMENTATION

    def test_complex_project_indicator(self):
        """Complex project indicators should suggest documentation need."""
        # This tests the detection, not forced routing
        intent, reason = classify_intent(
            "Build an enterprise invoice processing system with SAP integration, "
            "human approvals, and compliance reporting"
        )
        # Could be BUILD but complexity should be flagged
        assert intent in (IntentType.BUILD, IntentType.DOCUMENTATION)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_doc_need_detector.py -v`
Expected: FAIL with "IntentType has no attribute DOCUMENTATION"

- [ ] **Step 3: Add DOCUMENTATION intent type to enum**

```python
# uipath_claude/query/intent_classifier.py
# Add to IntentType enum (around line 9-15)

class IntentType(str, Enum):
    """High-level intent for a user message."""

    QUESTION = "question"
    BUILD = "build"
    AMBIGUOUS = "ambiguous"
    DOCUMENTATION = "documentation"  # NEW: explicit doc requests
```

- [ ] **Step 4: Add documentation phrase detection**

```python
# uipath_claude/query/intent_classifier.py
# Add after _BUILD_PHRASES (around line 38)

_DOC_PHRASES = (
    "create a pdd",
    "create pdd",
    "write a pdd",
    "create a sdd",
    "create sdd", 
    "write a sdd",
    "create a tdd",
    "create tdd",
    "process definition document",
    "solution design document",
    "technical design document",
    "agent design document",
    "help me document",
    "document this process",
    "document this automation",
    "need documentation",
    "create documentation",
    "write documentation",
)

_DOC_KEYWORDS = frozenset({
    "pdd",
    "sdd",
    "tdd",
    "add",
})
```

- [ ] **Step 5: Update classify_intent function**

```python
# uipath_claude/query/intent_classifier.py
# Update classify_intent function to check documentation first

def classify_intent(user_input: str) -> tuple[IntentType, str]:
    """
    Classify user intent.

    Returns:
        (IntentType, short reason code for logging/tests)
    """
    stripped = user_input.strip()
    if not stripped:
        return IntentType.AMBIGUOUS, "empty"

    lower = stripped.lower()
    user_tokens = _tokenize(stripped)

    # Check documentation intent FIRST (highest priority for explicit requests)
    has_doc = any(p in lower for p in _DOC_PHRASES)
    has_doc_keyword = bool(user_tokens & _DOC_KEYWORDS)
    
    if has_doc or has_doc_keyword:
        return IntentType.DOCUMENTATION, "doc_phrase"

    has_build = any(p in lower for p in _BUILD_PHRASES)
    has_question = any(p in lower for p in _QUESTION_PHRASES)

    if has_question and not has_build:
        return IntentType.QUESTION, "question_phrase"

    if has_build:
        if _is_vague(lower, user_tokens):
            return IntentType.AMBIGUOUS, "vague_build"
        return IntentType.BUILD, "build_phrase"

    if _is_vague(lower, user_tokens):
        return IntentType.AMBIGUOUS, "vague_request"

    return IntentType.BUILD, "default"
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_doc_need_detector.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add uipath_claude/query/intent_classifier.py tests/test_doc_need_detector.py
git commit -m "feat: add DOCUMENTATION intent type to intent classifier"
```

---

### Task 2: Create Documentation Need Detector

**Files:**
- Create: `uipath_claude/query/doc_need_detector.py`
- Test: `tests/test_doc_need_detector.py`

- [ ] **Step 1: Write failing tests for complexity detection**

```python
# tests/test_doc_need_detector.py
# Add to existing file

from uipath_claude.query.doc_need_detector import (
    DocNeedLevel,
    detect_documentation_need,
    ComplexityIndicators,
)


class TestDocNeedDetector:
    """Tests for documentation need detection based on project complexity."""

    def test_simple_workflow_no_doc_needed(self):
        """Simple workflow should not require documentation."""
        result = detect_documentation_need("Send an email with attachment")
        assert result.level == DocNeedLevel.NONE
        assert result.recommended_docs == []

    def test_integration_suggests_sdd(self):
        """Integration with external system suggests SDD."""
        result = detect_documentation_need(
            "Create workflow that reads from Salesforce and updates SAP"
        )
        assert result.level in (DocNeedLevel.RECOMMENDED, DocNeedLevel.REQUIRED)
        assert "sdd" in result.recommended_docs

    def test_human_approval_suggests_pdd(self):
        """Human-in-the-loop suggests PDD."""
        result = detect_documentation_need(
            "Build invoice processing with manager approval for amounts over 10k"
        )
        assert result.level in (DocNeedLevel.RECOMMENDED, DocNeedLevel.REQUIRED)
        assert "pdd" in result.recommended_docs

    def test_agentic_workflow_suggests_add(self):
        """AI/Agent components suggest ADD."""
        result = detect_documentation_need(
            "Create an AI agent that analyzes documents and makes decisions"
        )
        assert "add" in result.recommended_docs

    def test_enterprise_project_requires_full_docs(self):
        """Enterprise-scale project requires full documentation."""
        result = detect_documentation_need(
            "Build enterprise invoice processing system with SAP integration, "
            "Salesforce CRM sync, manager approvals, compliance reporting, "
            "multi-department routing, and audit trail"
        )
        assert result.level == DocNeedLevel.REQUIRED
        assert "pdd" in result.recommended_docs
        assert "sdd" in result.recommended_docs

    def test_explicit_doc_type_requested(self):
        """Explicit doc request returns that doc type."""
        result = detect_documentation_need("Create a PDD for this process")
        assert result.level == DocNeedLevel.REQUIRED
        assert "pdd" in result.recommended_docs
        assert result.explicit_request is True

    def test_complexity_indicators_detected(self):
        """Should detect various complexity indicators."""
        result = detect_documentation_need(
            "Build workflow with Oracle database, REST API, exception handling, "
            "retry logic, and notification system"
        )
        indicators = result.indicators
        assert indicators.has_integration is True
        assert indicators.has_error_handling is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_doc_need_detector.py::TestDocNeedDetector -v`
Expected: FAIL with "cannot import name 'DocNeedLevel'"

- [ ] **Step 3: Create doc_need_detector module**

```python
# uipath_claude/query/doc_need_detector.py
"""Detect when a project requires documentation based on complexity and scope."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class DocNeedLevel(str, Enum):
    """Level of documentation need."""
    
    NONE = "none"
    OPTIONAL = "optional"
    RECOMMENDED = "recommended"
    REQUIRED = "required"


@dataclass
class ComplexityIndicators:
    """Indicators of project complexity."""
    
    has_integration: bool = False
    has_human_approval: bool = False
    has_agentic_component: bool = False
    has_error_handling: bool = False
    has_compliance: bool = False
    has_multi_system: bool = False
    has_data_transformation: bool = False
    integration_count: int = 0
    
    @property
    def complexity_score(self) -> int:
        """Calculate overall complexity score (0-10)."""
        score = 0
        if self.has_integration:
            score += 2
        if self.has_human_approval:
            score += 2
        if self.has_agentic_component:
            score += 3
        if self.has_error_handling:
            score += 1
        if self.has_compliance:
            score += 2
        if self.has_multi_system:
            score += 2
        if self.has_data_transformation:
            score += 1
        score += min(self.integration_count, 3)
        return min(score, 10)


@dataclass
class DocNeedResult:
    """Result of documentation need detection."""
    
    level: DocNeedLevel
    recommended_docs: list[str] = field(default_factory=list)
    indicators: ComplexityIndicators = field(default_factory=ComplexityIndicators)
    explicit_request: bool = False
    reason: str = ""


# Patterns for detecting complexity indicators
_INTEGRATION_PATTERNS = (
    r"\b(salesforce|sap|oracle|servicenow|dynamics|workday|jira|confluence)\b",
    r"\b(api|rest|soap|graphql|webhook)\b",
    r"\b(database|sql|mongodb|postgres|mysql)\b",
    r"\b(integration|connect|sync)\b",
)

_APPROVAL_PATTERNS = (
    r"\b(approv|review|sign.?off|authorize|confirm)\b",
    r"\b(manager|supervisor|human|manual)\b",
    r"\b(action.?center|hitl|human.?in.?the.?loop)\b",
)

_AGENTIC_PATTERNS = (
    r"\b(ai|agent|llm|gpt|claude|intelligent|ml|machine.?learning)\b",
    r"\b(decision|analyze|classify|predict|recommend)\b",
    r"\b(langchain|langgraph|openai|anthropic|bedrock)\b",
)

_ERROR_PATTERNS = (
    r"\b(error|exception|retry|fallback|recover)\b",
    r"\b(handle|catch|throw|fail)\b",
)

_COMPLIANCE_PATTERNS = (
    r"\b(compliance|audit|gdpr|hipaa|sox|pci|regulation)\b",
    r"\b(security|encrypt|sensitive|pii|phi)\b",
    r"\b(log|track|trace|report)\b",
)

_DOC_TYPE_PATTERNS = {
    "pdd": r"\b(pdd|process.?definition)\b",
    "sdd": r"\b(sdd|solution.?design)\b",
    "add": r"\b(add|agent.?design)\b",
    "tdd": r"\b(tdd|technical.?design)\b",
}


def _count_matches(text: str, patterns: tuple[str, ...]) -> int:
    """Count how many patterns match in text."""
    lower = text.lower()
    return sum(1 for p in patterns if re.search(p, lower, re.IGNORECASE))


def _detect_indicators(text: str) -> ComplexityIndicators:
    """Detect complexity indicators from user input."""
    lower = text.lower()
    
    integration_count = _count_matches(text, _INTEGRATION_PATTERNS)
    
    return ComplexityIndicators(
        has_integration=integration_count > 0,
        has_human_approval=_count_matches(text, _APPROVAL_PATTERNS) > 0,
        has_agentic_component=_count_matches(text, _AGENTIC_PATTERNS) > 0,
        has_error_handling=_count_matches(text, _ERROR_PATTERNS) > 0,
        has_compliance=_count_matches(text, _COMPLIANCE_PATTERNS) > 0,
        has_multi_system=integration_count > 1,
        has_data_transformation="transform" in lower or "convert" in lower or "map" in lower,
        integration_count=integration_count,
    )


def _detect_explicit_doc_request(text: str) -> tuple[bool, list[str]]:
    """Check if user explicitly requested specific documentation."""
    lower = text.lower()
    requested = []
    
    for doc_type, pattern in _DOC_TYPE_PATTERNS.items():
        if re.search(pattern, lower, re.IGNORECASE):
            requested.append(doc_type)
    
    # Also check for generic documentation requests
    if re.search(r"\b(document|documentation)\b", lower):
        if not requested:
            # Generic doc request without specific type
            requested.append("pdd")  # Default to PDD for business process docs
    
    return bool(requested), requested


def detect_documentation_need(user_input: str) -> DocNeedResult:
    """
    Detect whether a project requires documentation and which types.
    
    Args:
        user_input: The user's project description or request
        
    Returns:
        DocNeedResult with level, recommended docs, and indicators
    """
    indicators = _detect_indicators(user_input)
    explicit, explicit_docs = _detect_explicit_doc_request(user_input)
    
    if explicit:
        return DocNeedResult(
            level=DocNeedLevel.REQUIRED,
            recommended_docs=explicit_docs,
            indicators=indicators,
            explicit_request=True,
            reason="User explicitly requested documentation",
        )
    
    score = indicators.complexity_score
    recommended = []
    
    # Determine recommended doc types based on indicators
    if indicators.has_human_approval or indicators.has_compliance:
        recommended.append("pdd")
    
    if indicators.has_integration or indicators.has_multi_system:
        recommended.append("sdd")
    
    if indicators.has_agentic_component:
        recommended.append("add")
    
    # If multiple docs recommended, also suggest TDD
    if len(recommended) >= 2:
        recommended.append("tdd")
    
    # Determine level based on score
    if score >= 7:
        level = DocNeedLevel.REQUIRED
        reason = f"High complexity score ({score}/10) - documentation required"
    elif score >= 4:
        level = DocNeedLevel.RECOMMENDED
        reason = f"Moderate complexity ({score}/10) - documentation recommended"
    elif score >= 2:
        level = DocNeedLevel.OPTIONAL
        reason = f"Low complexity ({score}/10) - documentation optional"
    else:
        level = DocNeedLevel.NONE
        reason = "Simple project - no documentation needed"
        recommended = []
    
    return DocNeedResult(
        level=level,
        recommended_docs=recommended,
        indicators=indicators,
        explicit_request=False,
        reason=reason,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_doc_need_detector.py::TestDocNeedDetector -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/query/doc_need_detector.py tests/test_doc_need_detector.py
git commit -m "feat: add documentation need detector with complexity analysis"
```

---

## Phase 2: Documentation Tools

### Task 3: Create Documentation Tools

**Files:**
- Create: `uipath_claude/tools/doc_tools.py`
- Test: `tests/test_doc_tools.py`

- [ ] **Step 1: Write failing tests for doc tools**

```python
# tests/test_doc_tools.py
"""Tests for documentation tools."""

import pytest
import tempfile
from pathlib import Path

from uipath_claude.tools.doc_tools import (
    read_template,
    write_doc,
    read_doc,
    list_docs,
    get_doc_tools,
)


class TestDocTools:
    """Tests for documentation tools."""

    def test_read_template_pdd(self):
        """Should read PDD template."""
        content = read_template("pdd")
        assert "Process Definition Document" in content
        assert "{{process_name}}" in content

    def test_read_template_sdd(self):
        """Should read SDD template."""
        content = read_template("sdd")
        assert "Solution Design Document" in content

    def test_read_template_invalid(self):
        """Should raise error for invalid template."""
        with pytest.raises(ValueError, match="Unknown template"):
            read_template("invalid")

    def test_write_and_read_doc(self, tmp_path):
        """Should write and read documentation."""
        doc_content = "# Test PDD\n\nThis is a test."
        
        result = write_doc(
            doc_type="pdd",
            content=doc_content,
            project_dir=str(tmp_path),
        )
        assert result["success"] is True
        assert "pdd.md" in result["path"]
        
        read_content = read_doc("pdd", project_dir=str(tmp_path))
        assert read_content == doc_content

    def test_list_docs(self, tmp_path):
        """Should list existing documentation."""
        # Create some docs
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "pdd.md").write_text("# PDD")
        (docs_dir / "sdd.md").write_text("# SDD")
        
        docs = list_docs(project_dir=str(tmp_path))
        assert "pdd" in docs
        assert "sdd" in docs
        assert docs["pdd"]["exists"] is True
        assert docs["sdd"]["exists"] is True

    def test_get_doc_tools_returns_tools(self):
        """Should return list of documentation tools."""
        tools = get_doc_tools()
        tool_names = [t.name for t in tools]
        assert "read_doc_template" in tool_names
        assert "write_documentation" in tool_names
        assert "read_documentation" in tool_names
        assert "list_documentation" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_doc_tools.py -v`
Expected: FAIL with "cannot import name 'read_template'"

- [ ] **Step 3: Create doc_tools module**

```python
# uipath_claude/tools/doc_tools.py
"""Tools for reading and writing documentation files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


def _get_templates_dir() -> Path:
    """Get the templates directory path."""
    # Look for templates in the package directory
    pkg_dir = Path(__file__).parent.parent
    templates_dir = pkg_dir / "templates"
    if templates_dir.exists():
        return templates_dir
    # Fallback to workspace templates
    return Path.cwd() / "templates"


def _get_docs_dir(project_dir: str | None = None) -> Path:
    """Get the docs directory for a project."""
    if project_dir:
        base = Path(project_dir)
    else:
        base = Path.cwd()
    docs_dir = base / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir


_TEMPLATE_NAMES = {
    "pdd": "pdd.md",
    "sdd": "sdd.md",
    "add": "add.md",
    "tdd": "tdd.md",
}


def read_template(doc_type: str) -> str:
    """
    Read a documentation template.
    
    Args:
        doc_type: Type of document (pdd, sdd, add, tdd)
        
    Returns:
        Template content as string
        
    Raises:
        ValueError: If template type is unknown
        FileNotFoundError: If template file not found
    """
    doc_type = doc_type.lower()
    if doc_type not in _TEMPLATE_NAMES:
        raise ValueError(f"Unknown template type: {doc_type}. Valid types: {list(_TEMPLATE_NAMES.keys())}")
    
    template_file = _get_templates_dir() / _TEMPLATE_NAMES[doc_type]
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")
    
    return template_file.read_text(encoding="utf-8")


def write_doc(
    doc_type: str,
    content: str,
    project_dir: str | None = None,
) -> dict[str, Any]:
    """
    Write documentation to a project.
    
    Args:
        doc_type: Type of document (pdd, sdd, add, tdd)
        content: Document content
        project_dir: Project directory (defaults to CWD)
        
    Returns:
        Dict with success status and path
    """
    doc_type = doc_type.lower()
    if doc_type not in _TEMPLATE_NAMES:
        return {
            "success": False,
            "error": f"Unknown document type: {doc_type}",
        }
    
    docs_dir = _get_docs_dir(project_dir)
    doc_path = docs_dir / _TEMPLATE_NAMES[doc_type]
    
    try:
        doc_path.write_text(content, encoding="utf-8")
        return {
            "success": True,
            "path": str(doc_path),
            "bytes_written": len(content.encode("utf-8")),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def read_doc(doc_type: str, project_dir: str | None = None) -> str:
    """
    Read documentation from a project.
    
    Args:
        doc_type: Type of document (pdd, sdd, add, tdd)
        project_dir: Project directory (defaults to CWD)
        
    Returns:
        Document content
        
    Raises:
        FileNotFoundError: If document doesn't exist
    """
    doc_type = doc_type.lower()
    if doc_type not in _TEMPLATE_NAMES:
        raise ValueError(f"Unknown document type: {doc_type}")
    
    docs_dir = _get_docs_dir(project_dir)
    doc_path = docs_dir / _TEMPLATE_NAMES[doc_type]
    
    if not doc_path.exists():
        raise FileNotFoundError(f"Document not found: {doc_path}")
    
    return doc_path.read_text(encoding="utf-8")


def list_docs(project_dir: str | None = None) -> dict[str, dict[str, Any]]:
    """
    List existing documentation in a project.
    
    Args:
        project_dir: Project directory (defaults to CWD)
        
    Returns:
        Dict mapping doc type to status info
    """
    docs_dir = _get_docs_dir(project_dir)
    result = {}
    
    for doc_type, filename in _TEMPLATE_NAMES.items():
        doc_path = docs_dir / filename
        if doc_path.exists():
            stat = doc_path.stat()
            result[doc_type] = {
                "exists": True,
                "path": str(doc_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
            }
        else:
            result[doc_type] = {
                "exists": False,
                "path": str(doc_path),
            }
    
    return result


# LangChain tool wrappers

@tool
def read_doc_template(doc_type: str) -> str:
    """
    Read a documentation template (PDD, SDD, ADD, or TDD).
    
    Use this to get the structure and placeholders for a documentation type
    before filling it out with project-specific information.
    
    Args:
        doc_type: Type of document - one of: pdd, sdd, add, tdd
        
    Returns:
        Template content with placeholders
    """
    return read_template(doc_type)


@tool
def write_documentation(doc_type: str, content: str) -> dict[str, Any]:
    """
    Write completed documentation to the project's docs folder.
    
    Args:
        doc_type: Type of document - one of: pdd, sdd, add, tdd
        content: The completed documentation content (markdown)
        
    Returns:
        Dict with success status and file path
    """
    return write_doc(doc_type, content)


@tool
def read_documentation(doc_type: str) -> str:
    """
    Read existing documentation from the project.
    
    Args:
        doc_type: Type of document - one of: pdd, sdd, add, tdd
        
    Returns:
        Document content
    """
    return read_doc(doc_type)


@tool
def list_documentation() -> dict[str, dict[str, Any]]:
    """
    List all documentation files in the current project.
    
    Returns:
        Dict mapping doc type to existence and path info
    """
    return list_docs()


def get_doc_tools() -> list:
    """Get all documentation tools for agent use."""
    return [
        read_doc_template,
        write_documentation,
        read_documentation,
        list_documentation,
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_doc_tools.py -v`
Expected: PASS (may need to create template files first)

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/tools/doc_tools.py tests/test_doc_tools.py
git commit -m "feat: add documentation tools for reading/writing docs"
```

---

### Task 4: Create Documentation Templates

**Files:**
- Create: `uipath_claude/templates/pdd.md`
- Create: `uipath_claude/templates/sdd.md`
- Create: `uipath_claude/templates/add.md`
- Create: `uipath_claude/templates/tdd.md`

- [ ] **Step 1: Create templates directory**

```bash
mkdir -p uipath_claude/templates
```

- [ ] **Step 2: Create PDD template**

Copy the PDD template from `C:\Users\DanielaRosenstein\cursor_projects\UiPath_Spec_Project_Template\docs\pdd.md` to `uipath_claude/templates/pdd.md`.

- [ ] **Step 3: Create SDD template**

Copy the SDD template from `C:\Users\DanielaRosenstein\cursor_projects\UiPath_Spec_Project_Template\templates\sdd-template.md` to `uipath_claude/templates/sdd.md`.

- [ ] **Step 4: Create ADD template**

Copy the ADD template from `C:\Users\DanielaRosenstein\cursor_projects\UiPath_Spec_Project_Template\docs\agent.md` to `uipath_claude/templates/add.md`.

- [ ] **Step 5: Create TDD template**

Copy the TDD template from `C:\Users\DanielaRosenstein\cursor_projects\UiPath_Spec_Project_Template\templates\tdd-template.md` to `uipath_claude/templates/tdd.md`.

- [ ] **Step 6: Run doc tools tests again**

Run: `pytest tests/test_doc_tools.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add uipath_claude/templates/
git commit -m "feat: add documentation templates (PDD, SDD, ADD, TDD)"
```

---

## Phase 3: Documentation Agents

### Task 5: Create Business Analyst Agent

**Files:**
- Create: `uipath_claude/query/ba_agent.py`
- Test: `tests/test_ba_agent.py`

- [ ] **Step 1: Write failing tests for BA agent**

```python
# tests/test_ba_agent.py
"""Tests for Business Analyst agent."""

import pytest
from unittest.mock import AsyncMock, patch

from uipath_claude.query.ba_agent import (
    run_ba_agent,
    BA_SYSTEM_PROMPT,
)


class TestBAAgent:
    """Tests for BA agent."""

    def test_system_prompt_contains_pdd_focus(self):
        """BA agent system prompt should focus on PDD creation."""
        assert "PDD" in BA_SYSTEM_PROMPT or "Process Definition" in BA_SYSTEM_PROMPT
        assert "business" in BA_SYSTEM_PROMPT.lower()

    def test_system_prompt_has_questioning_strategy(self):
        """BA agent should have strategy for gathering requirements."""
        assert "question" in BA_SYSTEM_PROMPT.lower() or "ask" in BA_SYSTEM_PROMPT.lower()

    @pytest.mark.asyncio
    async def test_ba_agent_returns_result(self):
        """BA agent should return AgenticResult."""
        with patch("uipath_claude.query.ba_agent.AgenticExecutor") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute.return_value = AsyncMock(
                final_response="Here is the PDD...",
                tool_calls=[],
                iterations=3,
            )
            mock_executor.return_value = mock_instance
            
            result = await run_ba_agent(
                user_request="Create a PDD for invoice processing",
                model_name="test-model",
                region="us-east-1",
            )
            
            assert result is not None
            mock_instance.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_ba_agent_uses_doc_tools(self):
        """BA agent should have access to documentation tools."""
        with patch("uipath_claude.query.ba_agent.AgenticExecutor") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute.return_value = AsyncMock(
                final_response="PDD created",
                tool_calls=[{"name": "write_documentation"}],
                iterations=2,
            )
            mock_executor.return_value = mock_instance
            
            await run_ba_agent(
                user_request="Create a PDD",
                model_name="test-model",
                region="us-east-1",
            )
            
            # Check that doc tools were passed
            call_kwargs = mock_instance.execute.call_args[1]
            tool_names = [t.name for t in call_kwargs.get("tools", [])]
            assert "write_documentation" in tool_names or "read_doc_template" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ba_agent.py -v`
Expected: FAIL with "cannot import name 'run_ba_agent'"

- [ ] **Step 3: Create BA agent module**

```python
# uipath_claude/query/ba_agent.py
"""Business Analyst agent for PDD creation."""

from __future__ import annotations

import os
from typing import Any

from uipath_claude.query.agentic_executor import AgenticExecutor, AgenticResult
from uipath_claude.tools.doc_tools import get_doc_tools
from uipath_claude.tools.skill_execution_tools import get_planning_tools


BA_SYSTEM_PROMPT = """You are a Business Analyst specialist for UiPath automation projects. Your role is to create comprehensive Process Definition Documents (PDD) through conversational requirement gathering.

=== YOUR MISSION ===
Create a complete PDD that captures all business requirements, process flows, exceptions, and success metrics. The PDD is the foundation document that Solution Architects and Developers will use to design and build the automation.

=== PDD CREATION PROCESS ===

1. **Initial Assessment**
   - Understand the business problem being solved
   - Identify the process name and owner
   - Determine process frequency and volume

2. **AS-IS Process Documentation**
   - Walk through current manual steps
   - Identify decision points and branches
   - Document applications used
   - Note current pain points

3. **TO-BE Process Design**
   - Define what will be automated vs manual
   - Specify automation touchpoints
   - Design exception handling
   - Plan human-in-the-loop scenarios

4. **Requirements Gathering**
   - Input/output data specifications
   - Business rules and validation
   - Security and compliance needs
   - Integration requirements

5. **Success Metrics**
   - Define measurable objectives
   - Establish baseline metrics
   - Set automation targets

=== QUESTIONING STRATEGY ===

Ask targeted questions to gather information. Start broad, then drill into specifics:

**Opening Questions:**
- "What business problem does this automation solve?"
- "Who are the key stakeholders?"
- "How often is this process executed?"

**Process Questions:**
- "Walk me through the process from start to finish"
- "What triggers this process to start?"
- "What decisions or branching occurs?"

**Technical Questions:**
- "What applications or systems are involved?"
- "How do users access these systems?"
- "Are there any API integrations available?"

**Exception Questions:**
- "What can go wrong during this process?"
- "How are errors currently handled?"
- "What should the robot do when it encounters an error?"

=== DOCUMENT OUTPUT ===

Use the `read_doc_template` tool to get the PDD template structure.
Use the `write_documentation` tool to save the completed PDD.

Generate a complete, professional PDD with:
- All sections filled with specific details (no placeholders)
- Flow diagrams described in text or Mermaid format
- Tables for structured data (applications, exceptions, metrics)
- Clear, actionable content

=== TOOLS AVAILABLE ===

You have access to:
- `read_doc_template` - Get the PDD template
- `write_documentation` - Save the completed PDD
- `read_documentation` - Read existing documentation
- `list_documentation` - Check what docs exist
- `read_file` - Read project files for context
- `list_directory` - Explore project structure

REMEMBER: Your goal is to produce a complete, professional PDD that enables the technical team to design and build the automation without needing to revisit business requirements."""


async def run_ba_agent(
    user_request: str,
    project_context: dict[str, Any] | None = None,
    *,
    model_name: str,
    region: str,
) -> AgenticResult:
    """
    Run the Business Analyst agent for PDD creation.
    
    Args:
        user_request: The user's request for documentation
        project_context: Optional project context
        model_name: Bedrock model ID
        region: AWS region
        
    Returns:
        AgenticResult containing the PDD or conversation
    """
    # Combine planning tools with doc tools
    tools = get_planning_tools() + get_doc_tools()
    
    executor = AgenticExecutor(model_name=model_name, region=region)
    
    ctx = dict(project_context) if project_context else {}
    if "selected_skill_names" not in ctx:
        ctx = {**ctx, "selected_skill_names": ["uipath-ba", "pdd-creation"]}
    
    # Get max iterations from env (default higher for doc creation)
    raw_cap = os.environ.get("UIPATH_BA_MAX_ITERATIONS", "15").strip()
    max_iter: int | None = None
    try:
        max_iter = int(raw_cap)
    except ValueError:
        max_iter = 15
    
    return await executor.execute(
        skill_content=BA_SYSTEM_PROMPT,
        user_request=user_request,
        tools=tools,
        project_context=ctx,
        skill_name="uipath-ba",
        max_iterations=max_iter,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_ba_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/query/ba_agent.py tests/test_ba_agent.py
git commit -m "feat: add Business Analyst agent for PDD creation"
```

---

### Task 6: Create Solution Architect Agent

**Files:**
- Create: `uipath_claude/query/solution_architect_agent.py`
- Test: `tests/test_solution_architect_agent.py`

- [ ] **Step 1: Write failing tests for SA agent**

```python
# tests/test_solution_architect_agent.py
"""Tests for Solution Architect agent."""

import pytest
from unittest.mock import AsyncMock, patch

from uipath_claude.query.solution_architect_agent import (
    run_solution_architect_agent,
    SA_SYSTEM_PROMPT,
    DocType,
)


class TestSolutionArchitectAgent:
    """Tests for Solution Architect agent."""

    def test_system_prompt_contains_sdd_focus(self):
        """SA agent system prompt should handle SDD/ADD/TDD."""
        assert "SDD" in SA_SYSTEM_PROMPT or "Solution Design" in SA_SYSTEM_PROMPT
        assert "architect" in SA_SYSTEM_PROMPT.lower()

    def test_system_prompt_references_pdd(self):
        """SA agent should reference PDD as input."""
        assert "PDD" in SA_SYSTEM_PROMPT

    @pytest.mark.asyncio
    async def test_sa_agent_sdd_mode(self):
        """SA agent should create SDD when requested."""
        with patch("uipath_claude.query.solution_architect_agent.AgenticExecutor") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute.return_value = AsyncMock(
                final_response="Here is the SDD...",
                tool_calls=[],
                iterations=3,
            )
            mock_executor.return_value = mock_instance
            
            result = await run_solution_architect_agent(
                user_request="Create an SDD based on the PDD",
                doc_type=DocType.SDD,
                model_name="test-model",
                region="us-east-1",
            )
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_sa_agent_add_mode(self):
        """SA agent should create ADD for agentic projects."""
        with patch("uipath_claude.query.solution_architect_agent.AgenticExecutor") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute.return_value = AsyncMock(
                final_response="Here is the ADD...",
                tool_calls=[],
                iterations=3,
            )
            mock_executor.return_value = mock_instance
            
            result = await run_solution_architect_agent(
                user_request="Create an Agent Design Document",
                doc_type=DocType.ADD,
                model_name="test-model",
                region="us-east-1",
            )
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_sa_agent_reads_pdd_first(self):
        """SA agent should attempt to read PDD for context."""
        with patch("uipath_claude.query.solution_architect_agent.AgenticExecutor") as mock_executor:
            mock_instance = AsyncMock()
            mock_instance.execute.return_value = AsyncMock(
                final_response="SDD created",
                tool_calls=[{"name": "read_documentation"}],
                iterations=2,
            )
            mock_executor.return_value = mock_instance
            
            await run_solution_architect_agent(
                user_request="Create SDD",
                doc_type=DocType.SDD,
                model_name="test-model",
                region="us-east-1",
            )
            
            # Check that doc tools were passed
            call_kwargs = mock_instance.execute.call_args[1]
            tool_names = [t.name for t in call_kwargs.get("tools", [])]
            assert "read_documentation" in tool_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_solution_architect_agent.py -v`
Expected: FAIL with "cannot import name 'run_solution_architect_agent'"

- [ ] **Step 3: Create Solution Architect agent module**

```python
# uipath_claude/query/solution_architect_agent.py
"""Solution Architect agent for SDD/ADD/TDD creation."""

from __future__ import annotations

import os
from enum import Enum
from typing import Any

from uipath_claude.query.agentic_executor import AgenticExecutor, AgenticResult
from uipath_claude.tools.doc_tools import get_doc_tools
from uipath_claude.tools.skill_execution_tools import get_planning_tools


class DocType(str, Enum):
    """Documentation type for SA agent."""
    
    SDD = "sdd"
    ADD = "add"
    TDD = "tdd"


SA_SYSTEM_PROMPT = """You are a Solution Architect specialist for UiPath automation projects. Your role is to create technical design documents (SDD, ADD, TDD) based on business requirements.

=== YOUR MISSION ===
Transform business requirements from the PDD into detailed technical specifications that developers can implement. Your documents bridge the gap between business needs and technical implementation.

=== DOCUMENT TYPES ===

**SDD (Solution Design Document)**
- Technical architecture overview
- Component design and interactions
- Integration specifications
- Security and error handling design
- Deployment and monitoring strategy

**ADD (Agent Design Document)** - For AI/agentic components
- Agent architecture (planner/executor/tools)
- Memory and context strategy
- Guardrails and safety controls
- HITL (Human-in-the-Loop) design
- Evaluation and testing plan

**TDD (Technical Design Document)**
- Detailed implementation specifications
- API contracts and data models
- Code-level design decisions
- Testing strategy
- Operational runbook

=== CREATION WORKFLOW ===

1. **Read Existing Documentation**
   - Use `read_documentation` to check for existing PDD
   - Use `list_documentation` to see what docs exist
   - The PDD is your primary input for technical design

2. **Analyze Requirements**
   - Extract technical requirements from PDD
   - Identify integration points
   - Note compliance and security needs
   - Understand exception handling requirements

3. **Design Architecture**
   - Choose appropriate patterns (ReFramework, Maestro, etc.)
   - Design component interactions
   - Specify data flows
   - Plan error handling strategy

4. **Document Technical Details**
   - Use `read_doc_template` to get the correct template
   - Fill all sections with specific technical decisions
   - Include diagrams (Mermaid format)
   - Specify APIs, schemas, and configurations

5. **Save Documentation**
   - Use `write_documentation` to save the completed doc

=== PLATFORM DETECTION ===

**UiPath Maestro (Cloud BPMN)**
- BPMN process orchestration
- Integration Service connectors
- Action Center for human tasks
- Cloud-native deployment

**UiPath Studio (Traditional)**
- ReFramework or custom framework
- Queue-based processing
- Orchestrator assets and credentials
- Machine-based robots

Detect the platform from the PDD and tailor your design accordingly.

=== QUALITY STANDARDS ===

Your documents must be:
- **Complete**: No placeholder text or TBD sections
- **Specific**: Exact configurations, not generic descriptions
- **Consistent**: Match PDD scope and terminology
- **Actionable**: Developers can implement from your specs

=== TOOLS AVAILABLE ===

You have access to:
- `read_doc_template` - Get SDD/ADD/TDD templates
- `write_documentation` - Save completed documents
- `read_documentation` - Read PDD and other docs
- `list_documentation` - Check existing docs
- `read_file` - Read project files
- `list_directory` - Explore project structure

CRITICAL: Always read the PDD first if it exists. Your technical design must align with the documented business requirements."""


_DOC_TYPE_PROMPTS = {
    DocType.SDD: """
Focus on creating a Solution Design Document (SDD) that covers:
- Executive summary and solution overview
- High-level architecture with component diagram
- Integration points with API/protocol details
- Security and credential management
- Error handling and recovery strategy
- Deployment and rollback procedures
- Performance and scalability design""",
    
    DocType.ADD: """
Focus on creating an Agent Design Document (ADD) for AI/agentic components:
- Agent mission and boundaries
- Architecture (planner, router, executor, memory)
- Tool definitions with permissions and rate limits
- Guardrails and safety controls
- Human-in-the-loop escalation design
- Evaluation metrics and test scenarios
- Deployment and monitoring strategy""",
    
    DocType.TDD: """
Focus on creating a Technical Design Document (TDD) with:
- Component specifications and responsibilities
- API contracts (endpoints, request/response schemas)
- Data models and storage patterns
- Code-level design patterns
- Testing strategy (unit, integration, e2e)
- Deployment configuration per environment
- Operational runbook and alerting""",
}


async def run_solution_architect_agent(
    user_request: str,
    doc_type: DocType,
    project_context: dict[str, Any] | None = None,
    *,
    model_name: str,
    region: str,
) -> AgenticResult:
    """
    Run the Solution Architect agent for technical documentation.
    
    Args:
        user_request: The user's request
        doc_type: Type of document to create (SDD, ADD, TDD)
        project_context: Optional project context
        model_name: Bedrock model ID
        region: AWS region
        
    Returns:
        AgenticResult containing the document or conversation
    """
    # Build system prompt with doc-type specific instructions
    system_prompt = SA_SYSTEM_PROMPT + "\n\n=== CURRENT TASK ===" + _DOC_TYPE_PROMPTS[doc_type]
    
    # Combine planning tools with doc tools
    tools = get_planning_tools() + get_doc_tools()
    
    executor = AgenticExecutor(model_name=model_name, region=region)
    
    ctx = dict(project_context) if project_context else {}
    skill_name = f"uipath-sa-{doc_type.value}"
    if "selected_skill_names" not in ctx:
        ctx = {**ctx, "selected_skill_names": [skill_name, f"{doc_type.value}-creation"]}
    
    # Get max iterations from env
    raw_cap = os.environ.get("UIPATH_SA_MAX_ITERATIONS", "15").strip()
    max_iter: int | None = None
    try:
        max_iter = int(raw_cap)
    except ValueError:
        max_iter = 15
    
    return await executor.execute(
        skill_content=system_prompt,
        user_request=user_request,
        tools=tools,
        project_context=ctx,
        skill_name=skill_name,
        max_iterations=max_iter,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_solution_architect_agent.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/query/solution_architect_agent.py tests/test_solution_architect_agent.py
git commit -m "feat: add Solution Architect agent for SDD/ADD/TDD creation"
```

---

## Phase 4: Documentation Router

### Task 7: Create Documentation Router

**Files:**
- Create: `uipath_claude/query/doc_router.py`
- Test: `tests/test_doc_router.py`

- [ ] **Step 1: Write failing tests for doc router**

```python
# tests/test_doc_router.py
"""Tests for documentation router."""

import pytest
from unittest.mock import AsyncMock, patch

from uipath_claude.query.doc_router import (
    route_to_doc_agent,
    DocRouteDecision,
)
from uipath_claude.query.doc_need_detector import DocNeedLevel


class TestDocRouter:
    """Tests for documentation router."""

    @pytest.mark.asyncio
    async def test_routes_to_ba_for_pdd(self):
        """Should route to BA agent for PDD creation."""
        decision = await route_to_doc_agent(
            user_input="Create a PDD for invoice processing",
            recommended_docs=["pdd"],
        )
        assert decision.agent == "ba"
        assert decision.doc_type == "pdd"

    @pytest.mark.asyncio
    async def test_routes_to_sa_for_sdd(self):
        """Should route to SA agent for SDD creation."""
        decision = await route_to_doc_agent(
            user_input="Create an SDD for the integration layer",
            recommended_docs=["sdd"],
        )
        assert decision.agent == "sa"
        assert decision.doc_type == "sdd"

    @pytest.mark.asyncio
    async def test_routes_to_sa_for_add(self):
        """Should route to SA agent for ADD creation."""
        decision = await route_to_doc_agent(
            user_input="Create an Agent Design Document",
            recommended_docs=["add"],
        )
        assert decision.agent == "sa"
        assert decision.doc_type == "add"

    @pytest.mark.asyncio
    async def test_pdd_first_when_multiple_docs(self):
        """Should prioritize PDD when multiple docs needed."""
        decision = await route_to_doc_agent(
            user_input="I need full documentation for this enterprise project",
            recommended_docs=["pdd", "sdd", "tdd"],
        )
        # PDD should be first (BA agent)
        assert decision.agent == "ba"
        assert decision.doc_type == "pdd"
        assert "sdd" in decision.next_docs
        assert "tdd" in decision.next_docs

    @pytest.mark.asyncio
    async def test_skips_pdd_if_exists(self):
        """Should skip PDD if it already exists."""
        with patch("uipath_claude.query.doc_router.list_docs") as mock_list:
            mock_list.return_value = {
                "pdd": {"exists": True, "path": "/docs/pdd.md"},
                "sdd": {"exists": False},
            }
            
            decision = await route_to_doc_agent(
                user_input="Create documentation",
                recommended_docs=["pdd", "sdd"],
            )
            # Should skip to SDD since PDD exists
            assert decision.agent == "sa"
            assert decision.doc_type == "sdd"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_doc_router.py -v`
Expected: FAIL with "cannot import name 'route_to_doc_agent'"

- [ ] **Step 3: Create doc_router module**

```python
# uipath_claude/query/doc_router.py
"""Route to appropriate documentation agent based on detected needs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from uipath_claude.tools.doc_tools import list_docs


@dataclass
class DocRouteDecision:
    """Decision about which documentation agent to invoke."""
    
    agent: Literal["ba", "sa", "none"]
    doc_type: str | None
    next_docs: list[str] = field(default_factory=list)
    reason: str = ""
    skip_reason: str | None = None


# Document creation order (business docs before technical)
_DOC_PRIORITY = ["pdd", "sdd", "add", "tdd"]

# Which agent handles which doc type
_DOC_TO_AGENT = {
    "pdd": "ba",  # Business Analyst for PDD
    "sdd": "sa",  # Solution Architect for SDD
    "add": "sa",  # Solution Architect for ADD
    "tdd": "sa",  # Solution Architect for TDD
}


async def route_to_doc_agent(
    user_input: str,
    recommended_docs: list[str],
    project_dir: str | None = None,
) -> DocRouteDecision:
    """
    Route to the appropriate documentation agent.
    
    Args:
        user_input: The user's request
        recommended_docs: List of recommended doc types from detector
        project_dir: Optional project directory
        
    Returns:
        DocRouteDecision with agent type and doc to create
    """
    if not recommended_docs:
        return DocRouteDecision(
            agent="none",
            doc_type=None,
            reason="No documentation needed",
        )
    
    # Check which docs already exist
    existing = list_docs(project_dir)
    existing_types = {k for k, v in existing.items() if v.get("exists")}
    
    # Sort recommended docs by priority order
    sorted_docs = sorted(
        recommended_docs,
        key=lambda d: _DOC_PRIORITY.index(d) if d in _DOC_PRIORITY else 99,
    )
    
    # Find the first doc that doesn't exist
    doc_to_create = None
    skipped = []
    
    for doc in sorted_docs:
        if doc in existing_types:
            skipped.append(doc)
        else:
            doc_to_create = doc
            break
    
    if doc_to_create is None:
        # All recommended docs already exist
        return DocRouteDecision(
            agent="none",
            doc_type=None,
            reason="All recommended documentation already exists",
            skip_reason=f"Skipped existing: {', '.join(skipped)}",
        )
    
    # Determine remaining docs to create after this one
    remaining = [d for d in sorted_docs if d != doc_to_create and d not in existing_types]
    
    agent = _DOC_TO_AGENT.get(doc_to_create, "sa")
    
    skip_msg = None
    if skipped:
        skip_msg = f"Skipped existing: {', '.join(skipped)}"
    
    return DocRouteDecision(
        agent=agent,
        doc_type=doc_to_create,
        next_docs=remaining,
        reason=f"Creating {doc_to_create.upper()} using {agent.upper()} agent",
        skip_reason=skip_msg,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_doc_router.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add uipath_claude/query/doc_router.py tests/test_doc_router.py
git commit -m "feat: add documentation router for agent selection"
```

---

## Phase 5: Graph Integration

### Task 8: Add Documentation State Fields

**Files:**
- Modify: `uipath_claude/graph/state.py`

- [ ] **Step 1: Read current state.py**

```bash
cat uipath_claude/graph/state.py
```

- [ ] **Step 2: Add documentation state fields**

Add to the state TypedDict:

```python
# Add to state.py imports
from uipath_claude.query.doc_need_detector import DocNeedLevel, DocNeedResult

# Add to GraphState TypedDict
class GraphState(TypedDict, total=False):
    # ... existing fields ...
    
    # Documentation state
    doc_need_result: DocNeedResult | None
    doc_phase: Literal["detect", "route", "create", "complete"] | None
    current_doc_type: str | None
    pending_docs: list[str]
    created_docs: list[str]
```

- [ ] **Step 3: Commit**

```bash
git add uipath_claude/graph/state.py
git commit -m "feat: add documentation state fields to graph state"
```

---

### Task 9: Add Documentation Node to Graph

**Files:**
- Create: `uipath_claude/graph/nodes/documentation.py`
- Modify: `uipath_claude/graph/builder.py`

- [ ] **Step 1: Create documentation node**

```python
# uipath_claude/graph/nodes/documentation.py
"""Documentation creation node for the agent graph."""

from __future__ import annotations

from typing import Any

from uipath_claude.query.doc_need_detector import detect_documentation_need, DocNeedLevel
from uipath_claude.query.doc_router import route_to_doc_agent
from uipath_claude.query.ba_agent import run_ba_agent
from uipath_claude.query.solution_architect_agent import run_solution_architect_agent, DocType


async def documentation_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    Node that handles documentation creation flow.
    
    This node:
    1. Detects documentation need (if not already detected)
    2. Routes to appropriate agent (BA or SA)
    3. Runs the documentation agent
    4. Updates state with created docs
    """
    messages = list(state.get("messages") or [])
    if not messages:
        return state
    
    last = messages[-1]
    if last.get("role") != "user":
        return state
    
    user_input = str(last.get("content", ""))
    
    # Get config from state
    config = state.get("config", {})
    model_name = config.get("model_name", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    region = config.get("region", "us-east-1")
    
    # Check if we already detected documentation need
    doc_need = state.get("doc_need_result")
    if doc_need is None:
        doc_need = detect_documentation_need(user_input)
        
    # If no documentation needed, pass through
    if doc_need.level == DocNeedLevel.NONE:
        return {
            **state,
            "doc_need_result": doc_need,
            "doc_phase": "complete",
        }
    
    # Route to appropriate agent
    route_decision = await route_to_doc_agent(
        user_input=user_input,
        recommended_docs=doc_need.recommended_docs,
    )
    
    if route_decision.agent == "none":
        return {
            **state,
            "doc_need_result": doc_need,
            "doc_phase": "complete",
        }
    
    # Run the appropriate agent
    project_context = state.get("project_context", {})
    
    if route_decision.agent == "ba":
        result = await run_ba_agent(
            user_request=user_input,
            project_context=project_context,
            model_name=model_name,
            region=region,
        )
    else:  # sa
        doc_type = DocType(route_decision.doc_type)
        result = await run_solution_architect_agent(
            user_request=user_input,
            doc_type=doc_type,
            project_context=project_context,
            model_name=model_name,
            region=region,
        )
    
    # Update state
    created_docs = list(state.get("created_docs", []))
    if route_decision.doc_type:
        created_docs.append(route_decision.doc_type)
    
    # Add assistant response to messages
    new_messages = messages + [{
        "role": "assistant",
        "content": result.final_response,
    }]
    
    return {
        **state,
        "messages": new_messages,
        "doc_need_result": doc_need,
        "doc_phase": "create" if route_decision.next_docs else "complete",
        "current_doc_type": route_decision.doc_type,
        "pending_docs": route_decision.next_docs,
        "created_docs": created_docs,
    }
```

- [ ] **Step 2: Update graph builder to include documentation node**

Add documentation node as a conditional branch after route node:

```python
# In uipath_claude/graph/builder.py
# Add import
from uipath_claude.graph.nodes.documentation import documentation_node
from uipath_claude.query.intent_classifier import IntentType

# Add conditional edge from route to documentation when intent is DOCUMENTATION
def should_route_to_docs(state: dict) -> str:
    """Determine if we should route to documentation node."""
    intent = state.get("intent")
    if intent == IntentType.DOCUMENTATION:
        return "documentation"
    return "execute"

# In build_graph function, add:
graph.add_node("documentation", documentation_node)
graph.add_conditional_edges(
    "route",
    should_route_to_docs,
    {
        "documentation": "documentation",
        "execute": "execute",
    }
)
```

- [ ] **Step 3: Commit**

```bash
git add uipath_claude/graph/nodes/documentation.py uipath_claude/graph/builder.py
git commit -m "feat: integrate documentation node into agent graph"
```

---

### Task 10: Add CLI Markers for Documentation Phase

**Files:**
- Modify: `uipath_claude/cli/app.py`
- Modify: `uipath_claude/rendering/progress.py`

- [ ] **Step 1: Add documentation phase markers to progress.py**

```python
# In uipath_claude/rendering/progress.py
# Add method to ProgressRenderer class

def doc_phase_start(self, doc_type: str, agent: str) -> None:
    """Render documentation phase start."""
    agent_label = "Business Analyst" if agent == "ba" else "Solution Architect"
    self.console.print(f"[bold cyan][DOC_PHASE: {doc_type.upper()}][/bold cyan]")
    self.console.print(f"[dim]Agent: {agent_label}[/dim]")
    sys.stdout.flush()

def doc_created(self, doc_type: str, path: str) -> None:
    """Render documentation created message."""
    self.console.print(f"[bold green][DOC_CREATED: {doc_type.upper()}][/bold green] {path}")
    sys.stdout.flush()
```

- [ ] **Step 2: Update app.py to emit markers**

Integrate with documentation flow to emit markers when entering doc creation.

- [ ] **Step 3: Commit**

```bash
git add uipath_claude/cli/app.py uipath_claude/rendering/progress.py
git commit -m "feat: add CLI markers for documentation phase"
```

---

## Phase 6: Testing and Documentation

### Task 11: Add Integration Tests

**Files:**
- Create: `tests/integration/test_doc_flow.py`

- [ ] **Step 1: Write integration tests**

```python
# tests/integration/test_doc_flow.py
"""Integration tests for documentation-driven development flow."""

import pytest
from unittest.mock import patch, AsyncMock

from uipath_claude.query.intent_classifier import classify_intent, IntentType
from uipath_claude.query.doc_need_detector import detect_documentation_need, DocNeedLevel
from uipath_claude.query.doc_router import route_to_doc_agent


class TestDocumentationFlow:
    """Integration tests for the full documentation flow."""

    def test_pdd_request_routes_correctly(self):
        """PDD request should classify and route to BA agent."""
        # 1. Intent classification
        intent, reason = classify_intent("Create a PDD for invoice processing")
        assert intent == IntentType.DOCUMENTATION
        
        # 2. Need detection
        need = detect_documentation_need("Create a PDD for invoice processing")
        assert need.explicit_request is True
        assert "pdd" in need.recommended_docs
        
    @pytest.mark.asyncio
    async def test_pdd_request_routes_to_ba(self):
        """PDD request should route to BA agent."""
        decision = await route_to_doc_agent(
            user_input="Create a PDD for invoice processing",
            recommended_docs=["pdd"],
        )
        assert decision.agent == "ba"
        assert decision.doc_type == "pdd"

    def test_complex_project_detects_multiple_docs(self):
        """Complex project should recommend multiple doc types."""
        need = detect_documentation_need(
            "Build enterprise invoice processing with SAP integration, "
            "manager approvals, compliance audit trail, and AI document classification"
        )
        assert need.level in (DocNeedLevel.REQUIRED, DocNeedLevel.RECOMMENDED)
        assert len(need.recommended_docs) >= 2

    @pytest.mark.asyncio
    async def test_doc_flow_creates_pdd_before_sdd(self):
        """Flow should create PDD before SDD."""
        # First request
        decision1 = await route_to_doc_agent(
            user_input="Create full documentation",
            recommended_docs=["pdd", "sdd", "tdd"],
        )
        assert decision1.doc_type == "pdd"
        assert "sdd" in decision1.next_docs
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/integration/test_doc_flow.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_doc_flow.py
git commit -m "test: add integration tests for documentation flow"
```

---

### Task 12: Update HOW_TO_RUN_TESTS.md

**Files:**
- Modify: `docs/evaluations/HOW_TO_RUN_TESTS.md`

- [ ] **Step 1: Add documentation flow section**

Add a section documenting the new documentation-driven development feature:

```markdown
## Documentation-Driven Development

The agent now supports automatic documentation detection and creation for complex projects.

### Documentation Types

| Type | Agent | Purpose |
|------|-------|---------|
| PDD | Business Analyst | Process Definition Document - business requirements |
| SDD | Solution Architect | Solution Design Document - technical architecture |
| ADD | Solution Architect | Agent Design Document - AI/agentic components |
| TDD | Solution Architect | Technical Design Document - implementation specs |

### CLI Markers

- `[DOC_PHASE: TYPE]` - Entering documentation creation phase
- `[DOC_CREATED: TYPE]` - Documentation file created

### Environment Variables

- `UIPATH_BA_MAX_ITERATIONS` - Max iterations for BA agent (default: 15)
- `UIPATH_SA_MAX_ITERATIONS` - Max iterations for SA agent (default: 15)
```

- [ ] **Step 2: Commit**

```bash
git add docs/evaluations/HOW_TO_RUN_TESTS.md
git commit -m "docs: add documentation-driven development to HOW_TO_RUN_TESTS"
```

---

## Self-Review Checklist

### Spec Coverage

- [x] Documentation need detection based on complexity
- [x] BA agent for PDD creation
- [x] SA agent for SDD/ADD/TDD creation
- [x] Router to select appropriate agent
- [x] Documentation tools for reading/writing
- [x] Graph integration for documentation flow
- [x] CLI markers for documentation phases
- [x] Templates ported from UiPath_Spec_Project_Template

### Placeholder Scan

- No TBD, TODO, or "implement later" markers
- All code blocks contain complete implementations
- All file paths are exact

### Type Consistency

- `DocNeedLevel` enum used consistently
- `DocType` enum for SA agent
- `DocRouteDecision` dataclass for routing
- `AgenticResult` return type for agents

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-16-documentation-driven-development.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
