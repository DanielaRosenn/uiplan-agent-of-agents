"""Test state management."""
from uipath_claude.query.state import ProjectState


def test_project_state_creation():
    """Test ProjectState can be created with required fields."""
    state = ProjectState(
        messages=[],
        current_step="init",
        project_context=None,
        tool_results=[],
        session_id="test-123",
    )
    
    assert state["messages"] == []
    assert state["current_step"] == "init"
    assert state["project_context"] is None
    assert state["tool_results"] == []
    assert state["session_id"] == "test-123"


def test_project_state_with_context():
    """Test ProjectState with UiPath project context."""
    from uipath_claude.query.state import UiPathProjectContext
    
    context = UiPathProjectContext(
        project_path="/path/to/project",
        project_name="TestProject",
        project_type="process",
        has_project_json=True,
    )
    
    state = ProjectState(
        messages=[],
        current_step="init",
        project_context=context,
        tool_results=[],
        session_id="test-456",
    )
    
    assert state["project_context"] == context
    assert state["project_context"]["project_name"] == "TestProject"
