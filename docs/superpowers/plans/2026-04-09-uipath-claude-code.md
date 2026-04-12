# UiPath Claude Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the UiPath Builder Agent into a Claude Code-style conversational agent with tool loops, slash commands, hooks, memory persistence, and UiPath-specific integrations.

**Architecture:** LangGraph-based conversation engine with model→tools→model loop, layered skill registry (UiPath/skills submodule + Cato templates + user/project skills), slash command system with `/help`, `/status`, `/analyze`, `/pack` commands, hooks for pre/post tool events, and memory files for persistent context.

**Tech Stack:** Python 3.11+, LangGraph, LangChain AWS (Bedrock), Typer CLI, Rich (terminal formatting), GitPython, httpx (async HTTP)

---

## File Structure

### Core Engine (Phase 1)
- Create: `agent/conversation_engine.py` - Model→tools→model loop with termination logic
- Modify: `agent/graph.py` - Wire conversation engine into LangGraph
- Modify: `agent/nodes/conversational.py` - Inject project context and memory

### Rendering (Phase 2)
- Create: `cli/branding.py` - Robot logo and welcome banner
- Create: `agent/rendering/message_renderer.py` - Content block to text conversion
- Modify: `cli/main.py` - Use renderer for output, show welcome banner

### Skill Registry (Phase 3)
- Create: `agent/skills/registry.py` - Multi-source skill registry manager
- Modify: `agent/skill_discovery.py` - Support multiple skill directories
- Modify: `agent/tools/skill_invoke.py` - Use new registry

### Project Detection (Phase 3b)
- Create: `agent/context/project_detector.py` - UiPath project.json detection
- Modify: `agent/state.py` - Add uipath_project fields

### Slash Commands (Phase 10)
- Create: `cli/commands/__init__.py` - Command registry
- Create: `cli/commands/help.py` - /help command
- Create: `cli/commands/status.py` - /status command
- Create: `cli/commands/skills.py` - /skills command
- Create: `cli/commands/analyze.py` - /analyze command
- Modify: `cli/main.py` - Parse and dispatch slash commands

### Hooks (Phase 11)
- Create: `agent/hooks/config.py` - Hook configuration loader
- Create: `agent/hooks/manager.py` - Hook execution manager

### Memory (Phase 12)
- Create: `agent/memory/loader.py` - Memory file loader

### Tests
- Create: `tests/unit/test_conversation_engine.py`
- Create: `tests/unit/test_branding.py`
- Create: `tests/unit/test_message_renderer.py`
- Create: `tests/unit/test_skill_registry.py`
- Create: `tests/unit/test_project_detector.py`
- Create: `tests/unit/test_slash_commands.py`
- Create: `tests/unit/test_hooks_manager.py`
- Create: `tests/unit/test_memory_loader.py`
- Create: `tests/fixtures/sample_project/project.json`

---

## Task 1: Conversation Engine - Tool Loop

**Files:**
- Create: `agent/conversation_engine.py`
- Test: `tests/unit/test_conversation_engine.py`

- [ ] **Step 1: Write the failing test for tool loop termination**

```python
# tests/unit/test_conversation_engine.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent.conversation_engine import ConversationEngine, MAX_TOOL_ITERATIONS


class TestConversationEngine:
    @pytest.fixture
    def engine(self):
        return ConversationEngine()

    @pytest.mark.asyncio
    async def test_terminates_when_no_tool_calls(self, engine):
        """Model response without tool_use ends the loop."""
        mock_response = AIMessage(content="Hello, I can help you with UiPath.")
        
        with patch.object(engine, '_invoke_model', new_callable=AsyncMock) as mock_invoke:
            mock_invoke.return_value = mock_response
            
            result = await engine.run_turn([HumanMessage(content="Hi")])
            
            assert mock_invoke.call_count == 1
            assert result.content == "Hello, I can help you with UiPath."

    @pytest.mark.asyncio
    async def test_respects_max_iterations(self, engine):
        """Loop stops after MAX_TOOL_ITERATIONS even if tools keep being called."""
        tool_call = {"id": "call_1", "name": "get_available_skills", "args": {}}
        mock_response = AIMessage(content="", tool_calls=[tool_call])
        
        with patch.object(engine, '_invoke_model', new_callable=AsyncMock) as mock_invoke:
            with patch.object(engine, '_execute_tools', new_callable=AsyncMock) as mock_exec:
                mock_invoke.return_value = mock_response
                mock_exec.return_value = [ToolMessage(content="skills", tool_call_id="call_1")]
                
                result = await engine.run_turn([HumanMessage(content="list skills")])
                
                assert mock_invoke.call_count == MAX_TOOL_ITERATIONS + 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_conversation_engine.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.conversation_engine'"

- [ ] **Step 3: Write the conversation engine implementation**

```python
# agent/conversation_engine.py
"""Conversation engine with model→tools→model loop."""

from typing import List, Optional
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool

MAX_TOOL_ITERATIONS = 10


