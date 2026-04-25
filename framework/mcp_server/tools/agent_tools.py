"""Bootstrap, planner, intent classification, and agentic execution MCP tools."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.types import Tool, ToolAnnotations

def _ro(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True)


def _orchestration(title: str) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
    )


_BEDROCK_NOTE = (
    "Requires Amazon Bedrock access (UIPATH_CLAUDE_MODEL_HEAVY / "
    "UIPATH_CLAUDE_MODEL + AWS credentials in the configured region)."
)

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
            description=(
                "Run the full BA -> SA -> Developer -> QA bootstrap flow end "
                "to end, writing PDD, SDD, generated code, and a validation "
                "report under output_dir/docs and output_dir/. Long-running "
                "and destructive (mutates the project tree). " + _BEDROCK_NOTE
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "Natural-language description of what to build.",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Project root to write docs and code into (default: current dir).",
                    },
                },
                "required": ["user_request"],
            },
            annotations=_orchestration("Bootstrap full BA->SA->Dev->QA flow"),
        ),
        Tool(
            name="uipath_agent_plan",
            description=(
                "Run the planner agent: produces a structured plan and tool-call "
                "trace from a user request without touching the project. "
                "Read-only by intent but classified as orchestration because the "
                "underlying Bedrock model can pick destructive tools if "
                "configured. Use before uipath_agent_execute. " + _BEDROCK_NOTE
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_request": {
                        "type": "string",
                        "description": "Natural-language task to plan.",
                    },
                    "project_context": {
                        "type": "object",
                        "description": "Optional project context dict (paths, env, prior decisions).",
                    },
                },
                "required": ["user_request"],
            },
            annotations=_orchestration("Plan task (read-only intent)"),
        ),
        Tool(
            name="uipath_agent_execute",
            description=(
                "Run the agentic ReAct loop with the full skill-execution tool "
                "belt for a chosen skill. Destructive: can transitively call "
                "uipath_workflow_write_file, _install_package, _run, _deploy, "
                "etc. Use uipath_agent_plan first for a dry-run trace. "
                + _BEDROCK_NOTE
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task description for the agent to execute.",
                    },
                    "skill_name": {
                        "type": "string",
                        "description": "Skill to load as the agent's system prompt.",
                        "default": "uipath-rpa",
                    },
                    "max_iterations": {
                        "type": "integer",
                        "description": "Hard cap on ReAct iterations.",
                        "default": 25,
                    },
                    "project_context": {
                        "type": "object",
                        "description": "Optional project context dict passed to the executor.",
                    },
                },
                "required": ["task"],
            },
            annotations=_orchestration("Execute agentic ReAct loop"),
        ),
        Tool(
            name="uipath_agent_classify_intent",
            description=(
                "Classify a user message into one of: question, build, ambiguous, "
                "documentation. Read-only and cheap (no LLM call required). Use "
                "as a triage step before deciding between uipath_agent_plan, "
                "uipath_agent_execute, uipath_doc_query, or a library lookup."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "user_input": {
                        "type": "string",
                        "description": "Raw user message to classify.",
                    },
                },
                "required": ["user_input"],
            },
            annotations=_ro("Classify user intent"),
        ),
        Tool(
            name="uipath_agent_ba",
            description=(
                "Single-shot BA agent: turn free-form requirements into a PDD "
                "draft and return it as text (does NOT write the file). Pair "
                "with uipath_doc_write_doc to persist. " + _BEDROCK_NOTE
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "string",
                        "description": "Free-form requirements / user story.",
                    },
                },
                "required": ["requirements"],
            },
            annotations=_orchestration("Generate PDD (BA agent)"),
        ),
        Tool(
            name="uipath_agent_sa",
            description=(
                "Single-shot SA agent: turn a PDD into an SDD draft and return "
                "it as text (does NOT write the file). Pair with "
                "uipath_doc_write_doc to persist. " + _BEDROCK_NOTE
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pdd": {
                        "type": "string",
                        "description": "Existing PDD text to design from.",
                    },
                },
                "required": ["pdd"],
            },
            annotations=_orchestration("Generate SDD (SA agent)"),
        ),
    ]


def _model_region() -> tuple[str | None, str]:
    """Region for downstream callers; model id is resolved lazily by the routing helper."""
    region = os.environ.get("AWS_REGION", "us-east-1")
    return None, region


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
        skill_name = arguments.get("skill_name", "uipath-rpa")
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
