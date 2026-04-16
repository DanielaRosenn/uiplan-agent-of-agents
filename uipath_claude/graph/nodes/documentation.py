"""Documentation creation node for the agent graph."""

from __future__ import annotations

from typing import Any

from uipath_claude.query.doc_need_detector import detect_documentation_need, DocNeedLevel
from uipath_claude.query.doc_router import route_to_doc_agent
from uipath_claude.query.ba_agent import run_ba_agent
from uipath_claude.query.solution_architect_agent import run_solution_architect_agent, DocType


async def handle_documentation_request(
    user_input: str,
    state: dict[str, Any],
    *,
    model_name: str,
    region: str,
) -> dict[str, Any]:
    """
    Handle a documentation request.
    
    This function:
    1. Detects documentation need
    2. Routes to appropriate agent (BA or SA)
    3. Runs the documentation agent
    4. Returns updated state
    
    Args:
        user_input: The user's request
        state: Current graph state
        model_name: Bedrock model ID
        region: AWS region
        
    Returns:
        Updated state dict with documentation results
    """
    doc_need = detect_documentation_need(user_input)
    
    new_state = {
        **state,
        "doc_need_level": doc_need.level.value,
        "doc_explicit_request": doc_need.explicit_request,
    }
    
    if doc_need.level == DocNeedLevel.NONE:
        new_state["doc_phase"] = "complete"
        return new_state
    
    route_decision = await route_to_doc_agent(
        user_input=user_input,
        recommended_docs=doc_need.recommended_docs,
        project_dir=state.get("project_path"),
    )
    
    if route_decision.agent == "none":
        new_state["doc_phase"] = "complete"
        return new_state
    
    new_state["doc_phase"] = "create"
    new_state["current_doc_type"] = route_decision.doc_type
    new_state["pending_docs"] = route_decision.next_docs
    
    project_context = {
        "project_path": state.get("project_path"),
        "session_id": state.get("session_id"),
    }
    
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
    
    created_docs = list(state.get("created_docs", []))
    if route_decision.doc_type:
        created_docs.append(route_decision.doc_type)
    
    new_state["created_docs"] = created_docs
    new_state["assistant_response"] = result.final_response
    new_state["doc_phase"] = "complete" if not route_decision.next_docs else "create"
    
    return new_state


def make_documentation_node(
    *,
    model_name: str,
    region: str,
):
    """
    Create a documentation node for the graph.
    
    Args:
        model_name: Bedrock model ID
        region: AWS region
        
    Returns:
        Async function suitable for use as a LangGraph node
    """
    async def documentation_node(state: dict[str, Any]) -> dict[str, Any]:
        """Documentation creation node."""
        messages = list(state.get("messages") or [])
        if not messages:
            return state
        
        last = messages[-1]
        if last.get("role") != "user":
            return state
        
        user_input = str(last.get("content", ""))
        
        return await handle_documentation_request(
            user_input=user_input,
            state=state,
            model_name=model_name,
            region=region,
        )
    
    return documentation_node
