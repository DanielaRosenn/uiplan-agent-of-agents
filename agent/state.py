"""State schema for UiPath Builder Agent."""

from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages


class ProjectState(TypedDict, total=False):
    """
    Complete state for UiPath Builder Agent.

    Tracks project metadata, design artifacts, generation state,
    and conversation flow across bootstrap and conversational modes.
    """

    # ── Core I/O ─────────────────────────────────────────
    messages: Annotated[list, add_messages]

    # ── Project metadata ──────────────────────────────────
    project_name: str
    project_path: str
    template_type: str  # dispatcher|performer|lrw
    git_repo_url: str

    # ── Mode tracking ─────────────────────────────────────
    mode: Literal["bootstrap", "conversational"]
    current_phase: Literal["ba", "sa", "hitl", "generation", "qa", "dev"]

    # ── Design artifacts ──────────────────────────────────
    pdd: dict  # Process Design Document (from BA)
    sdd: dict  # Solution Design Document (from SA)

    # ── Generation state ──────────────────────────────────
    artifacts: dict[str, str]  # relative_path → file_content
    active_skills: list[str]  # skills available for current context

    # ── BA clarification flow ─────────────────────────────
    needs_clarification: bool
    clarify_question: str
    clarification_answer: str

    # ── HITL flow ─────────────────────────────────────────
    requires_hitl: bool
    hitl_approved: bool
    hitl_feedback: str

    # ── QA validation ─────────────────────────────────────
    validation_errors: list[str]
    qa_iterations: int  # max 2 fix loops
    qa_report: dict

    # ── Deployment ────────────────────────────────────────
    orchestrator_tenant: str
    deployed_version: str

    # ── UiPath project context ────────────────────────────
    uipath_project: dict  # Parsed project.json
    uipath_workflows: list[str]  # List of .xaml files
    uipath_dependencies: dict  # Package dependencies

    # ── Tool execution tracking ───────────────────────────
    tool_calls_this_turn: int  # For max tool cap
    tool_results: list[dict]  # Accumulated tool results

    # ── Session metadata ──────────────────────────────────
    session_id: str  # Unique session ID
    memory_context: str  # Loaded memory content

    # ── Slash command state ───────────────────────────────
    pending_command: str  # Current slash command
    command_result: str  # Command output
