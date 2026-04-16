"""AgenticExecutor system prompt contract."""

from uipath_claude.query.agentic_executor import AgenticExecutor


def test_system_prompt_references_approved_implementation_plan() -> None:
    ex = AgenticExecutor(model_name="anthropic.claude-3-sonnet-20240229-v1:0", region="us-east-1")
    text = ex._build_system_prompt("skill body", {})
    assert "Approved Implementation Plan" in text


def test_execute_loop_nudges_when_plan_present_but_no_tools() -> None:
    """Regression: executor must not exit immediately on prose-only first turn with a plan."""
    import inspect

    src = inspect.getsource(AgenticExecutor.execute)
    assert "plan_tool_nudges" in src
    assert "call tools now" in src.lower()
