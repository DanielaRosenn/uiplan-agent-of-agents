"""Planner prompt contract (no Bedrock calls)."""

import inspect

from uipath_claude.query import planner


def test_planner_prompt_documents_tool_actionable_plans() -> None:
    src = inspect.getsource(planner.run_planner_agent)
    assert "get_planning_tools" in src
    assert "ensure_project_structure" in src
    assert "write_file" in src or "UIPATH_FILE" in src