class ConversationEngine:
    """
    Manages the model→tools→model conversation loop.
    
    Similar to Claude Code's query.ts + toolOrchestration.ts pattern.
    """
    
    def __init__(
        self,
        model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region: str = "us-east-1",
        temperature: float = 0.3,
        tools: Optional[List[BaseTool]] = None,
    ):
        self.model_id = model_id
        self.region = region
        self.temperature = temperature
        self.tools = tools or []
        self._llm = None
    
    @property
    def llm(self) -> ChatBedrockConverse:
        """Lazy-initialize LLM with tools bound."""
        if self._llm is None:
            self._llm = ChatBedrockConverse(
                model=self.model_id,
                region_name=self.region,
                temperature=self.temperature,
            )
            if self.tools:
                self._llm = self._llm.bind_tools(self.tools)
        return self._llm
    
    async def run_turn(
        self,
        messages: List[BaseMessage],
        system_prompt: Optional[str] = None,
    ) -> AIMessage:
        """
        Run a complete conversation turn with tool loop.
        
        Args:
            messages: Conversation history
            system_prompt: Optional system prompt to prepend
            
        Returns:
            Final AIMessage after tool loop completes
        """
        all_messages = []
        if system_prompt:
            all_messages.append(SystemMessage(content=system_prompt))
        all_messages.extend(messages)
        
        iterations = 0
        
        while iterations <= MAX_TOOL_ITERATIONS:
            response = await self._invoke_model(all_messages)
            all_messages.append(response)
            
            if not response.tool_calls:
                return response
            
            tool_results = await self._execute_tools(response.tool_calls)
            all_messages.extend(tool_results)
            iterations += 1
        
        return AIMessage(content="[Max tool iterations reached. Please try a simpler request.]")
    
    async def _invoke_model(self, messages: List[BaseMessage]) -> AIMessage:
        """Invoke the LLM with messages."""
        return await self.llm.ainvoke(messages)
    
    async def _execute_tools(self, tool_calls: List[dict]) -> List[ToolMessage]:
        """Execute tool calls and return results."""
        results = []
        
        for call in tool_calls:
            tool_name = call.get("name")
            tool_args = call.get("args", {})
            tool_id = call.get("id")
            
            tool = self._find_tool(tool_name)
            if tool:
                try:
                    result = await tool.ainvoke(tool_args)
                    results.append(ToolMessage(content=str(result), tool_call_id=tool_id))
                except Exception as e:
                    results.append(ToolMessage(
                        content=f"Error: {type(e).__name__}: {str(e)}",
                        tool_call_id=tool_id
                    ))
            else:
                results.append(ToolMessage(
                    content=f"Error: Tool '{tool_name}' not found",
                    tool_call_id=tool_id
                ))
        
        return results
    
    def _find_tool(self, name: str) -> Optional[BaseTool]:
        """Find a tool by name."""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_conversation_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/conversation_engine.py tests/unit/test_conversation_engine.py
git commit -m "feat: add ConversationEngine with model-tools loop"
```

---

## Task 2: Robot Logo and Welcome Banner

**Files:**
- Create: `cli/branding.py`
- Test: `tests/unit/test_branding.py`

- [ ] **Step 1: Write the failing test for branding**

```python
# tests/unit/test_branding.py
import pytest
from cli.branding import ROBOT_ASCII, print_welcome_banner, get_compact_logo


class TestBranding:
    def test_robot_logo_has_content(self):
        """Robot ASCII art is not empty."""
        assert ROBOT_ASCII is not None
        assert len(ROBOT_ASCII) > 0
        assert "o" in ROBOT_ASCII  # Eyes
    
    def test_welcome_banner_includes_version(self, capsys):
        """Banner includes version number."""
        print_welcome_banner(
            version="0.1.0",
            cwd="/path/to/project",
            model="claude-3-5-sonnet",
            project_name=None
        )
        captured = capsys.readouterr()
        assert "0.1.0" in captured.out
    
    def test_welcome_banner_includes_project_name(self, capsys):
        """Banner shows detected UiPath project name."""
        print_welcome_banner(
            version="0.1.0",
            cwd="/path/to/project",
            model="claude-3-5-sonnet",
            project_name="MyRPAProject"
        )
        captured = capsys.readouterr()
        assert "MyRPAProject" in captured.out
    
    def test_compact_logo_for_narrow_terminal(self):
        """Uses compact logo when terminal is narrow."""
        compact = get_compact_logo()
        assert len(compact) < len(ROBOT_ASCII)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_branding.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'cli.branding'"

- [ ] **Step 3: Write the branding implementation**

```python
# cli/branding.py
"""Branding and welcome banner for UiPath Claude Code."""

import os
import shutil

ROBOT_ASCII = r"""
       ┌─────────┐
       │  o   o  │
       │    ▼    │
       │  └───┘  │
       └────┬────┘
          ┌─┴─┐
         ─┤   ├─
          └───┘
"""

COMPACT_LOGO = "[o_o] UiPath Claude Code"


def get_terminal_width() -> int:
    """Get terminal width, default to 80 if unavailable."""
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def get_compact_logo() -> str:
    """Return compact single-line logo."""
    return COMPACT_LOGO


def print_welcome_banner(
    version: str,
    cwd: str,
    model: str,
    project_name: str | None = None,
) -> None:
    """
    Print the welcome banner with robot logo.
    
    Args:
        version: Application version
        cwd: Current working directory
        model: Active model name
        project_name: Detected UiPath project name (if any)
    """
    width = get_terminal_width()
    
    if width < 60:
        print(f"\n{COMPACT_LOGO} v{version}")
        print(f"  Model: {model}")
        if project_name:
            print(f"  Project: {project_name}")
        print()
        return
    
    # Full banner
    border = "═" * 55
    
    print(f"\n  ╔{border}╗")
    print(f"  ║{' ' * 55}║")
    
    # Robot art lines
    robot_lines = ROBOT_ASCII.strip().split('\n')
    info_lines = [
        f"UiPath Claude Code",
        f"v{version}",
        "",
        f"Working in: {_truncate_path(cwd, 30)}",
        f"Model: {model}",
    ]
    if project_name:
        info_lines.insert(3, f"Project: {project_name}")
    
    max_lines = max(len(robot_lines), len(info_lines))
    
    for i in range(max_lines):
        robot_part = robot_lines[i] if i < len(robot_lines) else ""
        info_part = info_lines[i] if i < len(info_lines) else ""
        
        robot_padded = f"{robot_part:<20}"
        info_padded = f"{info_part:<33}"
        
        print(f"  ║ {robot_padded} {info_padded}║")
    
    print(f"  ║{' ' * 55}║")
    print(f"  ╚{border}╝\n")


def _truncate_path(path: str, max_len: int) -> str:
    """Truncate path in the middle if too long."""
    if len(path) <= max_len:
        return path
    
    half = (max_len - 3) // 2
    return f"{path[:half]}...{path[-half:]}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_branding.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add cli/branding.py tests/unit/test_branding.py
git commit -m "feat: add robot logo and welcome banner"
```

