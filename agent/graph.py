"""LangGraph orchestrator for UiPath Builder Agent."""

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
    # Check for termination signal
    if state.get("_should_end", False):
        return END

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
    END: END,
})

# Use MemorySaver for local development
checkpointer = MemorySaver()

# Compile graph
graph = builder.compile(
    checkpointer=checkpointer,
)
