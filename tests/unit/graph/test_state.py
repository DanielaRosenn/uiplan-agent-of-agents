"""Agent state typing smoke test."""

from uipath_claude.graph.state import AgentState


def test_agent_state_shape() -> None:
    state: AgentState = {
        "messages": [],
        "phase": "route",
        "selected_skill_names": [],
        "assistant_response": "",
        "pending_question": None,
    }
    assert state["phase"] == "route"
