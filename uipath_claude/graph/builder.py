"""Compile the conversational chat graph."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, START, StateGraph

from uipath_claude.graph.nodes.execute import make_execute_node
from uipath_claude.graph.nodes.route import make_route_node


def compile_chat_graph(
    skills: list[dict[str, Any]],
    *,
    select_skills_fn: Callable[[str], list[dict[str, Any]]],
    build_runtime_for_selected: Callable[[str, list[dict[str, Any]]], str],
    run_model: Callable[
        [list[dict[str, str]], str, bool], Awaitable[str]
    ],
    default_stream: bool = False,
    agentic_tools: list | None = None,
    model_name: str | None = None,
    region: str | None = None,
):
    """Build ``route`` → ``execute`` → ``END`` workflow.
    
    Args:
        skills: List of skill dictionaries
        select_skills_fn: Function to select skills for a user input
        build_runtime_for_selected: Function to build runtime context
        run_model: Function to call LLM (single-shot mode)
        default_stream: Whether to stream by default
        agentic_tools: Optional list of tools for agentic execution
        model_name: Model name for agentic execution
        region: AWS region for agentic execution
    
    Returns:
        Compiled LangGraph workflow
    """
    skills_by_name = {str(s["name"]): s for s in skills if s.get("name")}
    workflow = StateGraph(dict)
    workflow.add_node("route", make_route_node(select_skills_fn))
    workflow.add_node(
        "execute",
        make_execute_node(
            skills_by_name,
            build_runtime_for_selected,
            run_model,
            default_stream=default_stream,
            agentic_tools=agentic_tools,
            model_name=model_name,
            region=region,
        ),
    )
    workflow.add_edge(START, "route")
    workflow.add_edge("route", "execute")
    workflow.add_edge("execute", END)
    return workflow.compile()


def get_documentation_handler(
    *,
    model_name: str,
    region: str,
):
    """
    Get a documentation handler function for use outside the main graph.
    
    This allows the CLI or other entry points to handle documentation
    requests before entering the normal route->execute flow.
    
    Args:
        model_name: Bedrock model ID
        region: AWS region
        
    Returns:
        Async function that handles documentation requests
    """
    from uipath_claude.graph.nodes.documentation import handle_documentation_request
    
    async def handler(user_input: str, state: dict) -> dict:
        return await handle_documentation_request(
            user_input=user_input,
            state=state,
            model_name=model_name,
            region=region,
        )
    
    return handler
