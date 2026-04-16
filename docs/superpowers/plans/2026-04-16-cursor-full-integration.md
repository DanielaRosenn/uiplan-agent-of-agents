# Cursor Full Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the complete UiPath Builder Agent functionality in Cursor via MCP server, including subagents, workflow graphs, doc cache, skills system, memory, and agentic execution.

**Architecture:** Extend the existing `mcp_server/server.py` to expose all agent capabilities as MCP tools and resources. Tools handle actions (bootstrap, validate, execute), resources provide context (skills, docs, memory). The MCP server wraps existing Python functions from `uipath_claude/`.

**Tech Stack:** Python 3.11+, MCP SDK (`mcp` package), existing `uipath_claude` modules, LangGraph (for agentic execution)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `mcp_server/server.py` | MCP server entry point, tool/resource registration |
| `mcp_server/tools/workflow_tools.py` | Workflow validation, execution, project management |
| `mcp_server/tools/skill_tools.py` | Skill registry, matching, insights |
| `mcp_server/tools/agent_tools.py` | Bootstrap flow, subagents (BA/SA/Dev/QA) |
| `mcp_server/tools/doc_tools.py` | Activity docs, package documentation |
| `mcp_server/tools/memory_tools.py` | Session memory, conversation history |
| `mcp_server/resources/skills.py` | Skill list, skill content as resources |
| `mcp_server/resources/docs.py` | Activity documentation resources |
| `mcp_server/resources/project.py` | Project context resources |
| `tests/mcp/test_server.py` | MCP server tests |
| `tests/mcp/test_tools.py` | Tool integration tests |

---

## Task 1: Refactor MCP Server Structure

**Files:**
- Modify: `mcp_server/server.py`
- Create: `mcp_server/tools/__init__.py`
- Create: `mcp_server/resources/__init__.py`

- [ ] **Step 1: Create tools package init**

```python
# mcp_server/tools/__init__.py
"""MCP tool modules."""
```

- [ ] **Step 2: Create resources package init**

```python
# mcp_server/resources/__init__.py
"""MCP resource modules."""
```

- [ ] **Step 3: Refactor server.py to use modular structure**

```python
# mcp_server/server.py
"""UiPath Builder Agent MCP Server."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, Resource
except ImportError:
    print("MCP package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

from mcp_server.tools.workflow_tools import get_workflow_tools, call_workflow_tool
from mcp_server.tools.skill_tools import get_skill_tools, call_skill_tool
from mcp_server.tools.agent_tools import get_agent_tools, call_agent_tool
from mcp_server.tools.doc_tools import get_doc_tools, call_doc_tool
from mcp_server.tools.memory_tools import get_memory_tools, call_memory_tool
from mcp_server.resources.skills import get_skill_resources, fetch_skill_resource
from mcp_server.resources.docs import get_doc_resources, fetch_doc_resource

server = Server("uipath-builder-agent")


def _text_result(result: Any) -> list[TextContent]:
    if isinstance(result, str):
        return [TextContent(type="text", text=result)]
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


@server.list_tools()
async def list_tools() -> list[Tool]:
    tools = []
    tools.extend(get_workflow_tools())
    tools.extend(get_skill_tools())
    tools.extend(get_agent_tools())
    tools.extend(get_doc_tools())
    tools.extend(get_memory_tools())
    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name.startswith("uipath_workflow_"):
            result = await call_workflow_tool(name, arguments)
        elif name.startswith("uipath_skill_"):
            result = await call_skill_tool(name, arguments)
        elif name.startswith("uipath_agent_"):
            result = await call_agent_tool(name, arguments)
        elif name.startswith("uipath_doc_"):
            result = await call_doc_tool(name, arguments)
        elif name.startswith("uipath_memory_"):
            result = await call_memory_tool(name, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        return _text_result(result)
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@server.list_resources()
async def list_resources() -> list[Resource]:
    resources = []
    resources.extend(await get_skill_resources())
    resources.extend(await get_doc_resources())
    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    if uri.startswith("uipath://skill/"):
        return await fetch_skill_resource(uri)
    elif uri.startswith("uipath://doc/"):
        return await fetch_doc_resource(uri)
    return f"Unknown resource: {uri}"


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run to verify imports work**

Run: `python -c "import sys; sys.path.insert(0, '.'); from mcp_server.server import server; print('OK')"`
Expected: OK (will fail until we create the tool modules)

- [ ] **Step 5: Commit**

```bash
git add mcp_server/
git commit -m "refactor: modular MCP server structure"
```

---

## Task 2: Workflow Tools Module

**Files:**
- Create: `mcp_server/tools/workflow_tools.py`

- [ ] **Step 1: Create workflow_tools.py with all workflow operations**

```python
# mcp_server/tools/workflow_tools.py
"""Workflow validation, execution, and project management tools."""
from __future__ import annotations

