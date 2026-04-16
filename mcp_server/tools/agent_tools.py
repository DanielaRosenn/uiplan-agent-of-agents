"""Bootstrap, planner, intent classification, and agentic execution MCP tools."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.types import Tool

from uipath_claude.query.agentic_executor import AgenticExecutor
from uipath_claude.query.bootstrap import run_bootstrap_flow
from uipath_claude.query.intent_classifier import classify_intent
from uipath_claude.query.planner import run_planner_agent
from uipath_claude.skills.loader import load_skill_content
from uipath_claude.tools.skill_execution_tools import get_skill_execution_tools


def get_agent_tools() -> list[Tool]:
    return [
        Tool(
            name="uipath_agent_bootstrap",
            description="Run BA -> SA -> Developer -> QA bootstrap flow (writes docs under output_dir)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {"type": "string"},
                    "output_dir": {"type": "string"},
                },
                "required": ["user_request"],
            },
        ),
        Tool(
            name="uipath_agent_plan",
            description="Read-only planner agent (Bedrock + planning tools)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {"type": "string"},
                    "project_context": {"type": "object"},
                },
                "required": ["user_request"],
            },
        ),
        Tool(
            name="uipath_agent_execute",
            description="Agentic ReAct loop with full skill execution tools (Bedrock required)",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "skill_name": {"type": "string", "default": "uipath-automation"},
                    "max_iterations": {"type": "integer", "default": 25},
                    "project_context": {"type": "object"},
                },
                "required": ["task"],
            },
        ),
        Tool(
            name="uipath_agent_classify_intent",
            description="Classify user intent (question/build/ambiguous/documentation)",
            inputSchema={
                "type": "object",
                "properties": {"user_input": {"type": "string"}},
                "required": ["user_input"],
            },
        ),
        Tool(
            name="uipath_agent_ba",
            description="Single-shot BA agent: produce PDD from requirements (Bedrock required)",
            inputSchema={
                "type": "object",
                "properties": {"requirements": {"type": "string"}},
                "required": ["requirements"],
            },
        ),
        Tool(
            name="uipath_agent_sa",
            description="Single-shot SA agent: produce SDD from PDD text (Bedrock required)",
            inputSchema={
                "type": "object",
                "properties": {"pdd": {"type": "string"}},
                "required": ["pdd"],
            },
        ),
    ]


def _model_region() -> tuple[str, str]:
    model = os.environ.get("UIPATH_CLAUDE_MODEL", "anthropic.claude-3-sonnet-20240229-v1:0")
    region = os.environ.get("AWS_REGION", "us-east-1")
    return model, region


async def call_agent_tool(name: str, arguments: dict[str, Any]) -> Any:
    model_name, region = _model_region()

    if name == "uipath_agent_bootstrap":
        out = Path(arguments.get("output_dir", ".")).resolve()
        result = await run_bootstrap_flow(arguments["user_request"], output_root=out)
        return {
            "paths": result["paths"],
            "pdd_preview": result["pdd"][:2000],
            "sdd_preview": result["sdd"][:2000],
            "code_preview": result["code"][:2000],
            "validation_preview": result["validation"][:2000],
        }

    if name == "uipath_agent_plan":
        result = await run_planner_agent(
            arguments["user_request"],
            project_context=arguments.get("project_context"),
            model_name=model_name,
            region=region,
        )
        return {
            "success": result.success,
            "final_response": result.final_response,
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_made,
            "error": result.error,
        }

    if name == "uipath_agent_execute":
        from mcp_server.tools.skill_tools import _get_registry

        registry = _get_registry()
        skill_name = arguments.get("skill_name", "uipath-automation")
        skill = registry.get_skill(skill_name)
        skill_content = load_skill_content(skill) if skill else ""

        executor = AgenticExecutor(model_name=model_name, region=region)
        tools = get_skill_execution_tools()
        ctx = arguments.get("project_context") if isinstance(arguments.get("project_context"), dict) else {}
        max_iter = arguments.get("max_iterations")
        result = await executor.execute(
            skill_content=skill_content,
            user_request=arguments["task"],
            tools=tools,
            project_context=ctx,
            skill_name=skill_name,
            max_iterations=int(max_iter) if max_iter is not None else None,
        )
        return {
            "success": result.success,
            "final_response": result.final_response,
            "iterations": result.iterations,
            "tool_calls": result.tool_calls_made,
            "files_written": result.files_written,
            "validation_status": result.validation_status,
            "error": result.error,
        }

    if name == "uipath_agent_classify_intent":
        intent, reason = classify_intent(arguments["user_input"])
        return {"intent": intent.value, "reason": reason}

    if name == "uipath_agent_ba":
        from uipath_claude.agents.ba import BAAgent
        from uipath_claude.query.agent_invoke import invoke_agent_llm
        from uipath_claude.query.engine_factory import create_conversation_engine_from_env

        engine = create_conversation_engine_from_env()
        ba = BAAgent()
        pdd = await invoke_agent_llm(engine, ba.get_system_prompt(), arguments["requirements"])
        return {"pdd": pdd}

    if name == "uipath_agent_sa":
        from uipath_claude.agents.sa import SAAgent
        from uipath_claude.query.agent_invoke import invoke_agent_llm
        from uipath_claude.query.engine_factory import create_conversation_engine_from_env

        engine = create_conversation_engine_from_env()
        sa = SAAgent()
        sdd = await invoke_agent_llm(
            engine,
            sa.get_system_prompt(),
            f"Create SDD based on this PDD:\n\n{arguments['pdd']}",
        )
        return {"sdd": sdd}

    raise ValueError(f"Unknown agent tool: {name}")
