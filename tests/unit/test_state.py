"""Tests for ProjectState schema."""

from agent.state import ProjectState


def test_project_state_has_required_fields():
    """ProjectState should define all required fields."""
    # This will fail until we implement ProjectState
    state: ProjectState = {}

    # Core I/O
    assert "messages" in ProjectState.__annotations__
    assert "project_name" in ProjectState.__annotations__
    assert "mode" in ProjectState.__annotations__

    # Design artifacts
    assert "pdd" in ProjectState.__annotations__
    assert "sdd" in ProjectState.__annotations__

    # Generation state
    assert "artifacts" in ProjectState.__annotations__


def test_project_state_messages_uses_add_messages_reducer():
    """messages field should use add_messages reducer."""
    from langgraph.graph.message import add_messages
    from typing import get_args, Annotated

    msg_annotation = ProjectState.__annotations__["messages"]

    # Check if it's Annotated with add_messages
    assert hasattr(msg_annotation, "__metadata__")
    assert add_messages in msg_annotation.__metadata__