from typing import Any
from mcp.types import Tool

from uipath_claude.tools.skill_execution_tools import (
    read_file as _read_file,
    write_file as _write_file,
    list_directory as _list_directory,
    read_project_json as _read_project_json,
    install_package as _install_package,
    validate_file as _validate_file,
    run_workflow as _run_workflow,
    run_uip_command as _run_uip_command,
    ensure_project_structure as _ensure_project_structure,
    validate_and_fix_loop as _validate_and_fix_loop,
    debug_workflow as _debug_workflow,
)
from uipath_claude.tools.deploy_tool import deploy_to_orchestrator as _deploy


def get_workflow_tools() -> list[Tool]:
    """Return workflow-related MCP tools."""
    return [
        Tool(
            name="uipath_workflow_read_file",
            description="Read contents of a file in a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file"}
                },
                "required": ["file_path"]
            }
        ),
        Tool(
            name="uipath_workflow_write_file",
            description="Write content to a file in a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Path to the file"},
                    "content": {"type": "string", "description": "Content to write"}
                },
                "required": ["file_path", "content"]
            }
        ),
        Tool(
            name="uipath_workflow_list_directory",
            description="List files and directories in a path",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {"type": "string", "description": "Path to directory"}
                },
                "required": ["directory_path"]
            }
        ),
        Tool(
            name="uipath_workflow_read_project",
            description="Read and parse project.json from a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project directory", "default": "."}
                }
            }
        ),
        Tool(
            name="uipath_workflow_install_package",
            description="Install a NuGet package in a UiPath project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project directory"},
                    "package_id": {"type": "string", "description": "NuGet package ID"},
                    "version": {"type": "string", "description": "Package version (optional)"}
                },
                "required": ["project_dir", "package_id"]
            }
        ),
        Tool(
            name="uipath_workflow_validate",
            description="Validate a XAML workflow using UiPath Studio (uip rpa get-errors --use-studio)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project directory"},
                    "file_path": {"type": "string", "description": "XAML file to validate"}
                },
                "required": ["project_dir", "file_path"]
            }
        ),
        Tool(
            name="uipath_workflow_run",
            description="Execute a workflow to verify runtime behavior. Use AFTER validation passes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project directory"},
                    "file_path": {"type": "string", "description": "Workflow file (e.g., Main.xaml)"},
                    "input_arguments": {"type": "string", "description": "JSON input arguments"},
                    "timeout_seconds": {"type": "integer", "description": "Timeout", "default": 60}
                },
                "required": ["project_dir", "file_path"]
            }
        ),
        Tool(
            name="uipath_workflow_validate_and_fix",
            description="Validate workflow and automatically fix errors in a loop",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project directory"},
                    "file_path": {"type": "string", "description": "XAML file to validate"},
                    "max_iterations": {"type": "integer", "description": "Max fix attempts", "default": 5}
                },
                "required": ["project_dir", "file_path"]
            }
        ),
        Tool(
            name="uipath_workflow_ensure_project",
            description="Create or validate UiPath project structure with project.json",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project directory"},
                    "project_name": {"type": "string", "description": "Project name"},
                    "target_framework": {"type": "string", "description": "Windows or Portable", "default": "Windows"}
                },
                "required": ["project_dir", "project_name"]
            }
        ),
        Tool(
            name="uipath_workflow_run_command",
            description="Run a UiPath CLI (uip) command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "uip command (e.g., 'rpa get-errors')"},
                    "args": {"type": "array", "items": {"type": "string"}, "description": "Arguments"},
                    "project_dir": {"type": "string", "description": "Working directory"}
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="uipath_workflow_deploy",
            description="Deploy package to Orchestrator",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_dir": {"type": "string", "description": "Project directory"},
                    "folder_path": {"type": "string", "description": "Orchestrator folder path"},
                    "feed_name": {"type": "string", "description": "Feed name (optional)"}
                },
                "required": ["project_dir", "folder_path"]
            }
        ),
    ]


