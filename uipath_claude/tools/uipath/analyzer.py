"""UiPath Workflow Analyzer tool."""
from langchain_core.tools import tool

from uipath_claude.tools.uipath.approval import check_cli_approval
from uipath_claude.tools.uipath.cli_runner import (
    format_cli_result,
    run_studio_package_analyze,
)


@tool
def workflow_analyzer_tool(project_path: str) -> str:
    """
    Run UiPath Workflow Analyzer on a project.

    Args:
        project_path: Path to UiPath project

    Returns:
        Analyzer results
    """
    allowed, message = check_cli_approval()
    if not allowed:
        return message

    try:
        proc = run_studio_package_analyze(project_path, timeout=120)
        return format_cli_result("uipath studio package analyze", proc)
    except Exception as exc:
        return f"Error running analyzer: {exc}"