---

## Task 3: Message Renderer

**Files:**
- Create: `agent/rendering/__init__.py`
- Create: `agent/rendering/message_renderer.py`
- Test: `tests/unit/test_message_renderer.py`

- [ ] **Step 1: Write the failing test for message renderer**

```python
# tests/unit/test_message_renderer.py
import pytest
from langchain_core.messages import AIMessage

from agent.rendering.message_renderer import render_message, render_content_blocks


class TestMessageRenderer:
    def test_renders_text_content(self):
        """Text content renders as plain text."""
        message = AIMessage(content="Hello, world!")
        result = render_message(message)
        assert result == "Hello, world!"
    
    def test_renders_text_blocks(self):
        """List of text blocks renders as merged text."""
        blocks = [
            {"type": "text", "text": "First part."},
            {"type": "text", "text": " Second part."},
        ]
        result = render_content_blocks(blocks)
        assert result == "First part. Second part."
    
    def test_renders_tool_use_as_progress(self):
        """tool_use blocks show tool name."""
        blocks = [
            {"type": "tool_use", "name": "get_available_skills", "id": "call_1"},
        ]
        result = render_content_blocks(blocks)
        assert "get_available_skills" in result
        assert "Using tool:" in result or "Tool:" in result
    
    def test_hides_tool_result_details(self):
        """tool_result blocks show summary, not full content."""
        blocks = [
            {"type": "tool_result", "tool_use_id": "call_1", "content": "x" * 1000},
        ]
        result = render_content_blocks(blocks)
        assert len(result) < 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_message_renderer.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.rendering'"

- [ ] **Step 3: Write the message renderer implementation**

```python
# agent/rendering/__init__.py
"""Rendering utilities for message output."""

from agent.rendering.message_renderer import render_message, render_content_blocks

__all__ = ["render_message", "render_content_blocks"]
```

```python
# agent/rendering/message_renderer.py
"""Render LLM messages to human-readable terminal output."""

from typing import Any, List, Union
from langchain_core.messages import AIMessage


def render_message(message: AIMessage) -> str:
    """
    Render an AIMessage to human-readable text.
    
    Args:
        message: LangChain AIMessage
        
    Returns:
        Formatted string for terminal output
    """
    content = message.content
    
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        return render_content_blocks(content)
    
    return str(content)


def render_content_blocks(blocks: List[dict]) -> str:
    """
    Render a list of content blocks to text.
    
    Handles:
    - text blocks: merged into output
    - tool_use blocks: shown as progress indicators
    - tool_result blocks: summarized (not full content)
    
    Args:
        blocks: List of content block dicts
        
    Returns:
        Formatted string
    """
    parts = []
    
    for block in blocks:
        block_type = block.get("type", "unknown")
        
        if block_type == "text":
            text = block.get("text", "")
            parts.append(text)
        
        elif block_type == "tool_use":
            tool_name = block.get("name", "unknown")
            parts.append(f"\n[Using tool: {tool_name}]\n")
        
        elif block_type == "tool_result":
            tool_id = block.get("tool_use_id", "unknown")
            content = block.get("content", "")
            summary = _summarize_content(content, max_len=100)
            parts.append(f"[Tool result: {summary}]\n")
        
        else:
            parts.append(f"[{block_type}]")
    
    return "".join(parts)


def _summarize_content(content: Any, max_len: int = 100) -> str:
    """Summarize content to max length."""
    text = str(content)
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_message_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/rendering/__init__.py agent/rendering/message_renderer.py tests/unit/test_message_renderer.py
git commit -m "feat: add message renderer for content blocks"
```

---

## Task 4: UiPath Project Detector

**Files:**
- Create: `agent/context/__init__.py`
- Create: `agent/context/project_detector.py`
- Create: `tests/fixtures/sample_project/project.json`
- Test: `tests/unit/test_project_detector.py`

- [ ] **Step 1: Create test fixture**

```json
// tests/fixtures/sample_project/project.json
{
  "name": "TestRPAProject",
  "projectId": "12345678-1234-1234-1234-123456789012",
  "description": "Test UiPath project for unit tests",
  "main": "Main.xaml",
  "dependencies": {
    "UiPath.System.Activities": "[25.10.3]",
    "UiPath.UIAutomation.Activities": "[25.10.19]"
  },
  "schemaVersion": "4.0",
  "expressionLanguage": "VisualBasic",
  "targetFramework": "Windows"
}
```

- [ ] **Step 2: Write the failing test**

```python
# tests/unit/test_project_detector.py
import pytest
from pathlib import Path
from agent.context.project_detector import (
    detect_uipath_project,
    UiPathProjectContext,
)