async def call_workflow_tool(name: str, arguments: dict) -> Any:
    """Execute a workflow tool."""
    tool_map = {
        "uipath_workflow_read_file": lambda a: _read_file.invoke({"file_path": a["file_path"]}),
        "uipath_workflow_write_file": lambda a: _write_file.invoke({"file_path": a["file_path"], "content": a["content"]}),
        "uipath_workflow_list_directory": lambda a: _list_directory.invoke({"directory_path": a["directory_path"]}),
        "uipath_workflow_read_project": lambda a: _read_project_json.invoke({"project_dir": a.get("project_dir", ".")}),
        "uipath_workflow_install_package": lambda a: _install_package.invoke(a),
        "uipath_workflow_validate": lambda a: _validate_file.invoke(a),
        "uipath_workflow_run": lambda a: _run_workflow.invoke(a),
        "uipath_workflow_validate_and_fix": lambda a: _validate_and_fix_loop.invoke(a),
        "uipath_workflow_ensure_project": lambda a: _ensure_project_structure.invoke(a),
        "uipath_workflow_run_command": lambda a: _run_uip_command.invoke(a),
        "uipath_workflow_deploy": lambda a: _deploy.invoke(a),
    }
    
    if name in tool_map:
        return tool_map[name](arguments)
    raise ValueError(f"Unknown workflow tool: {name}")
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/tools/workflow_tools.py
git commit -m "feat: add workflow tools module for MCP"
```

---

## Task 3: Skill Tools Module

**Files:**
- Create: `mcp_server/tools/skill_tools.py`

- [ ] **Step 1: Create skill_tools.py**

```python
# mcp_server/tools/skill_tools.py
"""Skill registry, matching, and insights tools."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from mcp.types import Tool

from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.loader import load_skill_content
from uipath_claude.skills.insights import SkillInsightsStore
from uipath_claude.query.router import route_user_input


_registry: SkillRegistry | None = None


def _get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry(project_root=Path.cwd())
        _registry.load_skills()
    return _registry


def get_skill_tools() -> list[Tool]:
    """Return skill-related MCP tools."""
    return [
        Tool(
            name="uipath_skill_list",
            description="List all available UiPath skills with their descriptions",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_role": {
                        "type": "string",
                        "description": "Filter by agent role (ba, sa, developer, qa, conversational)",
                        "enum": ["ba", "sa", "developer", "qa", "conversational"]
                    }
                }
            }
        ),
        Tool(
            name="uipath_skill_get",
            description="Get the full content of a specific skill",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of the skill"}
                },
                "required": ["skill_name"]
            }
        ),
        Tool(
            name="uipath_skill_match",
            description="Find the best matching skills for a user request",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {"type": "string", "description": "User's request or question"},
                    "top_k": {"type": "integer", "description": "Number of matches", "default": 3}
                },
                "required": ["user_input"]
            }
        ),
        Tool(
            name="uipath_skill_insights_query",
            description="Query insights (learnings, gotchas) for a skill",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Name of the skill"}
                },
                "required": ["skill_name"]
            }
        ),
        Tool(
            name="uipath_skill_insights_add",
            description="Add an insight (gotcha, failure pattern, etc.) for a skill",
            inputSchema={
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string", "description": "Skill name"},
                    "insight_type": {
                        "type": "string",
                        "enum": ["gotcha", "failure_pattern", "success_pattern", "edge_case", "improvement"],
                        "description": "Type of insight"
                    },
                    "content": {"type": "string", "description": "The insight content"},
                    "context": {"type": "string", "description": "Additional context"}
                },
                "required": ["skill_name", "insight_type", "content"]
            }
        ),
        Tool(
            name="uipath_skill_manifest",
            description="Generate skills manifest for auditing",
            inputSchema={"type": "object", "properties": {}}
        ),
    ]


async def call_skill_tool(name: str, arguments: dict) -> Any:
    """Execute a skill tool."""
    registry = _get_registry()
    
    if name == "uipath_skill_list":
        if "agent_role" in arguments:
            skills = registry.filter_by_agent(arguments["agent_role"])
        else:
            skills = registry.skills
        return [{"name": s["name"], "description": s.get("description", "")[:200], "origin": s.get("origin")} for s in skills]
    
    elif name == "uipath_skill_get":
        skill = registry.get_skill(arguments["skill_name"])
        if not skill:
            return f"Skill not found: {arguments['skill_name']}"
        return load_skill_content(skill)
    
    elif name == "uipath_skill_match":
        matches = route_user_input(arguments["user_input"], registry.skills)
        top_k = arguments.get("top_k", 3)
        return matches[:top_k]
    
    elif name == "uipath_skill_insights_query":
        store = SkillInsightsStore()
        return store.get_summary(arguments["skill_name"])
    
    elif name == "uipath_skill_insights_add":
        store = SkillInsightsStore()
        store.add_insight(
            skill_name=arguments["skill_name"],
            insight_type=arguments["insight_type"],
            content=arguments["content"],
            context=arguments.get("context"),
        )
        return f"Insight added for {arguments['skill_name']}"
    
    elif name == "uipath_skill_manifest":
        return registry.generate_manifest()
    
    raise ValueError(f"Unknown skill tool: {name}")
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/tools/skill_tools.py
git commit -m "feat: add skill tools module for MCP"
```

---

## Task 4: Agent Tools Module (Bootstrap Flow, Subagents)

**Files:**
- Create: `mcp_server/tools/agent_tools.py`

- [ ] **Step 1: Create agent_tools.py with bootstrap and agentic execution**

```python
# mcp_server/tools/agent_tools.py
"""Bootstrap flow and subagent tools."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from mcp.types import Tool

