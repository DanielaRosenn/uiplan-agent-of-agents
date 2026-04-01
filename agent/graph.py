"""LangGraph orchestrator for UiPath Builder Agent."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agent.state import ProjectState
from agent.nodes.conversational import conversational_agent
from agent.nodes.ba_persona import ba_persona
from agent.nodes.sa_persona import sa_persona
from agent.nodes.hitl_node import hitl_node
from agent.nodes.developer_node import developer_node
from agent.nodes.qa_node import qa_node


# ── Routing functions ──────────────────────────────────────────


def route_after_ba(state: ProjectState) -> str:
    """Route after BA: to SA if PDD is ready, or END for clarification."""
    if state.get("needs_clarification", False):
        # BA needs more info - return to user (END the current run)
        return END
    if state.get("pdd"):
        return "sa"
    return END


def route_after_sa(state: ProjectState) -> str:
    """Route after SA: to HITL if complex, otherwise straight to developer."""
    if state.get("requires_hitl", False):
        return "hitl"
    return "developer"


def route_after_hitl(state: ProjectState) -> str:
    """Route after HITL: to developer if approved, END if rejected."""
    if state.get("hitl_approved", False):
        return "developer"
    return END


def route_after_qa(state: ProjectState) -> str:
    """Route after QA: END if passed or max iterations, developer if errors."""
    errors = state.get("validation_errors", [])
    iterations = state.get("qa_iterations", 0)

    if not errors:
        return END  # All good
    if iterations >= 2:
        return END  # Max retries reached
    return "developer"  # Try to fix


def route_main(state: ProjectState) -> str:
    """
    Main routing from conversational agent.

    Routes to BA for bootstrap mode, stays in conversational otherwise.
    """
    if state.get("_should_end", False):
        return END

    mode = state.get("mode", "conversational")

    if mode == "bootstrap":
        return "ba"

    return "conversational"


# ── Build graph ─────────────────────────────────────────────────

builder = StateGraph(ProjectState)

# Add nodes
builder.add_node("conversational", conversational_agent)
builder.add_node("ba", ba_persona)
builder.add_node("sa", sa_persona)
builder.add_node("hitl", hitl_node)
builder.add_node("developer", developer_node)
builder.add_node("qa", qa_node)

# Set entry point
builder.set_entry_point("ba")

# Add edges
builder.add_conditional_edges("ba", route_after_ba, {
    "sa": "sa",
    END: END,
})

builder.add_conditional_edges("sa", route_after_sa, {
    "hitl": "hitl",
    "developer": "developer",
})

builder.add_conditional_edges("hitl", route_after_hitl, {
    "developer": "developer",
    END: END,
})

builder.add_edge("developer", "qa")

builder.add_conditional_edges("qa", route_after_qa, {
    "developer": "developer",
    END: END,
})

# Use MemorySaver for local development
checkpointer = MemorySaver()

# Compile graph with HITL interrupt support
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["hitl"],
)


# ── Conversational-only graph (for chat mode) ──────────────────


def route_conversational(state: ProjectState) -> str:
    """Route for conversational-only graph. Always stays in conversational or ends."""
    if state.get("_should_end", False):
        return END
    return "conversational"


conv_builder = StateGraph(ProjectState)
conv_builder.add_node("conversational", conversational_agent)
conv_builder.set_entry_point("conversational")
conv_builder.add_conditional_edges("conversational", route_conversational, {
    "conversational": "conversational",
    END: END,
})

conv_checkpointer = MemorySaver()
conversational_graph = conv_builder.compile(checkpointer=conv_checkpointer)