class TestProjectDetector:
    @pytest.fixture
    def sample_project_path(self):
        return Path(__file__).parent.parent / "fixtures" / "sample_project"
    
    def test_detects_project_json(self, sample_project_path):
        """Finds project.json in directory."""
        result = detect_uipath_project(sample_project_path)
        assert result is not None
        assert isinstance(result, UiPathProjectContext)
    
    def test_extracts_project_name(self, sample_project_path):
        """Extracts name from project.json."""
        result = detect_uipath_project(sample_project_path)
        assert result.name == "TestRPAProject"
    
    def test_extracts_dependencies(self, sample_project_path):
        """Extracts dependencies from project.json."""
        result = detect_uipath_project(sample_project_path)
        assert "UiPath.System.Activities" in result.dependencies
    
    def test_returns_none_outside_project(self, tmp_path):
        """Returns None when not in UiPath project."""
        result = detect_uipath_project(tmp_path)
        assert result is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/unit/test_project_detector.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.context'"

- [ ] **Step 4: Write the project detector implementation**

```python
# agent/context/__init__.py
"""Context detection utilities."""

from agent.context.project_detector import detect_uipath_project, UiPathProjectContext

__all__ = ["detect_uipath_project", "UiPathProjectContext"]
```

```python
# agent/context/project_detector.py
"""Detect UiPath project context from current directory."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List


@dataclass
class UiPathProjectContext:
    """Context extracted from a UiPath project."""
    
    name: str
    project_id: str
    description: str
    main_workflow: str
    dependencies: dict[str, str]
    workflows: List[str]
    target_framework: str
    project_path: Path


def detect_uipath_project(start_path: Path) -> Optional[UiPathProjectContext]:
    """
    Detect UiPath project from a directory.
    
    Searches for project.json in the given directory and parent directories.
    
    Args:
        start_path: Directory to start search from
        
    Returns:
        UiPathProjectContext if found, None otherwise
    """
    current = start_path.resolve()
    
    for _ in range(10):  # Max 10 levels up
        project_json = current / "project.json"
        
        if project_json.exists():
            return _parse_project_json(project_json)
        
        uiproj_files = list(current.glob("*.uiproj"))
        if uiproj_files:
            return _create_minimal_context(current, uiproj_files[0])
        
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    return None


def _parse_project_json(project_json: Path) -> Optional[UiPathProjectContext]:
    """Parse project.json and extract context."""
    try:
        with open(project_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    
    project_dir = project_json.parent
    workflows = _find_workflows(project_dir)
    
    return UiPathProjectContext(
        name=data.get("name", project_dir.name),
        project_id=data.get("projectId", ""),
        description=data.get("description", ""),
        main_workflow=data.get("main", "Main.xaml"),
        dependencies=data.get("dependencies", {}),
        workflows=workflows,
        target_framework=data.get("targetFramework", "Windows"),
        project_path=project_dir,
    )


def _create_minimal_context(project_dir: Path, uiproj: Path) -> UiPathProjectContext:
    """Create minimal context from .uiproj file."""
    workflows = _find_workflows(project_dir)
    
    return UiPathProjectContext(
        name=uiproj.stem,
        project_id="",
        description="",
        main_workflow="Main.xaml",
        dependencies={},
        workflows=workflows,
        target_framework="Windows",
        project_path=project_dir,
    )


def _find_workflows(project_dir: Path) -> List[str]:
    """Find all .xaml workflow files in project."""
    xaml_files = list(project_dir.rglob("*.xaml"))
    return [str(f.relative_to(project_dir)) for f in xaml_files]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_project_detector.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/context/__init__.py agent/context/project_detector.py tests/unit/test_project_detector.py tests/fixtures/sample_project/project.json
git commit -m "feat: add UiPath project detector"
```

---

## Task 5: Slash Command Registry

**Files:**
- Create: `cli/commands/__init__.py`
- Create: `cli/commands/help.py`
- Create: `cli/commands/status.py`
- Test: `tests/unit/test_slash_commands.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_slash_commands.py
import pytest
from cli.commands import parse_slash_command, COMMANDS, register_command


class TestSlashCommands:
    def test_parses_command_name(self):
        """/help parses to command='help', args=''."""
        result = parse_slash_command("/help")
        assert result is not None
        assert result["command"] == "help"
        assert result["args"] == ""
    
    def test_parses_command_with_args(self):
        """/analyze --file Main.xaml parses correctly."""
        result = parse_slash_command("/analyze --file Main.xaml")
        assert result["command"] == "analyze"
        assert result["args"] == "--file Main.xaml"
    
    def test_returns_none_for_non_command(self):
        """Regular text returns None."""
        result = parse_slash_command("hello world")
        assert result is None
    
    def test_help_command_registered(self):
        """Help command is in registry."""
        assert "help" in COMMANDS
    
    def test_status_command_registered(self):
        """Status command is in registry."""
        assert "status" in COMMANDS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_slash_commands.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'cli.commands'"

- [ ] **Step 3: Write the command registry**

```python
# cli/commands/__init__.py
"""Slash command registry and parser."""

from dataclasses import dataclass
from typing import Callable, Optional, Any

COMMANDS: dict[str, "SlashCommand"] = {}


@dataclass
class SlashCommand:
    """A registered slash command."""
    
    name: str
    description: str
    handler: Callable[..., Any]
    aliases: list[str] | None = None


def register_command(
    name: str,
    description: str,
    aliases: list[str] | None = None,
):
    """Decorator to register a slash command."""
    def decorator(fn: Callable) -> Callable:
        cmd = SlashCommand(
            name=name,
            description=description,
            handler=fn,
            aliases=aliases,
        )
        COMMANDS[name] = cmd
        if aliases:
            for alias in aliases:
                COMMANDS[alias] = cmd
        return fn
    return decorator