from uipath_claude.query.bootstrap import run_bootstrap_flow
from uipath_claude.query.planner import run_planner_agent
from uipath_claude.query.agentic_executor import AgenticExecutor
from uipath_claude.query.intent_classifier import classify_intent, IntentType
from uipath_claude.tools.skill_execution_tools import get_skill_execution_tools


def get_agent_tools() -> list[Tool]:
    """Return agent-related MCP tools."""
    return [
        Tool(
            name="uipath_agent_bootstrap",
            description="Run full bootstrap flow: BA -> SA -> Developer -> QA. Creates PDD, SDD, implementation plan, and QA validation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {"type": "string", "description": "Description of what to build"},
                    "output_dir": {"type": "string", "description": "Output directory (optional)"}
                },
                "required": ["user_request"]
            }
        ),
        Tool(
            name="uipath_agent_plan",
            description="Run the planning agent to analyze a request and create an implementation plan (read-only exploration)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {"type": "string", "description": "What to plan"},
                    "project_context": {"type": "object", "description": "Optional project context"}
                },
                "required": ["user_request"]
            }
        ),
        Tool(
            name="uipath_agent_execute",
            description="Execute a task using the agentic executor with ReAct-style tool loop",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task to execute"},
                    "skill_name": {"type": "string", "description": "Skill to use (e.g., uipath-automation)"},
                    "max_iterations": {"type": "integer", "description": "Max tool iterations", "default": 25}
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="uipath_agent_classify_intent",
            description="Classify user intent (QUESTION, BUILD, AMBIGUOUS, DOCUMENTATION)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {"type": "string", "description": "User's message"}
                },
                "required": ["user_input"]
            }
        ),
        Tool(
            name="uipath_agent_ba",
            description="Run Business Analyst agent to create PDD from requirements",
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {"type": "string", "description": "Business requirements"}
                },
                "required": ["requirements"]
            }
        ),
        Tool(
            name="uipath_agent_sa",
            description="Run Solution Architect agent to create SDD from PDD",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdd": {"type": "string", "description": "Process Definition Document content"}
                },
                "required": ["pdd"]
            }
        ),
    ]


