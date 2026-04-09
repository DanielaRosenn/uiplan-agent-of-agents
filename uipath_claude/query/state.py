"""State management for conversation and bootstrap flows."""
from typing import TypedDict, Optional, Any
from typing_extensions import NotRequired


class UiPathProjectContext(TypedDict):
    """UiPath project context information."""
    project_path: str
    project_name: str
    project_type: str
    has_project_json: bool
    dependencies: NotRequired[list[str]]
    activities: NotRequired[list[str]]


class ToolResult(TypedDict):
    """Tool execution result."""
    tool_name: str
    input: dict[str, Any]
    output: Any
    success: bool
    error: NotRequired[str]


class ProjectState(TypedDict):
    """State for agent conversation and bootstrap flows."""
    messages: list[dict[str, str]]
    current_step: str
    project_context: Optional[UiPathProjectContext]
    tool_results: list[ToolResult]
    session_id: str
    
    # Bootstrap flow specific
    pdd: NotRequired[str]
    sdd: NotRequired[str]
    code: NotRequired[str]
    validation: NotRequired[str]
    
    # Agent mode
    agent_mode: NotRequired[str]  # "conversational", "ba", "sa", "developer", "qa"
