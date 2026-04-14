# UiPath Claude Code: Skill-First Architecture Plan

> **Date:** 2026-04-14  
> **Status:** Ready for Implementation  
> **Goal:** Align agent with Claude Code patterns, properly use UiPath skills repo, consolidate project structure

---

## Executive Summary

The UiPath builder agent has the right skills (via git submodule from https://github.com/UiPath/skills) but doesn't use them correctly. Key gaps:

1. **Planner skill is bypassed** - `uipath-planner` exists but routing uses keyword scoring instead
2. **Skills injected as text** - Should be invoked as structured tools with forked context  
3. **No feedback loop** - Skills say "ask before building" but agent generates immediately
4. **Validation incomplete** - Missing `uip rpa get-errors --use-studio` integration
5. **Project structure bloated** - Legacy directories, worktrees, duplicate code

**Eval Results (from 904ba034):**
- WG-001: FAIL (score 4/10) - Wrong skill, no artifacts
- WG-002: PASS (score 10/10) - Correct skill, 44 files generated
- WG-003: FAIL (score 4/10) - Correct skill, no artifacts  
- WG-004: FAIL (score 5/10) - Correct skill, no artifacts
- WG-005: FAIL (score 2/10) - Timeout, no artifacts

**Root Cause:** `artifact_generation_gap` - skills selected but `generate_workflow` fails silently

---

## Part 1: Project Structure Consolidation

### Current Structure (Bloated)

```
uipath-builder-agent/
├── .worktrees/           # REMOVE - empty, not needed
├── agent/                # REMOVE - legacy, replaced by uipath_claude/
│   ├── nodes/
│   ├── prompts/
│   └── tools/
├── archive/              # REMOVE - old reports, not needed
│   ├── docs/
│   └── reports/
├── cli/                  # REMOVE - empty, legacy
├── generated/            # KEEP - runtime output, add to .gitignore
├── scripts/              # CONSOLIDATE - keep useful scripts only
├── skills/               # KEEP - git submodule (UiPath/skills)
├── templates/            # KEEP - git submodules (Cato templates)
├── tests/                # KEEP - consolidate with uipath_claude tests
├── uipath_claude/        # KEEP - main package
└── docs/                 # KEEP - consolidate plans here
```

### Target Structure (Clean)

```
uipath-builder-agent/
├── .github/              # CI/CD workflows
│   └── workflows/
│       └── update-skills-submodule.yml
├── docs/                 # Documentation
│   ├── plans/            # Implementation plans
│   ├── architecture/     # Architecture docs
│   └── guides/           # User guides
├── scripts/              # Utility scripts
│   ├── eval_suite/       # Evaluation harness
│   └── maintenance/      # Maintenance scripts
├── skills/               # Git submodule → UiPath/skills
├── templates/            # Git submodules → Cato templates
├── tests/                # All tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── uipath_claude/        # Main package
│   ├── cli/              # CLI entry points
│   ├── commands/         # Slash commands
│   ├── graph/            # LangGraph state machine (NEW)
│   ├── nodes/            # Graph nodes (NEW)
│   ├── skills/           # Skill loading and invocation
│   ├── tools/            # Tool implementations
│   ├── validation/       # Validation pipeline
│   ├── activities/       # Activity discovery (NEW)
│   └── artifacts/        # File generation
├── pyproject.toml
├── README.md
└── .gitignore
```

### Cleanup Tasks

- [ ] **Task C1:** Delete `.worktrees/` directory
- [ ] **Task C2:** Delete `agent/` directory (legacy code)
- [ ] **Task C3:** Delete `archive/` directory (old reports)
- [ ] **Task C4:** Delete `cli/` directory (empty)
- [ ] **Task C5:** Add `generated/` to `.gitignore`
- [ ] **Task C6:** Consolidate `scripts/` - keep only `eval_suite/` and essential maintenance scripts
- [ ] **Task C7:** Move any useful code from `agent/` to `uipath_claude/` before deletion

---

## Part 2: Skill-First Architecture

### 2.1 Planner Integration

The `uipath-planner` skill should be the entry point for:
- Ambiguous requests
- Multi-skill requests (build + deploy)
- Exploration questions ("what can I build?")

**Current Flow (Wrong):**
```
User Input → Keyword Scoring → Select 2 Skills → Inject as Text → LLM → Output
```

**Target Flow (Correct):**
```
User Input → Route Decision
  ├── Clear single skill → Invoke skill directly
  ├── Ambiguous/Multi-skill → Invoke uipath-planner → Get plan → Execute steps
  └── Slash command → Execute command
```

#### Implementation

**File:** `uipath_claude/query/planner_router.py` (NEW)

```python
"""Planner routing logic."""
from typing import Literal

# Thresholds
PLANNER_CONFIDENCE_THRESHOLD = 70  # Below this, use planner
MULTI_SKILL_KEYWORDS = {"deploy", "publish", "then", "and then", "after that"}
EXPLORATION_KEYWORDS = {"what can", "help me", "recommend", "should i", "how do i"}

def should_use_planner(
    user_input: str,
    top_skill_score: int,
    top_skill_name: str,
) -> tuple[bool, str]:
    """
    Determine if request should go through uipath-planner.
    
    Returns:
        (should_use_planner, reason)
    """
    lower_input = user_input.lower()
    
    # Low confidence - planner should help
    if top_skill_score < PLANNER_CONFIDENCE_THRESHOLD:
        return True, f"Low confidence ({top_skill_score}%) - planner will clarify"
    
    # Multi-skill keywords
    for keyword in MULTI_SKILL_KEYWORDS:
        if keyword in lower_input:
            return True, f"Multi-skill keyword '{keyword}' detected"
    
    # Exploration questions
    for keyword in EXPLORATION_KEYWORDS:
        if keyword in lower_input:
            return True, f"Exploration question detected"
    
    return False, "Direct skill invocation"


def get_planner_skill_name() -> str:
    """Return the planner skill name from UiPath skills repo."""
    return "uipath-planner"
```

**Tasks:**
- [ ] **Task P1:** Create `uipath_claude/query/planner_router.py`
- [ ] **Task P2:** Modify `uipath_claude/cli/app.py` to check planner routing before skill selection
- [ ] **Task P3:** Implement planner skill invocation as first step when needed

---

### 2.2 Skill Tool Implementation

Skills should be invoked as tools with isolated context, not injected as prompt text.

**Current (Wrong):**
```python
# Skills injected into system prompt
runtime_context = f"[Skill: {name}]\n{content[:20000]}"
response = await engine.run(messages=messages, system_prompt=context_prompt)
```

**Target (Correct):**
```python
# Skills invoked as tools with forked context
result = await skill_tool.invoke(
    skill_name="uipath-rpa",
    args=user_request,
    context=forked_context,
)
```

#### Implementation

**File:** `uipath_claude/tools/skill_tool.py` (ENHANCE)

```python
"""Skill tool for structured skill invocation."""
from dataclasses import dataclass
from typing import Any
from pathlib import Path

from uipath_claude.skills.loader import load_skill_content
from uipath_claude.skills.registry import SkillRegistry


@dataclass
class SkillResult:
    """Result from skill invocation."""
    success: bool
    output: str
    artifacts: list[Path]
    errors: list[str]
    follow_up_required: bool
    follow_up_question: str | None


class SkillTool:
    """Execute skills as structured tool calls with forked context."""
    
    def __init__(self, registry: SkillRegistry, engine):
        self.registry = registry
        self.engine = engine
    
    async def invoke(
        self,
        skill_name: str,
        user_request: str,
        context: dict[str, Any],
    ) -> SkillResult:
        """
        Invoke a skill with isolated context.
        
        This follows Claude Code's SkillTool pattern:
        1. Load skill content
        2. Create forked context (isolated from main conversation)
        3. Execute with skill-specific system prompt
        4. Return structured result
        """
        # Get skill
        skill = self._get_skill(skill_name)
        if not skill:
            return SkillResult(
                success=False,
                output="",
                artifacts=[],
                errors=[f"Skill not found: {skill_name}"],
                follow_up_required=False,
                follow_up_question=None,
            )
        
        # Load skill content
        content = load_skill_content(skill["path"])
        
        # Build skill-specific system prompt
        system_prompt = self._build_skill_prompt(skill, content, context)
        
        # Execute in forked context
        response = await self._execute_forked(
            system_prompt=system_prompt,
            user_request=user_request,
            skill=skill,
        )
        
        # Parse response for artifacts, questions, errors
        return self._parse_response(response, skill)
    
    def _get_skill(self, name: str) -> dict | None:
        """Get skill by name."""
        for skill in self.registry.skills:
            if skill["name"] == name:
                return skill
        return None
    
    def _build_skill_prompt(
        self,
        skill: dict,
        content: str,
        context: dict,
    ) -> str:
        """Build system prompt for skill execution."""
        # Extract CRITICAL sections first (per existing logic)
        critical = self._extract_critical_sections(content)
        
        parts = [
            f"You are executing the '{skill['name']}' skill.",
            "Follow the skill instructions EXACTLY.",
            "",
            "## CRITICAL RULES",
            critical if critical else "(none)",
            "",
            "## SKILL INSTRUCTIONS",
            content,
            "",
            "## CONTEXT",
            f"Project path: {context.get('project_path', 'unknown')}",
            f"Session ID: {context.get('session_id', 'unknown')}",
        ]
        return "\n".join(parts)
    
    async def _execute_forked(
        self,
        system_prompt: str,
        user_request: str,
        skill: dict,
    ) -> str:
        """Execute skill in forked context."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request},
        ]
        
        # Use engine with empty tools (skill provides instructions)
        return await self.engine.run(
            messages=messages,
            tools=[],
            system_prompt=system_prompt,
        )
    
    def _parse_response(self, response: str, skill: dict) -> SkillResult:
        """Parse skill response for artifacts and follow-ups."""
        # Check if response contains a question (feedback loop)
        follow_up = self._detect_question(response)
        
        # Check for file blocks
        from uipath_claude.artifacts.materialize import contains_file_blocks
        has_files = contains_file_blocks(response)
        
        return SkillResult(
            success=True,
            output=response,
            artifacts=[],  # Populated after materialization
            errors=[],
            follow_up_required=follow_up is not None,
            follow_up_question=follow_up,
        )
    
    def _detect_question(self, response: str) -> str | None:
        """Detect if response is asking a clarifying question."""
        question_markers = [
            "?",
            "would you like",
            "do you want",
            "please specify",
            "which option",
            "could you clarify",
        ]
        
        # Simple heuristic: if response ends with question or contains markers
        lower = response.lower()
        for marker in question_markers:
            if marker in lower and len(response) < 2000:  # Short responses with questions
                # Extract the question
                lines = response.strip().split("\n")
                for line in reversed(lines):
                    if "?" in line:
                        return line.strip()
        return None
    
    def _extract_critical_sections(self, content: str) -> str:
        """Extract CRITICAL sections from skill content."""
        # Reuse existing logic from app.py
        from uipath_claude.cli.app import _extract_critical_sections
        return _extract_critical_sections(content)
```

**Tasks:**
- [ ] **Task S1:** Enhance `uipath_claude/tools/skill_tool.py` with forked execution
- [ ] **Task S2:** Add `SkillResult` dataclass for structured responses
- [ ] **Task S3:** Implement question detection for feedback loop
- [ ] **Task S4:** Integrate skill tool into main chat loop

---

### 2.3 Feedback Loop

Skills instruct the agent to ask clarifying questions. The agent must detect and honor this.

**Per uipath-rpa skill:**
> "If the user's request is ambiguous, vague, or missing critical details needed to build a correct workflow, ASK for clarification BEFORE generating any files."

**Per uipath-planner skill:**
> "Ask the user to clarify... After 2 questions, plan with the best available information."

#### Implementation

**File:** `uipath_claude/query/feedback_loop.py` (NEW)

```python
"""Feedback loop management for human-in-the-loop."""
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class FeedbackState:
    """Track feedback loop state."""
    questions_asked: int = 0
    max_questions: int = 2
    awaiting_response: bool = False
    pending_question: str | None = None
    responses: list[tuple[str, str]] = field(default_factory=list)


class FeedbackLoop:
    """Manage clarification questions and user responses."""
    
    def __init__(self, max_questions: int = 2):
        self.state = FeedbackState(max_questions=max_questions)
    
    def should_ask_more(self) -> bool:
        """Check if we can ask more clarifying questions."""
        return self.state.questions_asked < self.state.max_questions
    
    def record_question(self, question: str) -> None:
        """Record that a question was asked."""
        self.state.questions_asked += 1
        self.state.awaiting_response = True
        self.state.pending_question = question
    
    def record_response(self, response: str) -> None:
        """Record user's response to question."""
        if self.state.pending_question:
            self.state.responses.append((self.state.pending_question, response))
        self.state.awaiting_response = False
        self.state.pending_question = None
    
    def get_context_summary(self) -> str:
        """Get summary of Q&A for context."""
        if not self.state.responses:
            return ""
        
        lines = ["Previous clarifications:"]
        for q, a in self.state.responses:
            lines.append(f"Q: {q}")
            lines.append(f"A: {a}")
        return "\n".join(lines)
    
    def reset(self) -> None:
        """Reset for new request."""
        self.state = FeedbackState(max_questions=self.state.max_questions)
```

**Modify chat loop in `uipath_claude/cli/app.py`:**

```python
# In the main chat loop
async def _handle_chat_message(self, user_input: str):
    # Check if this is a response to a pending question
    if self.feedback_loop.state.awaiting_response:
        self.feedback_loop.record_response(user_input)
        # Continue with original request + clarification
        user_input = self._build_clarified_request()
    
    # Invoke skill
    result = await self.skill_tool.invoke(
        skill_name=selected_skill,
        user_request=user_input,
        context=self.context,
    )
    
    # Check if skill is asking a question
    if result.follow_up_required and self.feedback_loop.should_ask_more():
        self.feedback_loop.record_question(result.follow_up_question)
        # Display question to user and return (wait for response)
        self.console.print(result.follow_up_question)
        return
    
    # Otherwise, process result
    await self._process_skill_result(result)
```

**Tasks:**
- [ ] **Task F1:** Create `uipath_claude/query/feedback_loop.py`
- [ ] **Task F2:** Integrate feedback loop into chat handler
- [ ] **Task F3:** Modify skill tool to detect questions
- [ ] **Task F4:** Add `/answer` command for explicit responses

---

### 2.4 Validation Pipeline

Per `uipath-rpa` skill:
> "ALWAYS validate after every file create or edit. Run `uip rpa get-errors --file-path " " --project-dir " " --output json --use-studio` until 0 errors. Cap at 5 fix attempts."

#### Implementation

**File:** `uipath_claude/validation/pipeline.py` (NEW)

```python
"""Validation pipeline per uipath-rpa skill instructions."""
import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationError:
    """Single validation error."""
    file: str
    line: int | None
    column: int | None
    code: str
    message: str
    severity: str  # error, warning, info
    category: str  # package, structure, type, activity, logic


@dataclass
class ValidationResult:
    """Result of validation run."""
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    studio_ran: bool = False


class ValidationPipeline:
    """
    Full validation pipeline following uipath-rpa skill instructions.
    
    Priority order for fixes:
    1. Package errors (missing dependencies)
    2. Structure errors (XML malformed)
    3. Type errors (wrong data types)
    4. Activity errors (wrong properties)
    5. Logic errors (semantic issues)
    """
    
    MAX_FIX_ATTEMPTS = 5
    
    async def validate(
        self,
        project_path: Path,
        file_path: Path | None = None,
    ) -> ValidationResult:
        """
        Run full validation pipeline.
        
        Args:
            project_path: Path to UiPath project
            file_path: Optional specific file to validate
        """
        # 1. Structural checks (fast, local)
        structural = await self._run_structural_checks(project_path, file_path)
        
        # 2. Studio validation (if project.json exists)
        project_json = project_path / "project.json"
        if project_json.exists():
            studio = await self._run_studio_validation(project_path, file_path)
        else:
            studio = ValidationResult(
                valid=True,
                warnings=[ValidationError(
                    file="",
                    line=None,
                    column=None,
                    code="NO_PROJECT_JSON",
                    message="No project.json - Studio validation skipped",
                    severity="warning",
                    category="structure",
                )],
            )
        
        # Combine results
        return self._combine_results(structural, studio)
    
    async def _run_structural_checks(
        self,
        project_path: Path,
        file_path: Path | None,
    ) -> ValidationResult:
        """Run fast local structural checks."""
        errors = []
        
        # Check XAML files
        xaml_files = [file_path] if file_path else list(project_path.rglob("*.xaml"))
        
        for xaml in xaml_files:
            if not xaml.exists():
                continue
            
            content = xaml.read_text(encoding="utf-8")
            
            # Known bad patterns from eval results
            if "GetOutlookMailMessages.Result" in content:
                errors.append(ValidationError(
                    file=str(xaml.relative_to(project_path)),
                    line=None,
                    column=None,
                    code="OUTLOOK_RESULT",
                    message="Use Messages attribute instead of Result for GetOutlookMailMessages",
                    severity="error",
                    category="activity",
                ))
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
        )
    
    async def _run_studio_validation(
        self,
        project_path: Path,
        file_path: Path | None,
    ) -> ValidationResult:
        """Run uip rpa get-errors --use-studio."""
        cmd = [
            "uip", "rpa", "get-errors",
            "--project-dir", str(project_path),
            "--output", "json",
            "--use-studio",
        ]
        
        if file_path:
            cmd.extend(["--file-path", str(file_path)])
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            return ValidationResult(
                valid=False,
                errors=[ValidationError(
                    file="",
                    line=None,
                    column=None,
                    code="TIMEOUT",
                    message="Studio validation timed out after 60s",
                    severity="error",
                    category="structure",
                )],
            )
        except FileNotFoundError:
            return ValidationResult(
                valid=False,
                errors=[ValidationError(
                    file="",
                    line=None,
                    column=None,
                    code="UIP_NOT_FOUND",
                    message="uip CLI not found - install UiPath CLI",
                    severity="error",
                    category="structure",
                )],
            )
        
        if proc.returncode != 0:
            # Parse error output
            try:
                data = json.loads(stdout.decode("utf-8"))
                errors = [
                    ValidationError(
                        file=e.get("file", ""),
                        line=e.get("line"),
                        column=e.get("column"),
                        code=e.get("code", "UNKNOWN"),
                        message=e.get("message", ""),
                        severity=e.get("severity", "error"),
                        category=self._categorize_error(e),
                    )
                    for e in data.get("errors", [])
                ]
            except json.JSONDecodeError:
                errors = [ValidationError(
                    file="",
                    line=None,
                    column=None,
                    code="PARSE_ERROR",
                    message=stdout.decode("utf-8", errors="replace"),
                    severity="error",
                    category="structure",
                )]
            
            return ValidationResult(valid=False, errors=errors, studio_ran=True)
        
        return ValidationResult(valid=True, studio_ran=True)
    
    def _categorize_error(self, error: dict) -> str:
        """Categorize error for fix prioritization."""
        code = error.get("code", "").upper()
        message = error.get("message", "").lower()
        
        if "package" in message or "dependency" in message or "nuget" in message:
            return "package"
        if "xml" in message or "parse" in message or "malformed" in message:
            return "structure"
        if "type" in message or "cannot convert" in message:
            return "type"
        if "activity" in message or "property" in message:
            return "activity"
        return "logic"
    
    def _combine_results(
        self,
        structural: ValidationResult,
        studio: ValidationResult,
    ) -> ValidationResult:
        """Combine validation results."""
        all_errors = structural.errors + studio.errors
        all_warnings = structural.warnings + studio.warnings
        
        return ValidationResult(
            valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings,
            studio_ran=studio.studio_ran,
        )
```

**Tasks:**
- [ ] **Task V1:** Create `uipath_claude/validation/pipeline.py`
- [ ] **Task V2:** Integrate validation into artifact materialization
- [ ] **Task V3:** Implement auto-fix loop (max 5 attempts)
- [ ] **Task V4:** Add validation error categories for prioritized fixing

---

### 2.5 Activity Discovery

Per `uipath-rpa` skill:
> "Check `{projectRoot}/.local/docs/packages/{PackageId}/` first. Always."

#### Implementation

**File:** `uipath_claude/activities/discovery.py` (NEW)

```python
"""Activity discovery following uipath-rpa skill instructions."""
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ActivityInfo:
    """Information about a UiPath activity."""
    name: str
    full_name: str
    package_id: str
    description: str
    properties: dict
    example_xaml: str | None
    source: str  # local_docs, bundled, live


class ActivityDiscovery:
    """
    Discover activity documentation with priority order.
    
    Priority:
    1. .local/docs/packages/{PackageId}/ (auto-generated, most accurate)
    2. skills/skills/uipath-rpa/references/activity-docs/ (bundled fallback)
    3. uip rpa find-activities (live discovery)
    """
    
    def __init__(self, skills_root: Path):
        self.skills_root = skills_root
        self._cache: dict[str, ActivityInfo] = {}
    
    async def find_activity(
        self,
        query: str,
        project_path: Path,
    ) -> ActivityInfo | None:
        """
        Find activity documentation.
        
        Args:
            query: Activity name or search term
            project_path: Path to UiPath project
        """
        # Check cache first
        cache_key = f"{project_path}:{query}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Priority 1: .local/docs/packages/
        result = await self._search_local_docs(query, project_path)
        if result:
            self._cache[cache_key] = result
            return result
        
        # Priority 2: Bundled references
        result = await self._search_bundled_docs(query)
        if result:
            self._cache[cache_key] = result
            return result
        
        # Priority 3: Live discovery
        result = await self._search_live(query, project_path)
        if result:
            self._cache[cache_key] = result
            return result
        
        return None
    
    async def _search_local_docs(
        self,
        query: str,
        project_path: Path,
    ) -> ActivityInfo | None:
        """Search .local/docs/packages/ directory."""
        local_docs = project_path / ".local" / "docs" / "packages"
        if not local_docs.exists():
            return None
        
        query_lower = query.lower()
        
        for package_dir in local_docs.iterdir():
            if not package_dir.is_dir():
                continue
            
            # Search markdown files in package
            for md_file in package_dir.rglob("*.md"):
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                if query_lower in content.lower():
                    return ActivityInfo(
                        name=query,
                        full_name=self._extract_full_name(content, query),
                        package_id=package_dir.name,
                        description=self._extract_description(content),
                        properties=self._extract_properties(content),
                        example_xaml=self._extract_example(content),
                        source="local_docs",
                    )
        
        return None
    
    async def _search_bundled_docs(self, query: str) -> ActivityInfo | None:
        """Search bundled activity docs."""
        bundled = self.skills_root / "skills" / "uipath-rpa" / "references" / "activity-docs"
        if not bundled.exists():
            return None
        
        query_lower = query.lower()
        
        for package_dir in bundled.iterdir():
            if not package_dir.is_dir():
                continue
            
            for md_file in package_dir.rglob("*.md"):
                content = md_file.read_text(encoding="utf-8", errors="ignore")
                if query_lower in content.lower():
                    return ActivityInfo(
                        name=query,
                        full_name=self._extract_full_name(content, query),
                        package_id=package_dir.name,
                        description=self._extract_description(content),
                        properties=self._extract_properties(content),
                        example_xaml=self._extract_example(content),
                        source="bundled",
                    )
        
        return None
    
    async def _search_live(
        self,
        query: str,
        project_path: Path,
    ) -> ActivityInfo | None:
        """Run uip rpa find-activities."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "uip", "rpa", "find-activities",
                "--query", query,
                "--project-dir", str(project_path),
                "--output", "json",
                "--use-studio",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        except (asyncio.TimeoutError, FileNotFoundError):
            return None
        
        if proc.returncode != 0:
            return None
        
        try:
            data = json.loads(stdout.decode("utf-8"))
            activities = data.get("activities", [])
            if activities:
                a = activities[0]
                return ActivityInfo(
                    name=a.get("name", query),
                    full_name=a.get("fullName", ""),
                    package_id=a.get("packageId", ""),
                    description=a.get("description", ""),
                    properties=a.get("properties", {}),
                    example_xaml=None,
                    source="live",
                )
        except json.JSONDecodeError:
            pass
        
        return None
    
    def _extract_full_name(self, content: str, query: str) -> str:
        """Extract full activity name from docs."""
        # Look for namespace patterns
        import re
        pattern = rf"([\w.]+\.{re.escape(query)})"
        match = re.search(pattern, content, re.IGNORECASE)
        return match.group(1) if match else query
    
    def _extract_description(self, content: str) -> str:
        """Extract description from markdown."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("# ") and i + 1 < len(lines):
                return lines[i + 1].strip()
        return ""
    
    def _extract_properties(self, content: str) -> dict:
        """Extract properties from markdown."""
        # Simple extraction - look for property sections
        properties = {}
        # Implementation depends on doc format
        return properties
    
    def _extract_example(self, content: str) -> str | None:
        """Extract XAML example from markdown."""
        import re
        pattern = r"```xml\n(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
```

**Tasks:**
- [ ] **Task A1:** Create `uipath_claude/activities/discovery.py`
- [ ] **Task A2:** Add activity caching
- [ ] **Task A3:** Integrate with skill tool for activity lookups
- [ ] **Task A4:** Add `/activity` command for manual lookup

---

### 2.6 LangGraph State Machine

Restructure the agent as a proper LangGraph state machine.

**File:** `uipath_claude/graph/state.py` (NEW)

```python
"""LangGraph state definition."""
from typing import TypedDict, Literal, Annotated
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """State shared across all nodes."""
    # Conversation
    messages: Annotated[list, add_messages]
    
    # Current phase
    phase: Literal["route", "plan", "execute", "validate", "feedback", "complete"]
    
    # Skill routing
    selected_skill: str | None
    skill_confidence: int
    plan: list[str]  # Multi-skill plan steps
    current_plan_step: int
    
    # Artifacts
    project_path: str | None
    generated_files: list[str]
    
    # Validation
    validation_errors: list[dict]
    fix_attempts: int
    
    # Feedback
    pending_question: str | None
    user_response: str | None
    
    # Session
    session_id: str
```

**File:** `uipath_claude/graph/builder.py` (NEW)

```python
"""LangGraph graph construction."""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from uipath_claude.graph.state import AgentState
from uipath_claude.graph.nodes import (
    route_node,
    plan_node,
    execute_node,
    validate_node,
    feedback_node,
)


def build_agent_graph() -> StateGraph:
    """Build the agent state machine."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("route", route_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("feedback", feedback_node)
    
    # Entry point
    workflow.add_edge(START, "route")
    
    # Route decides where to go
    workflow.add_conditional_edges(
        "route",
        lambda s: s["phase"],
        {
            "plan": "plan",
            "execute": "execute",
            "feedback": "feedback",
        },
    )
    
    # Plan produces execution steps
    workflow.add_edge("plan", "execute")
    
    # Execute produces artifacts
    workflow.add_conditional_edges(
        "execute",
        lambda s: "validate" if s["generated_files"] else "feedback",
        {
            "validate": "validate",
            "feedback": "feedback",
        },
    )
    
    # Validate checks artifacts
    workflow.add_conditional_edges(
        "validate",
        lambda s: "execute" if s["validation_errors"] and s["fix_attempts"] < 5 else "feedback",
        {
            "execute": "execute",
            "feedback": "feedback",
        },
    )
    
    # Feedback can loop back or complete
    workflow.add_conditional_edges(
        "feedback",
        lambda s: "route" if s["user_response"] else END,
        {
            "route": "route",
            END: END,
        },
    )
    
    return workflow


def compile_agent():
    """Compile agent with checkpointer."""
    workflow = build_agent_graph()
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)
```

**Tasks:**
- [ ] **Task G1:** Create `uipath_claude/graph/state.py`
- [ ] **Task G2:** Create `uipath_claude/graph/builder.py`
- [ ] **Task G3:** Create `uipath_claude/graph/nodes/` with route, plan, execute, validate, feedback nodes
- [ ] **Task G4:** Migrate CLI to use graph-based execution

---

## Part 3: Implementation Order

Execute tasks in this order to minimize risk:

### Phase 1: Cleanup (Day 1)
- [ ] C1: Delete `.worktrees/`
- [ ] C2: Delete `agent/`
- [ ] C3: Delete `archive/`
- [ ] C4: Delete `cli/`
- [ ] C5: Add `generated/` to `.gitignore`
- [ ] C6: Consolidate `scripts/`

### Phase 2: Foundation (Day 2-3)
- [ ] P1-P3: Planner routing
- [ ] F1-F4: Feedback loop
- [ ] V1-V4: Validation pipeline

### Phase 3: Skill Tool (Day 4-5)
- [ ] S1-S4: Skill tool enhancement
- [ ] A1-A4: Activity discovery

### Phase 4: Graph Refactor (Day 6-7)
- [ ] G1-G4: LangGraph state machine

### Phase 5: Testing & Verification
- [ ] Re-run eval suite (WG-001 through WG-005)
- [ ] Target: 80%+ pass rate (4/5 scenarios)
- [ ] Fix any regressions

---

## Part 4: Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Eval pass rate | 20% (1/5) | 80% (4/5) |
| Planner usage | 0% | 100% for ambiguous requests |
| Validation coverage | Regex only | Full Studio validation |
| Feedback loop | None | 2 clarifying questions max |
| Project structure | 6 top-level dirs | 4 top-level dirs |

---

## Part 5: Files to Create/Modify

### New Files
- `uipath_claude/query/planner_router.py`
- `uipath_claude/query/feedback_loop.py`
- `uipath_claude/validation/pipeline.py`
- `uipath_claude/activities/discovery.py`
- `uipath_claude/graph/state.py`
- `uipath_claude/graph/builder.py`
- `uipath_claude/graph/nodes/__init__.py`
- `uipath_claude/graph/nodes/route.py`
- `uipath_claude/graph/nodes/plan.py`
- `uipath_claude/graph/nodes/execute.py`
- `uipath_claude/graph/nodes/validate.py`
- `uipath_claude/graph/nodes/feedback.py`

### Modified Files
- `uipath_claude/cli/app.py` - Integrate new components
- `uipath_claude/tools/skill_tool.py` - Add forked execution
- `uipath_claude/artifacts/materialize.py` - Use validation pipeline
- `pyproject.toml` - Update if dependencies change

### Deleted Files/Directories
- `.worktrees/`
- `agent/`
- `archive/`
- `cli/`

---

## Part 6: Rollback Plan

If implementation fails:
1. Git revert to pre-implementation commit
2. Restore deleted directories from git history if needed
3. Re-run eval to confirm baseline

---

## Appendix: Skill Inventory from UiPath/skills

Skills available via git submodule (as of 2026-04-14):

| Skill | Status | Used By Agent |
|-------|--------|---------------|
| `uipath-rpa` | Active | Yes (keyword match) |
| `uipath-planner` | Active | **No (bypassed)** |
| `uipath-platform` | Active | Yes (keyword match) |
| `uipath-maestro-flow` | Active | Yes (keyword match) |
| `uipath-agents` | Active | Yes (keyword match) |
| `uipath-coded-apps` | Active | Yes (keyword match) |
| `uipath-servo` | Active | Yes (keyword match) |
| `uipath-diagnostics` | Active | Yes (keyword match) |
| `uipath-feedback` | Active | Yes (keyword match) |
| `uipath-human-in-the-loop` | Active | Yes (keyword match) |
| `uipath-case-management` | Active | Yes (keyword match) |

**Key Gap:** `uipath-planner` is the orchestrator skill but never invoked.