async def call_agent_tool(name: str, arguments: dict) -> Any:
    """Execute an agent tool."""
    model_name = os.environ.get("UIPATH_CLAUDE_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    if name == "uipath_agent_bootstrap":
        output_dir = Path(arguments.get("output_dir", "."))
        result = await run_bootstrap_flow(
            arguments["user_request"],
            output_root=output_dir,
        )
        return {
            "status": "complete",
            "paths": result["paths"],
            "summary": {
                "pdd_length": len(result["pdd"]),
                "sdd_length": len(result["sdd"]),
                "code_length": len(result["code"]),
            }
        }
    
    elif name == "uipath_agent_plan":
        result = await run_planner_agent(
            arguments["user_request"],
            project_context=arguments.get("project_context"),
            model_name=model_name,
            region=region,
        )
        return {
            "success": result.success,
            "plan": result.final_response,
            "iterations": result.iterations,
            "tool_calls": len(result.tool_calls_made),
        }
    
    elif name == "uipath_agent_execute":
        executor = AgenticExecutor(model_name=model_name, region=region)
        tools = get_skill_execution_tools()
        skill_name = arguments.get("skill_name", "uipath-automation")
        
        # Load skill content
        from mcp_server.tools.skill_tools import _get_registry
        registry = _get_registry()
        skill = registry.get_skill(skill_name)
        skill_content = ""
        if skill:
            from uipath_claude.skills.loader import load_skill_content
            skill_content = load_skill_content(skill)
        
        result = await executor.execute(
            skill_content=skill_content,
            user_request=arguments["task"],
            tools=tools,
            skill_name=skill_name,
            max_iterations=arguments.get("max_iterations", 25),
        )
        return {
            "success": result.success,
            "response": result.final_response,
            "iterations": result.iterations,
            "tool_calls": len(result.tool_calls_made),
            "files_written": result.files_written,
            "validation_status": result.validation_status,
        }
    
    elif name == "uipath_agent_classify_intent":
        intent, reason = classify_intent(arguments["user_input"])
        return {"intent": intent.value, "reason": reason}
    
    elif name == "uipath_agent_ba":
        from uipath_claude.agents.ba import BAAgent
        from uipath_claude.query.agent_invoke import invoke_agent_llm
        from uipath_claude.query.engine_factory import create_conversation_engine_from_env
        
        engine = create_conversation_engine_from_env()
        ba = BAAgent()
        pdd = await invoke_agent_llm(engine, ba.get_system_prompt(), arguments["requirements"])
        return {"pdd": pdd}
    
    elif name == "uipath_agent_sa":
        from uipath_claude.agents.sa import SAAgent
        from uipath_claude.query.agent_invoke import invoke_agent_llm
        from uipath_claude.query.engine_factory import create_conversation_engine_from_env
        
        engine = create_conversation_engine_from_env()
        sa = SAAgent()
        sdd = await invoke_agent_llm(engine, sa.get_system_prompt(), f"Create SDD based on this PDD:\n\n{arguments['pdd']}")
        return {"sdd": sdd}
    
    raise ValueError(f"Unknown agent tool: {name}")
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/tools/agent_tools.py
git commit -m "feat: add agent tools module (bootstrap, subagents, agentic execution)"
```

---

## Task 5: Documentation Tools Module

**Files:**
- Create: `mcp_server/tools/doc_tools.py`

- [ ] **Step 1: Create doc_tools.py**

```python
# mcp_server/tools/doc_tools.py
"""Activity documentation and UiPath docs tools."""
from __future__ import annotations

from typing import Any
from mcp.types import Tool

from uipath_claude.skills.activity_docs import (
    list_available_packages,
    get_package_versions,
    get_activity_doc,
    get_package_overview,
    list_activities,
    search_activities,
)
from uipath_claude.tools.skill_execution_tools import (
    find_activity_info as _find_activity_info,
    query_uipath_docs as _query_uipath_docs,
)


def get_doc_tools() -> list[Tool]:
    """Return documentation-related MCP tools."""
    return [
        Tool(
            name="uipath_doc_list_packages",
            description="List all packages with activity documentation",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="uipath_doc_list_activities",
            description="List all documented activities for a package",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {"type": "string", "description": "Package ID (e.g., UiPath.Mail.Activities)"},
                    "version": {"type": "string", "description": "Version (optional, uses latest)"}
                },
                "required": ["package_id"]
            }
        ),
        Tool(
            name="uipath_doc_get_activity",
            description="Get documentation for a specific activity",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {"type": "string", "description": "Package ID"},
                    "activity_name": {"type": "string", "description": "Activity name (e.g., GetOutlookMailMessages)"},
                    "version": {"type": "string", "description": "Version (optional)"}
                },
                "required": ["package_id", "activity_name"]
            }
        ),
        Tool(
            name="uipath_doc_get_package_overview",
            description="Get overview documentation for a package",
            inputSchema={
                "type": "object",
                "properties": {
                    "package_id": {"type": "string", "description": "Package ID"},
                    "version": {"type": "string", "description": "Version (optional)"}
                },
                "required": ["package_id"]
            }
        ),
        Tool(
            name="uipath_doc_search",
            description="Search for activities across all packages",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="uipath_doc_find_activity",
            description="Find activity information by name or capability (uses CLI)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Activity name or capability"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="uipath_doc_query",
            description="Search UiPath official documentation",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Documentation search query"}
                },
                "required": ["query"]
            }
        ),
    ]