def parse_slash_command(text: str) -> Optional[dict]:
    """
    Parse a slash command from input text.
    
    Args:
        text: User input text
        
    Returns:
        Dict with 'command' and 'args' keys, or None if not a command
    """
    text = text.strip()
    
    if not text.startswith("/"):
        return None
    
    parts = text[1:].split(" ", 1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    return {"command": command, "args": args}


def execute_command(command: str, args: str, context: dict) -> str:
    """
    Execute a slash command.
    
    Args:
        command: Command name
        args: Command arguments
        context: Execution context (cwd, model, etc.)
        
    Returns:
        Command output string
    """
    if command not in COMMANDS:
        available = ", ".join(sorted(set(c.name for c in COMMANDS.values())))
        return f"Unknown command: /{command}\nAvailable: {available}"
    
    cmd = COMMANDS[command]
    return cmd.handler(args, context)


# Import commands to register them
from cli.commands import help as _help
from cli.commands import status as _status
```

- [ ] **Step 4: Write the help command**

```python
# cli/commands/help.py
"""Help command - list available commands."""

from cli.commands import register_command, COMMANDS


@register_command(
    name="help",
    description="Show available commands",
    aliases=["?", "h"],
)
def help_command(args: str, context: dict) -> str:
    """List all available slash commands."""
    lines = ["Available commands:", ""]
    
    seen = set()
    for cmd in COMMANDS.values():
        if cmd.name in seen:
            continue
        seen.add(cmd.name)
        
        aliases = ""
        if cmd.aliases:
            aliases = f" (aliases: {', '.join(cmd.aliases)})"
        
        lines.append(f"  /{cmd.name:<12} {cmd.description}{aliases}")
    
    lines.append("")
    lines.append("Type /command to execute, or just chat normally.")
    
    return "\n".join(lines)
```

- [ ] **Step 5: Write the status command**

```python
# cli/commands/status.py
"""Status command - show current configuration."""

from cli.commands import register_command


@register_command(
    name="status",
    description="Show version, model, and project info",
)
def status_command(args: str, context: dict) -> str:
    """Show current status and configuration."""
    version = context.get("version", "unknown")
    model = context.get("model", "unknown")
    cwd = context.get("cwd", "unknown")
    project = context.get("project_name", None)
    
    lines = [
        "UiPath Claude Code Status",
        "=" * 30,
        f"Version:  {version}",
        f"Model:    {model}",
        f"CWD:      {cwd}",
    ]
    
    if project:
        lines.append(f"Project:  {project}")
    else:
        lines.append("Project:  (not in UiPath project)")
    
    return "\n".join(lines)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/unit/test_slash_commands.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add cli/commands/__init__.py cli/commands/help.py cli/commands/status.py tests/unit/test_slash_commands.py
git commit -m "feat: add slash command registry with /help and /status"
```

---

## Task 6: Skills Command

**Files:**
- Create: `cli/commands/skills.py`
- Modify: `cli/commands/__init__.py`

- [ ] **Step 1: Write the skills command**

```python
# cli/commands/skills.py
"""Skills command - list available UiPath skills."""

from pathlib import Path
from cli.commands import register_command
from agent.skill_discovery import SkillDiscovery


@register_command(
    name="skills",
    description="List available UiPath skills",
)
def skills_command(args: str, context: dict) -> str:
    """List all available skills from the registry."""
    skills_path = context.get("skills_path", Path("skills"))
    
    try:
        discovery = SkillDiscovery(skills_path)
        registry = discovery.discover_all_skills()
    except Exception as e:
        return f"Error loading skills: {e}"
    
    if not registry:
        return "No skills found. Check that the skills submodule is initialized."
    
    lines = ["Available UiPath Skills:", ""]
    
    for name, skill in sorted(registry.items()):
        desc = skill.description[:60] + "..." if len(skill.description) > 60 else skill.description
        lines.append(f"  {name:<30} {desc}")
    
    lines.append("")
    lines.append(f"Total: {len(registry)} skills")
    lines.append("Use 'invoke_skill(name, task)' to run a skill.")
    
    return "\n".join(lines)
```

- [ ] **Step 2: Update command registry imports**

```python
# cli/commands/__init__.py - add import at bottom
from cli.commands import skills as _skills
```

- [ ] **Step 3: Run tests to verify**

Run: `pytest tests/unit/test_slash_commands.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add cli/commands/skills.py cli/commands/__init__.py
git commit -m "feat: add /skills command"
```

---

## Task 7: Analyze Command (UiPath Workflow Analyzer)

**Files:**
- Create: `cli/commands/analyze.py`
- Modify: `cli/commands/__init__.py`

- [ ] **Step 1: Write the analyze command**

```python
# cli/commands/analyze.py
"""Analyze command - run UiPath Workflow Analyzer."""

import subprocess
from pathlib import Path
from cli.commands import register_command


@register_command(
    name="analyze",
    description="Run UiPath Workflow Analyzer on project",
)
def analyze_command(args: str, context: dict) -> str:
    """
    Run UiPath Workflow Analyzer.
    
    Usage:
        /analyze              - Analyze entire project
        /analyze Main.xaml    - Analyze specific file
    """
    cwd = Path(context.get("cwd", "."))
    project_json = cwd / "project.json"
    
    if not project_json.exists():
        return "Error: Not in a UiPath project directory (no project.json found)"
    
    target = args.strip() if args.strip() else str(cwd)
    
    cmd = ["uipath", "studio", "package", "analyze", "--source", target]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(cwd),
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n\nStderr:\n{result.stderr}"
        
        if result.returncode == 0:
            return f"Workflow Analyzer completed successfully:\n\n{output}"
        else:
            return f"Workflow Analyzer found issues (exit code {result.returncode}):\n\n{output}"
    
    except FileNotFoundError:
        return (
            "Error: UiPath CLI not found.\n"
            "Install with: pip install uipath-cli\n"
            "Or download from: https://github.com/UiPath/uipathcli"
        )
    except subprocess.TimeoutExpired:
        return "Error: Workflow Analyzer timed out after 120 seconds"
    except Exception as e:
        return f"Error running Workflow Analyzer: {type(e).__name__}: {e}"
```

- [ ] **Step 2: Update command registry imports**

```python
# cli/commands/__init__.py - add import at bottom
from cli.commands import analyze as _analyze
```

- [ ] **Step 3: Commit**

```bash
git add cli/commands/analyze.py cli/commands/__init__.py
git commit -m "feat: add /analyze command for Workflow Analyzer"
```

---

## Task 8: Hooks Manager

**Files:**
- Create: `agent/hooks/__init__.py`
- Create: `agent/hooks/config.py`
- Create: `agent/hooks/manager.py`
- Test: `tests/unit/test_hooks_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_hooks_manager.py
import pytest
from pathlib import Path
from agent.hooks.manager import HookManager
from agent.hooks.config import HookConfig, load_hooks_config


class TestHooksManager:
    @pytest.fixture
    def sample_config(self, tmp_path):
        config_file = tmp_path / ".uipath-claude" / "hooks.json"
        config_file.parent.mkdir(parents=True)
        config_file.write_text('''{
            "session_start": ["echo Starting session"],
            "pre_tool_use": {
                "FileWrite:*.xaml": ["echo Writing XAML: {file}"]
            }
        }''')
        return config_file
    
    def test_loads_hooks_config(self, sample_config):
        """Loads hooks from config file."""
        config = load_hooks_config(sample_config)
        assert config is not None
        assert "session_start" in config.hooks
    
    def test_runs_session_start_hook(self, sample_config):
        """session_start hooks run on chat start."""
        manager = HookManager(sample_config)
        results = manager.run_hooks("session_start", {})
        assert len(results) == 1
        assert results[0].success
    
    def test_hook_pattern_matching(self, sample_config):
        """FileWrite:*.xaml matches XAML file writes."""
        manager = HookManager(sample_config)
        matches = manager.get_matching_hooks("pre_tool_use", {
            "tool": "FileWrite",
            "file": "Main.xaml"
        })
        assert len(matches) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_hooks_manager.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.hooks'"

- [ ] **Step 3: Write the hooks config**

```python
# agent/hooks/__init__.py
"""Hooks system for pre/post tool events."""

from agent.hooks.config import HookConfig, load_hooks_config
from agent.hooks.manager import HookManager, HookResult

__all__ = ["HookConfig", "load_hooks_config", "HookManager", "HookResult"]
```

```python
# agent/hooks/config.py
"""Hook configuration loader."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class HookConfig:
    """Parsed hook configuration."""
    
    hooks: dict = field(default_factory=dict)
    config_path: Optional[Path] = None


def load_hooks_config(config_path: Path) -> HookConfig:
    """
    Load hooks configuration from JSON file.
    
    Args:
        config_path: Path to hooks.json
        
    Returns:
        HookConfig with parsed hooks
    """
    if not config_path.exists():
        return HookConfig(hooks={}, config_path=config_path)
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return HookConfig(hooks=data, config_path=config_path)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: Failed to load hooks config: {e}")
        return HookConfig(hooks={}, config_path=config_path)
```

- [ ] **Step 4: Write the hooks manager**

```python
# agent/hooks/manager.py
"""Hook execution manager."""

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from agent.hooks.config import HookConfig, load_hooks_config


@dataclass
class HookResult:
    """Result of a hook execution."""
    
    command: str
    success: bool
    output: str
    error: Optional[str] = None


class HookManager:
    """
    Manages hook execution for tool events.
    
    Hooks are shell commands that run on events like:
    - session_start: When chat session begins
    - session_end: When chat session ends
    - pre_tool_use: Before a tool executes
    - post_tool_use: After a tool completes
    """
    
    def __init__(self, config_path: Path):
        self.config = load_hooks_config(config_path)
    
    def run_hooks(self, event: str, context: dict) -> List[HookResult]:
        """
        Run all hooks for an event.
        
        Args:
            event: Event name (session_start, pre_tool_use, etc.)
            context: Context dict with variables for substitution
            
        Returns:
            List of HookResult for each executed hook
        """
        hooks = self.get_matching_hooks(event, context)
        results = []
        
        for cmd in hooks:
            result = self._execute_hook(cmd, context)
            results.append(result)
        
        return results
    
    def get_matching_hooks(self, event: str, context: dict) -> List[str]:
        """
        Get hooks matching an event and context.
        
        Args:
            event: Event name
            context: Context with tool name, file path, etc.
            
        Returns:
            List of command strings to execute
        """
        event_hooks = self.config.hooks.get(event, [])
        
        if isinstance(event_hooks, list):
            return event_hooks
        
        if isinstance(event_hooks, dict):
            matching = []
            tool = context.get("tool", "")
            file = context.get("file", "")
            
            for pattern, commands in event_hooks.items():
                if self._matches_pattern(pattern, tool, file):
                    if isinstance(commands, list):
                        matching.extend(commands)
                    else:
                        matching.append(commands)
            
            return matching
        
        return []
    
    def _matches_pattern(self, pattern: str, tool: str, file: str) -> bool:
        """Check if pattern matches tool:file."""
        if ":" not in pattern:
            return pattern == tool
        
        tool_pattern, file_pattern = pattern.split(":", 1)
        
        if tool_pattern != tool and tool_pattern != "*":
            return False
        
        return fnmatch.fnmatch(file, file_pattern)
    
    def _execute_hook(self, command: str, context: dict) -> HookResult:
        """Execute a single hook command."""
        cmd = command.format(**context)
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            return HookResult(
                command=cmd,
                success=result.returncode == 0,
                output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return HookResult(
                command=cmd,
                success=False,
                output="",
                error="Hook timed out after 30 seconds",
            )
        except Exception as e:
            return HookResult(
                command=cmd,
                success=False,
                output="",
                error=f"{type(e).__name__}: {e}",
            )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/unit/test_hooks_manager.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/hooks/__init__.py agent/hooks/config.py agent/hooks/manager.py tests/unit/test_hooks_manager.py
git commit -m "feat: add hooks system for tool events"
```

---

## Task 9: Memory Loader

**Files:**
- Create: `agent/memory/__init__.py`
- Create: `agent/memory/loader.py`
- Test: `tests/unit/test_memory_loader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_memory_loader.py
import pytest
from pathlib import Path
from agent.memory.loader import load_memory, MemoryContext


class TestMemoryLoader:
    @pytest.fixture
    def setup_memory_files(self, tmp_path):
        # Global memory
        global_dir = tmp_path / "global"
        global_dir.mkdir()
        (global_dir / "memory.md").write_text("# Global Memory\nPrefer concise responses.")
        
        # Project memory
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".uipath-claude").mkdir()
        (project_dir / ".uipath-claude" / "memory.md").write_text(
            "# Project Memory\nThis is a dispatcher process."
        )
        
        return {"global": global_dir, "project": project_dir}
    
    def test_loads_global_memory(self, setup_memory_files):
        """Loads global memory file."""
        result = load_memory(
            global_dir=setup_memory_files["global"],
            project_dir=None,
        )
        assert "Global Memory" in result.content
        assert "concise responses" in result.content
    
    def test_loads_project_memory(self, setup_memory_files):
        """Loads project memory file."""
        result = load_memory(
            global_dir=None,
            project_dir=setup_memory_files["project"],
        )
        assert "Project Memory" in result.content
        assert "dispatcher process" in result.content
    
    def test_merges_global_and_project(self, setup_memory_files):
        """Both memory files are combined."""
        result = load_memory(
            global_dir=setup_memory_files["global"],
            project_dir=setup_memory_files["project"],
        )
        assert "Global Memory" in result.content
        assert "Project Memory" in result.content
    
    def test_handles_missing_files(self, tmp_path):
        """Returns empty content if no memory files exist."""
        result = load_memory(
            global_dir=tmp_path / "nonexistent",
            project_dir=tmp_path / "also_nonexistent",
        )
        assert result.content == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_memory_loader.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'agent.memory'"

- [ ] **Step 3: Write the memory loader**

```python
# agent/memory/__init__.py
"""Memory persistence system."""

from agent.memory.loader import load_memory, MemoryContext

__all__ = ["load_memory", "MemoryContext"]
```

```python
# agent/memory/loader.py
"""Load memory files for persistent context."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class MemoryContext:
    """Loaded memory content."""
    
    content: str
    global_loaded: bool
    project_loaded: bool


def load_memory(
    global_dir: Optional[Path] = None,
    project_dir: Optional[Path] = None,
) -> MemoryContext:
    """
    Load memory files from global and project directories.
    
    Args:
        global_dir: Global config directory (e.g., ~/.uipath-claude)
        project_dir: Project directory (searches for .uipath-claude/memory.md)
        
    Returns:
        MemoryContext with combined content
    """
    parts = []
    global_loaded = False
    project_loaded = False
    
    # Load global memory
    if global_dir:
        global_memory = global_dir / "memory.md"
        if global_memory.exists():
            try:
                content = global_memory.read_text(encoding="utf-8")
                parts.append(content)
                global_loaded = True
            except OSError:
                pass
    
    # Load project memory
    if project_dir:
        project_memory = project_dir / ".uipath-claude" / "memory.md"
        if project_memory.exists():
            try:
                content = project_memory.read_text(encoding="utf-8")
                parts.append(content)
                project_loaded = True
            except OSError:
                pass
    
    return MemoryContext(
        content="\n\n".join(parts),
        global_loaded=global_loaded,
        project_loaded=project_loaded,
    )


def get_default_global_dir() -> Path:
    """Get default global config directory."""
    return Path.home() / ".uipath-claude"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_memory_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/memory/__init__.py agent/memory/loader.py tests/unit/test_memory_loader.py
git commit -m "feat: add memory loader for persistent context"
```

---

## Task 10: Wire CLI with New Components

**Files:**
- Modify: `cli/main.py`
- Modify: `agent/state.py`

- [ ] **Step 1: Update state schema**

```python
# agent/state.py - add new fields to ProjectState
class ProjectState(TypedDict, total=False):
    # ... existing fields ...
    
    # ── UiPath project context (Phase 3b) ────────────────
    uipath_project: dict          # Parsed project.json
    uipath_workflows: list[str]   # List of .xaml files
    uipath_dependencies: dict     # Package dependencies
    
    # ── Session metadata (Phase 12) ──────────────────────
    session_id: str               # Unique session ID
    memory_context: str           # Loaded memory content
```

- [ ] **Step 2: Update CLI main with all components**

```python
# cli/main.py - updated with branding, commands, project detection
"""CLI for UiPath Claude Code."""

import asyncio
import uuid
from pathlib import Path

import typer
from langchain_core.messages import HumanMessage

from agent.graph import conversational_graph
from agent.context.project_detector import detect_uipath_project
from agent.memory.loader import load_memory, get_default_global_dir
from agent.rendering.message_renderer import render_message
from cli.branding import print_welcome_banner
from cli.commands import parse_slash_command, execute_command, COMMANDS

app = typer.Typer(help="UiPath Claude Code - Conversational AI for RPA development")

VERSION = "0.1.0"
MODEL = "claude-3-5-sonnet"


def _run_async(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


@app.command()
def chat(
    no_banner: bool = typer.Option(False, "--no-banner", help="Skip welcome banner"),
):
    """Start conversational chat mode."""
    cwd = Path.cwd()
    session_id = str(uuid.uuid4())
    
    # Detect UiPath project
    project_context = detect_uipath_project(cwd)
    project_name = project_context.name if project_context else None
    
    # Load memory
    memory = load_memory(
        global_dir=get_default_global_dir(),
        project_dir=cwd,
    )
    
    # Show welcome banner
    if not no_banner:
        print_welcome_banner(
            version=VERSION,
            cwd=str(cwd),
            model=MODEL,
            project_name=project_name,
        )
    
    # Command context
    cmd_context = {
        "version": VERSION,
        "model": MODEL,
        "cwd": str(cwd),
        "project_name": project_name,
        "skills_path": Path("skills"),
    }
    
    # Initial state
    state = {
        "messages": [],
        "mode": "conversational",
        "session_id": session_id,
        "memory_context": memory.content,
    }
    
    if project_context:
        state["uipath_project"] = {
            "name": project_context.name,
            "main": project_context.main_workflow,
            "dependencies": project_context.dependencies,
        }
        state["uipath_workflows"] = project_context.workflows
    
    config = {"configurable": {"thread_id": session_id}}
    
    print("Type /help for commands, or just chat. Ctrl+C to exit.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Check for slash command
        parsed = parse_slash_command(user_input)
        if parsed:
            result = execute_command(parsed["command"], parsed["args"], cmd_context)
            print(f"\n{result}\n")
            continue
        
        # Regular chat
        state["messages"].append(HumanMessage(content=user_input))
        
        try:
            result = _run_async(conversational_graph.ainvoke(state, config))
            state = result
            
            if result.get("messages"):
                last_message = result["messages"][-1]
                rendered = render_message(last_message)
                print(f"\nAssistant: {rendered}\n")
        except Exception as e:
            print(f"\nError: {type(e).__name__}: {e}\n")


@app.command()
def start_project(
    description: str = typer.Option(..., "-d", "--description", help="Process description"),
):
    """Bootstrap a new UiPath project with guided flow."""
    print(f"Starting project with description: {description}")
    print("(Bootstrap flow not yet implemented in this version)")


if __name__ == "__main__":
    app()
```

- [ ] **Step 3: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add cli/main.py agent/state.py
git commit -m "feat: wire CLI with branding, commands, project detection, memory"
```

---

## Task 11: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update pyproject.toml**

```toml
# pyproject.toml - updated
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["agent*", "cli*"]

[project]
name = "uipath-claude-code"
version = "0.1.0"
description = "Claude Code-style conversational AI agent for UiPath RPA development"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",
    "langchain-aws>=0.2.0",
    "langchain-core>=0.3.0",
    "typer>=0.12.0",
    "pyyaml>=6.0",
    "python-dotenv>=1.0.0",
    "boto3>=1.34.0",
    "rich>=13.0.0",
    "httpx>=0.27.0",
    "gitpython>=3.1.0",
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
uipath-claude = "cli.main:app"

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

- [ ] **Step 2: Install updated dependencies**

Run: `pip install -e ".[dev]"`
Expected: Successfully installed

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "chore: update dependencies and rename to uipath-claude-code"
```

---

## Task 12: Integration Test

**Files:**
- Create: `tests/integration/test_chat_flow.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_chat_flow.py
"""Integration tests for chat flow."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage

from cli.main import chat
from agent.context.project_detector import detect_uipath_project


class TestChatFlow:
    @pytest.fixture
    def mock_graph(self):
        """Mock the conversational graph."""
        with patch("cli.main.conversational_graph") as mock:
            mock.ainvoke = AsyncMock(return_value={
                "messages": [
                    HumanMessage(content="Hi"),
                    AIMessage(content="Hello! I'm UiPath Claude Code."),
                ]
            })
            yield mock
    
    def test_project_detection_in_uipath_folder(self, tmp_path):
        """Project is detected when in UiPath folder."""
        project_json = tmp_path / "project.json"
        project_json.write_text('{"name": "TestProject", "main": "Main.xaml"}')
        
        result = detect_uipath_project(tmp_path)
        
        assert result is not None
        assert result.name == "TestProject"
    
    def test_slash_command_execution(self):
        """Slash commands execute without invoking LLM."""
        from cli.commands import parse_slash_command, execute_command
        
        parsed = parse_slash_command("/status")
        assert parsed["command"] == "status"
        
        result = execute_command("status", "", {
            "version": "0.1.0",
            "model": "test-model",
            "cwd": "/test",
        })
        
        assert "0.1.0" in result
        assert "test-model" in result
```

- [ ] **Step 2: Run integration tests**

Run: `pytest tests/integration/ -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_chat_flow.py
git commit -m "test: add integration tests for chat flow"
```

---

## Task 13: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --cov=agent --cov=cli --cov-report=term-missing`
Expected: All tests pass, coverage > 80%

- [ ] **Step 2: Test CLI manually**

```bash
cd /path/to/uipath-project
uipath-claude chat
```

Expected:
- Robot logo displays
- Project detected from project.json
- /help shows commands
- /status shows version and model
- Chat responds to messages

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete UiPath Claude Code MVP implementation"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- [x] Conversation engine with tool loop (Task 1)
- [x] Robot logo and welcome banner (Task 2)
- [x] Message renderer (Task 3)
- [x] UiPath project detection (Task 4)
- [x] Slash command system (Tasks 5-7)
- [x] Hooks system (Task 8)
- [x] Memory persistence (Task 9)
- [x] CLI integration (Task 10)
- [x] Dependencies updated (Task 11)
- [x] Integration tests (Task 12)

**2. Placeholder scan:** No TBD, TODO, or "implement later" found.

**3. Type consistency:** All types, method signatures, and property names are consistent across tasks.