async def call_doc_tool(name: str, arguments: dict) -> Any:
    """Execute a documentation tool."""
    if name == "uipath_doc_list_packages":
        return list_available_packages()
    
    elif name == "uipath_doc_list_activities":
        return list_activities(arguments["package_id"], arguments.get("version"))
    
    elif name == "uipath_doc_get_activity":
        doc = get_activity_doc(
            arguments["package_id"],
            arguments["activity_name"],
            arguments.get("version")
        )
        return doc or f"No documentation found for {arguments['activity_name']}"
    
    elif name == "uipath_doc_get_package_overview":
        overview = get_package_overview(arguments["package_id"], arguments.get("version"))
        return overview or f"No overview found for {arguments['package_id']}"
    
    elif name == "uipath_doc_search":
        return search_activities(arguments["query"])
    
    elif name == "uipath_doc_find_activity":
        return _find_activity_info.invoke({"query": arguments["query"]})
    
    elif name == "uipath_doc_query":
        return _query_uipath_docs.invoke({"query": arguments["query"]})
    
    raise ValueError(f"Unknown doc tool: {name}")
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/tools/doc_tools.py
git commit -m "feat: add documentation tools module for MCP"
```

---

## Task 6: Memory Tools Module

**Files:**
- Create: `mcp_server/tools/memory_tools.py`

- [ ] **Step 1: Create memory_tools.py**

```python
# mcp_server/tools/memory_tools.py
"""Session memory and conversation history tools."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from mcp.types import Tool

from uipath_claude.memory.loader import load_memory
from uipath_claude.memory.store import save_memory


def get_memory_tools() -> list[Tool]:
    """Return memory-related MCP tools."""
    return [
        Tool(
            name="uipath_memory_load",
            description="Load memory from global or project-specific location",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {"type": "string", "description": "Project path (optional, uses global if not set)"}
                }
            }
        ),
        Tool(
            name="uipath_memory_save",
            description="Save memory to global or project-specific location",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content to save"},
                    "project_path": {"type": "string", "description": "Project path (optional)"}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="uipath_memory_append",
            description="Append to existing memory",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Content to append"},
                    "project_path": {"type": "string", "description": "Project path (optional)"}
                },
                "required": ["content"]
            }
        ),
    ]


async def call_memory_tool(name: str, arguments: dict) -> Any:
    """Execute a memory tool."""
    project_path = arguments.get("project_path")
    
    if name == "uipath_memory_load":
        memory = load_memory(project_path)
        return memory or "No memory found"
    
    elif name == "uipath_memory_save":
        save_memory(arguments["content"], project_path)
        return "Memory saved"
    
    elif name == "uipath_memory_append":
        existing = load_memory(project_path) or ""
        new_content = existing + "\n\n" + arguments["content"] if existing else arguments["content"]
        save_memory(new_content, project_path)
        return "Memory appended"
    
    raise ValueError(f"Unknown memory tool: {name}")
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/tools/memory_tools.py
git commit -m "feat: add memory tools module for MCP"
```

---

## Task 7: Skill Resources

**Files:**
- Create: `mcp_server/resources/skills.py`

- [ ] **Step 1: Create skills.py resources**

```python
# mcp_server/resources/skills.py
"""Skill resources for MCP."""
from __future__ import annotations

from pathlib import Path
from mcp.types import Resource

from uipath_claude.skills.registry import SkillRegistry
from uipath_claude.skills.loader import load_skill_content


_registry: SkillRegistry | None = None


def _get_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry(project_root=Path.cwd())
        _registry.load_skills()
    return _registry


async def get_skill_resources() -> list[Resource]:
    """Return skill resources."""
    registry = _get_registry()
    resources = []
    
    for skill in registry.skills:
        resources.append(Resource(
            uri=f"uipath://skill/{skill['name']}",
            name=skill["name"],
            description=skill.get("description", "")[:200],
            mimeType="text/markdown",
        ))
    
    return resources


async def fetch_skill_resource(uri: str) -> str:
    """Fetch a skill resource by URI."""
    skill_name = uri.replace("uipath://skill/", "")
    registry = _get_registry()
    skill = registry.get_skill(skill_name)
    
    if not skill:
        return f"Skill not found: {skill_name}"
    
    return load_skill_content(skill)
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/resources/skills.py
git commit -m "feat: add skill resources for MCP"
```

---

## Task 8: Documentation Resources

**Files:**
- Create: `mcp_server/resources/docs.py`

- [ ] **Step 1: Create docs.py resources**

```python
# mcp_server/resources/docs.py
"""Documentation resources for MCP."""
from __future__ import annotations

from mcp.types import Resource

from uipath_claude.skills.activity_docs import (
    list_available_packages,
    get_latest_version,
    list_activities,
    get_activity_doc,
    get_package_overview,
)


async def get_doc_resources() -> list[Resource]:
    """Return documentation resources."""
    resources = []
    
    for package_id in list_available_packages():
        version = get_latest_version(package_id)
        if version:
            resources.append(Resource(
                uri=f"uipath://doc/{package_id}/overview",
                name=f"{package_id} Overview",
                description=f"Overview documentation for {package_id}",
                mimeType="text/markdown",
            ))
            
            for activity in list_activities(package_id, version)[:10]:
                resources.append(Resource(
                    uri=f"uipath://doc/{package_id}/{activity}",
                    name=f"{package_id}/{activity}",
                    description=f"Documentation for {activity}",
                    mimeType="text/markdown",
                ))
    
    return resources


async def fetch_doc_resource(uri: str) -> str:
    """Fetch a documentation resource by URI."""
    parts = uri.replace("uipath://doc/", "").split("/")
    
    if len(parts) < 2:
        return f"Invalid doc URI: {uri}"
    
    package_id = parts[0]
    item = parts[1]
    
    if item == "overview":
        content = get_package_overview(package_id)
        return content or f"No overview for {package_id}"
    else:
        content = get_activity_doc(package_id, item)
        return content or f"No documentation for {package_id}/{item}"
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server/resources/docs.py
git commit -m "feat: add documentation resources for MCP"
```

---

## Task 9: Integration Tests

**Files:**
- Create: `tests/mcp/__init__.py`
- Create: `tests/mcp/test_server.py`

- [ ] **Step 1: Create test directory**

```python
# tests/mcp/__init__.py
"""MCP server tests."""
```

- [ ] **Step 2: Create test_server.py**

```python
# tests/mcp/test_server.py
"""Tests for MCP server."""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestWorkflowTools:
    """Test workflow tools."""
    
    def test_get_workflow_tools_returns_list(self):
        from mcp_server.tools.workflow_tools import get_workflow_tools
        tools = get_workflow_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all(hasattr(t, "name") for t in tools)
    
    def test_workflow_tool_names_prefixed(self):
        from mcp_server.tools.workflow_tools import get_workflow_tools
        tools = get_workflow_tools()
        for tool in tools:
            assert tool.name.startswith("uipath_workflow_")


class TestSkillTools:
    """Test skill tools."""
    
    def test_get_skill_tools_returns_list(self):
        from mcp_server.tools.skill_tools import get_skill_tools
        tools = get_skill_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
    
    def test_skill_tool_names_prefixed(self):
        from mcp_server.tools.skill_tools import get_skill_tools
        tools = get_skill_tools()
        for tool in tools:
            assert tool.name.startswith("uipath_skill_")


class TestAgentTools:
    """Test agent tools."""
    
    def test_get_agent_tools_returns_list(self):
        from mcp_server.tools.agent_tools import get_agent_tools
        tools = get_agent_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
    
    def test_agent_tool_names_prefixed(self):
        from mcp_server.tools.agent_tools import get_agent_tools
        tools = get_agent_tools()
        for tool in tools:
            assert tool.name.startswith("uipath_agent_")


class TestDocTools:
    """Test documentation tools."""
    
    def test_get_doc_tools_returns_list(self):
        from mcp_server.tools.doc_tools import get_doc_tools
        tools = get_doc_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0


class TestMemoryTools:
    """Test memory tools."""
    
    def test_get_memory_tools_returns_list(self):
        from mcp_server.tools.memory_tools import get_memory_tools
        tools = get_memory_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0


class TestServerImports:
    """Test server can be imported."""
    
    def test_server_imports(self):
        from mcp_server.server import server
        assert server is not None
        assert server.name == "uipath-builder-agent"
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/mcp/test_server.py -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/mcp/
git commit -m "test: add MCP server integration tests"
```

---

## Task 10: Update Documentation

**Files:**
- Modify: `docs/CURSOR_USER_GUIDE.md`
- Modify: `README.md`

- [ ] **Step 1: Update CURSOR_USER_GUIDE.md MCP section**

Add to the MCP Tools section in `docs/CURSOR_USER_GUIDE.md`:

```markdown
### Full MCP Tool Catalog

The MCP server exposes the complete agent functionality:

**Workflow Tools (`uipath_workflow_*`):**
| Tool | Description |
|------|-------------|
| `uipath_workflow_validate` | Static XAML validation via Studio |
| `uipath_workflow_run` | Execute workflow, capture runtime errors |
| `uipath_workflow_validate_and_fix` | Auto-fix validation loop |
| `uipath_workflow_install_package` | Install NuGet packages |
| `uipath_workflow_ensure_project` | Create project structure |
| `uipath_workflow_deploy` | Deploy to Orchestrator |
| `uipath_workflow_run_command` | Run any `uip` CLI command |

**Skill Tools (`uipath_skill_*`):**
| Tool | Description |
|------|-------------|
| `uipath_skill_list` | List all skills, filter by agent role |
| `uipath_skill_get` | Get full skill content |
| `uipath_skill_match` | Find best skills for a request |
| `uipath_skill_insights_query` | Get learnings/gotchas for a skill |
| `uipath_skill_insights_add` | Record a new insight |

**Agent Tools (`uipath_agent_*`):**
| Tool | Description |
|------|-------------|
| `uipath_agent_bootstrap` | Full BA -> SA -> Dev -> QA flow |
| `uipath_agent_plan` | Read-only planning agent |
| `uipath_agent_execute` | Agentic ReAct execution loop |
| `uipath_agent_classify_intent` | Classify QUESTION/BUILD/AMBIGUOUS |
| `uipath_agent_ba` | Run BA agent (create PDD) |
| `uipath_agent_sa` | Run SA agent (create SDD) |

**Documentation Tools (`uipath_doc_*`):**
| Tool | Description |
|------|-------------|
| `uipath_doc_list_packages` | List packages with docs |
| `uipath_doc_list_activities` | List activities in a package |
| `uipath_doc_get_activity` | Get activity documentation |
| `uipath_doc_search` | Search across all activities |

**Memory Tools (`uipath_memory_*`):**
| Tool | Description |
|------|-------------|
| `uipath_memory_load` | Load session memory |
| `uipath_memory_save` | Save memory |
| `uipath_memory_append` | Append to memory |
```

- [ ] **Step 2: Commit documentation**

```bash
git add docs/CURSOR_USER_GUIDE.md README.md
git commit -m "docs: update MCP tool documentation"
```

---

## Task 11: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/integration`
Expected: All tests pass

- [ ] **Step 2: Verify MCP server starts**

Run: `python -m mcp_server.server`
Expected: Server starts without errors (will wait for stdio input)

- [ ] **Step 3: Verify Cursor MCP config**

Check `.cursor/mcp.json` is correct:

```json
{
  "mcpServers": {
    "uipath-builder-agent": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  }
}
```

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "feat: complete MCP server with full agent capabilities"
```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Workflow tools (validate, run, install, deploy) - Task 2
- [x] Skill tools (list, get, match, insights) - Task 3
- [x] Agent tools (bootstrap, plan, execute, subagents) - Task 4
- [x] Documentation tools (activity docs, search) - Task 5
- [x] Memory tools (load, save, append) - Task 6
- [x] Resources (skills, docs) - Tasks 7-8
- [x] Tests - Task 9
- [x] Documentation - Task 10

**Placeholder scan:** No TBD, TODO, or "implement later" found.

**Type consistency:** All tool names use consistent `uipath_<category>_<action>` pattern.

---

Plan complete and saved to `docs/superpowers/plans/2026-04-16-cursor-full-integration.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
